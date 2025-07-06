# -*- coding: utf-8 -*-
"""
서울특별시 사회적경제지원센터(SEHUB) 스크래퍼 - Enhanced 버전
URL: https://sehub.net/archives/category/alarm/opencat
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import os
import time
import logging
from enhanced_base_scraper import StandardTableScraper

logger = logging.getLogger(__name__)

class EnhancedSehubScraper(StandardTableScraper):
    """서울특별시 사회적경제지원센터 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://sehub.net"
        self.list_url = "https://sehub.net/archives/category/alarm/opencat"
        
        # SEHUB 특화 설정
        self.verify_ssl = True  # SSL 인증서 정상
        self.default_encoding = 'utf-8'
        self.timeout = 15
        self.delay_between_requests = 1
        
        # 세션 설정
        self.session.headers.update({
            'Referer': self.base_url,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성"""
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}/page/{page_num}"
    
    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 메인 테이블 찾기
        table = soup.find('table')
        if not table:
            logger.warning("메인 테이블을 찾을 수 없습니다")
            return announcements
        
        tbody = table.find('tbody')
        if not tbody:
            # tbody가 없으면 table에서 직접 tr 찾기
            rows = table.find_all('tr')[1:]  # 헤더 제외
        else:
            rows = tbody.find_all('tr')
        
        logger.info(f"총 {len(rows)}개 행 발견")
        
        for i, row in enumerate(rows):
            try:
                cells = row.find_all('td')
                if len(cells) < 4:
                    continue
                
                # 번호 (첫 번째 셀) - 모든 공고가 "알림"으로 표시됨
                number_cell = cells[0]
                number = number_cell.get_text(strip=True)
                if not number:
                    number = f"row_{i+1}"
                
                # 제목 (두 번째 셀)
                title_cell = cells[1]
                title_link = title_cell.find('a')
                if not title_link:
                    continue
                
                title = title_link.get_text(strip=True)
                if not title:
                    continue
                
                # 상세 페이지 URL
                href = title_link.get('href', '')
                if href.startswith('/'):
                    detail_url = self.base_url + href
                elif href.startswith('http'):
                    detail_url = href
                else:
                    detail_url = urljoin(self.base_url, href)
                
                # 작성일 (세 번째 셀)
                date_cell = cells[2]
                date = date_cell.get_text(strip=True)
                
                # 주최/주관 (네 번째 셀)
                host_cell = cells[3]
                host = host_cell.get_text(strip=True)
                
                # 첨부파일 여부는 상세 페이지에서 확인
                has_attachment = False
                
                announcement = {
                    'number': number,
                    'title': title,
                    'url': detail_url,
                    'date': date,
                    'host': host,
                    'has_attachment': has_attachment
                }
                
                announcements.append(announcement)
                logger.info(f"공고 추가: [{number}] {title}")
                
            except Exception as e:
                logger.error(f"행 파싱 오류 (행 {i+1}): {e}")
                continue
        
        logger.info(f"총 {len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> dict:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 제목 찾기
        title = ""
        title_selectors = [
            'h1',
            '.entry-title',
            '[class*="title"]',
            '.post-title'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = title_elem.get_text(strip=True)
                if title:
                    break
        
        # 본문 내용 찾기
        content_area = None
        content_selectors = [
            '.entry-content',
            '[class*="content"]',
            'article',
            '.post-content',
            '#content'
        ]
        
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                break
        
        if not content_area:
            logger.warning("내용 영역을 찾을 수 없습니다")
            content_area = soup
        
        # 본문 텍스트 추출
        content_parts = []
        
        # p 태그들에서 내용 추출
        paragraphs = content_area.find_all('p')
        for p in paragraphs:
            text = p.get_text(strip=True)
            if text and len(text) > 10:  # 충분한 길이의 텍스트만
                content_parts.append(text)
        
        # p 태그가 없으면 다른 방법으로 텍스트 추출
        if not content_parts:
            # div나 다른 요소에서 텍스트 추출
            text_elements = content_area.find_all(['div', 'span'], string=True)
            for elem in text_elements:
                text = elem.get_text(strip=True) if hasattr(elem, 'get_text') else str(elem).strip()
                if text and len(text) > 20:
                    content_parts.append(text)
        
        # 여전히 내용이 없으면 전체 텍스트에서 추출
        if not content_parts:
            all_text = content_area.get_text(strip=True)
            if all_text and len(all_text) > 50:
                # 긴 텍스트를 적절히 나누기
                sentences = all_text.split('.')
                for sentence in sentences[:10]:  # 처음 10문장만
                    if sentence.strip() and len(sentence.strip()) > 10:
                        content_parts.append(sentence.strip())
        
        content = '\n\n'.join(content_parts) if content_parts else ''
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup)
        
        return {
            'title': title,
            'content': content,
            'attachments': attachments
        }
    
    def _extract_attachments(self, soup: BeautifulSoup) -> list:
        """첨부파일 추출 - SEHUB 특화"""
        attachments = []
        
        # 다양한 패턴으로 파일 링크 찾기
        file_patterns = [
            # PDF, HWP, DOC 등의 파일 링크
            r'\.pdf(\?.*)?$',
            r'\.hwp(\?.*)?$', 
            r'\.hwpx(\?.*)?$',
            r'\.doc(\?.*)?$',
            r'\.docx(\?.*)?$',
            r'\.xls(\?.*)?$',
            r'\.xlsx(\?.*)?$',
            r'\.ppt(\?.*)?$',
            r'\.pptx(\?.*)?$',
            r'\.zip(\?.*)?$'
        ]
        
        # 모든 링크 검사
        links = soup.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # 파일 확장자 패턴 매칭
            for pattern in file_patterns:
                if re.search(pattern, href, re.IGNORECASE):
                    # 상대 URL을 절대 URL로 변환
                    if href.startswith('/'):
                        file_url = self.base_url + href
                    elif href.startswith('http'):
                        file_url = href
                    else:
                        file_url = urljoin(self.base_url, href)
                    
                    # 파일명 추출 - URL에서 확장자 포함된 실제 파일명 우선 사용
                    url_filename = os.path.basename(urlparse(href).path)
                    
                    # URL에서 확장자가 포함된 파일명이 있으면 우선 사용
                    if url_filename and '.' in url_filename:
                        filename = url_filename
                    # URL에 파일명이 없거나 확장자가 없으면 링크 텍스트 사용 + 확장자 추가
                    elif text and text not in ['다운로드', 'Download', '첨부파일']:
                        # 링크 텍스트에서 확장자 추출
                        if '.' in text:
                            filename = text
                        else:
                            # URL에서 확장자 추출해서 텍스트에 추가
                            url_ext = None
                            for pattern in file_patterns:
                                match = re.search(pattern, href, re.IGNORECASE)
                                if match:
                                    # 패턴에서 확장자 추출 (예: \.pdf -> .pdf)
                                    url_ext = pattern.replace('\\', '').replace('(\\?.*)?$', '').replace('$', '')
                                    break
                            
                            if url_ext:
                                filename = text + url_ext
                            else:
                                filename = text
                    # 둘 다 없으면 기본 파일명
                    else:
                        if url_filename:
                            filename = url_filename
                        else:
                            filename = f"attachment_{len(attachments)+1}.unknown"
                    
                    attachments.append({
                        'name': filename,
                        'url': file_url
                    })
                    break
        
        # 중복 제거
        seen_urls = set()
        unique_attachments = []
        for att in attachments:
            if att['url'] not in seen_urls:
                seen_urls.add(att['url'])
                unique_attachments.append(att)
        
        logger.info(f"첨부파일 {len(unique_attachments)}개 발견")
        for att in unique_attachments:
            logger.info(f"  - {att['name']}: {att['url']}")
        
        return unique_attachments

def create_scraper():
    """스크래퍼 인스턴스 생성"""
    return EnhancedSehubScraper()

if __name__ == "__main__":
    # 테스트 실행
    scraper = EnhancedSehubScraper()
    scraper.scrape_pages(max_pages=3, output_base='output/sehub')