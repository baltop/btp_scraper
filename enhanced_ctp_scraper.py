# -*- coding: utf-8 -*-
"""
충남테크노파크(CTP) 전용 스크래퍼 - 향상된 버전
"""

import re
import os
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
from enhanced_base_scraper import StandardTableScraper
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class EnhancedCTPScraper(StandardTableScraper):
    """충남테크노파크(CTP) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://ctp.or.kr"
        self.list_url = "https://ctp.or.kr/business/data.do"
        
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
        # CTP 특화 페이지네이션 파라미터
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}?pn={page_num}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: 사이트 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """CTP 특화된 파싱 로직 - Bootstrap 반응형 테이블 기반"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # CTP 특화: Bootstrap 반응형 테이블 구조
        # 실제 테이블 클래스는 'w-100 mb4'
        table = soup.find('table', class_='w-100 mb4')
        
        if not table:
            # Fallback: 다른 테이블 패턴 시도
            table = soup.find('table')
            if not table:
                logger.warning("테이블을 찾을 수 없습니다")
                return announcements
            else:
                logger.info("일반 table 태그로 테이블 발견")
        
        tbody = table.find('tbody')
        if not tbody:
            tbody = table
        
        rows = tbody.find_all('tr')
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 7:  # 번호, 제목, 마감일, 첨부, 작성자, 작성일, 조회
                    continue
                
                # 각 셀 정보 추출 (CTP 실제 구조)
                num_cell = cells[0]  # 번호
                title_cell = cells[1]  # 제목 (링크 포함)
                deadline_cell = cells[2]  # 마감일
                attachment_cell = cells[3]  # 첨부파일 아이콘
                author_cell = cells[4]  # 작성자
                date_cell = cells[5]  # 작성일
                views_cell = cells[6]  # 조회수
                
                # 제목 링크 찾기
                title_link = title_cell.find('a')
                if not title_link:
                    continue
                
                # 제목과 URL 추출
                title = title_link.get_text(strip=True)
                href = title_link.get('href', '')
                
                if not href or not title:
                    continue
                
                # 상세 페이지 URL 생성 (상대 URL)
                detail_url = urljoin(self.base_url + '/business/', href)
                
                # 첨부파일 여부 확인
                has_attachment = False
                if attachment_cell.find('img'):
                    has_attachment = True
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'category': '',  # CTP는 카테고리 구분 없음
                    'has_attachment': has_attachment
                }
                
                # 추가 정보 추출
                try:
                    # 번호
                    num_text = num_cell.get_text(strip=True)
                    if num_text and num_text.isdigit():
                        announcement['number'] = int(num_text)
                    
                    # 마감일
                    deadline_text = deadline_cell.get_text(strip=True)
                    if deadline_text:
                        # 마감일과 상태 분리
                        deadline_spans = deadline_cell.find_all('span')
                        if len(deadline_spans) >= 1:
                            deadline = deadline_spans[0].get_text(strip=True)
                            announcement['deadline'] = deadline
                        if len(deadline_spans) >= 2:
                            status = deadline_spans[1].get_text(strip=True)
                            announcement['status'] = status
                    
                    # 작성자
                    author = author_cell.get_text(strip=True)
                    if author:
                        announcement['author'] = author
                    
                    # 작성일
                    date = date_cell.get_text(strip=True)
                    if date:
                        announcement['date'] = date
                    
                    # 조회수
                    views = views_cell.get_text(strip=True)
                    if views and views.isdigit():
                        announcement['views'] = int(views)
                    
                    # seq 추출 (첨부파일 다운로드에 필요)
                    if href:
                        seq_match = re.search(r'seq=(\d+)', href)
                        if seq_match:
                            announcement['seq'] = seq_match.group(1)
                            
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
        """상세 페이지 파싱 - CTP 구조 기반"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        result = {
            'content': '',
            'attachments': []
        }
        
        # URL에서 seq 추출 (첨부파일 다운로드에 필요)
        seq = None
        if url:
            seq_match = re.search(r'seq=(\d+)', url)
            if seq_match:
                seq = seq_match.group(1)
                logger.debug(f"URL에서 seq 추출: {seq}")
        
        # CTP 특화: 본문 영역 찾기
        content_parts = []
        
        # 제목 추출
        title_elem = soup.find('h3')
        if title_elem:
            title = title_elem.get_text(strip=True)
            content_parts.append(f"# {title}")
        
        # 메타 정보 추출 (작성자, 작성일, 조회수)
        meta_list = soup.find('ul', class_='clearfix')
        if meta_list:
            meta_items = meta_list.find_all('li')
            meta_info = []
            for item in meta_items:
                text = item.get_text(strip=True)
                if text and not text.startswith('첨부파일'):
                    meta_info.append(text)
            
            if meta_info:
                content_parts.append("## 메타 정보")
                content_parts.extend([f"- {info}" for info in meta_info])
        
        # 본문 영역 찾기
        # CTP는 다양한 구조를 가질 수 있으므로 여러 선택자 시도
        content_selectors = [
            '.content_area',
            '.board_view',
            '.view_content',
            '#content',
            '.detail_content'
        ]
        
        content_found = False
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                try:
                    # HTML to Markdown 변환
                    content_md = self.h.handle(str(content_elem))
                    content_parts.append("## 본문")
                    content_parts.append(content_md)
                    content_found = True
                    logger.debug(f"{selector} 선택자로 본문 추출 완료")
                    break
                except Exception as e:
                    logger.error(f"HTML to Markdown 변환 실패: {e}")
                    content_parts.append("## 본문")
                    content_parts.append(content_elem.get_text(separator='\n', strip=True))
                    content_found = True
                    break
        
        # 본문이 없으면 전체 페이지에서 추출
        if not content_found:
            logger.warning("본문 영역을 찾을 수 없어 전체 페이지에서 추출")
            # 불필요한 요소들 제거
            for tag in soup(['script', 'style', 'nav', 'header', 'footer', '.navigation', '.sidebar']):
                tag.decompose()
            
            # 메인 콘텐츠 영역 찾기
            main_content = soup.find('div', class_='content') or soup.find('div', id='content')
            if main_content:
                content_parts.append("## 본문")
                content_parts.append(main_content.get_text(separator='\n', strip=True))
            else:
                content_parts.append("## 본문")
                content_parts.append(soup.get_text(separator='\n', strip=True))
        
        result['content'] = '\n\n'.join(content_parts)
        
        # 첨부파일 찾기
        result['attachments'] = self._extract_attachments(soup)
        
        logger.info(f"상세 페이지 파싱 완료 - 내용길이: {len(result['content'])}, 첨부파일: {len(result['attachments'])}")
        return result
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """첨부파일 추출 - CTP 구조 기반"""
        attachments = []
        
        # CTP 첨부파일 패턴: /boardfiledownload.do?seq=숫자
        download_links = soup.find_all('a', href=re.compile(r'/boardfiledownload\.do\?seq='))
        
        for idx, link in enumerate(download_links):
            try:
                href = link.get('href', '')
                file_name = link.get_text(strip=True)
                
                if not file_name:
                    file_name = f"attachment_{idx}"
                
                # 절대 URL 생성
                file_url = urljoin(self.base_url, href)
                
                # URL에서 seq 추출
                seq_match = re.search(r'seq=(\d+)', href)
                file_seq = seq_match.group(1) if seq_match else str(idx)
                
                attachment = {
                    'name': file_name,
                    'url': file_url,
                    'seq': file_seq,
                    'type': 'get_download'  # GET 요청임을 표시
                }
                
                attachments.append(attachment)
                logger.debug(f"첨부파일 발견: {file_name} (seq: {file_seq})")
                
            except Exception as e:
                logger.error(f"첨부파일 추출 중 오류: {e}")
                continue
        
        # Fallback: 파일 확장자가 포함된 링크 찾기
        if not attachments:
            logger.debug("직접 다운로드 링크를 찾지 못해 파일 확장자 기반 검색")
            
            file_links = soup.find_all('a', text=re.compile(r'\.(pdf|hwp|doc|docx|xls|xlsx|ppt|pptx|zip|rar)$', re.IGNORECASE))
            for idx, link in enumerate(file_links):
                href = link.get('href', '')
                if href:
                    file_name = link.get_text(strip=True)
                    file_url = urljoin(self.base_url, href)
                    
                    attachment = {
                        'name': file_name,
                        'url': file_url,
                        'seq': str(idx),
                        'type': 'direct_link'
                    }
                    
                    attachments.append(attachment)
                    logger.debug(f"Fallback 첨부파일 발견: {file_name}")
        
        logger.info(f"총 {len(attachments)}개 첨부파일 발견")
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment_info: dict = None) -> bool:
        """CTP 특화 파일 다운로드 - GET 요청 처리"""
        try:
            logger.info(f"파일 다운로드 시작: {url}")
            
            # CTP의 GET 다운로드 처리
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
CTPScraper = EnhancedCTPScraper