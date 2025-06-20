# -*- coding: utf-8 -*-
"""
안양산업진흥원(AYVENTURE) 스크래퍼 - 향상된 버전
URL: https://www.ayventure.net/bbs/board.do?id=382&menuId=855
"""

from enhanced_base_scraper import StandardTableScraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin, parse_qs, urlparse
import requests
import re
import os
import time
import logging
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

class EnhancedAyventureScraper(StandardTableScraper):
    """안양산업진흥원 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 기본 설정
        self.base_url = "https://www.ayventure.net"
        self.list_url = "https://www.ayventure.net/bbs/board.do?id=382&menuId=855"
        
        # 사이트별 특화 설정
        self.verify_ssl = False  # SSL 인증서 문제로 비활성화
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 2
        
        # JavaScript 렌더링이 필요한 사이트
        self.requires_js = True
        
        # SSL 문제 해결을 위한 추가 세션 설정
        self._configure_session_for_ssl_issues()
    
    def _configure_session_for_ssl_issues(self):
        """SSL 문제 해결을 위한 세션 설정"""
        import ssl
        import urllib3
        from requests.adapters import HTTPAdapter
        from urllib3.util.ssl_ import create_urllib3_context
        
        # SSL 경고 비활성화
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # 레거시 SSL 컨텍스트 생성 (완전히 관대한 SSL 설정)
        class LegacyHTTPAdapter(HTTPAdapter):
            def init_poolmanager(self, *args, **kwargs):
                ctx = create_urllib3_context()
                ctx.set_ciphers('DEFAULT@SECLEVEL=1')
                ctx.check_hostname = False  # 호스트명 검증 비활성화
                ctx.verify_mode = ssl.CERT_NONE  # 인증서 검증 비활성화
                kwargs['ssl_context'] = ctx
                return super().init_poolmanager(*args, **kwargs)
        
        # 기존 어댑터를 레거시 어댑터로 교체
        self.session.mount('https://', LegacyHTTPAdapter())
        
        logger.info("SSL 문제 해결을 위한 레거시 어댑터 적용")
        
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성"""
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: AYVENTURE 특화 URL 패턴 (JavaScript 기반)
        return f"{self.list_url}#{page_num}"
    
    def get_page(self, url: str, **kwargs) -> requests.Response:
        """페이지 가져오기 - JavaScript 렌더링 지원"""
        if self.requires_js:
            return self._get_page_with_playwright(url)
        else:
            return super().get_page(url, **kwargs)
    
    def _get_page_with_playwright(self, url: str) -> requests.Response:
        """Playwright를 사용한 페이지 가져오기"""
        logger.info(f"Playwright로 페이지 로드: {url}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url)
            
            # 테이블이 로드될 때까지 기다리기
            try:
                page.wait_for_selector('table tbody tr td:not([colspan])', timeout=10000)
                logger.info("테이블 로드 완료")
            except:
                logger.warning("테이블 로드 타임아웃, 계속 진행...")
            
            time.sleep(3)  # 추가 로딩 시간
            content = page.content()
            browser.close()
            
            # requests.Response 객체로 변환
            class MockResponse:
                def __init__(self, content):
                    self.text = content
                    self.content = content.encode('utf-8')
                    self.status_code = 200
                    
                def raise_for_status(self):
                    pass
            
            return MockResponse(content)
    
    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱"""
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: AYVENTURE 특화 파싱
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> list:
        """AYVENTURE 특화된 목록 파싱 로직"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # boardList ID를 가진 테이블 찾기
        table = soup.find('table', id='boardList')
        if not table:
            logger.warning("boardList ID를 가진 테이블을 찾을 수 없습니다")
            return []
        
        tbody = table.find('tbody')
        if not tbody:
            tbody = table
        
        rows = tbody.find_all('tr')
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 4:  # 번호, 제목, 등록일, 조회
                    continue
                
                # 첫 번째 셀: 번호 또는 공지
                number_cell = cells[0]
                
                # 두 번째 셀: 제목과 링크
                title_cell = cells[1]
                link_elem = title_cell.find('a')
                
                if link_elem:
                    title = link_elem.get_text(strip=True)
                    href = link_elem.get('href', '')
                    
                    if href:
                        detail_url = urljoin(self.base_url, href)
                        
                        # 세 번째 셀: 등록일
                        date = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                        
                        # 네 번째 셀: 조회수
                        views = cells[3].get_text(strip=True) if len(cells) > 3 else ""
                        
                        # 공지사항 여부 확인
                        is_notice = bool(number_cell.find('span', class_='ico_notice'))
                        
                        announcement = {
                            'title': title,
                            'url': detail_url,
                            'date': date,
                            'views': views,
                            'is_notice': is_notice
                        }
                        announcements.append(announcement)
                        logger.debug(f"공고 파싱됨: {title}")
                        
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str, url: str = None) -> dict:
        """상세 페이지 파싱"""
        if self.config and self.config.selectors:
            return super().parse_detail_page(html_content)
        
        # Fallback: AYVENTURE 특화 파싱
        return self._parse_detail_fallback(html_content, url)
    
    def _parse_detail_fallback(self, html_content: str, detail_url: str = None) -> dict:
        """AYVENTURE 특화된 상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 제목 추출
        title_elem = soup.find('div', class_='panel-title')
        if not title_elem:
            title_elem = soup.find('div', id='boardSubject')
        title = title_elem.get_text(strip=True) if title_elem else "제목 없음"
        
        # 본문 내용 추출 (bbs_memo 클래스)
        content_elem = soup.find('div', class_='bbs_memo')
        content = ""
        
        if content_elem:
            # HTML을 마크다운으로 변환
            content = self.h.handle(str(content_elem))
            logger.debug("본문을 bbs_memo 선택자로 찾음")
        else:
            # 대체 선택자들 시도
            for selector in ['.panel-body', '.view_content', '.board_view']:
                content_elem = soup.select_one(selector)
                if content_elem:
                    content = self.h.handle(str(content_elem))
                    logger.debug(f"본문을 {selector} 선택자로 찾음")
                    break
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup)
        
        return {
            'title': title,
            'content': content,
            'attachments': attachments,
            'url': detail_url or ""
        }
    
    def _extract_attachments(self, soup: BeautifulSoup) -> list:
        """첨부파일 정보 추출"""
        attachments = []
        
        # list-group 클래스에서 첨부파일 링크 찾기
        file_sections = soup.find_all('ul', class_='list-group')
        
        for section in file_sections:
            # 첨부파일 관련 항목 찾기
            for item in section.find_all('li', class_='list-group-item'):
                # "첨부파일"이 포함된 항목 확인
                if '첨부파일' in item.get_text():
                    # 다운로드 링크 찾기
                    link = item.find('a', href=re.compile(r'/cmmn/download\.do'))
                    if link:
                        href = link.get('href', '')
                        if href:
                            # 파일명 추출
                            filename = link.get_text(strip=True)
                            # 이미지 태그가 있다면 alt 속성에서 파일명 추출
                            img = link.find('img')
                            if img and img.get('alt'):
                                filename = img.get('alt')
                            
                            # 전체 URL 생성
                            download_url = urljoin(self.base_url, href)
                            
                            attachments.append({
                                'name': filename,
                                'filename': filename,
                                'url': download_url
                            })
                            logger.debug(f"첨부파일 발견: {filename}")
        
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment_info: dict = None) -> bool:
        """파일 다운로드 - SSL 검증 비활성화"""
        try:
            logger.info(f"파일 다운로드 시작: {url}")
            
            # SSL 검증을 명시적으로 비활성화하고 스트리밍 다운로드 사용
            response = self.session.get(
                url, 
                timeout=self.timeout, 
                verify=False,  # SSL 검증 명시적 비활성화
                stream=True
            )
            response.raise_for_status()
            
            # 디렉토리 생성
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # 스트리밍 방식으로 파일 저장 (메모리 효율성)
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
AyventureScraper = EnhancedAyventureScraper