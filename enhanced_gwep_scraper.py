# -*- coding: utf-8 -*-
"""
강원경제진흥원(GWEP) 전용 스크래퍼 - 향상된 버전
"""

import re
import os
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
from enhanced_base_scraper import StandardTableScraper
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class EnhancedGwepScraper(StandardTableScraper):
    """강원경제진흥원(GWEP) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://www.gwep.or.kr"
        self.list_url = "https://www.gwep.or.kr/bbs/board.php?bo_table=gw_sub21"
        
        # 사이트 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        self.delay_between_pages = 2
        
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - 설정 주입과 Fallback 패턴"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: 사이트 특화 로직
        if page_num == 1:
            return self.list_url
        else:
            # GWEP 특화 페이지네이션 파라미터
            return f"{self.list_url}&page={page_num}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: 사이트 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """GWEP 특화된 파싱 로직 - 실제 HTML 구조 기반"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # GWEP 실제 구조: .tbl_head01.tbl_wrap > table
        tbl_wrap = soup.find('div', class_='tbl_head01')
        if not tbl_wrap:
            tbl_wrap = soup.find('div', class_='tbl_wrap')
        
        if not tbl_wrap:
            logger.warning("tbl_head01 또는 tbl_wrap 클래스를 찾을 수 없습니다")
            # Fallback: 일반 테이블 찾기
            table = soup.find('table')
        else:
            table = tbl_wrap.find('table')
        
        if not table:
            logger.warning("테이블을 찾을 수 없습니다")
            return announcements
        
        tbody = table.find('tbody')
        if not tbody:
            tbody = table
        
        rows = tbody.find_all('tr')
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 5:  # 번호, 제목, 글쓴이, 조회, 날짜
                    continue
                
                # 각 셀 정보 추출 (GWEP 실제 구조)
                num_cell = cells[0]  # td_num2
                title_cell = cells[1]  # td_subject
                author_cell = cells[2]  # td_name
                views_cell = cells[3]  # td_num
                date_cell = cells[4]  # td_datetime
                
                # 제목 영역에서 링크 찾기
                title_div = title_cell.find('div', class_='bo_tit')
                if not title_div:
                    # Fallback: 직접 링크 찾기
                    title_link = title_cell.find('a')
                    if title_link:
                        title = title_link.get_text(strip=True)
                        href = title_link.get('href', '')
                        detail_url = urljoin(self.base_url, href)
                        category = ""
                    else:
                        continue
                else:
                    # 제목 링크 찾기 (카테고리 링크 제외)
                    title_links = title_div.find_all('a')
                    detail_link = None
                    category = ""
                    title = ""
                    
                    if len(title_links) == 1:
                        # 카테고리가 없는 경우
                        detail_link = title_links[0]
                        title = detail_link.get_text(strip=True)
                    elif len(title_links) >= 2:
                        # 카테고리와 제목이 모두 있는 경우
                        category_link = title_links[0]
                        if 'bo_cate_link' in category_link.get('class', []):
                            category = category_link.get_text(strip=True)
                            detail_link = title_links[1]
                        else:
                            detail_link = title_links[0]
                        title = detail_link.get_text(strip=True)
                    
                    if not detail_link or not title:
                        continue
                    
                    # 상세 페이지 URL 생성
                    href = detail_link.get('href', '')
                    if not href:
                        continue
                    
                    detail_url = urljoin(self.base_url, href)
                
                # 첨부파일 여부 확인 (여러 패턴 시도)
                has_attachment = False
                # 패턴 1: Font Awesome 아이콘
                if title_div and title_div.find('i', class_='fa-download'):
                    has_attachment = True
                # 패턴 2: 일반적인 첨부파일 표시
                elif title_cell.find(text=re.compile(r'첨부|파일')):
                    has_attachment = True
                # 패턴 3: 이미지나 다른 아이콘
                elif title_cell.find('img', alt=re.compile(r'첨부|파일')):
                    has_attachment = True
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'category': category,
                    'has_attachment': has_attachment
                }
                
                # 추가 정보 추출
                try:
                    # 번호
                    num_text = num_cell.get_text(strip=True)
                    if num_text and num_text != '공지':
                        announcement['number'] = num_text
                    
                    # 작성자
                    author = author_cell.get_text(strip=True)
                    if author:
                        announcement['author'] = author
                    
                    # 조회수
                    views = views_cell.get_text(strip=True)
                    if views and views.isdigit():
                        announcement['views'] = int(views)
                    
                    # 날짜
                    date = date_cell.get_text(strip=True)
                    if date:
                        announcement['date'] = date
                        
                except Exception as e:
                    logger.warning(f"추가 정보 추출 중 오류: {e}")
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱 완료: {title[:50]}...")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str, url: str = None) -> Dict[str, Any]:
        """상세 페이지 파싱 - GWEP 그누보드 구조 기반"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        result = {
            'content': '',
            'attachments': []
        }
        
        # URL에서 wr_id 추출 (첨부파일 다운로드에 필요)
        wr_id = None
        if url:
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            wr_id = query_params.get('wr_id', [None])[0]
            logger.debug(f"URL에서 wr_id 추출: {wr_id}")
        
        # GWEP 특화: 본문 영역 찾기
        content_area = soup.find('div', id='bo_v_con')
        
        if content_area:
            # bo_v_con 영역에서 본문 추출
            try:
                result['content'] = self.h.handle(str(content_area))
                logger.debug("bo_v_con 영역에서 본문 추출 완료")
            except Exception as e:
                logger.error(f"HTML to Markdown 변환 실패: {e}")
                result['content'] = content_area.get_text(separator='\n', strip=True)
        else:
            # Fallback: 다양한 선택자로 본문 찾기
            content_selectors = [
                '#bo_v_atc',
                '.board-read-content',
                '.content',
                '.read-content',
                '#content',
                '.board-content'
            ]
            
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    try:
                        result['content'] = self.h.handle(str(content_elem))
                        logger.debug(f"{selector} 선택자로 본문 추출 완료")
                        break
                    except Exception as e:
                        logger.error(f"HTML to Markdown 변환 실패: {e}")
                        result['content'] = content_elem.get_text(separator='\n', strip=True)
                        break
            else:
                # 최종 Fallback: 전체 페이지에서 추출
                logger.warning("본문 영역을 찾을 수 없어 전체 페이지에서 추출")
                # 불필요한 요소들 제거
                for tag in soup(['script', 'style', 'nav', 'header', 'footer', '.navigation', '.sidebar']):
                    tag.decompose()
                result['content'] = soup.get_text(separator='\n', strip=True)
        
        # 첨부파일 찾기 (wr_id 전달)
        result['attachments'] = self._extract_attachments(soup, wr_id)
        
        logger.info(f"상세 페이지 파싱 완료 - 내용길이: {len(result['content'])}, 첨부파일: {len(result['attachments'])}")
        return result
    
    def _extract_attachments(self, soup: BeautifulSoup, wr_id: str = None) -> List[Dict[str, Any]]:
        """첨부파일 추출 - GWEP 그누보드 구조 기반"""
        attachments = []
        
        if not wr_id:
            logger.warning("wr_id가 없어 첨부파일 다운로드 URL을 생성할 수 없습니다")
            return attachments
        
        # GWEP 실제 구조: 첨부파일 영역 찾기
        file_section = soup.find('section', id='bo_v_file')
        
        if file_section:
            file_list = file_section.find('ul')
            if file_list:
                file_items = file_list.find_all('li')
                
                for idx, item in enumerate(file_items):
                    try:
                        # 파일명 추출
                        file_link = item.find('a', class_='view_file_download')
                        if not file_link:
                            continue
                        
                        file_name = file_link.find('strong')
                        if file_name:
                            file_name = file_name.get_text(strip=True)
                        else:
                            file_name = file_link.get_text(strip=True)
                        
                        if not file_name:
                            file_name = f"attachment_{idx}"
                        
                        # GWEP의 실제 다운로드 URL 패턴
                        # download.php?bo_table=gw_sub21&wr_id=3134&no=0
                        file_url = f"{self.base_url}/bbs/download.php?bo_table=gw_sub21&wr_id={wr_id}&no={idx}"
                        
                        attachment = {
                            'name': file_name,
                            'url': file_url,
                            'wr_id': wr_id,
                            'file_no': idx,
                            'type': 'get_download'  # GET 요청임을 표시
                        }
                        
                        # 파일 크기 정보 추출 (있는 경우)
                        file_size_text = item.get_text()
                        size_match = re.search(r'\(([^)]+)\)', file_size_text)
                        if size_match:
                            attachment['size'] = size_match.group(1)
                        
                        attachments.append(attachment)
                        logger.debug(f"첨부파일 발견: {file_name} (wr_id: {wr_id}, no: {idx})")
                        
                    except Exception as e:
                        logger.error(f"첨부파일 추출 중 오류: {e}")
                        continue
        
        # Fallback: 다른 패턴으로 첨부파일 찾기
        if not attachments:
            logger.debug("bo_v_file에서 첨부파일을 찾지 못해 다른 패턴 시도")
            
            # 다운로드 링크 직접 찾기
            download_links = soup.find_all('a', href=re.compile(r'download\.php'))
            for idx, link in enumerate(download_links):
                href = link.get('href', '')
                file_name = link.get_text(strip=True)
                
                if not file_name:
                    file_name = f"attachment_{idx}"
                
                file_url = urljoin(self.base_url, href)
                
                # URL에서 파라미터 추출
                parsed_url = urlparse(file_url)
                query_params = parse_qs(parsed_url.query)
                file_no = query_params.get('no', [idx])[0]
                
                attachment = {
                    'name': file_name,
                    'url': file_url,
                    'wr_id': wr_id,
                    'file_no': file_no,
                    'type': 'get_download'
                }
                
                attachments.append(attachment)
                logger.debug(f"Fallback 첨부파일 발견: {file_name}")
        
        logger.info(f"총 {len(attachments)}개 첨부파일 발견 (wr_id: {wr_id})")
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment_info: dict = None) -> bool:
        """GWEP 특화 파일 다운로드 - GET 요청 처리"""
        try:
            logger.info(f"파일 다운로드 시작: {url}")
            
            # GWEP의 GET 다운로드 처리
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
GwepScraper = EnhancedGwepScraper