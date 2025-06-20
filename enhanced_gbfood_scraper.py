"""
경기도 농수산진흥원(GBFOOD) 전용 스크래퍼 - 향상된 버전

사이트 특성:
- URL: https://www.gbfood.or.kr/public
- 시스템: 그누보드 기반 게시판
- 페이지네이션: GET 파라미터 방식 (?page=2)
- 목록 구조: .list-row 클래스의 div 반복
- 링크 패턴: 직접 href 링크
- 첨부파일: download.php 방식
- 인코딩: UTF-8
"""

import os
import re
import logging
import time
from urllib.parse import urljoin, unquote
from bs4 import BeautifulSoup
from enhanced_base_scraper import StandardTableScraper

logger = logging.getLogger(__name__)

class EnhancedGbfoodScraper(StandardTableScraper):
    """GBFOOD 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (fallback용)
        self.base_url = "https://www.gbfood.or.kr"
        self.list_url = "https://www.gbfood.or.kr/public"
        
        # 사이트별 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        
        # 요청 헤더 설정
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if hasattr(self, 'config') and self.config and hasattr(self.config, 'pagination'):
            return super().get_list_url(page_num)
        
        # Fallback: 사이트 특화 로직
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}?page={page_num}"
    
    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱"""
        # 설정 기반 파싱이 가능하면 사용
        if hasattr(self, 'config') and self.config and hasattr(self.config, 'selectors'):
            return super().parse_list_page(html_content)
        
        # Fallback: 사이트 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> list:
        """GBFOOD 특화된 목록 파싱 로직"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # .list-row 클래스를 가진 div들 찾기 (공지 제외)
        list_rows = soup.find_all('div', class_='list-row')
        logger.info(f"{len(list_rows)}개의 목록 행 발견")
        
        for row in list_rows:
            try:
                # 공지사항이나 제목 행 건너뛰기
                if 'notice-row' in row.get('class', []) or 'list-top' in row.get('class', []):
                    continue
                
                # 제목과 링크 추출
                title_div = row.find('div', class_='list-title')
                if not title_div:
                    continue
                
                link_elem = title_div.find('a', class_='list-subject')
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                href = link_elem.get('href', '')
                
                # 잘못된 URL 건너뛰기
                if not title or not href or href.startswith('javascript:'):
                    continue
                
                detail_url = urljoin(self.base_url, href)
                
                # 작성자 정보
                author_div = title_div.find('div', class_='list-author')
                author = "경북농식품유통교육진흥원"  # 기본값
                if author_div:
                    author_link = author_div.find('a')
                    if author_link:
                        author = author_link.get_text(strip=True)
                
                # 날짜 정보
                time_div = row.find('div', class_='list-time')
                date = ""
                if time_div:
                    time_span = time_div.find('span', class_='time')
                    if time_span:
                        date = time_span.get_text(strip=True)
                
                # 조회수 정보
                hit_div = row.find('div', class_='list-hit')
                views = "0"
                if hit_div:
                    hit_span = hit_div.find('span', class_='hit')
                    if hit_span:
                        views = hit_span.get_text(strip=True)
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'author': author,
                    'date': date,
                    'views': views
                }
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱: {title}")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> dict:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 제목 추출
        title = ""
        title_elem = soup.find('h3', class_='title-subject')
        if title_elem:
            title_div = title_elem.find('div')
            if title_div:
                title = title_div.get_text(strip=True)
        
        # 본문 추출 - 여러 선택자 시도
        content = ""
        for selector in ['.post-article', '.fr-view', '.post-content article']:
            content_area = soup.select_one(selector)
            if content_area:
                # 이미지 태그들 처리
                for img in content_area.find_all('img'):
                    src = img.get('src', '')
                    if src and not src.startswith('http'):
                        img['src'] = urljoin(self.base_url, src)
                
                content = str(content_area)
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        if not content:
            logger.warning("본문을 찾을 수 없습니다")
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup)
        
        # 관련링크 추출
        links = []
        source_div = soup.find('div', class_='post-source')
        if source_div:
            for link in source_div.find_all('a'):
                href = link.get('href', '')
                text = link.get_text(strip=True)
                if href and text:
                    links.append({'url': href, 'text': text})
        
        return {
            'title': title,
            'content': content,
            'attachments': attachments,
            'links': links
        }
    
    def _extract_attachments(self, soup: BeautifulSoup) -> list:
        """첨부파일 정보 추출"""
        attachments = []
        
        # .attached-list 내의 다운로드 링크들 찾기
        attached_list = soup.find('div', class_='attached-list')
        if not attached_list:
            logger.debug("첨부파일 목록을 찾을 수 없습니다")
            return attachments
        
        download_links = attached_list.find_all('a', href=re.compile(r'download\.php'))
        logger.info(f"{len(download_links)}개의 첨부파일 발견")
        
        for link in download_links:
            try:
                href = link.get('href', '')
                if not href:
                    continue
                
                file_url = urljoin(self.base_url, href)
                
                # 파일명 추출
                filename = ""
                strong_elem = link.find('strong')
                if strong_elem:
                    filename = strong_elem.get_text(strip=True)
                
                if not filename:
                    filename = link.get_text(strip=True)
                    # 파일 크기 정보 제거
                    filename = re.sub(r'\s*\([^)]+\)$', '', filename)
                
                if filename:
                    attachment = {
                        'filename': filename,
                        'url': file_url
                    }
                    attachments.append(attachment)
                    logger.debug(f"첨부파일: {filename}")
                
            except Exception as e:
                logger.error(f"첨부파일 파싱 중 오류: {e}")
                continue
        
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment: dict = None) -> bool:
        """파일 다운로드"""
        try:
            response = self.session.get(url, stream=True, verify=self.verify_ssl, timeout=self.timeout)
            response.raise_for_status()
            
            # 파일 크기 확인
            total_size = int(response.headers.get('content-length', 0))
            
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
            if os.path.exists(save_path):
                os.remove(save_path)
            return False

# 하위 호환성을 위한 별칭
GbfoodScraper = EnhancedGbfoodScraper