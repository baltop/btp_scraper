#!/usr/bin/env python3
"""
NIPA (한국지능정보사회진흥원) 전용 스크래퍼 - 향상된 버전

사이트: https://www.nipa.kr/home/2-2
특징: 표준 HTML 테이블 구조, GET 파라미터 페이지네이션
"""

import os
import re
import time
import logging
from typing import List, Dict, Any
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import requests

from enhanced_base_scraper import StandardTableScraper

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedNIPAScraper(StandardTableScraper):
    """NIPA 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 기본 설정
        self.base_url = "https://www.nipa.kr"
        self.list_url = "https://www.nipa.kr/home/2-2"
        
        # 사이트별 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        
        # 헤더 설정
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # 세션 설정
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - 설정 주입과 Fallback 패턴"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: NIPA 표준 페이지네이션
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}?curPage={page_num}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: NIPA 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """NIPA 특화된 목록 페이지 파싱"""
        announcements = []
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # NIPA 사업공고 테이블 구조
        table = soup.find('table')
        if not table:
            logger.warning("테이블을 찾을 수 없습니다")
            return announcements
        
        tbody = table.find('tbody')
        if not tbody:
            tbody = table
        
        logger.info(f"테이블에서 {len(tbody.find_all('tr'))}개 행 발견")
        
        for row in tbody.find_all('tr'):
            try:
                cells = row.find_all('td')
                if len(cells) < 5:  # 최소 5개 컬럼 필요 (번호, 신청기간, 제목, 작성자, 작성일)
                    continue
                
                # 번호 (첫 번째 컬럼)
                number_text = cells[0].get_text(strip=True)
                
                # D-day 정보 (두 번째 컬럼)
                dday_cell = cells[1]
                dday_text = dday_cell.get_text(strip=True)
                
                # 제목 영역 (세 번째 컬럼) - 복잡한 구조
                title_cell = cells[2]
                
                # 제목 링크 추출
                link_elem = title_cell.find('a')
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                href = link_elem.get('href', '')
                
                if not title or not href:
                    continue
                
                # 상대 URL을 절대 URL로 변환
                detail_url = urljoin(self.base_url, href)
                
                # 부가 정보 추출 (사업명, 신청기간)
                sub_info_div = title_cell.find('div', class_='sub-info')
                project_name = ""
                period = ""
                
                if sub_info_div:
                    project_span = sub_info_div.find('span', class_='project-name')
                    if project_span:
                        project_name = project_span.get_text(strip=True)
                    
                    period_span = sub_info_div.find('span', class_='period')
                    if period_span:
                        period = period_span.get_text(strip=True)
                
                # 작성자 (네 번째 컬럼)
                author_text = cells[3].get_text(strip=True)
                
                # 작성일 (다섯 번째 컬럼)  
                date_text = cells[4].get_text(strip=True)
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'number': number_text,
                    'dday': dday_text,
                    'project_name': project_name,
                    'period': period,
                    'author': author_text,
                    'date': date_text,
                    'has_attachment': False  # 상세 페이지에서 확인
                }
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱 완료: {title}")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str, url: str = None) -> Dict[str, Any]:
        """상세 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_detail_page(html_content, url)
        
        # Fallback: NIPA 특화 로직
        return self._parse_detail_fallback(html_content, url)
    
    def _parse_detail_fallback(self, html_content: str, announcement_url: str = None) -> Dict[str, Any]:
        """NIPA 특화된 상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 제목 추출
        title = ""
        title_selectors = [
            'h1',           # 일반적인 제목
            '.page-title',  # 페이지 제목
            '.title',       # 일반 제목
            'h2', 'h3'      # 서브 헤더들
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = title_elem.get_text(strip=True)
                logger.debug(f"제목을 {selector} 선택자로 찾음")
                break
        
        # 본문 추출
        content = ""
        content_selectors = [
            '.view-content',    # 뷰 컨텐츠
            '.content-area',    # 컨텐츠 영역
            '.board-content',   # 게시판 컨텐츠
            '.detail-content',  # 상세 컨텐츠
            'main',             # 메인 영역
            '.container'        # 컨테이너
        ]
        
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                # 불필요한 요소들 제거
                for unwanted in content_area.find_all(['script', 'style', 'nav', 'header', 'footer']):
                    unwanted.decompose()
                content = content_area.get_text(strip=True)
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        # 본문이 너무 짧으면 전체 페이지에서 추출
        if len(content) < 100:
            # 전체 페이지에서 본문 추출
            for unwanted in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                unwanted.decompose()
            content = soup.get_text(strip=True)
            logger.debug("전체 페이지에서 본문 추출")
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup)
        
        # 메타데이터 추출
        metadata = self._extract_metadata(soup)
        
        return {
            'title': title,
            'content': content,
            'attachments': attachments,
            'metadata': metadata,
            'url': announcement_url
        }
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """첨부파일 정보 추출"""
        attachments = []
        
        # NIPA 첨부파일 패턴: /comm/getFile?srvcId=BBSTY1&upperNo=...&fileTy=ATTACH&fileNo=...
        file_links = soup.find_all('a', href=re.compile(r'/comm/getFile'))
        
        for link in file_links:
            href = link.get('href', '')
            if not href:
                continue
            
            # 파일명 추출 (링크 텍스트에서)
            link_text = link.get_text(strip=True)
            
            # 파일 크기 정보 제거 (예: "파일명.pdf (249 KB)")
            filename_match = re.search(r'([^()]+?)(?:\s*\([^)]*\))?$', link_text)
            if filename_match:
                filename = filename_match.group(1).strip()
            else:
                filename = link_text
            
            # 빈 파일명 처리
            if not filename or filename.isspace():
                filename = f"attachment_{len(attachments)+1}"
            
            # 파일 URL (이미 절대 URL일 가능성 높음, 아니면 변환)
            if href.startswith('http'):
                file_url = href
            else:
                file_url = urljoin(self.base_url, href)
            
            attachments.append({
                'name': filename,
                'url': file_url
            })
            
            logger.debug(f"첨부파일 발견: {filename}")
        
        logger.info(f"{len(attachments)}개 첨부파일 발견")
        return attachments
    
    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, str]:
        """메타데이터 추출"""
        metadata = {}
        
        # 공고 번호나 기타 메타데이터
        meta_elements = soup.find_all(['div', 'span', 'p'], class_=re.compile(r'meta|info'))
        for elem in meta_elements:
            text = elem.get_text(strip=True)
            if text:
                metadata[f'meta_{len(metadata)}'] = text
        
        return metadata
    
    def download_file(self, url: str, save_path: str, attachment: Dict[str, Any] = None) -> bool:
        """파일 다운로드"""
        try:
            logger.info(f"파일 다운로드 시작: {url}")
            
            response = self.session.get(url, stream=True, verify=self.verify_ssl, timeout=self.timeout)
            response.raise_for_status()
            
            # 파일 크기 확인
            total_size = int(response.headers.get('content-length', 0))
            
            # 파일 저장
            with open(save_path, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
            
            file_size = os.path.getsize(save_path)
            logger.info(f"다운로드 완료: {save_path} ({file_size:,} bytes)")
            
            return True
            
        except Exception as e:
            logger.error(f"파일 다운로드 실패 {url}: {e}")
            return False

# 하위 호환성을 위한 별칭
NIPAScraper = EnhancedNIPAScraper

if __name__ == "__main__":
    # 간단한 테스트
    scraper = EnhancedNIPAScraper()
    output_dir = "output/nipa"
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info("NIPA 스크래퍼 테스트 시작")
    scraper.scrape_pages(max_pages=1, output_base=output_dir)
    logger.info("NIPA 스크래퍼 테스트 완료")