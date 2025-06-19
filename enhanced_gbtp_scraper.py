# -*- coding: utf-8 -*-
"""
경북테크노파크(GBTP) Enhanced 스크래퍼
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

class EnhancedGbtpScraper(StandardTableScraper):
    """경북테크노파크(GBTP) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.gbtp.or.kr"
        self.list_url = "https://www.gbtp.or.kr/user/board.do?bbsId=BBSMSTR_000000000021"
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        
        # JavaScript 기반 사이트이므로 특별 처리 필요
        self.detail_urls = {}  # 상세 페이지 URL 매핑
        
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성"""
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&pageIndex={page_num}"
    
    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱"""
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> list:
        """사이트별 특화된 파싱 로직"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 테이블 찾기
        table = soup.find('table')
        if not table:
            logger.warning("테이블을 찾을 수 없습니다")
            return announcements
        
        # tbody 찾기
        tbody = table.find('tbody')
        if not tbody:
            logger.warning("tbody를 찾을 수 없습니다")
            return announcements
        
        rows = tbody.find_all('tr')
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for row in rows:
            try:
                cells = row.find_all(['td', 'th'])
                if len(cells) < 4:
                    continue
                
                # 공고명 링크 찾기 (보통 2번째 셀에 있음)
                title_cell = cells[1]
                link_elem = title_cell.find('a')
                
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                if not title:
                    continue
                
                # 번호 (1번째 셀) - 먼저 추출
                number_cell = cells[0]
                number = number_cell.get_text(strip=True)
                
                # 임시 row_data 생성
                row_data = {'number': number}
                
                # JavaScript 함수에서 상세 페이지 파라미터 추출
                onclick = link_elem.get('onclick', '')
                detail_url = self._extract_detail_url(onclick, title, row_data)
                
                if not detail_url:
                    logger.warning(f"상세 URL을 찾을 수 없습니다: {title}")
                    continue
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'number': number
                }
                
                # 추가 정보 추출
                if len(cells) >= 3:
                    # 공고일 (3번째 셀)
                    date_cell = cells[2]
                    announcement['date'] = date_cell.get_text(strip=True)
                
                if len(cells) >= 4:
                    # 접수기간 (4번째 셀)
                    period_cell = cells[3]
                    announcement['period'] = period_cell.get_text(strip=True)
                
                if len(cells) >= 5:
                    # 접수상태 (5번째 셀)
                    status_cell = cells[4]
                    announcement['status'] = status_cell.get_text(strip=True)
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱 완료: {title}")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def _extract_detail_url(self, onclick: str, title: str, row_data: dict = None) -> str:
        """JavaScript onclick에서 상세 페이지 URL 생성"""
        try:
            # JavaScript 함수에서 파라미터 추출
            if onclick:
                # 일반적인 패턴들 시도
                patterns = [
                    r"javascript:fn_egov_select_bbs\('(\d+)'\)",
                    r"javascript:view\('(\d+)'\)",
                    r"javascript:goDetail\('(\d+)'\)",
                    r"javascript:boardDetail\('([^']+)'\)",
                    r"'(\d+)'",
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, onclick)
                    if match:
                        param = match.group(1)
                        detail_url = f"{self.base_url}/user/boardDetail.do?bbsId=BBSMSTR_000000000021&nttId={param}"
                        return detail_url
            
            # onclick이 없거나 패턴을 찾지 못한 경우, 다른 방법 시도
            # 행 번호를 사용
            if row_data and 'number' in row_data:
                number = row_data['number']
                if number.isdigit():
                    detail_url = f"{self.base_url}/user/boardDetail.do?bbsId=BBSMSTR_000000000021&nttId={number}"
                    return detail_url
            
            # 기본 URL 반환 (파라미터 없이)
            detail_url = f"{self.base_url}/user/boardDetail.do?bbsId=BBSMSTR_000000000021"
            return detail_url
            
        except Exception as e:
            logger.error(f"상세 URL 추출 실패: {e}")
            return None
    
    def _get_page_announcements(self, page_num: int) -> list:
        """페이지별 공고 목록 가져오기 - GBTP 특화"""
        page_url = self.get_list_url(page_num)
        
        # 세션 유지를 위한 초기 요청
        response = self.get_page(page_url)
        
        if not response:
            logger.warning(f"페이지 {page_num} 응답을 가져올 수 없습니다")
            return []
        
        # 페이지가 에러 상태거나 잘못된 경우 감지
        if response.status_code >= 400:
            logger.warning(f"페이지 {page_num} HTTP 에러: {response.status_code}")
            return []
        
        announcements = self.parse_list_page(response.text)
        
        # GBTP 특성상 JavaScript로 상세 페이지 로드하므로, 
        # 실제 상세 페이지 URL을 동적으로 찾아야 함
        announcements = self._resolve_detail_urls(announcements, response.text)
        
        # 추가 마지막 페이지 감지 로직
        if not announcements and page_num > 1:
            logger.info(f"페이지 {page_num}에 공고가 없어 마지막 페이지로 판단됩니다")
        
        return announcements
    
    def _resolve_detail_urls(self, announcements: list, html_content: str) -> list:
        """상세 페이지 URL 해결"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 실제 데이터나 숨겨진 폼에서 상세 페이지 정보 추출
        for i, announcement in enumerate(announcements):
            try:
                # 번호를 기반으로 실제 상세 페이지 URL 생성
                number = announcement.get('number', '')
                if number.isdigit():
                    # 실제 게시글 번호 기반 URL (추측)
                    detail_url = f"{self.base_url}/user/boardDetail.do?bbsId=BBSMSTR_000000000021&nttId={number}"
                    announcement['url'] = detail_url
                    
            except Exception as e:
                logger.error(f"상세 URL 해결 실패: {e}")
                
        return announcements
    
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
        # GBTP 상세 페이지의 본문 추출
        
        content_text = ""
        
        # 1. 테이블에서 "내용" 행 찾기
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    header = cells[0].get_text(strip=True)
                    if header == "내용":
                        content_cell = cells[1]
                        # 내용 셀에서 HTML을 마크다운으로 변환
                        content_html = str(content_cell)
                        content_text = self.h.handle(content_html)
                        logger.debug("테이블 '내용' 행에서 본문 추출")
                        break
            if content_text:
                break
        
        # 2. figure 태그 찾기 (이미지나 첨부 콘텐츠)
        if not content_text:
            figures = soup.find_all('figure')
            if figures:
                for figure in figures:
                    content_html = str(figure)
                    content_text += self.h.handle(content_html) + "\n\n"
                logger.debug("figure 태그에서 본문 추출")
        
        # 3. 긴 텍스트가 있는 셀 찾기
        if not content_text:
            for table in tables:
                cells = table.find_all(['td', 'th'])
                for cell in cells:
                    text = cell.get_text(strip=True)
                    if len(text) > 50:  # 충분히 긴 텍스트
                        # 헤더가 아닌 경우만
                        parent_row = cell.find_parent('tr')
                        if parent_row:
                            row_cells = parent_row.find_all(['td', 'th'])
                            if len(row_cells) >= 2 and cell == row_cells[-1]:  # 마지막 셀
                                content_html = str(cell)
                                content_text = self.h.handle(content_html)
                                logger.debug("긴 텍스트 셀에서 본문 추출")
                                break
                if content_text:
                    break
        
        # 4. 전체 페이지에서 본문 영역 찾기
        if not content_text:
            # div나 다른 콘텐츠 영역 찾기
            content_areas = [
                'div.content',
                'div.board-content',
                'div.view-content',
                'div[class*="content"]'
            ]
            
            for selector in content_areas:
                area = soup.select_one(selector)
                if area:
                    content_html = str(area)
                    content_text = self.h.handle(content_html)
                    logger.debug(f"{selector}에서 본문 추출")
                    break
        
        if not content_text:
            logger.warning("본문 내용을 찾을 수 없습니다")
            content_text = "본문을 찾을 수 없습니다."
        
        return content_text.strip()
    
    def _extract_attachments(self, soup: BeautifulSoup) -> list:
        """첨부파일 정보 추출"""
        attachments = []
        
        # 테이블에서 "첨부파일" 행 찾기
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    header = cells[0].get_text(strip=True)
                    if header == "첨부파일":
                        attachment_cell = cells[1]
                        
                        # 첨부파일 링크 찾기
                        links = attachment_cell.find_all('a')
                        for link in links:
                            try:
                                href = link.get('href', '')
                                link_text = link.get_text(strip=True)
                                
                                # JavaScript 링크 처리
                                if 'javascript:' in href:
                                    # onclick에서 실제 다운로드 URL 추출
                                    onclick = link.get('onclick', '')
                                    file_url = self._extract_download_url(onclick, link_text)
                                else:
                                    # 직접 링크
                                    if href.startswith('/'):
                                        file_url = self.base_url + href
                                    else:
                                        file_url = urljoin(self.base_url, href)
                                
                                if file_url and link_text:
                                    attachment = {
                                        'name': link_text,
                                        'url': file_url
                                    }
                                    attachments.append(attachment)
                                    logger.debug(f"첨부파일 발견: {link_text}")
                                    
                            except Exception as e:
                                logger.error(f"첨부파일 처리 중 오류: {e}")
                                continue
        
        logger.info(f"{len(attachments)}개 첨부파일 발견")
        return attachments
    
    def _extract_download_url(self, onclick: str, filename: str) -> str:
        """JavaScript onclick에서 다운로드 URL 추출"""
        try:
            # GBTP 사이트의 파일 다운로드 패턴 분석
            if onclick:
                # 일반적인 패턴들을 시도
                patterns = [
                    r"fn_egov_downFile\('([^']+)',\s*'([^']+)'\)",
                    r"downloadFile\('([^']+)',\s*'([^']+)'\)",
                    r"fileDown\('([^']+)',\s*'([^']+)'\)",
                    r"download\('([^']+)',\s*'([^']+)'\)",
                    r"fn_egov_downFile\('([^']+)'\)",
                    r"downloadFile\('([^']+)'\)",
                    r"fileDown\('([^']+)'\)",
                    r"download\('([^']+)'\)",
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, onclick, re.IGNORECASE)
                    if match:
                        groups = match.groups()
                        if len(groups) >= 2:
                            # 두 개 파라미터가 있는 경우
                            param1, param2 = groups[0], groups[1]
                            download_url = f"{self.base_url}/user/downloadFile.do?atchFileId={param1}&fileSn={param2}"
                        else:
                            # 하나 파라미터가 있는 경우
                            param = groups[0]
                            download_url = f"{self.base_url}/user/downloadFile.do?fileId={param}"
                        
                        logger.debug(f"다운로드 URL 생성: {download_url}")
                        return download_url
            
            # JavaScript 패턴을 찾지 못한 경우, 직접 href 확인
            # (이미 _extract_attachments에서 처리됨)
            
            return None
            
        except Exception as e:
            logger.error(f"다운로드 URL 추출 실패: {e}")
            return None
    
    def get_page(self, url: str, **kwargs) -> requests.Response:
        """페이지 가져오기 - GBTP 특화 헤더 추가"""
        try:
            # GBTP 사이트 접근을 위한 특별 헤더
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
        """파일 다운로드 - GBTP 특화"""
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
GbtpScraper = EnhancedGbtpScraper