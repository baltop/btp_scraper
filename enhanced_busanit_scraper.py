# -*- coding: utf-8 -*-
"""
부산정보산업진흥원(BUSANIT) Enhanced 스크래퍼 - 표준 HTML 테이블 기반
"""

import requests
from bs4 import BeautifulSoup
import re
import logging
import os
from urllib.parse import urljoin, parse_qs, urlparse
from enhanced_base_scraper import StandardTableScraper
import time
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class EnhancedBusanitScraper(StandardTableScraper):
    """부산정보산업진흥원(BUSANIT) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        
        # 향상된 헤더 설정 (차단 방지)
        self.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.session.headers.update(self.headers)
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "http://www.busanit.or.kr/board/"
        self.list_url = "http://www.busanit.or.kr/board/list.asp?bcode=notice"
        
        # 사이트 특화 설정
        self.verify_ssl = False  # HTTP 사이트
        self.default_encoding = 'utf-8'
        self.timeout = 60  # 타임아웃 증가
        self.delay_between_requests = 2  # 요청 간 지연 증가
        
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - GET 파라미터 방식"""
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&ipage={page_num}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - BUSANIT 사이트 특화"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # BUSANIT 사이트 테이블 구조 분석
        # 테이블의 tbody 영역에서 데이터 행 찾기
        table = soup.find('table')
        if not table:
            logger.warning("테이블을 찾을 수 없습니다")
            return announcements
        
        tbody = table.find('tbody')
        if not tbody:
            # tbody가 없는 경우 table에서 직접 tr 찾기
            tbody = table
        
        rows = tbody.find_all('tr')
        logger.info(f"BUSANIT 테이블에서 {len(rows)}개 행 발견")
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 4:  # 번호, 제목, 날짜, 조회수
                    continue
                
                # 제목 셀에서 링크 찾기
                title_cell = cells[1]  # 두 번째 셀이 제목
                link_elem = title_cell.find('a')
                
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                if not title:
                    continue
                
                # URL 구성
                href = link_elem.get('href', '')
                detail_url = urljoin(self.base_url, href)
                
                announcement = {
                    'title': title,
                    'url': detail_url
                }
                
                # 추가 메타 정보 추출
                self._extract_meta_info(cells, announcement)
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱: {title[:50]}...")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 BUSANIT 공고 파싱 완료")
        return announcements
    
    def _extract_meta_info(self, cells: list, announcement: Dict[str, Any]):
        """추가 메타 정보 추출"""
        try:
            # 번호 (첫 번째 셀)
            if len(cells) > 0:
                number_text = cells[0].get_text(strip=True)
                if number_text.isdigit():
                    announcement['number'] = number_text
            
            # 날짜 (세 번째 셀)
            if len(cells) > 2:
                date_text = cells[2].get_text(strip=True)
                announcement['date'] = date_text
            
            # 조회수 (네 번째 셀)
            if len(cells) > 3:
                views_text = cells[3].get_text(strip=True)
                if views_text.isdigit():
                    announcement['views'] = views_text
            
            # 공고 진행 상태 확인 (제목 셀에 이미지가 있는 경우)
            title_cell = cells[1]
            status_img = title_cell.find('img')
            if status_img:
                alt_text = status_img.get('alt', '')
                if alt_text:
                    announcement['status'] = alt_text
                    
        except Exception as e:
            logger.debug(f"메타 정보 추출 중 오류: {e}")
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        result = {
            'content': '',
            'attachments': []
        }
        
        try:
            # 페이지 제목
            page_title = soup.find('title')
            title_text = page_title.get_text() if page_title else ''
            
            # 본문 내용 추출
            content_text = self._extract_content(soup, title_text)
            result['content'] = content_text
            
            # 첨부파일 추출
            attachments = self._extract_attachments(soup)
            result['attachments'] = attachments
            
            logger.info(f"BUSANIT 상세 페이지 파싱 완료 - 내용: {len(content_text)}자, 첨부파일: {len(attachments)}개")
            
        except Exception as e:
            logger.error(f"BUSANIT 상세 페이지 파싱 실패: {e}")
        
        return result
    
    def _extract_content(self, soup: BeautifulSoup, title_text: str) -> str:
        """본문 내용 추출"""
        content_parts = []
        
        # 제목 추가
        if title_text:
            clean_title = title_text.replace('사업공고│알림마당│부산정보산업진흥원', '').strip()
            if clean_title:
                content_parts.append(f"# {clean_title}\n")
        
        # 상세 페이지 테이블에서 정보 추출
        detail_table = soup.find('table')
        if detail_table:
            rows = detail_table.find_all('tr')
            
            for row in rows:
                cells = row.find_all(['th', 'td'])
                if len(cells) == 2:
                    # 제목과 날짜 정보
                    header = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    if header and value and '첨부파일' not in header:
                        content_parts.append(f"**{header}**: {value}")
                
                elif len(cells) == 1:
                    # 본문 내용이 있는 셀
                    cell_content = cells[0]
                    
                    # 이미지가 있는 경우
                    if cell_content.find('img'):
                        # HTML을 마크다운으로 변환
                        cell_html = str(cell_content)
                        markdown_content = self.h.handle(cell_html)
                        content_parts.append(markdown_content)
                    else:
                        # 텍스트만 있는 경우
                        text_content = cell_content.get_text(strip=True)
                        if text_content and len(text_content) > 50:  # 의미있는 내용만
                            content_parts.append(text_content)
        
        if not content_parts or len(content_parts) <= 1:
            # 폴백: 전체 페이지에서 의미있는 텍스트 추출
            logger.debug("테이블에서 내용을 찾을 수 없어 전체 페이지에서 추출")
            
            # 네비게이션 및 불필요한 요소 제거
            for tag in soup.find_all(['script', 'style', 'nav', 'header', 'footer']):
                tag.decompose()
            
            # 본문 영역만 추출
            main_content = soup.find('article') or soup.find('main') or soup.find('body')
            if main_content:
                paragraphs = main_content.find_all('p')
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if text and len(text) > 20:
                        content_parts.append(text)
        
        return '\n\n'.join(content_parts)
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """첨부파일 추출"""
        attachments = []
        
        # BUSANIT 사이트 첨부파일 패턴 분석
        # 다운로드 링크는 /intranet/include/download.asp 형태
        download_links = soup.find_all('a', href=re.compile(r'download\.asp'))
        
        for link in download_links:
            try:
                href = link.get('href', '')
                
                # 파일명 추출 (링크 텍스트에서)
                file_name = link.get_text(strip=True)
                
                # 다운로드 이미지가 있는 경우 제거
                if '다운로드 이미지' in file_name:
                    file_name = file_name.replace('다운로드 이미지', '').strip()
                
                if not file_name:
                    # URL에서 파일명 추출 시도
                    parsed_url = urlparse(href)
                    query_params = parse_qs(parsed_url.query)
                    if 'originFile' in query_params:
                        file_name = query_params['originFile'][0]
                    elif 'file' in query_params:
                        file_name = query_params['file'][0]
                
                # 파일 확장자 확인
                if file_name and any(ext in file_name.lower() for ext in ['.pdf', '.hwp', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.ppt', '.pptx']):
                    file_url = urljoin(self.base_url, href)
                    
                    attachment = {
                        'name': file_name,
                        'url': file_url
                    }
                    attachments.append(attachment)
                    logger.debug(f"첨부파일 발견: {file_name}")
                
            except Exception as e:
                logger.debug(f"첨부파일 링크 처리 중 오류: {e}")
                continue
        
        logger.info(f"{len(attachments)}개 첨부파일 발견")
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment_info: Dict[str, Any] = None) -> bool:
        """파일 다운로드 - BUSANIT 사이트 특화"""
        try:
            logger.info(f"파일 다운로드 시작: {url}")
            
            # 다운로드 헤더 설정
            download_headers = self.headers.copy()
            download_headers['Referer'] = self.list_url
            
            response = self.session.get(
                url, 
                headers=download_headers, 
                stream=True, 
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            
            # 실제 파일명 추출 (Content-Disposition 헤더에서)
            actual_filename = self._extract_filename_from_response(response, save_path)
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
    
    def _extract_filename_from_response(self, response: requests.Response, default_path: str) -> str:
        """응답에서 실제 파일명 추출"""
        content_disposition = response.headers.get('Content-Disposition', '')
        
        if content_disposition:
            # filename 파라미터 추출
            filename_match = re.search(r'filename[^;=\n]*=(([\'"]).*?\2|[^;\n]*)', content_disposition)
            if filename_match:
                filename = filename_match.group(1).strip('"\'')
                
                # URL 디코딩
                try:
                    from urllib.parse import unquote
                    filename = unquote(filename, encoding='utf-8')
                    
                    # 파일명 정리
                    filename = self.sanitize_filename(filename)
                    save_dir = os.path.dirname(default_path)
                    return os.path.join(save_dir, filename)
                except:
                    pass
        
        return default_path


# 하위 호환성을 위한 별칭
BusanitScraper = EnhancedBusanitScraper