# -*- coding: utf-8 -*-
"""
경기테크노파크(GTP) Enhanced 스크래퍼
"""

import requests
from bs4 import BeautifulSoup
import os
import time
import re
import logging
from urllib.parse import urljoin, unquote, parse_qs, urlparse
from enhanced_base_scraper import StandardTableScraper
import json

logger = logging.getLogger(__name__)

class EnhancedGtpScraper(StandardTableScraper):
    """경기테크노파크(GTP) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://pms.gtp.or.kr"
        self.list_url = "https://pms.gtp.or.kr/web/business/webBusinessList.do"
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성"""
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        if page_num == 1:
            return self.list_url
        else:
            # 표준 페이지네이션 패턴 추측
            return f"{self.list_url}?page={page_num}"
    
    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱"""
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> list:
        """사이트별 특화된 파싱 로직"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 데이터 테이블 찾기 - 여러 테이블 중에서 올바른 것 찾기
        tables = soup.find_all('table')
        logger.debug(f"총 {len(tables)}개 테이블 발견")
        
        table = None
        for i, t in enumerate(tables):
            # 헤더에 "No", "공고 제목" 등이 있는 테이블 찾기
            header_row = t.find('tr')
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
                logger.debug(f"테이블 {i} 헤더: {headers}")
                
                # "No"와 "공고 제목"이 포함된 테이블이 데이터 테이블
                if any('No' in h for h in headers) and any('제목' in h for h in headers):
                    table = t
                    logger.info(f"데이터 테이블 발견: 테이블 {i}")
                    break
        
        if not table:
            logger.warning("데이터 테이블을 찾을 수 없습니다")
            return announcements
        
        # tbody 찾기
        tbody = table.find('tbody')
        if not tbody:
            logger.warning("tbody를 찾을 수 없습니다")
            # tbody가 없는 경우 table에서 직접 tr 찾기
            rows = table.find_all('tr')
        else:
            rows = tbody.find_all('tr')
        
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        # 디버깅을 위해 첫 번째 행의 HTML 저장
        if rows:
            with open('debug_first_row.html', 'w', encoding='utf-8') as f:
                f.write(str(rows[0]))
        
        for i, row in enumerate(rows):
            try:
                cells = row.find_all(['td', 'th'])
                logger.debug(f"행 {i}: {len(cells)}개 셀 발견")
                
                if len(cells) < 6:  # No, 제목, 사업유형, 지역, 주최기관, 접수기간
                    logger.debug(f"행 {i}: 셀 수가 부족함 ({len(cells)}개)")
                    continue
                
                # 번호 (1번째 셀)
                number_cell = cells[0]
                number = number_cell.get_text(strip=True)
                
                # 공고명 링크 찾기 (2번째 셀)
                title_cell = cells[1]
                link_elem = title_cell.find('a')
                
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                if not title:
                    continue
                
                # 상세 페이지 URL 추출
                href = link_elem.get('href', '')
                logger.debug(f"링크 href: {href}, 제목: {title}")
                
                if href and href != '#none':
                    if href.startswith('/'):
                        detail_url = self.base_url + href
                    else:
                        detail_url = urljoin(self.base_url, href)
                else:
                    # href가 #none인 경우, JavaScript나 다른 방법으로 URL 추출 시도
                    onclick = link_elem.get('onclick', '')
                    logger.debug(f"onclick 속성: {onclick}")
                    detail_url = self._extract_detail_url_from_onclick(onclick, number)
                
                # href가 #none이더라도 일단 진행 (번호로 URL 추측)
                if not detail_url:
                    # 번호를 기반으로 URL 생성
                    if number.isdigit():
                        detail_url = f"{self.base_url}/web/business/webBusinessView.do?b_idx={number}"
                    else:
                        logger.warning(f"상세 URL을 찾을 수 없습니다: {title}")
                        continue
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'number': number
                }
                
                # 추가 정보 추출
                if len(cells) >= 3:
                    # 사업유형 (3번째 셀)
                    type_cell = cells[2]
                    announcement['type'] = type_cell.get_text(strip=True)
                
                if len(cells) >= 4:
                    # 지역 (4번째 셀)
                    region_cell = cells[3]
                    announcement['region'] = region_cell.get_text(strip=True)
                
                if len(cells) >= 5:
                    # 주최기관 (5번째 셀)
                    org_cell = cells[4]
                    announcement['organization'] = org_cell.get_text(strip=True)
                
                if len(cells) >= 6:
                    # 접수기간 (6번째 셀)
                    period_cell = cells[5]
                    announcement['period'] = period_cell.get_text(strip=True)
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱 완료: {title}")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def _extract_detail_url_from_onclick(self, onclick: str, number: str) -> str:
        """onclick 속성에서 상세 페이지 URL 추출"""
        try:
            if onclick:
                # GTP 사이트 특화 패턴들
                patterns = [
                    r"fn_goView\('([^']+)'\)",  # fn_goView('172045')
                    r"goView\('([^']+)'\)",
                    r"viewDetail\('([^']+)'\)",
                    r"location\.href='([^']+)'",
                    r"location='([^']+)'",
                    r"window\.open\('([^']+)'",
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, onclick)
                    if match:
                        param = match.group(1)
                        logger.debug(f"onclick에서 파라미터 추출: {param}")
                        
                        # 숫자인 경우 b_idx로 사용
                        if param.isdigit():
                            detail_url = f"{self.base_url}/web/business/webBusinessView.do?b_idx={param}"
                            return detail_url
                        # URL인 경우 직접 사용
                        elif param.startswith('/'):
                            return self.base_url + param
                        else:
                            return urljoin(self.base_url, param)
            
            # onclick이 없거나 패턴을 찾지 못한 경우
            # 번호를 기반으로 추측
            if number.isdigit():
                detail_url = f"{self.base_url}/web/business/webBusinessView.do?b_idx={number}"
                return detail_url
            
            return None
            
        except Exception as e:
            logger.error(f"onclick URL 추출 실패: {e}")
            return None
    
    def parse_detail_page(self, html_content: str) -> dict:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 내용 추출
        content = self._extract_content(soup)
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup)
        
        return {
            'content': content,
            'attachments': attachments
        }
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """본문 내용 추출"""
        content_text = ""
        
        # 1. 제목 추출
        title_elem = soup.find('h3')
        if title_elem:
            title = title_elem.get_text(strip=True)
            content_text += f"# {title}\n\n"
        
        # 2. 메타 정보 테이블 추출
        meta_info = []
        dl_elements = soup.find_all('dl')
        for dl in dl_elements:
            dt_elements = dl.find_all('dt')
            dd_elements = dl.find_all('dd')
            
            for dt, dd in zip(dt_elements, dd_elements):
                key = dt.get_text(strip=True)
                value = dd.get_text(strip=True)
                if key and value:
                    meta_info.append(f"**{key}**: {value}")
        
        if meta_info:
            content_text += "\n".join(meta_info) + "\n\n"
        
        # 3. 본문 내용 추출 - 여러 방법 시도
        content_areas = [
            'div.board_view_content',
            'div.view_content',
            'div.content',
            'div[class*="content"]'
        ]
        
        main_content = ""
        for selector in content_areas:
            area = soup.select_one(selector)
            if area:
                main_content = self.h.handle(str(area))
                logger.debug(f"{selector}에서 본문 추출")
                break
        
        # 4. 본문을 찾지 못한 경우, 이미지가 포함된 영역 찾기
        if not main_content:
            # 이미지가 있는 모든 p 태그 영역 찾기
            img_paragraphs = soup.find_all('p')
            img_content = []
            
            for p in img_paragraphs:
                if p.find('img'):
                    img_html = str(p)
                    img_content.append(self.h.handle(img_html))
            
            if img_content:
                main_content = "\n\n".join(img_content)
                logger.debug("이미지 포함 영역에서 본문 추출")
        
        # 5. 여전히 본문이 없으면 전체 페이지에서 긴 텍스트 찾기
        if not main_content:
            all_paragraphs = soup.find_all(['p', 'div'])
            for elem in all_paragraphs:
                text = elem.get_text(strip=True)
                if len(text) > 100:  # 충분히 긴 텍스트
                    main_content = self.h.handle(str(elem))
                    logger.debug("긴 텍스트 영역에서 본문 추출")
                    break
        
        content_text += main_content
        
        if not content_text.strip():
            logger.warning("본문 내용을 찾을 수 없습니다")
            content_text = "본문을 찾을 수 없습니다."
        
        return content_text.strip()
    
    def _extract_attachments(self, soup: BeautifulSoup) -> list:
        """첨부파일 정보 추출"""
        attachments = []
        
        # 첨부파일 영역 찾기 - dl/dt/dd 구조
        attachment_areas = soup.find_all('dl')
        
        for dl in attachment_areas:
            dt_elements = dl.find_all('dt')
            dd_elements = dl.find_all('dd')
            
            for dt, dd in zip(dt_elements, dd_elements):
                dt_text = dt.get_text(strip=True)
                
                # "첨부파일"이라는 텍스트가 포함된 경우
                if '첨부파일' in dt_text:
                    # dd에서 링크 찾기
                    links = dd.find_all('a')
                    for link in links:
                        try:
                            href = link.get('href', '')
                            link_text = link.get_text(strip=True)
                            
                            if href and link_text:
                                # 상대 경로를 절대 경로로 변환
                                if href.startswith('/'):
                                    file_url = self.base_url + href
                                else:
                                    file_url = urljoin(self.base_url, href)
                                
                                attachment = {
                                    'name': link_text,
                                    'url': file_url
                                }
                                attachments.append(attachment)
                                logger.debug(f"첨부파일 발견: {link_text}")
                                
                        except Exception as e:
                            logger.error(f"첨부파일 처리 중 오류: {e}")
                            continue
        
        # 위에서 찾지 못한 경우, 모든 링크에서 파일 확장자가 있는 것들 찾기
        if not attachments:
            all_links = soup.find_all('a')
            file_patterns = [
                r'\.hwp$', r'\.pdf$', r'\.doc$', r'\.docx$',
                r'\.xls$', r'\.xlsx$', r'\.ppt$', r'\.pptx$',
                r'\.zip$', r'\.txt$'
            ]
            
            for link in all_links:
                href = link.get('href', '')
                link_text = link.get_text(strip=True)
                
                # URL이나 링크 텍스트에서 파일 확장자 확인
                if any(re.search(pattern, href, re.IGNORECASE) for pattern in file_patterns) or \
                   any(re.search(pattern, link_text, re.IGNORECASE) for pattern in file_patterns):
                    
                    if href and link_text:
                        if href.startswith('/'):
                            file_url = self.base_url + href
                        else:
                            file_url = urljoin(self.base_url, href)
                        
                        attachment = {
                            'name': link_text,
                            'url': file_url
                        }
                        attachments.append(attachment)
                        logger.debug(f"파일 확장자로 첨부파일 발견: {link_text}")
        
        logger.info(f"{len(attachments)}개 첨부파일 발견")
        return attachments
    
    def get_page(self, url: str, **kwargs) -> requests.Response:
        """페이지 가져오기 - GTP 특화 헤더 추가"""
        try:
            # GTP 사이트 접근을 위한 헤더
            headers = self.headers.copy()
            headers.update({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            })
            
            # 기본 옵션들
            options = {
                'verify': self.verify_ssl,
                'timeout': self.timeout,
                'headers': headers,
                **kwargs
            }
            
            response = self.session.get(url, **options)
            
            # 인코딩 처리
            self._fix_encoding(response)
            
            return response
            
        except Exception as e:
            logger.error(f"페이지 가져오기 실패 {url}: {e}")
            return None
    
    def download_file(self, url: str, save_path: str, attachment_info: dict = None) -> bool:
        """파일 다운로드 - GTP 특화"""
        try:
            logger.info(f"파일 다운로드 시작: {url}")
            
            # 다운로드 헤더 설정
            download_headers = self.headers.copy()
            download_headers['Referer'] = self.base_url
            
            response = self.session.get(
                url, 
                headers=download_headers, 
                stream=True, 
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            
            # 실제 파일명 추출
            actual_filename = self._extract_filename(response, save_path)
            if actual_filename != save_path:
                save_path = actual_filename
            
            # 파일 저장
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(save_path)
            logger.info(f"다운로드 완료: {save_path} ({file_size:,} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"파일 다운로드 실패 {url}: {e}")
            return False

# 하위 호환성을 위한 별칭
GtpScraper = EnhancedGtpScraper