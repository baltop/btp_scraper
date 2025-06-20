"""
경기도 중소기업 지원 플랫폼(GBMAKERS) 전용 스크래퍼 - 향상된 버전

사이트 특성:
- URL: https://gbmakers.or.kr/notice?category=
- 시스템: 커스텀 CMS (DOZ 기반)
- 페이지네이션: q 파라미터와 page 파라미터 조합
- 목록 구조: a.list_text_title._fade_link 클래스
- 링크 패턴: bmode=view&idx={id}&t=board 형태
- 첨부파일: 제한적 (확인 필요)
- 인코딩: UTF-8
"""

import os
import re
import logging
import time
from urllib.parse import urljoin, unquote, urlparse, parse_qs
from bs4 import BeautifulSoup
from enhanced_base_scraper import StandardTableScraper

logger = logging.getLogger(__name__)

class EnhancedGbmakersScraper(StandardTableScraper):
    """GBMAKERS 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (fallback용)
        self.base_url = "https://gbmakers.or.kr"
        self.list_url = "https://gbmakers.or.kr/notice?category="
        
        # 사이트별 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 2  # 조금 더 긴 대기 시간
        
        
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
        """페이지별 URL 생성 - 특수한 q 파라미터 방식"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if hasattr(self, 'config') and self.config and hasattr(self.config, 'pagination'):
            return super().get_list_url(page_num)
        
        # Fallback: GBMAKERS 특화 로직
        if page_num == 1:
            return self.list_url
        else:
            # q 파라미터를 기반으로 페이지 URL 구성
            # 실제 패턴: /notice/?q=YToxOntzOjEyOiJrZXl3b3JkX3R5cGUiO3M6MzoiYWxsIjt9&page=2
            base_q = "YToxOntzOjEyOiJrZXl3b3JkX3R5cGUiO3M6MzoiYWxsIjt9"  # base64 인코딩된 기본 쿼리
            return f"{self.base_url}/notice/?q={base_q}&page={page_num}"
    
    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱"""
        # 설정 기반 파싱이 가능하면 사용
        if hasattr(self, 'config') and self.config and hasattr(self.config, 'selectors'):
            return super().parse_list_page(html_content)
        
        # Fallback: 사이트 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> list:
        """GBMAKERS 특화된 목록 파싱 로직"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # a.list_text_title._fade_link 클래스를 가진 링크들 찾기
        notice_links = soup.find_all('a', class_='list_text_title _fade_link')
        logger.info(f"{len(notice_links)}개의 공고 링크 발견")
        
        for link in notice_links:
            try:
                title = link.get_text(strip=True)
                href = link.get('href', '')
                
                # 잘못된 URL 건너뛰기
                if not title or not href or href.startswith('javascript:') or '#' in href:
                    continue
                
                detail_url = urljoin(self.base_url, href)
                
                # 부모 요소에서 추가 정보 추출 시도
                parent_container = link.find_parent('div')
                author = "경기도중소기업지원플랫폼"  # 기본값
                date = ""
                views = ""
                
                # 날짜나 추가 정보가 있다면 추출
                if parent_container:
                    # 형제 요소들에서 날짜, 조회수 등 찾기
                    siblings = parent_container.find_all('div')
                    for sibling in siblings:
                        sibling_text = sibling.get_text(strip=True)
                        # 날짜 패턴 찾기 (YYYY-MM-DD, YYYY.MM.DD 등)
                        date_match = re.search(r'\d{4}[-./]\d{1,2}[-./]\d{1,2}', sibling_text)
                        if date_match:
                            date = date_match.group()
                        
                        # 조회수 패턴 찾기
                        views_match = re.search(r'조회\s*:?\s*(\d+)', sibling_text)
                        if views_match:
                            views = views_match.group(1)
                
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
                logger.error(f"링크 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> dict:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 제목 추출
        title = ""
        title_elem = soup.find('h1', class_='view_tit')
        if title_elem:
            title = title_elem.get_text(strip=True)
            # "공지" 등의 접두사 제거
            title = re.sub(r'^공지\s*', '', title)
        
        # 본문 추출 - 여러 선택자 시도
        content = ""
        for selector in ['.text-table', '.fr-view', '.view_content', '.board_content', '.post_content', '.content_area']:
            content_area = soup.select_one(selector)
            if content_area and content_area.get_text(strip=True):
                # 이미지 태그들 처리
                for img in content_area.find_all('img'):
                    src = img.get('src', '')
                    if src and not src.startswith('http'):
                        img['src'] = urljoin(self.base_url, src)
                
                content = str(content_area)
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        # 본문이 매우 짧거나 없는 경우 대체 방법 시도
        if not content or len(content.strip()) < 50:
            # DOZ 시스템의 특수한 구조 고려
            doz_text = soup.find('div', {'doz_type': 'text'})
            if doz_text:
                content = str(doz_text)
                logger.debug("DOZ 텍스트 위젯에서 본문 추출")
        
        if not content:
            logger.warning("본문을 찾을 수 없습니다")
            content = "<p>본문 내용을 추출할 수 없습니다.</p>"
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup)
        
        # 관련링크 추출
        links = []
        for link in soup.find_all('a'):
            href = link.get('href', '')
            text = link.get_text(strip=True)
            if href and text and href.startswith('http') and 'gbmakers' not in href:
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
        
        # 다양한 첨부파일 패턴 시도
        attachment_selectors = [
            'a[href*="download"]',
            'a[href*="file"]',
            'a[href*="attach"]',
            '.file a',
            '.attach a',
            '.download a'
        ]
        
        for selector in attachment_selectors:
            links = soup.select(selector)
            for link in links:
                try:
                    href = link.get('href', '')
                    if not href:
                        continue
                    
                    file_url = urljoin(self.base_url, href)
                    
                    # 파일명 추출
                    filename = link.get_text(strip=True)
                    
                    # 파일명에서 불필요한 텍스트 제거
                    filename = re.sub(r'다운로드|download|파일|file', '', filename, flags=re.IGNORECASE).strip()
                    
                    if filename and len(filename) > 0:
                        attachment = {
                            'filename': filename,
                            'url': file_url
                        }
                        attachments.append(attachment)
                        logger.debug(f"첨부파일: {filename}")
                    
                except Exception as e:
                    logger.error(f"첨부파일 파싱 중 오류: {e}")
                    continue
        
        # 중복 제거
        unique_attachments = []
        seen_urls = set()
        for att in attachments:
            if att['url'] not in seen_urls:
                unique_attachments.append(att)
                seen_urls.add(att['url'])
        
        logger.info(f"{len(unique_attachments)}개의 첨부파일 발견")
        return unique_attachments
    
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
GbmakersScraper = EnhancedGbmakersScraper