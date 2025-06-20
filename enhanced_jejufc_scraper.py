# -*- coding: utf-8 -*-
"""
제주콘텐츠진흥원(JEJUFC) Enhanced 스크래퍼 - JavaScript 기반 동적 사이트
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

class EnhancedJEJUFCScraper(StandardTableScraper):
    """제주콘텐츠진흥원(JEJUFC) 전용 스크래퍼 - 향상된 버전"""
    
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
        self.base_url = "https://jejufc.onlinekoreahrd.kr"
        self.list_url = "https://jejufc.onlinekoreahrd.kr/studyCenter/bbs.php?boardCode=1"
        
        # 사이트 특화 설정
        self.verify_ssl = True  # HTTPS 사이트, SSL 인증서 정상
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
        
        # Fallback: JEJUFC는 JavaScript pageMove() 함수 사용
        return self.list_url  # 기본 URL, 페이지네이션은 JavaScript로 처리
    
    def _get_page_announcements(self, page_num: int) -> List[Dict[str, Any]]:
        """페이지별 공고 목록 가져오기 - Playwright 사용"""
        try:
            if not self.page:
                self._start_browser()
            
            # 첫 페이지는 직접 접속
            if page_num == 1:
                logger.info(f"첫 페이지 로드: {self.list_url}")
                self.page.goto(self.list_url, wait_until='networkidle', timeout=30000)
                
                # JavaScript 렌더링 완료 대기
                self.page.wait_for_selector('table', timeout=30000)
                time.sleep(2)  # 추가 대기
            else:
                # 2페이지부터는 JavaScript 함수 실행
                logger.info(f"페이지 {page_num}로 이동")
                try:
                    # pageMove() 함수 실행
                    self.page.evaluate(f"pageMove({page_num})")
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
            
            # 콘텐츠 영역 확인
            if "contentsArea" not in html_content:
                logger.warning(f"페이지 {page_num}: 콘텐츠 영역을 찾을 수 없습니다")
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
        """JEJUFC 특화된 목록 파싱 로직"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 테이블 찾기 - JEJUFC는 표준 table 구조
        table = soup.find('table')
        if not table:
            logger.warning("공고 목록 테이블을 찾을 수 없습니다")
            return announcements
        
        # tbody에서 행 찾기
        tbody = table.find('tbody')
        if not tbody:
            logger.warning("테이블 tbody를 찾을 수 없습니다")
            return announcements
        
        rows = tbody.find_all('tr')
        if not rows:
            logger.warning("테이블 행을 찾을 수 없습니다")
            return announcements
        
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for i, row in enumerate(rows):
            try:
                cells = row.find_all('td')
                if len(cells) < 4:  # 번호, 카테고리, 제목, 작성일, 조회수 최소 4개 필요
                    logger.debug(f"행 {i}: 셀 수 부족 ({len(cells)}개)")
                    continue
                
                # 제목 셀에서 onclick 이벤트 찾기 (세 번째 셀)
                title_cell = cells[2] if len(cells) > 2 else cells[1]
                
                # 제목 추출
                title = title_cell.get_text(strip=True)
                
                if not title or len(title) < 3:
                    logger.debug(f"행 {i}: 제목이 너무 짧음: '{title}'")
                    continue
                
                # onclick 이벤트에서 ID 추출
                onclick = title_cell.get('onclick', '')
                if not onclick:
                    logger.debug(f"행 {i}: onclick 이벤트를 찾을 수 없음")
                    continue
                
                # viewAct(ID) 패턴에서 ID 추출
                match = re.search(r"viewAct\((\d+)\)", onclick)
                if not match:
                    logger.debug(f"행 {i}: viewAct 함수에서 ID 추출 실패: {onclick}")
                    continue
                
                view_id = match.group(1)
                # JEJUFC는 인라인 상세 보기이므로 JavaScript 실행이 필요한 가상 URL 생성
                detail_url = f"{self.base_url}/studyCenter/bbs.php?boardCode=1&viewId={view_id}"
                
                # 공고 번호 추출 (첫 번째 셀)
                number = ""
                number_cell = cells[0]
                if number_cell:
                    number_text = number_cell.get_text(strip=True)
                    if number_text and number_text != "번호":
                        number = number_text
                
                # 카테고리 추출 (두 번째 셀)
                category = ""
                if len(cells) > 1:
                    category_cell = cells[1]
                    category = category_cell.get_text(strip=True)
                
                # 작성일 추출 (네 번째 셀)
                date = ""
                if len(cells) > 3:
                    date_cell = cells[3]
                    date_text = date_cell.get_text(strip=True)
                    # 날짜 패턴 매칭 (YYYY-MM-DD)
                    date_match = re.search(r'(\d{4}-\d{1,2}-\d{1,2})', date_text)
                    if date_match:
                        date = date_match.group(1)
                
                # 조회수 추출 (다섯 번째 셀)
                views = ""
                if len(cells) > 4:
                    views_cell = cells[4]
                    views = views_cell.get_text(strip=True)
                
                # 첨부파일 여부 확인 (제목 셀에서 아이콘 확인)
                has_attachment = False
                attachment_icon = title_cell.find('img')
                if attachment_icon:
                    icon_src = attachment_icon.get('src', '')
                    if 'attach' in icon_src.lower() or 'file' in icon_src.lower():
                        has_attachment = True
                
                logger.debug(f"행 {i}: 공고 발견 - {title[:30]}... (날짜: {date})")
                
                # 공고 정보 구성
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'number': number,
                    'category': category,
                    'date': date,
                    'views': views,
                    'has_attachment': has_attachment,
                    'summary': ""
                }
                
                announcements.append(announcement)
                
            except Exception as e:
                logger.error(f"행 {i} 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str, announcement_url: str = None, original_title: str = None) -> Dict[str, Any]:
        """상세 페이지 파싱 - JEJUFC 인라인 상세 보기 구조 기반"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 제목 추출 - 인라인 상세 보기에서는 h1 태그에 전체 제목이 있음
        title = ""
        
        # 방법 1: 상세 보기 영역의 제목 찾기 - h1 태그 내에서 카테고리 제외한 부분
        detail_title = soup.find('h1')
        if detail_title:
            title_text = detail_title.get_text(strip=True)
            # 카테고리와 나머지 부분 분리
            if ']' in title_text:
                # [ 카테고리 ] 제목 패턴
                parts = title_text.split(']', 1)
                if len(parts) > 1:
                    title = parts[1].strip()
                else:
                    title = title_text
            else:
                title = title_text
            logger.debug(f"인라인 상세 보기에서 제목 추출: {title[:50]}...")
        
        # 방법 2: 백업 - 다른 헤딩 태그에서 찾기
        if not title or len(title) < 5:
            for tag in ['h2', 'h3', 'h4']:
                title_elem = soup.find(tag)
                if title_elem:
                    title_text = title_elem.get_text(strip=True)
                    if title_text and len(title_text) > 5:
                        if ']' in title_text:
                            parts = title_text.split(']', 1)
                            title = parts[1].strip() if len(parts) > 1 else title_text
                        else:
                            title = title_text
                        logger.debug(f"백업 방법으로 제목을 {tag}에서 찾음: {title[:50]}...")
                        break
        
        # 방법 3: 원래 공고 제목 사용 (fallback)
        if (not title or len(title) < 5) and original_title:
            title = original_title
            logger.debug(f"원래 공고 제목 사용: {title[:50]}...")
        
        # 본문 내용 추출 - 인라인 상세 보기의 본문 영역
        content = ""
        
        # 방법 1: 상세 보기 본문 영역 찾기 (보통 제목 다음의 div들)
        content_divs = []
        
        # 제목 다음의 p 태그들을 찾아서 본문으로 사용
        for p_tag in soup.find_all('p'):
            p_text = p_tag.get_text(strip=True)
            if p_text and len(p_text) > 10:  # 의미있는 텍스트
                # 날짜나 숫자만 있는 것은 제외
                if not re.match(r'^\d{4}-\d{2}-\d{2}.*\d+$', p_text):
                    content_divs.append(p_text)
        
        if content_divs:
            content = "\n\n".join(content_divs)
            logger.debug(f"상세 보기에서 {len(content_divs)}개 문단 추출")
        
        # 방법 2: 백업 - 긴 텍스트 영역 찾기
        if not content or len(content) < 100:
            for elem in soup.find_all(['div', 'section', 'article']):
                elem_text = elem.get_text(strip=True)
                if len(elem_text) > 200 and any(keyword in elem_text for keyword in ['교육', '공지', '안내', '모집', '신청', '활용', '방법']):
                    content = elem_text
                    logger.debug(f"백업 방법으로 본문 추출: {len(content)}자")
                    break
        
        # 방법 3: 최후 수단 - 전체 텍스트에서 의미있는 부분 추출
        if not content or len(content) < 50:
            all_text = soup.get_text()
            # 본문 시작점 찾기
            content_start_patterns = [
                r'한국중앙인재개발원.*?(?=\n|$)',  # 기관명으로 시작
                r'[^\n]*(?:교육|공지|안내|모집|신청|활용|방법)[^\n]*(?:\n.*?){0,20}',  # 키워드 포함 문장들
            ]
            
            for pattern in content_start_patterns:
                matches = re.findall(pattern, all_text, re.DOTALL)
                if matches:
                    content = matches[0][:2000]  # 적당한 길이로 제한
                    logger.debug(f"패턴 매칭으로 본문 추출: {len(content)}자")
                    break
        
        if not content or len(content) < 30:
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
    
    def process_announcement(self, announcement: Dict[str, Any], index: int, output_base: str = 'output') -> None:
        """공고 처리 - 원래 제목 전달을 위한 오버라이드"""
        try:
            logger.info(f"공고 처리 시작: {announcement['title'][:50]}...")
            
            # 원본 제목 저장
            original_title = announcement['title']
            
            # 상세 페이지 URL에서 콘텐츠 가져오기
            response_text = self.get_page_content(announcement['url'])
            if not response_text:
                logger.error("상세 페이지 내용을 가져올 수 없습니다")
                return
            
            # 상세 페이지 파싱 - 원래 제목 전달
            detail = self.parse_detail_page(response_text, announcement['url'], original_title)
            logger.info(f"상세 페이지 파싱 완료 - 내용길이: {len(detail['content'])}, 첨부파일: {len(detail['attachments'])}")
        except Exception as e:
            logger.error(f"상세 페이지 파싱 실패: {e}")
            return
        
        # 폴더명 생성 - 숫자 인덱스 없이 제목만 사용
        folder_title = self.sanitize_filename(announcement['title'])[:100]
        # viewId를 인덱스 대신 사용
        view_id = announcement['url'].split('viewId=')[1] if 'viewId=' in announcement['url'] else '000'
        folder_name = f"{view_id}_{folder_title}"
        output_folder = os.path.join(output_base, folder_name)
        
        # 출력 폴더 생성
        os.makedirs(output_folder, exist_ok=True)
        
        # 첨부파일 폴더 생성
        attachments_folder = os.path.join(output_folder, 'attachments')
        
        # 메타 정보 생성
        meta_info = self._create_meta_info(announcement)
        
        # content.md 파일 생성
        content_md = meta_info + detail['content']
        content_file_path = os.path.join(output_folder, 'content.md')
        
        try:
            with open(content_file_path, 'w', encoding='utf-8') as f:
                f.write(content_md)
            logger.info(f"content.md 저장 완료: {content_file_path}")
        except Exception as e:
            logger.error(f"content.md 저장 실패: {e}")
            return
        
        # 첨부파일 다운로드
        if detail['attachments']:
            os.makedirs(attachments_folder, exist_ok=True)
            
            for attachment in detail['attachments']:
                try:
                    filename = attachment['name']
                    download_url = attachment['url']
                    
                    # 안전한 파일명 생성
                    safe_filename = self.sanitize_filename(filename)
                    file_path = os.path.join(attachments_folder, safe_filename)
                    
                    if self.download_file(download_url, file_path, filename):
                        logger.info(f"첨부파일 다운로드 성공: {safe_filename}")
                    else:
                        logger.warning(f"첨부파일 다운로드 실패: {filename}")
                        
                except Exception as e:
                    logger.error(f"첨부파일 처리 중 오류: {e}")
        
        logger.info(f"공고 처리 완료: {folder_name}")
    
    def _extract_attachments(self, soup: BeautifulSoup, page_url: str = None) -> List[Dict[str, Any]]:
        """첨부파일 추출 - JEJUFC PHP 기반 다운로드"""
        attachments = []
        
        # PHP 파일 다운로드 링크 찾기 (fileDownLoad.php 패턴)
        for link in soup.find_all('a'):
            href = link.get('href', '')
            
            # 파일 다운로드 링크 확인
            if 'fileDownLoad.php' in href:
                # 파일명 추출 (링크 텍스트에서)
                filename = link.get_text(strip=True)
                
                # 절대 URL로 변환
                if href.startswith('../'):
                    # ../lib/fileDownLoad.php -> /studyCenter/lib/fileDownLoad.php
                    download_url = f"{self.base_url}/studyCenter/{href[3:]}"
                elif href.startswith('/'):
                    download_url = f"{self.base_url}{href}"
                else:
                    download_url = urljoin(self.base_url, href)
                
                if filename and download_url:
                    attachments.append({
                        'name': filename,
                        'url': download_url
                    })
                    
                    logger.debug(f"PHP 첨부파일 발견: {filename}")
        
        # 다른 다운로드 패턴도 확인 (직접 링크)
        for link in soup.find_all('a'):
            href = link.get('href', '')
            filename = link.get_text(strip=True)
            
            # 파일 확장자가 있는 직접 링크 확인
            if any(ext in href.lower() for ext in ['.pdf', '.hwp', '.doc', '.xls', '.zip', '.jpg', '.png']):
                download_url = urljoin(self.base_url, href)
                
                if filename:
                    attachments.append({
                        'name': filename,
                        'url': download_url
                    })
                    
                    logger.debug(f"직접 다운로드 링크 발견: {filename}")
        
        logger.info(f"총 {len(attachments)}개 첨부파일 발견")
        return attachments
    
    def get_page_content(self, url: str) -> str:
        """상세 페이지 내용 가져오기 - JavaScript viewAct 실행"""
        try:
            if not self.page:
                self._start_browser()
            
            # URL에서 viewId 추출
            if 'viewId=' in url:
                view_id = url.split('viewId=')[1]
                logger.info(f"JavaScript viewAct({view_id}) 실행")
                
                # 먼저 목록 페이지로 이동 (필요한 경우)
                current_url = self.page.url
                if 'bbs.php?boardCode=1' not in current_url:
                    self.page.goto(self.list_url, wait_until='networkidle', timeout=30000)
                    time.sleep(1)
                
                # JavaScript viewAct 함수 실행
                self.page.evaluate(f"viewAct({view_id})")
                
                # 상세 내용 로딩 대기
                time.sleep(3)  # 상세 내용이 AJAX로 로딩되므로 대기
                
                html_content = self.page.content()
                return html_content
            else:
                # 일반 URL인 경우 기존 방식 사용
                logger.info(f"상세 페이지 로드: {url}")
                self.page.goto(url, wait_until='networkidle', timeout=30000)
                time.sleep(1)
                html_content = self.page.content()
                return html_content
            
        except Exception as e:
            logger.error(f"페이지 로드 실패 {url}: {e}")
            return ""
    
    def download_file(self, url: str, save_path: str, filename: str = None) -> bool:
        """파일 다운로드 - JEJUFC PHP 다운로드 처리"""
        try:
            logger.info(f"파일 다운로드 시도: {url}")
            
            # 강화된 헤더로 다운로드 시도
            download_headers = self.headers.copy()
            download_headers.update({
                'Referer': self.base_url,
                'Accept': '*/*',
            })
            
            response = self.session.get(
                url, 
                headers=download_headers,
                verify=self.verify_ssl,
                stream=True,
                timeout=120
            )
            
            # 응답 상태 확인
            if response.status_code != 200:
                logger.error(f"파일 다운로드 실패 {url}: HTTP {response.status_code}")
                return False
            
            # Content-Type 확인
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' in content_type:
                logger.warning(f"HTML 응답 수신 (파일 다운로드 실패?): {url}")
                # PHP 에러 페이지일 가능성이 있지만 일단 시도
            
            # 파일 저장
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # 파일 크기 확인
            file_size = os.path.getsize(save_path)
            if file_size == 0:
                logger.error(f"다운로드된 파일이 비어있음: {save_path}")
                os.remove(save_path)
                return False
            
            logger.info(f"파일 다운로드 완료: {save_path} ({file_size:,} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"파일 다운로드 중 오류 {url}: {e}")
            return False
    
    def _create_meta_info(self, announcement: Dict[str, Any]) -> str:
        """JEJUFC 메타 정보 생성"""
        meta_lines = [f"# {announcement['title']}", ""]
        
        # JEJUFC 특화 메타 정보
        if 'number' in announcement and announcement['number']:
            meta_lines.append(f"**공고번호**: {announcement['number']}")
        if 'category' in announcement and announcement['category']:
            meta_lines.append(f"**카테고리**: {announcement['category']}")
        if 'date' in announcement and announcement['date']:
            meta_lines.append(f"**작성일**: {announcement['date']}")
        if 'views' in announcement and announcement['views']:
            meta_lines.append(f"**조회수**: {announcement['views']}")
        if 'has_attachment' in announcement and announcement['has_attachment']:
            meta_lines.append(f"**첨부파일**: 있음")
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
JEJUFCScraper = EnhancedJEJUFCScraper