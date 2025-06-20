# -*- coding: utf-8 -*-
"""
경기도 골목상권 상생발전소(ggbaro.kr) Enhanced 스크래퍼 - 표준 HTML 테이블 기반
"""

import requests
from bs4 import BeautifulSoup
import re
import logging
import os
from urllib.parse import urljoin, parse_qs, urlparse, unquote
from enhanced_base_scraper import StandardTableScraper
import time
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class EnhancedGgbaroScraper(StandardTableScraper):
    """경기도 골목상권 상생발전소(ggbaro.kr) 전용 스크래퍼 - 향상된 버전"""
    
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
        self.base_url = "https://ggbaro.kr"
        self.list_url = "https://ggbaro.kr/board/boardIndex.do?type=1"
        
        # 사이트 특화 설정
        self.verify_ssl = True  # HTTPS 사이트
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - GET 파라미터 방식"""
        if page_num == 1:
            return self.list_url
        else:
            return f"https://ggbaro.kr/board/boardIndex.do?page={page_num}&type=1"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - ggbaro.kr 사이트 특화"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # ggbaro.kr 사이트 테이블 구조 분석
        # 공고 목록이 테이블 형태로 되어 있음
        table = soup.find('table')
        if not table:
            logger.warning("테이블을 찾을 수 없습니다")
            return announcements
        
        tbody = table.find('tbody')
        if not tbody:
            # tbody가 없는 경우 table에서 직접 tr 찾기
            tbody = table
        
        rows = tbody.find_all('tr')
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 4:  # 번호, 제목, 작성자, 작성일
                    continue
                
                # 제목 셀에서 링크 찾기 (두 번째 셀, data-label="제목")
                title_cell = cells[1]
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
                logger.debug(f"공고 추가: {title[:50]}...")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def _extract_meta_info(self, cells: list, announcement: Dict[str, Any]):
        """테이블 셀에서 메타 정보 추출"""
        try:
            # 번호 (첫 번째 셀)
            if len(cells) > 0:
                number_text = cells[0].get_text(strip=True)
                if number_text.isdigit():
                    announcement['number'] = number_text
            
            # 작성자 (세 번째 셀, data-label="작성자")
            if len(cells) > 2:
                author_text = cells[2].get_text(strip=True)
                if author_text:
                    announcement['writer'] = author_text
            
            # 작성일 (네 번째 셀, data-label="작성일")
            if len(cells) > 3:
                date_text = cells[3].get_text(strip=True)
                if date_text:
                    announcement['date'] = date_text
        
        except Exception as e:
            logger.error(f"메타 정보 추출 중 오류: {e}")
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱 - ggbaro.kr 사이트 특화"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # ggbaro.kr 사이트의 실제 본문 내용 추출
        # 본문은 테이블의 td.tbl-content에 위치
        content_area = soup.select_one('td.tbl-content')
        
        if not content_area:
            # 대안으로 클래스에 'content'가 포함된 요소 찾기
            content_selectors = [
                '.tbl-content',
                '.content',
                '.view-content', 
                '.board-view',
                'td[class*="content"]',
                'div[class*="content"]'
            ]
            
            for selector in content_selectors:
                content_area = soup.select_one(selector)
                if content_area:
                    logger.debug(f"본문을 {selector} 선택자로 찾음")
                    break
        
        # 테이블 구조에서 본문 찾기 (ggbaro.kr 특화)
        if not content_area:
            tables = soup.find_all('table')
            for table in tables:
                tds = table.find_all('td')
                for td in tds:
                    # 긴 텍스트가 있는 td를 본문으로 판단
                    text = td.get_text(strip=True)
                    if len(text) > 50 and '첨부파일' not in text:
                        content_area = td
                        logger.debug("테이블 구조에서 본문 영역 찾음")
                        break
                if content_area:
                    break
        
        # 마지막 fallback: body 전체에서 추출
        if not content_area:
            content_area = soup.find('body') or soup
            logger.warning("본문 영역을 찾지 못해 전체 페이지에서 추출")
        
        # HTML을 마크다운으로 변환
        if content_area:
            # 불필요한 태그 제거
            for tag in content_area.find_all(['script', 'style', 'nav', 'header', 'footer']):
                tag.decompose()
            
            content_html = str(content_area)
            content_text = self.h.handle(content_html)
            
            # 내용 정리 - 불필요한 줄바꿈 제거
            content_text = re.sub(r'\n\s*\n\s*\n', '\n\n', content_text)
            content_text = content_text.strip()
        else:
            content_text = "내용을 추출할 수 없습니다."
            
        # 첨부파일 추출
        attachments = self._extract_attachments(soup)
        
        return {
            'content': content_text,
            'attachments': attachments
        }
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """첨부파일 링크 추출 - ggbaro.kr 사이트 특화"""
        attachments = []
        
        try:
            # ggbaro.kr의 특수한 첨부파일 구조 찾기
            # class="file-download-str download-list"인 요소들 찾기
            download_elements = soup.find_all(class_="file-download-str download-list")
            
            for element in download_elements:
                # data 속성에서 다운로드 정보 추출
                table_seq = element.get('data-table-seq')
                order_seq = element.get('data-order-seq')
                filename = element.get_text(strip=True)
                
                if table_seq and order_seq and filename:
                    # ggbaro.kr의 다운로드 URL 패턴
                    file_url = f"{self.base_url}/board/fileDownloadFront.do?tableSeq={table_seq}&orderSeq={order_seq}"
                    
                    attachment = {
                        'filename': filename,
                        'url': file_url
                    }
                    
                    attachments.append(attachment)
                    logger.info(f"첨부파일 발견: {filename}")
            
            # 일반적인 파일 링크도 확인 (fallback)
            if not attachments:
                file_links = soup.find_all('a', href=True)
                
                for link in file_links:
                    href = link.get('href', '')
                    
                    # 파일 다운로드 패턴 확인
                    if any(pattern in href.lower() for pattern in ['download', 'file', 'attach']):
                        filename = link.get_text(strip=True)
                        
                        if filename and len(filename) > 0:
                            file_url = urljoin(self.base_url, href)
                            
                            attachment = {
                                'filename': filename,
                                'url': file_url
                            }
                            
                            attachments.append(attachment)
                            logger.info(f"일반 링크 첨부파일 발견: {filename}")
            
        except Exception as e:
            logger.error(f"첨부파일 추출 중 오류: {e}")
        
        return attachments
    
    def _extract_js_file_downloads(self, soup: BeautifulSoup, attachments: List[Dict[str, Any]]):
        """JavaScript 기반 파일 다운로드 패턴 추출"""
        try:
            # JavaScript 함수 호출 패턴 찾기
            script_tags = soup.find_all('script')
            for script in script_tags:
                script_content = script.get_text()
                
                # 파일 다운로드 함수 패턴 찾기
                download_patterns = [
                    r'downloadFile\s*\(\s*[\'"]([^\'\"]+)[\'"]\s*,\s*[\'"]([^\'\"]+)[\'"]\s*\)',
                    r'fileDownload\s*\(\s*[\'"]([^\'\"]+)[\'"]\s*\)',
                ]
                
                for pattern in download_patterns:
                    matches = re.findall(pattern, script_content)
                    for match in matches:
                        if isinstance(match, tuple) and len(match) >= 2:
                            file_id, filename = match[0], match[1]
                            file_url = f"{self.base_url}/file/download?id={file_id}"
                        else:
                            file_id = match if isinstance(match, str) else match[0]
                            filename = f"attachment_{file_id}"
                            file_url = f"{self.base_url}/file/download?id={file_id}"
                        
                        attachment = {
                            'filename': filename,
                            'url': file_url
                        }
                        attachments.append(attachment)
                        logger.info(f"JavaScript 파일 다운로드 발견: {filename}")
        
        except Exception as e:
            logger.error(f"JavaScript 파일 다운로드 추출 중 오류: {e}")

# 하위 호환성을 위한 별칭
GgbaroScraper = EnhancedGgbaroScraper