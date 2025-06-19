# -*- coding: utf-8 -*-
"""
한국테크노파크진흥회 Enhanced 스크래퍼
"""

import requests
from bs4 import BeautifulSoup
import os
import time
import re
import logging
from urllib.parse import urljoin, unquote
from enhanced_base_scraper import StandardTableScraper

logger = logging.getLogger(__name__)

class EnhancedTechnoparkScraper(StandardTableScraper):
    """한국테크노파크진흥회 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "http://www.technopark.kr"
        self.list_url = "http://www.technopark.kr/businessboard"
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성"""
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.base_url}/index.php?mid=businessboard&page={page_num}"
    
    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱"""
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> list:
        """사이트별 특화된 파싱 로직"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 테이블 찾기 - 여러 선택자 시도
        table = None
        for selector in ['table']:
            table = soup.find('table')
            if table:
                logger.debug(f"테이블을 {selector} 선택자로 찾음")
                break
        
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
                if len(cells) < 3:
                    continue
                
                # 제목 링크 찾기 (보통 3번째 셀에 있음)
                title_cell = cells[2] if len(cells) > 2 else cells[1]
                link_elem = title_cell.find('a')
                
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                if not title:
                    continue
                
                # URL 구성
                href = link_elem.get('href', '')
                if href.startswith('/'):
                    detail_url = self.base_url + href
                else:
                    detail_url = urljoin(self.base_url, href)
                
                announcement = {
                    'title': title,
                    'url': detail_url
                }
                
                # 추가 정보 추출
                if len(cells) >= 4:
                    # 작성자 (4번째 셀)
                    writer_cell = cells[3]
                    announcement['writer'] = writer_cell.get_text(strip=True)
                
                if len(cells) >= 5:
                    # 등록일 (5번째 셀)
                    date_cell = cells[4]
                    announcement['date'] = date_cell.get_text(strip=True)
                
                if len(cells) >= 6:
                    # 조회수 (6번째 셀)
                    views_cell = cells[5]
                    announcement['views'] = views_cell.get_text(strip=True)
                
                if len(cells) >= 2:
                    # 지역 (2번째 셀)
                    region_cell = cells[1]
                    announcement['region'] = region_cell.get_text(strip=True)
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱 완료: {title}")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
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
        # 여러 선택자 시도
        content_selectors = [
            'div.board_view',
            'div.view_content',
            'div.content',
            'div[class*="content"]',
            'div[class*="view"]'
        ]
        
        content_area = None
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        # 선택자로 찾지 못한 경우 테이블 기반 검색
        if not content_area:
            # 테이블에서 본문 찾기
            tables = soup.find_all('table')
            for table in tables:
                # 본문이 포함된 셀 찾기 (긴 텍스트가 있는 셀)
                cells = table.find_all(['td', 'th'])
                for cell in cells:
                    text = cell.get_text(strip=True)
                    if len(text) > 100:  # 충분히 긴 텍스트
                        content_area = cell
                        logger.debug("테이블 셀에서 본문 찾음")
                        break
                if content_area:
                    break
        
        if not content_area:
            logger.warning("본문 영역을 찾을 수 없습니다")
            return "본문을 찾을 수 없습니다."
        
        # HTML을 마크다운으로 변환
        content_html = str(content_area)
        markdown_content = self.h.handle(content_html)
        
        return markdown_content
    
    def _extract_attachments(self, soup: BeautifulSoup) -> list:
        """첨부파일 정보 추출"""
        attachments = []
        
        # 첨부파일 링크 찾기
        attachment_links = []
        
        # 일반적인 첨부파일 패턴들
        file_patterns = [
            r'\.hwp$',
            r'\.pdf$',
            r'\.doc$',
            r'\.docx$',
            r'\.xls$',
            r'\.xlsx$',
            r'\.ppt$',
            r'\.pptx$',
            r'\.zip$',
            r'\.txt$'
        ]
        
        # 모든 링크 검사
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            link_text = link.get_text(strip=True)
            
            # 파일 다운로드 링크 패턴 확인
            if any(re.search(pattern, href, re.IGNORECASE) for pattern in file_patterns):
                attachment_links.append(link)
            elif 'download' in href.lower() or 'file' in href.lower():
                attachment_links.append(link)
            elif any(re.search(pattern, link_text, re.IGNORECASE) for pattern in file_patterns):
                attachment_links.append(link)
        
        # 첨부파일 정보 구성
        for link in attachment_links:
            try:
                href = link.get('href', '')
                link_text = link.get_text(strip=True)
                
                # URL 구성
                if href.startswith('/'):
                    file_url = self.base_url + href
                elif href.startswith('?'):
                    file_url = self.base_url + href
                else:
                    file_url = urljoin(self.base_url, href)
                
                # 파일명 추출
                file_name = link_text
                if not file_name:
                    # URL에서 파일명 추출 시도
                    if '=' in href:
                        file_name = href.split('=')[-1]
                    else:
                        file_name = "첨부파일"
                
                attachment = {
                    'name': file_name,
                    'url': file_url
                }
                
                attachments.append(attachment)
                logger.debug(f"첨부파일 발견: {file_name}")
                
            except Exception as e:
                logger.error(f"첨부파일 처리 중 오류: {e}")
                continue
        
        logger.info(f"{len(attachments)}개 첨부파일 발견")
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment_info: dict = None) -> bool:
        """파일 다운로드 - 향상된 버전"""
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
    
    def _extract_filename(self, response: requests.Response, default_path: str) -> str:
        """Content-Disposition에서 실제 파일명 추출 - 향상된 버전"""
        content_disposition = response.headers.get('content-disposition', '')
        save_dir = os.path.dirname(default_path)
        
        if not content_disposition:
            return default_path
        
        # RFC 5987 형식 우선 시도 (filename*=UTF-8''filename.ext)
        rfc5987_match = re.search(r"filename\*=([^']*)'([^']*)'(.+)", content_disposition)
        if rfc5987_match:
            encoding = rfc5987_match.group(1) or 'utf-8'
            filename = rfc5987_match.group(3)
            try:
                filename = unquote(filename, encoding=encoding)
                clean_filename = self.sanitize_filename(filename)
                return os.path.join(save_dir, clean_filename)
            except:
                pass
        
        # 일반적인 filename 파라미터 시도
        filename_match = re.search(r'filename[^;=\n]*=(([\'"]).*?\2|[^;\n]*)', content_disposition)
        if filename_match:
            filename = filename_match.group(1).strip('"\'')
            
            # 다양한 인코딩 시도: UTF-8, EUC-KR, CP949
            for encoding in ['utf-8', 'euc-kr', 'cp949']:
                try:
                    if encoding == 'utf-8':
                        # UTF-8로 잘못 해석된 경우 복구 시도
                        decoded = filename.encode('latin-1').decode('utf-8')
                    else:
                        decoded = filename.encode('latin-1').decode(encoding)
                    
                    if decoded and not decoded.isspace():
                        clean_filename = self.sanitize_filename(decoded.replace('+', ' '))
                        return os.path.join(save_dir, clean_filename)
                except:
                    continue
        
        return default_path

# 하위 호환성을 위한 별칭
TechnoparkScraper = EnhancedTechnoparkScraper