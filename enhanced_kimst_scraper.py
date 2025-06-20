# -*- coding: utf-8 -*-
"""
KIMST 전용 Enhanced 스크래퍼
사이트: https://www.kimst.re.kr/u/news/inform_01/pjtAnuc.do
특징: 이중 시스템 구조 (KIMST 목록 + IRIS 상세), JavaScript 기반 파일 다운로드
"""

from enhanced_base_scraper import StandardTableScraper
from bs4 import BeautifulSoup
import requests
import os
import re
import time
import logging
from urllib.parse import urljoin, urlparse, parse_qs
from typing import Dict, List, Any
from playwright.sync_api import sync_playwright
import base64
import urllib3
import ssl
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.ssl_ import create_urllib3_context

# SSL 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SSLAdapter(HTTPAdapter):
    """SSL 호환성 문제 해결을 위한 커스텀 어댑터"""
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        context.set_ciphers("DEFAULT:@SECLEVEL=1")
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = context
        return super().init_poolmanager(*args, **kwargs)

logger = logging.getLogger(__name__)

class EnhancedKimstScraper(StandardTableScraper):
    """KIMST 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (fallback용)
        self.base_url = "https://www.kimst.re.kr"
        self.list_url = "https://www.kimst.re.kr/u/news/inform_01/pjtAnuc.do"
        self.iris_base_url = "https://www.iris.go.kr"
        
        # 사이트 특화 설정
        self.verify_ssl = False  # KIMST SSL 문제로 인한 설정
        self.default_encoding = 'utf-8'
        self.timeout = 30
        
        # KIMST 특화 헤더
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en;q=0.6',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # SSL 어댑터 적용
        self.session.mount("https://", SSLAdapter())
        
        # Playwright 설정
        self.playwright = None
        self.browser = None
        self.page = None
    
    def get_page(self, url: str, **kwargs) -> requests.Response:
        """KIMST 특화 페이지 가져오기 - SSL 검증 비활성화"""
        try:
            # SSL 검증 비활성화하여 요청
            response = self.session.get(
                url, 
                verify=False,  # SSL 검증 비활성화
                timeout=self.timeout,
                **kwargs
            )
            response.raise_for_status()
            return response
        except Exception as e:
            logger.error(f"페이지 가져오기 실패 {url}: {e}")
            return None
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - GET 파라미터 기반"""
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: KIMST는 page 파라미터 사용
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}?page={page_num}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - 테이블 기반"""
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """KIMST 특화 목록 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 메인 테이블 찾기 - KIMST는 단일 테이블 구조
        table = soup.find('table')
        if not table:
            logger.warning("공고 목록 테이블을 찾을 수 없습니다")
            return announcements
        
        # KIMST는 표준 HTML 테이블 구조 사용
        tbody = table.find('tbody')
        if not tbody:
            logger.warning("tbody를 찾을 수 없습니다")
            return announcements
        
        rows = tbody.find_all('tr')
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 3:  # 디버그 결과: 3개 컬럼 (번호, 제목, 일자)
                    continue
                
                # KIMST 실제 테이블 구조: [번호] [제목] [일자]
                # 디버그 결과에 따르면 3컬럼 구조
                num_cell = cells[0]      # 번호 (IRIS 공고번호)
                title_cell = cells[1]    # 제목 (공고명 + IRIS 링크)
                date_cell = cells[2]     # 일자
                
                # 제목 및 IRIS 링크 추출 - 표준 a 태그 사용
                link_elem = title_cell.find('a')
                if not link_elem:
                    logger.debug("링크를 찾을 수 없는 행 건너뛰기")
                    continue
                
                title = link_elem.get_text(strip=True)
                href = link_elem.get('href', '')
                
                if not title or not href:
                    continue
                
                # IRIS 상세 페이지 URL 추출 (이미 절대 경로)
                iris_url = href
                
                # IRIS URL 확인
                if 'iris.go.kr' not in iris_url:
                    logger.debug(f"IRIS가 아닌 링크: {iris_url}")
                    continue
                
                # 공고번호 추출
                num = num_cell.get_text(strip=True)
                
                # 일자 추출
                date = date_cell.get_text(strip=True)
                
                # ancmId 추출 (IRIS URL에서)
                ancm_id = None
                if 'ancmId=' in iris_url:
                    parsed = urlparse(iris_url)
                    params = parse_qs(parsed.query)
                    if 'ancmId' in params:
                        ancm_id = params['ancmId'][0]
                
                announcement = {
                    'title': title,
                    'url': iris_url,  # IRIS 상세 페이지 URL
                    'date': date,
                    'num': num,
                    'ancm_id': ancm_id,
                    'original_kimst_url': self.list_url  # 원본 KIMST URL 보존
                }
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱: {title[:50]}...")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱 - IRIS 시스템"""
        if self.config and self.config.selectors:
            return super().parse_detail_page(html_content)
        
        return self._parse_detail_fallback(html_content)
    
    def _parse_detail_fallback(self, html_content: str) -> Dict[str, Any]:
        """KIMST/IRIS 특화 상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # IRIS 상세 페이지에서 본문 추출
        content_area = None
        content_selectors = [
            '.view_content',
            '.detail_content',
            '.content_area',
            '.board_view',
            '#content',
            '.content'
        ]
        
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        if not content_area:
            # IRIS 특화: 테이블 기반 상세 정보 찾기
            tables = soup.find_all('table')
            for table in tables:
                # 충분한 텍스트가 있는 테이블 찾기
                table_text = table.get_text(strip=True)
                if len(table_text) > 300:  # IRIS는 상세 정보가 많음
                    content_area = table
                    logger.debug("테이블 기반으로 본문 영역 추정")
                    break
            
            if not content_area:
                # 최후 수단: body 전체
                content_area = soup.find('body')
                logger.warning("특정 본문 영역을 찾지 못해 body 전체 사용")
        
        # 본문을 마크다운으로 변환
        if content_area:
            # 불필요한 요소 제거
            for unwanted in content_area.find_all(['script', 'style', 'nav', 'header', 'footer']):
                unwanted.decompose()
            
            content_html = str(content_area)
            content_markdown = self.h.handle(content_html)
        else:
            content_markdown = "본문을 찾을 수 없습니다."
            logger.warning("본문 영역을 찾을 수 없음")
        
        # 첨부파일 추출 (IRIS 시스템)
        attachments = self._extract_attachments(soup)
        
        # 제목 추출 시도
        title = ""
        title_selectors = ['h1', 'h2', 'h3', '.title', '.subject', '.view_title']
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = title_elem.get_text(strip=True)
                if title:
                    break
        
        return {
            'title': title,
            'content': content_markdown,
            'attachments': attachments,
            'url': self.iris_base_url
        }
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """첨부파일 추출 - IRIS 시스템 특화"""
        attachments = []
        
        try:
            # IRIS 특화 JavaScript 함수 패턴 - onclick 이벤트에서 추출
            # onclick="javascript:f_bsnsAncm_downloadAtchFile('param1','param2','filename','filesize');"
            onclick_elements = soup.find_all(onclick=lambda x: x and 'f_bsnsAncm_downloadAtchFile' in x)
            
            for element in onclick_elements:
                onclick = element.get('onclick', '')
                
                # JavaScript 함수에서 파라미터 추출
                js_pattern = r"f_bsnsAncm_downloadAtchFile\(['\"]([^'\"]+)['\"],\s*['\"]([^'\"]+)['\"],\s*['\"]([^'\"]+)['\"],\s*['\"]([^'\"]+)['\"]"
                match = re.search(js_pattern, onclick)
                
                if match:
                    param1, param2, filename, filesize = match.groups()
                    
                    # JavaScript 전체를 URL로 사용 (Playwright에서 실행용)
                    js_url = onclick.strip()
                    if not js_url.startswith('javascript:'):
                        js_url = 'javascript:' + js_url
                    
                    attachments.append({
                        'name': filename,
                        'filename': filename,
                        'url': js_url,  # JavaScript 코드 전체
                        'type': 'iris_js_download',
                        'param1': param1,
                        'param2': param2,
                        'filesize': filesize
                    })
                    logger.debug(f"IRIS 첨부파일 발견: {filename} ({filesize})")
            
            # 추가 패턴: 일반적인 다운로드 링크들도 확인
            download_links = soup.find_all('a', href=lambda x: x and ('download' in x.lower() or '.pdf' in x or '.hwp' in x))
            
            seen_urls = set()
            for link in download_links:
                href = link.get('href', '')
                if href and href not in seen_urls:
                    file_url = urljoin(self.iris_base_url, href)
                    filename = link.get_text(strip=True) or os.path.basename(href)
                    
                    if filename and len(filename) > 2:
                        attachments.append({
                            'name': filename,
                            'filename': filename,
                            'url': file_url,
                            'type': 'direct_link'
                        })
                        seen_urls.add(href)
            
            logger.info(f"{len(attachments)}개 첨부파일 발견")
            for att in attachments:
                logger.debug(f"- {att['filename']} ({att.get('type', 'unknown')})")
            
        except Exception as e:
            logger.error(f"첨부파일 추출 중 오류: {e}")
        
        return attachments
    
    def _init_playwright(self):
        """Playwright 초기화"""
        if not self.playwright:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=True)
            self.page = self.browser.new_page()
            
            # 기본 헤더 설정
            self.page.set_extra_http_headers({
                'Accept-Language': 'ko-KR,ko;q=0.8,en;q=0.6',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
    
    def _close_playwright(self):
        """Playwright 정리"""
        if self.page:
            self.page.close()
            self.page = None
        if self.browser:
            self.browser.close()
            self.browser = None
        if self.playwright:
            self.playwright.stop()
            self.playwright = None
    
    def download_file(self, url: str, save_path: str, attachment: dict = None, **kwargs) -> bool:
        """첨부파일 다운로드 - IRIS 시스템 특화"""
        logger.info(f"파일 다운로드 시작: {attachment.get('filename', 'unknown') if attachment else 'unknown'}")
        
        try:
            # IRIS JavaScript 함수 기반 다운로드인지 확인
            if attachment and attachment.get('url', '').startswith('javascript:f_bsnsAncm_downloadAtchFile'):
                # kwargs에서 detail_url 추출 (우선순위)
                detail_url = kwargs.get('detail_url')
                
                # kwargs에 없으면 현재 공고에서 추출
                if not detail_url and hasattr(self, '_current_announcement') and self._current_announcement:
                    detail_url = self._current_announcement.get('url')
                
                if detail_url:
                    return self._download_iris_file_with_url(attachment, save_path, detail_url)
                else:
                    logger.error("IRIS 파일 다운로드에 필요한 상세 페이지 URL을 찾을 수 없습니다")
                    return False
            else:
                # 일반적인 다운로드
                return self._download_regular_file(url, save_path, attachment)
            
        except Exception as e:
            logger.error(f"파일 다운로드 실패: {e}")
            return False
    
    def _download_iris_file_with_url(self, attachment: dict, save_path: str, detail_url: str) -> bool:
        """IRIS JavaScript 함수 기반 파일 다운로드 (URL 지정)"""
        try:
            self._init_playwright()
            
            # IRIS 상세 페이지로 이동
            if detail_url:
                self.page.goto(detail_url)
                self.page.wait_for_load_state('networkidle')
                
                # 다운로드 이벤트 대기 설정
                with self.page.expect_download(timeout=30000) as download_info:
                    # JavaScript URL에서 함수 부분만 추출하여 실행
                    js_url = attachment.get('url', '')
                    if js_url.startswith('javascript:'):
                        js_code = js_url[11:]  # 'javascript:' 제거
                    else:
                        js_code = js_url
                    
                    # JavaScript 함수 실행
                    self.page.evaluate(js_code)
                
                download = download_info.value
                
                # 파일 저장
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                download.save_as(save_path)
                
                file_size = os.path.getsize(save_path)
                logger.info(f"다운로드 완료: {save_path} ({file_size:,} bytes)")
                
                return True
            else:
                logger.error("상세 페이지 URL이 제공되지 않았습니다")
                return False
            
        except Exception as e:
            logger.error(f"IRIS 파일 다운로드 실패: {e}")
            return False
    
    def _download_regular_file(self, url: str, save_path: str, attachment: dict = None) -> bool:
        """일반적인 파일 다운로드"""
        try:
            # IRIS 파일 다운로드 헤더 설정
            download_headers = self.session.headers.copy()
            download_headers.update({
                'Referer': self.iris_base_url,
                'Accept': 'application/pdf,application/zip,application/octet-stream,*/*',
            })
            
            response = self.session.get(
                url,
                headers=download_headers,
                timeout=self.timeout,
                verify=self.verify_ssl,
                stream=True
            )
            
            response.raise_for_status()
            
            # 스트리밍 다운로드
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(save_path)
            logger.info(f"다운로드 완료: {save_path} ({file_size:,} bytes)")
            
            return True
            
        except Exception as e:
            logger.error(f"일반 파일 다운로드 실패: {e}")
            return False
    
    def _download_attachments(self, attachments: List[Dict[str, Any]], folder_path: str, detail_url: str = None):
        """첨부파일 다운로드 - KIMST 특화 (detail_url 전달)"""
        if not attachments:
            logger.info("첨부파일이 없습니다")
            return

        logger.info(f"{len(attachments)}개 첨부파일 다운로드 시작")
        attachments_folder = os.path.join(folder_path, 'attachments')
        os.makedirs(attachments_folder, exist_ok=True)

        for i, attachment in enumerate(attachments):
            try:
                logger.info(f"  첨부파일 {i+1}: {attachment['name']}")
                
                # 파일명 처리
                file_name = self.sanitize_filename(attachment['name'])
                if not file_name or file_name.isspace():
                    file_name = f"attachment_{i+1}"
                
                file_path = os.path.join(attachments_folder, file_name)
                
                # 파일 다운로드 - detail_url 전달
                success = self.download_file(
                    attachment['url'], 
                    file_path, 
                    attachment,
                    detail_url=detail_url  # KIMST 전용: IRIS 상세 페이지 URL 전달
                )
                
                if success:
                    logger.info(f"첨부파일 저장: {file_name}")
                else:
                    logger.warning(f"첨부파일 다운로드 실패: {attachment['name']}")
                
                # 요청 간격 (서버 부하 방지)
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"첨부파일 다운로드 중 오류: {e}")
                continue
    
    def process_announcement(self, announcement: Dict[str, Any], index: int, output_base: str = 'output'):
        """개별 공고 처리 - KIMST 특화 버전 (베이스 클래스 오버라이드)"""
        logger.info(f"공고 처리 중 {index}: {announcement['title']}")
        
        # 폴더 생성 - 파일시스템 제한을 고려한 제목 길이 조정
        folder_title = self.sanitize_filename(announcement['title'])[:100]  # 100자로 단축
        folder_name = f"{index:03d}_{folder_title}"
        
        # 최종 폴더명이 200자 이하가 되도록 추가 조정
        if len(folder_name) > 200:
            # 인덱스 부분(4자) + 언더스코어(1자) = 5자를 제외하고 195자로 제한
            folder_title = folder_title[:195]
            folder_name = f"{index:03d}_{folder_title}"
        
        folder_path = os.path.join(output_base, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        # 상세 페이지 가져오기
        detail_url = announcement.get('url', '')
        response = self.get_page(detail_url)
        if not response:
            logger.error(f"상세 페이지 가져오기 실패: {announcement['title']}")
            return
        
        # 상세 내용 파싱
        try:
            detail = self.parse_detail_page(response.text)
            logger.info(f"상세 페이지 파싱 완료 - 내용길이: {len(detail['content'])}, 첨부파일: {len(detail['attachments'])}")
        except Exception as e:
            logger.error(f"상세 페이지 파싱 실패: {e}")
            return
        
        # content.md 파일 생성
        content_file = os.path.join(folder_path, 'content.md')
        
        # 메타데이터 생성
        meta_content = self._create_meta_info(announcement)
        
        # 전체 마크다운 내용
        full_content = meta_content + detail['content']
        
        # content.md 저장
        with open(content_file, 'w', encoding='utf-8') as f:
            f.write(full_content)
        logger.info(f"내용 저장 완료: {content_file}")
        
        # 첨부파일 다운로드 - detail_url 전달
        self._download_attachments(detail['attachments'], folder_path, detail_url)
        
        # 처리한 제목을 기록
        self.add_processed_title(announcement['title'])
    
    def _create_meta_info(self, announcement: Dict[str, Any]) -> str:
        """KIMST 특화 메타 정보 생성"""
        meta_lines = [f"# {announcement['title']}", ""]
        
        # KIMST 특화 메타 정보
        if announcement.get('num'):
            meta_lines.append(f"**공고번호**: {announcement['num']}")
        if announcement.get('date'):
            meta_lines.append(f"**일자**: {announcement['date']}")
        
        meta_lines.extend([
            f"**원본 URL**: {announcement['url']}",
            f"**KIMST 목록 URL**: {announcement.get('original_kimst_url', 'N/A')}",
            "",
            "---",
            ""
        ])
        
        return "\n".join(meta_lines)
    
    def __del__(self):
        """소멸자에서 Playwright 정리"""
        self._close_playwright()


# 하위 호환성을 위한 별칭
KimstScraper = EnhancedKimstScraper