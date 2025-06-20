# -*- coding: utf-8 -*-
"""
한국환경산업기술원(KEITI) Enhanced 스크래퍼 - JavaScript 기반 동적 사이트
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
from playwright.sync_api import sync_playwright, TimeoutError

logger = logging.getLogger(__name__)

class EnhancedKEITIScraper(StandardTableScraper):
    """한국환경산업기술원(KEITI) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        
        # 향상된 헤더 설정 (차단 방지)
        self.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1',
        })
        self.session.headers.update(self.headers)
        
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://www.keiti.re.kr"
        self.list_url = "https://www.keiti.re.kr/site/keiti/ex/board/List.do?cbIdx=277&searchExt1=24000100"
        
        # 사이트 특화 설정
        self.verify_ssl = True  # HTTPS 사이트
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 2  # JavaScript 렌더링 대기
        
        # Playwright 브라우저 설정
        self.playwright = None
        self.browser = None
        self.page = None
    
    def __enter__(self):
        """컨텍스트 매니저 진입"""
        self._start_browser()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        self._close_browser()
    
    def _start_browser(self):
        """Playwright 브라우저 시작"""
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            self.page = self.browser.new_page()
            
            # 페이지 설정
            self.page.set_viewport_size({"width": 1920, "height": 1080})
            self.page.set_extra_http_headers(self.headers)
            
            logger.info("Playwright 브라우저 시작됨")
        except Exception as e:
            logger.error(f"브라우저 시작 실패: {e}")
            raise
    
    def _close_browser(self):
        """Playwright 브라우저 종료"""
        try:
            if self.page:
                self.page.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            logger.info("Playwright 브라우저 종료됨")
        except Exception as e:
            logger.warning(f"브라우저 종료 중 오류: {e}")
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - JavaScript 기반 페이지네이션"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: KEITI는 pageIndex 파라미터 사용
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&pageIndex={page_num}"
    
    def _get_page_announcements(self, page_num: int) -> List[Dict[str, Any]]:
        """페이지별 공고 목록 가져오기 - Playwright 사용"""
        try:
            if not self.page:
                self._start_browser()
            
            # 첫 페이지는 직접 접속
            if page_num == 1:
                url = self.list_url
                logger.info(f"첫 페이지 로드: {url}")
                self.page.goto(url, wait_until='networkidle', timeout=30000)
            else:
                # 2페이지부터는 JavaScript 함수 실행
                logger.info(f"페이지 {page_num}로 이동")
                try:
                    # doBbsContentFPag() 함수 실행
                    self.page.evaluate(f"doBbsContentFPag({page_num})")
                    # 페이지 로딩 대기
                    self.page.wait_for_load_state('networkidle', timeout=10000)
                    time.sleep(2)  # 추가 대기
                except TimeoutError:
                    logger.warning(f"페이지 {page_num} 로딩 타임아웃, 계속 진행")
                except Exception as e:
                    logger.error(f"페이지 {page_num} JavaScript 실행 실패: {e}")
                    return []
            
            # 현재 페이지 HTML 가져오기
            html_content = self.page.content()
            
            # 실제 페이지 확인
            if "한국환경산업기술원" not in html_content:
                logger.warning(f"페이지 {page_num}: 예상된 내용을 찾을 수 없습니다")
                return []
            
            announcements = self.parse_list_page(html_content)
            
            # 마지막 페이지 감지
            if not announcements and page_num > 1:
                logger.info(f"페이지 {page_num}에 공고가 없어 마지막 페이지로 판단됩니다")
            
            return announcements
            
        except Exception as e:
            logger.error(f"페이지 {page_num} 가져오기 중 오류: {e}")
            return []
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: 사이트 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """KEITI 특화된 목록 파싱 로직 - 실제 공지사항 테이블만 추출"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # KEITI 공지사항은 JavaScript로 렌더링되는 리스트 형태
        # View.do 링크를 포함한 모든 링크를 찾기
        view_links = soup.find_all('a', href=re.compile(r'/site/keiti/ex/board/View\.do\?cbIdx=277&bcIdx=\d+'))
        
        if not view_links:
            # cbIdx=277만 있는 경우도 확인
            view_links = soup.find_all('a', href=re.compile(r'/site/keiti/ex/board/View\.do.*bcIdx=\d+'))
        
        if not view_links:
            logger.warning("View.do 링크를 찾을 수 없습니다")
            # 디버깅을 위해 모든 링크 확인
            all_links = soup.find_all('a')
            view_count = 0
            for link in all_links[:10]:  # 처음 10개만 체크
                href = link.get('href', '')
                if 'View.do' in href:
                    view_count += 1
                    logger.debug(f"View.do 링크 발견: {href}")
            logger.info(f"총 View.do 링크 개수: {view_count}")
            return announcements
        
        logger.info(f"View.do 링크 {len(view_links)}개 발견")
        
        # 각 링크에서 공고 정보 추출
        for i, link in enumerate(view_links):
            try:
                # 제목 추출
                title = link.get_text(strip=True)
                if not title or len(title) < 5:
                    # 링크 텍스트가 짧으면 부모 요소에서 찾기
                    parent = link.parent
                    if parent:
                        title = parent.get_text(strip=True)
                        # 불필요한 텍스트 제거
                        title = re.sub(r'(공지|채용|입찰|공시송달)\s*\d{4}-\d{2}-\d{2}\s*', '', title).strip()
                
                if not title or len(title) < 5:
                    logger.debug(f"링크 {i}: 제목이 너무 짧음: '{title}'")
                    continue
                
                # URL 추출
                href = link.get('href')
                if href.startswith('/'):
                    detail_url = f"{self.base_url}{href}"
                else:
                    detail_url = href
                
                # 메타 정보 추출 (주변 텍스트에서)
                date = ""
                notice_type = ""
                
                # 부모 요소에서 날짜와 공고 유형 찾기
                parent = link.parent
                if parent:
                    parent_text = parent.get_text()
                    
                    # 날짜 패턴 찾기
                    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', parent_text)
                    if date_match:
                        date = date_match.group(1)
                    
                    # 공고 유형 찾기
                    type_match = re.search(r'^(공지|채용|입찰|공시송달)', parent_text.strip())
                    if type_match:
                        notice_type = type_match.group(1)
                
                logger.debug(f"링크 {i}: 공고 발견 - {title[:30]}... (날짜: {date})")
                
                # 공고 정보 구성
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'type': notice_type,
                    'date': date,
                    'summary': ""
                }
                
                announcements.append(announcement)
                
            except Exception as e:
                logger.error(f"링크 {i} 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str, announcement_url: str = None) -> Dict[str, Any]:
        """상세 페이지 파싱 - KEITI 실제 HTML 구조 기반"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 제목 추출 - 실제 HTML에서 찾기
        title = ""
        # 제목 후보들 검색
        for tag in ['h1', 'h2', 'h3', 'title']:
            title_elems = soup.find_all(tag)
            for elem in title_elems:
                text = elem.get_text(strip=True)
                if any(keyword in text for keyword in ['환경분야', '녹색기술', '모집', '공고', '지원']):
                    if len(text) > 10 and len(text) < 100:  # 적절한 제목 길이
                        title = text
                        break
            if title:
                break
        
        # 본문 내용 추출 - 실제 HTML 구조에서
        content = ""
        
        # 방법 1: 긴 텍스트를 포함한 div에서 본문 찾기
        for elem in soup.find_all(['div', 'section', 'article']):
            elem_text = elem.get_text(strip=True)
            
            # 본문 식별 조건: "환경부 공고"가 포함되고 충분히 긴 텍스트
            if '환경부 공고' in elem_text and len(elem_text) > 500:
                # 메타 정보와 네비게이션 제거
                clean_text = self._clean_keiti_content(elem_text)
                if len(clean_text) > 200:
                    content = clean_text
                    break
        
        # 방법 2: 백업 - 공고 번호가 포함된 텍스트 찾기
        if not content:
            all_text = soup.get_text()
            if '환경부 공고' in all_text:
                # 전체 텍스트에서 본문 부분만 추출
                content = self._extract_content_from_full_text(all_text)
        
        if not content or len(content) < 50:
            logger.warning("본문 영역을 찾을 수 없거나 내용이 부족합니다")
            content = "본문 내용을 추출할 수 없습니다."
        else:
            logger.info(f"본문 추출 성공: {len(content)}자")
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup, announcement_url)
        
        return {
            'title': title,
            'content': content,
            'attachments': attachments
        }
    
    def _clean_keiti_content(self, text: str) -> str:
        """KEITI 본문 텍스트 정리"""
        # 네비게이션 메뉴 제거
        nav_patterns = [
            r'공지/공고홈으로.*?공시송달',
            r'페이스북 바로가기.*?프린터 바로가기',
            r'전체공지채용입찰.*?공시송달',
            r'등록부서.*?조회수\d+',
            r'첨부파일.*?\.zip',
            r'이전글이 없습니다.*?목록바로가기',
            r'만족도 조사.*?TOP'
        ]
        
        for pattern in nav_patterns:
            text = re.sub(pattern, '', text, flags=re.DOTALL)
        
        # 본문 시작점 찾기 (환경부 공고부터)
        if '환경부 공고' in text:
            start_idx = text.find('환경부 공고')
            text = text[start_idx:]
        
        # 불필요한 연속 공백 제거
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        return text.strip()
    
    def _extract_content_from_full_text(self, full_text: str) -> str:
        """전체 텍스트에서 본문만 추출"""
        # 공고 시작점 찾기
        markers = ['환경부 공고', '한국환경산업기술원 공고']
        start_idx = -1
        
        for marker in markers:
            idx = full_text.find(marker)
            if idx != -1:
                start_idx = idx
                break
        
        if start_idx == -1:
            return ""
        
        # 본문 끝점 찾기 (문의처나 첨부파일 전까지)
        content = full_text[start_idx:]
        
        # 종료 지점들
        end_markers = [
            '이전글이 없습니다',
            '목록바로가기',
            '만족도 조사',
            '개인정보처리방침',
            'COPYRIGHT'
        ]
        
        for marker in end_markers:
            end_idx = content.find(marker)
            if end_idx != -1:
                content = content[:end_idx]
                break
        
        # 정리
        content = self._clean_keiti_content(content)
        
        return content
    
    def _extract_attachments(self, soup: BeautifulSoup, page_url: str = None) -> List[Dict[str, Any]]:
        """첨부파일 추출 - KEITI UUID 기반 다운로드"""
        attachments = []
        
        # URL에서 bcIdx와 cbIdx 추출
        bc_idx = ""
        cb_idx = "277"  # 기본값
        
        if page_url:
            parsed_url = urlparse(page_url)
            query_params = parse_qs(parsed_url.query)
            bc_idx = query_params.get('bcIdx', [''])[0]
            cb_idx = query_params.get('cbIdx', ['277'])[0]
        
        # 첨부파일 링크 찾기
        for link in soup.find_all('a'):
            href = link.get('href', '')
            
            # Download.do 패턴 확인
            if 'Download.do' in href:
                filename = link.get_text(strip=True)
                
                # 상대 URL을 절대 URL로 변환
                if href.startswith('/'):
                    download_url = f"{self.base_url}{href}"
                else:
                    download_url = href
                
                if filename:
                    attachments.append({
                        'name': filename,
                        'url': download_url
                    })
                    
                    logger.debug(f"첨부파일 발견: {filename}")
            
            # onclick 속성에서 JavaScript 함수 확인
            onclick = link.get('onclick', '')
            if 'doFileDown' in onclick or 'downloadFile' in onclick:
                filename = link.get_text(strip=True)
                
                # JavaScript 파라미터 추출
                # 예: doFileDown('uuid', 'filename')
                match = re.search(r"doFileDown\('([^']+)',\s*'([^']+)'\)", onclick)
                if match:
                    file_uuid = match.group(1)
                    file_name = match.group(2)
                    
                    download_url = f"{self.base_url}/common/board/Download.do?bcIdx={bc_idx}&cbIdx={cb_idx}&streFileNm={file_uuid}&fileNo=1"
                    
                    attachments.append({
                        'name': file_name or filename,
                        'url': download_url,
                        'uuid': file_uuid
                    })
                    
                    logger.debug(f"JavaScript 첨부파일 발견: {file_name or filename}")
        
        logger.info(f"총 {len(attachments)}개 첨부파일 발견")
        return attachments
    
    def get_page_content(self, url: str) -> str:
        """상세 페이지 내용 가져오기 - Playwright 사용"""
        try:
            if not self.page:
                self._start_browser()
            
            logger.info(f"상세 페이지 로드: {url}")
            self.page.goto(url, wait_until='networkidle', timeout=30000)
            
            # 페이지 로딩 확인
            time.sleep(1)
            
            html_content = self.page.content()
            
            # 디버깅을 위한 본문 영역 확인
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # term과 definition 태그 찾기
            term_elem = soup.find('term')
            definition_elem = soup.find('definition')
            
            logger.debug(f"term 태그 발견: {bool(term_elem)}")
            logger.debug(f"definition 태그 발견: {bool(definition_elem)}")
            
            if definition_elem:
                def_text = definition_elem.get_text(strip=True)
                logger.debug(f"definition 텍스트 길이: {len(def_text)}")
                logger.debug(f"definition 텍스트 일부: {def_text[:200]}...")
            
            return html_content
            
        except Exception as e:
            logger.error(f"페이지 로드 실패 {url}: {e}")
            return ""
    
    def _create_meta_info(self, announcement: Dict[str, Any]) -> str:
        """KEITI 메타 정보 생성"""
        meta_lines = [f"# {announcement['title']}", ""]
        
        # KEITI 특화 메타 정보
        if 'type' in announcement and announcement['type']:
            meta_lines.append(f"**공고유형**: {announcement['type']}")
        if 'date' in announcement and announcement['date']:
            meta_lines.append(f"**등록일**: {announcement['date']}")
        if 'summary' in announcement and announcement['summary']:
            meta_lines.append(f"**요약**: {announcement['summary']}")
        
        meta_lines.extend([
            f"**원본 URL**: {announcement['url']}",
            "",
            "---",
            ""
        ])
        
        return "\n".join(meta_lines)
    
    def scrape_pages(self, max_pages: int = 3, output_base: str = "output"):
        """페이지 스크래핑 실행 - 브라우저 컨텍스트 관리"""
        try:
            self._start_browser()
            super().scrape_pages(max_pages, output_base)
        finally:
            self._close_browser()

# 하위 호환성을 위한 별칭
KEITIScraper = EnhancedKEITIScraper