# -*- coding: utf-8 -*-
"""
SEOUL RNBD (서울시 R&BD) Enhanced 스크래퍼 - JSP 기반 표준 테이블 구조
URL: https://seoul.rnbd.kr/client/c030100/c030100_00.jsp
"""

import requests
from bs4 import BeautifulSoup
import re
import logging
import os
import time
from urllib.parse import urljoin, parse_qs, urlparse, unquote
from enhanced_base_scraper import StandardTableScraper
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class EnhancedSeoulRnbdScraper(StandardTableScraper):
    """서울시 R&BD 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        
        # 서울 R&BD 사이트 설정
        self.base_url = "https://seoul.rnbd.kr"
        self.list_url = "https://seoul.rnbd.kr/client/c030100/c030100_00.jsp"
        self.detail_base_url = "https://seoul.rnbd.kr/client/c030100/c030100_04.jsp"
        self.download_base_url = "https://seoul.rnbd.kr/common/cm04o01_new.jsp"
        
        # 사이트 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        
        # JSP 세션 관리
        self._session_initialized = False
    
    def _initialize_session(self):
        """JSP 세션 초기화"""
        if self._session_initialized:
            return True
            
        try:
            logger.info("SEOUL RNBD 세션 초기화 중...")
            response = self.session.get(self.list_url, timeout=self.timeout)
            response.raise_for_status()
            
            # JSESSIONID 확인
            jsessionid = None
            for cookie in self.session.cookies:
                if cookie.name == 'JSESSIONID':
                    jsessionid = cookie.value
                    break
            
            if jsessionid:
                logger.info(f"JSESSIONID 획득: {jsessionid[:10]}...")
            
            self._session_initialized = True
            logger.info("SEOUL RNBD 세션 초기화 완료")
            return True
            
        except Exception as e:
            logger.error(f"세션 초기화 실패: {e}")
            return False
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 목록 URL 생성"""
        if page_num == 1:
            return self.list_url
        return f"{self.list_url}?sField=&sWord=&sFlag=&cPage={page_num}"
    
    def fetch_page_content(self, url: str) -> str:
        """페이지 내용 가져오기"""
        if not self._initialize_session():
            return ""
            
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = self.default_encoding
            return response.text
            
        except Exception as e:
            logger.error(f"페이지 가져오기 실패 {url}: {e}")
            return ""
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        try:
            # 사업공고 테이블 찾기
            table = soup.find('table', {'class': '사업공고'})
            if not table:
                # 다른 테이블 선택자 시도
                table = soup.find('table')
                if not table:
                    logger.warning("공고 테이블을 찾을 수 없습니다")
                    return announcements
            
            tbody = table.find('tbody')
            if not tbody:
                tbody = table
            
            rows = tbody.find_all('tr')
            logger.info(f"테이블에서 {len(rows)}개 행 발견")
            
            for row in rows:
                try:
                    cells = row.find_all('td')
                    if len(cells) < 4:  # 최소 4개 셀 필요 (번호, 제목, 기간, 상태)
                        continue
                    
                    # 제목 셀에서 링크 찾기 (보통 두 번째 셀)
                    title_cell = cells[1] if len(cells) > 1 else cells[0]
                    link_elem = title_cell.find('a')
                    
                    if not link_elem:
                        continue
                    
                    title = link_elem.get_text(strip=True)
                    href = link_elem.get('href', '')
                    
                    if not title or not href:
                        continue
                    
                    # URL 파싱하여 seqNo 추출
                    # href는 /client/c030100/ 디렉토리 기준 상대 경로
                    base_path = "https://seoul.rnbd.kr/client/c030100/"
                    detail_url = urljoin(base_path, href)
                    
                    parsed_url = urlparse(href)
                    query_params = parse_qs(parsed_url.query)
                    seq_no = query_params.get('seqNo', [''])[0]
                    
                    if not seq_no:
                        continue
                    
                    announcement = {
                        'title': title,
                        'url': detail_url,
                        'seq_no': seq_no
                    }
                    
                    # 추가 정보 추출
                    if len(cells) >= 3:
                        # 모집기간 (세 번째 셀)
                        period_text = cells[2].get_text(strip=True)
                        if period_text:
                            announcement['period'] = period_text
                    
                    if len(cells) >= 4:
                        # 상태 (네 번째 셀)
                        status_text = cells[3].get_text(strip=True)
                        if status_text:
                            announcement['status'] = status_text
                    
                    if len(cells) >= 5:
                        # 조회수 (다섯 번째 셀)
                        views_text = cells[4].get_text(strip=True)
                        if views_text:
                            announcement['views'] = views_text
                    
                    announcements.append(announcement)
                    logger.debug(f"공고 파싱: {title[:50]}...")
                    
                except Exception as e:
                    logger.debug(f"행 파싱 중 오류: {e}")
                    continue
            
            logger.info(f"{len(announcements)}개 SEOUL RNBD 공고 파싱 완료")
            
        except Exception as e:
            logger.error(f"목록 페이지 파싱 실패: {e}")
        
        return announcements
    
    def get_detail_content(self, announcement: Dict[str, Any]) -> Dict[str, Any]:
        """상세 페이지 내용 가져오기"""
        detail_url = announcement.get('url', '')
        if not detail_url:
            return {'content': '', 'attachments': []}
        
        try:
            html_content = self.fetch_page_content(detail_url)
            if not html_content:
                return {'content': '', 'attachments': []}
            
            return self.parse_detail_page(html_content, announcement)
            
        except Exception as e:
            logger.error(f"상세 페이지 가져오기 실패: {e}")
            return {'content': '', 'attachments': []}
    
    def parse_detail_page(self, html_content: str, announcement: Dict[str, Any]) -> Dict[str, Any]:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        result = {
            'content': '',
            'attachments': []
        }
        
        try:
            # 본문 내용 추출
            content_text = self._extract_content(soup)
            result['content'] = content_text
            
            # 첨부파일 추출
            attachments = self._extract_attachments(soup, announcement)
            result['attachments'] = attachments
            
            logger.info(f"SEOUL RNBD 상세 페이지 파싱 완료 - 내용: {len(content_text)}자, 첨부파일: {len(attachments)}개")
            
        except Exception as e:
            logger.error(f"SEOUL RNBD 상세 페이지 파싱 실패: {e}")
        
        return result
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """본문 내용 추출"""
        content_parts = []
        
        try:
            # JSP 테이블 구조에서 본문 찾기
            content_selectors = [
                'table td',  # 일반적인 JSP 테이블 구조
                '.content',
                '.board-content',
                'div.content',
                'td'
            ]
            
            # 테이블의 모든 행을 확인하여 본문 찾기
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    for cell in cells:
                        text = cell.get_text(strip=True)
                        # 긴 텍스트가 있는 셀을 본문으로 간주
                        if text and len(text) > 50:
                            # HTML을 마크다운으로 변환
                            cell_html = str(cell)
                            markdown_content = self.h.handle(cell_html)
                            content_parts.append(markdown_content)
            
            # 결과가 없으면 폴백 방법 사용
            if not content_parts:
                for selector in content_selectors:
                    elements = soup.select(selector)
                    for element in elements:
                        text = element.get_text(strip=True)
                        if text and len(text) > 30:
                            content_parts.append(text)
                        if len(content_parts) >= 3:  # 충분한 내용을 찾으면 중단
                            break
                    if content_parts:
                        break
            
        except Exception as e:
            logger.error(f"본문 추출 중 오류: {e}")
        
        return '\n\n'.join(content_parts[:5])  # 최대 5개 섹션
    
    def _extract_attachments(self, soup: BeautifulSoup, announcement: Dict[str, Any]) -> List[Dict[str, Any]]:
        """첨부파일 추출"""
        attachments = []
        seq_no = announcement.get('seq_no', '')
        
        try:
            # 첨부파일 테이블 행 찾기
            attachment_patterns = [
                '첨부파일',
                '첨부',
                '파일',
                'attachment',
                'file'
            ]
            
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    row_text = row.get_text()
                    
                    # 첨부파일 관련 행인지 확인
                    is_attachment_row = any(pattern in row_text for pattern in attachment_patterns)
                    
                    if is_attachment_row:
                        # 이 행에서 링크 찾기
                        links = row.find_all('a')
                        for i, link in enumerate(links):
                            try:
                                href = link.get('href', '')
                                text = link.get_text(strip=True)
                                
                                # 파일 다운로드 링크인지 확인
                                if 'cm04o01_new.jsp' in href or any(ext in text.lower() for ext in ['.pdf', '.hwp', '.doc', '.xls', '.zip', '.jpg', '.png']):
                                    # 다운로드 URL 구성
                                    if href.startswith('/'):
                                        download_url = self.base_url + href
                                    elif href.startswith('http'):
                                        download_url = href
                                    else:
                                        # 상대 경로 처리
                                        download_url = f"{self.download_base_url}?menuCd=m030100&seqNo={seq_no}&attNo={i+1}"
                                    
                                    attachment = {
                                        'name': text if text else f'첨부파일_{i+1}',
                                        'url': download_url,
                                        'seq_no': seq_no,
                                        'att_no': str(i+1)
                                    }
                                    
                                    # 파일 크기 정보가 있으면 추출
                                    size_match = re.search(r'\(([0-9,]+(?:\.[0-9]+)?(?:KB|MB|GB))\)', row_text)
                                    if size_match:
                                        attachment['size'] = size_match.group(1)
                                    
                                    attachments.append(attachment)
                                    logger.debug(f"첨부파일 발견: {text}")
                                    
                            except Exception as e:
                                logger.debug(f"첨부파일 링크 처리 중 오류: {e}")
                                continue
            
            logger.info(f"{len(attachments)}개 첨부파일 발견")
            
        except Exception as e:
            logger.error(f"첨부파일 추출 중 오류: {e}")
        
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment_info: Dict[str, Any] = None) -> bool:
        """파일 다운로드"""
        try:
            logger.info(f"파일 다운로드 시도: {attachment_info.get('name', 'unknown') if attachment_info else 'unknown'}")
            
            response = self.session.get(url, stream=True, timeout=120)
            response.raise_for_status()
            
            # Content-Type 확인
            content_type = response.headers.get('Content-Type', '')
            logger.info(f"Content-Type: {content_type}")
            
            # HTML 응답인지 확인 (에러 페이지일 수 있음)
            if 'text/html' in content_type:
                logger.warning("HTML 응답 수신 - 다운로드 실패 가능성")
                response_text = response.text[:500]
                if 'error' in response_text.lower() or '오류' in response_text:
                    logger.warning(f"에러 응답: {response_text}")
                    return False
            
            # 파일 저장
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(save_path)
            if file_size > 0:
                logger.info(f"다운로드 완료: {save_path} ({file_size:,} bytes)")
                return True
            else:
                logger.warning("다운로드된 파일이 비어있음")
                os.remove(save_path)
                return False
                
        except Exception as e:
            logger.warning(f"파일 다운로드 실패: {e}")
            return False


# 하위 호환성을 위한 별칭
SeoulRnbdScraper = EnhancedSeoulRnbdScraper