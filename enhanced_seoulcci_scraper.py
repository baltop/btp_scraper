# -*- coding: utf-8 -*-
"""
서울상공회의소(SeoulCCI) 스크래퍼 - Enhanced 버전
"""

import re
import os
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from enhanced_base_scraper import StandardTableScraper
import logging

logger = logging.getLogger(__name__)

class EnhancedSeoulCCIScraper(StandardTableScraper):
    """서울상공회의소 공지사항 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.korcham.net"
        self.list_url = "https://www.korcham.net/nCham/Service/Kcci/appl/KcciNoticeList.asp"
        
        # SeoulCCI 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'euc-kr'  # ASP 사이트는 주로 EUC-KR
        self.timeout = 30
        self.delay_between_requests = 2
        
        # JavaScript 기반 상세 페이지 접근을 위한 기본 URL
        self.detail_base_url = "https://www.korcham.net/nCham/Service/Kcci/appl/KcciNoticeDetail.asp"
        
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 (JavaScript 기반 페이지네이션)"""
        if page_num == 1:
            return self.list_url
        else:
            # JavaScript page() 함수 기반 페이지네이션 처리
            return self.list_url
    
    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱 - JavaScript 렌더링된 내용도 고려"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 먼저 기본적인 테이블 구조 찾기
        # ASP 사이트 특성상 다양한 테이블 구조 시도
        tables = soup.find_all('table')
        target_table = None
        
        # 목록 테이블 찾기 - 다양한 방법으로 시도
        for table in tables:
            # caption이 '목록'인 테이블 찾기
            caption = table.find('caption')
            if caption and '목록' in caption.get_text():
                target_table = table
                break
            
            # class가 '목록'인 테이블 찾기
            if table.get('class') and '목록' in str(table.get('class')):
                target_table = table
                break
                
            # 헤더에 '번호', '제목' 등이 있는 테이블 찾기
            thead = table.find('thead')
            if thead:
                header_text = thead.get_text()
                if '번호' in header_text and '제목' in header_text:
                    target_table = table
                    break
        
        if not target_table:
            logger.warning("목록 테이블을 찾을 수 없습니다. JavaScript 렌더링이 필요할 수 있습니다.")
            return self._parse_with_playwright()
        
        tbody = target_table.find('tbody')
        if not tbody:
            tbody = target_table
            
        rows = tbody.find_all('tr')
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        if not rows:
            logger.warning("행을 찾을 수 없습니다. JavaScript 렌더링이 필요할 수 있습니다.")
            return self._parse_with_playwright()
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 4:  # 번호, 제목, 담당부서, 등록일
                    continue
                
                # 번호 (첫 번째 셀)
                number = cells[0].get_text(strip=True)
                if not number or not number.replace(',', '').isdigit():
                    continue
                
                # 제목 셀 (두 번째 셀)
                title_cell = cells[1]
                link_elem = title_cell.find('a')
                
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                if not title:
                    continue
                
                # href에서 goDetail ID 추출 (javascript:goDetail('ID') 패턴)
                href = link_elem.get('href', '')
                onclick = link_elem.get('onclick', '')
                article_id = None
                
                # href에서 먼저 시도 (주요 패턴)
                if href and 'goDetail' in href:
                    match = re.search(r"javascript:goDetail\s*\(\s*['\"]([^'\"]+)['\"]", href)
                    if match:
                        article_id = match.group(1)
                
                # onclick에서 시도 (fallback)
                if not article_id and onclick and 'goDetail' in onclick:
                    match = re.search(r"goDetail\s*\(\s*['\"]([^'\"]+)['\"]", onclick)
                    if match:
                        article_id = match.group(1)
                
                if not article_id:
                    logger.warning(f"기사 ID를 찾을 수 없습니다: {title}")
                    continue
                
                # 담당부서 (세 번째 셀)
                department_cell = cells[2]
                department = department_cell.get_text(strip=True)
                
                # 등록일 (네 번째 셀)
                date_cell = cells[3]
                date = date_cell.get_text(strip=True)
                
                # 상세 페이지 URL은 JavaScript로만 접근 가능
                detail_url = f"javascript:goDetail('{article_id}')"
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'date': date,
                    'number': number,
                    'department': department,
                    'article_id': article_id
                }
                
                announcements.append(announcement)
                logger.debug(f"공고 추가: {title}")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"총 {len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def _parse_with_playwright(self):
        """Playwright를 사용한 JavaScript 렌더링 후 파싱"""
        try:
            from playwright.sync_api import sync_playwright
            
            announcements = []
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # 페이지 로드
                page.goto(self.list_url)
                page.wait_for_load_state('networkidle')
                
                # 테이블 요소들 추출 - 다양한 선택자 시도
                rows = []
                
                # 여러 방법으로 행 찾기
                selectors = [
                    'table[caption*="목록"] tbody tr',
                    'table.목록 tbody tr',
                    'table tbody tr',
                    'tbody tr',
                    'table tr'
                ]
                
                for selector in selectors:
                    temp_rows = page.locator(selector).all()
                    if temp_rows and len(temp_rows) > 5:  # 최소 5개 이상의 행이 있어야 유효
                        rows = temp_rows
                        logger.info(f"Playwright로 '{selector}' 선택자로 {len(rows)}개 행 발견")
                        break
                
                if not rows:
                    logger.warning("Playwright로도 행을 찾을 수 없습니다.")
                    return []
                
                for i, row in enumerate(rows):
                    try:
                        # 셀 찾기
                        cells = row.locator('td').all()
                        if len(cells) < 4:  # 번호, 제목, 담당부서, 등록일
                            logger.debug(f"행 {i}: 셀 수 부족 ({len(cells)}개)")
                            continue
                        
                        # 번호
                        number = cells[0].inner_text().strip()
                        if not number or not number.replace(',', '').isdigit():
                            logger.debug(f"행 {i}: 번호가 유효하지 않음: {number}")
                            continue
                        
                        # 제목과 링크
                        title_cell = cells[1]
                        links = title_cell.locator('a').all()
                        if not links:
                            logger.debug(f"행 {i}: 링크를 찾을 수 없음")
                            continue
                        
                        link = links[0]  # 첫 번째 링크 사용
                        title = link.inner_text().strip()
                        if not title:
                            logger.debug(f"행 {i}: 제목이 비어있음")
                            continue
                        
                        # href와 onclick에서 article ID 추출
                        href = link.get_attribute('href') or ''
                        onclick = link.get_attribute('onclick') or ''
                        article_id = None
                        
                        # href에서 먼저 시도 (주요 패턴)
                        if href and 'goDetail' in href:
                            match = re.search(r"javascript:goDetail\s*\(\s*['\"]([^'\"]+)['\"]", href)
                            if match:
                                article_id = match.group(1)
                        
                        # onclick에서 시도 (fallback)
                        if not article_id and onclick and 'goDetail' in onclick:
                            match = re.search(r"goDetail\s*\(\s*['\"]([^'\"]+)['\"]", onclick)
                            if match:
                                article_id = match.group(1)
                        
                        if not article_id:
                            logger.debug(f"행 {i}: 기사 ID를 찾을 수 없음 (onclick: {onclick[:100] if onclick else 'None'})")
                            continue
                        
                        # 담당부서
                        department = cells[2].inner_text().strip()
                        
                        # 등록일
                        date = cells[3].inner_text().strip()
                        
                        detail_url = f"javascript:goDetail('{article_id}')"
                        
                        announcement = {
                            'title': title,
                            'url': detail_url,
                            'date': date,
                            'number': number,
                            'department': department,
                            'article_id': article_id
                        }
                        
                        announcements.append(announcement)
                        logger.info(f"공고 추가: {title}")
                        
                    except Exception as e:
                        logger.error(f"Playwright 행 {i} 파싱 중 오류: {e}")
                        continue
                
                browser.close()
            
            logger.info(f"Playwright로 {len(announcements)}개 공고 파싱 완료")
            return announcements
            
        except ImportError:
            logger.error("Playwright가 설치되지 않았습니다. pip install playwright 후 playwright install 실행하세요.")
            return []
        except Exception as e:
            logger.error(f"Playwright 파싱 중 오류: {e}")
            return []
    
    def get_detail_page_with_playwright(self, article_id: str) -> str:
        """Playwright를 사용해서 상세 페이지 가져오기"""
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # 목록 페이지로 이동
                page.goto(self.list_url)
                page.wait_for_load_state('networkidle')
                
                # JavaScript 함수로 상세 페이지 클릭
                try:
                    # goDetail JavaScript 함수 실행
                    page.evaluate(f"goDetail('{article_id}')")
                    
                    # 페이지 전환 대기 - URL 변경을 기다림
                    page.wait_for_url("**/KcciNoticeDetail.asp**", timeout=10000)
                    page.wait_for_load_state('networkidle', timeout=10000)
                    
                    # 추가 대기시간
                    page.wait_for_timeout(2000)
                    
                except Exception as e:
                    logger.warning(f"JavaScript 함수 실행 또는 페이지 전환 실패: {e}")
                    # 직접 URL로 접근 시도 (불가능할 수 있음)
                    logger.error("직접 URL 접근은 지원되지 않습니다.")
                    return ""
                
                # 페이지 내용 가져오기
                html_content = page.content()
                browser.close()
                
                logger.info(f"상세 페이지 HTML 길이: {len(html_content)}")
                return html_content
                
        except Exception as e:
            logger.error(f"Playwright 상세 페이지 가져오기 실패: {e}")
            return ""
    
    def navigate_to_page(self, page_num: int):
        """Playwright를 사용하여 특정 페이지로 이동"""
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # 목록 페이지로 이동
                page.goto(self.list_url)
                page.wait_for_load_state('networkidle')
                
                if page_num > 1:
                    # JavaScript page() 함수 실행
                    page.evaluate(f"page('{page_num}')")
                    page.wait_for_load_state('networkidle')
                    
                    # 추가 대기시간
                    page.wait_for_timeout(2000)
                
                # 페이지 내용 가져오기
                html_content = page.content()
                browser.close()
                
                return html_content
                
        except Exception as e:
            logger.error(f"페이지 {page_num} 이동 실패: {e}")
            return ""
    
    def parse_detail_page(self, html_content: str) -> dict:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 내용 찾기
        content = ""
        title = ""
        
        # 상세보기에서 제목 추출
        title_elem = soup.find('h3')
        if title_elem:
            title = title_elem.get_text(strip=True)
        
        # 본문 내용 추출 - 다양한 패턴 시도
        content_areas = [
            soup.find('div', class_='detail-content'),
            soup.find('table'),
            soup.find('td')
        ]
        
        for area in content_areas:
            if area:
                area_text = area.get_text(strip=True)
                if len(area_text) > 100:  # 긴 내용만 본문으로 간주
                    # HTML을 마크다운으로 변환
                    paragraphs = area.find_all(['p', 'div'])
                    if paragraphs:
                        content_parts = []
                        for p in paragraphs:
                            p_text = p.get_text(strip=True)
                            if p_text and len(p_text) > 10:
                                content_parts.append(p_text)
                        content = '\n\n'.join(content_parts)
                    else:
                        # p 태그가 없는 경우 전체 텍스트 사용
                        content = area_text
                    
                    # 불필요한 공백 정리
                    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
                    break
        
        # 첨부파일 찾기
        attachments = []
        
        # JavaScript down() 함수가 포함된 링크 찾기
        download_links = soup.find_all('a', href=re.compile(r'javascript:down'))
        for link in download_links:
            href = link.get('href', '')
            filename = link.get_text(strip=True)
            
            if href and filename:
                # down('filename.hwp','20250620') 패턴에서 파라미터 추출
                match = re.search(r"down\s*\(\s*['\"]([^'\"]+)['\"][,\s]*['\"]([^'\"]*)['\"]", href)
                if match:
                    file_name = match.group(1)
                    date_param = match.group(2)
                    
                    attachment = {
                        'filename': file_name,
                        'url': href,  # JavaScript 함수 그대로 저장
                        'date_param': date_param
                    }
                    attachments.append(attachment)
                    logger.info(f"첨부파일 발견: {file_name}")
        
        # 본문이 비어있으면 기본 텍스트 추가
        if not content.strip():
            content = "## 공고 내용\n\n공고 내용을 확인하려면 첨부파일을 다운로드하여 확인하세요.\n\n"
        else:
            # 마크다운 형태로 정리
            content = f"## 공고 내용\n\n{content}\n\n"
        
        result = {
            'title': title,
            'content': content,
            'attachments': attachments
        }
        
        logger.info(f"상세 페이지 파싱 완료 - 제목: {title}, 내용: {len(content)}자, 첨부파일: {len(attachments)}개")
        return result
    
    def process_announcement(self, announcement: dict, index: int, output_base: str = 'output', browser_page=None):
        """개별 공고 처리 - Playwright 사용 (브라우저 페이지 재사용)"""
        logger.info(f"공고 처리 중 {index}: {announcement['title']}")
        
        # 폴더 생성
        folder_title = self.sanitize_filename(announcement['title'])[:100]
        folder_name = f"{index:03d}_{folder_title}"
        
        if len(folder_name) > 200:
            folder_title = folder_title[:195]
            folder_name = f"{index:03d}_{folder_title}"
        
        folder_path = os.path.join(output_base, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        # 브라우저 페이지를 사용하여 상세 페이지 가져오기
        article_id = announcement.get('article_id')
        if article_id and browser_page:
            html_content = self.get_detail_page_with_existing_browser(browser_page, article_id)
            if not html_content:
                logger.error(f"상세 페이지 가져오기 실패: {announcement['title']}")
                # 기본 콘텐츠라도 저장
                self._save_basic_content(announcement, folder_path)
                return
        else:
            logger.error(f"기사 ID가 없거나 브라우저 페이지가 없습니다: {announcement['title']}")
            # 기본 콘텐츠라도 저장
            self._save_basic_content(announcement, folder_path)
            return
        
        # 상세 내용 파싱
        try:
            detail = self.parse_detail_page(html_content)
            logger.info(f"상세 페이지 파싱 완료 - 내용길이: {len(detail['content'])}, 첨부파일: {len(detail['attachments'])}")
            
            # HTML 길이 검증
            if len(html_content) < 1000:
                logger.warning(f"HTML 내용이 너무 짧습니다: {len(html_content)}자")
                
            # 파싱 결과 검증
            if not detail.get('content') or len(detail['content']) < 50:
                logger.warning(f"파싱된 내용이 부족합니다: {len(detail.get('content', ''))}자")
                
        except Exception as e:
            logger.error(f"상세 페이지 파싱 실패: {e}")
            # 기본 콘텐츠로라도 저장
            detail = {
                'title': announcement.get('title', ''),
                'content': "## 공고 내용\n\n상세 내용을 가져올 수 없습니다. 원본 페이지를 확인해주세요.\n\n",
                'attachments': []
            }
        
        # 메타 정보 생성
        meta_info = self._create_meta_info(announcement)
        
        # 본문 저장
        content_path = os.path.join(folder_path, 'content.md')
        with open(content_path, 'w', encoding='utf-8') as f:
            f.write(meta_info + detail['content'])
        
        logger.info(f"내용 저장 완료: {content_path}")
        
        # 첨부파일 다운로드 (JavaScript 기반이라 실제 다운로드는 제한됨)
        self._download_attachments_seoulcci(detail['attachments'], folder_path)
        
        # 처리된 제목으로 추가
        self.add_processed_title(announcement['title'])
        
        # 요청 간 대기
        if self.delay_between_requests > 0:
            time.sleep(self.delay_between_requests)
    
    def _download_attachments_seoulcci(self, attachments: list, folder_path: str):
        """서울상공회의소 첨부파일 다운로드 (JavaScript 제한으로 인해 정보만 저장)"""
        if not attachments:
            return
        
        # 첨부파일 정보를 텍스트 파일로 저장
        attachments_info_path = os.path.join(folder_path, 'attachments_info.txt')
        with open(attachments_info_path, 'w', encoding='utf-8') as f:
            f.write("첨부파일 정보\n")
            f.write("=" * 50 + "\n\n")
            
            for i, attachment in enumerate(attachments, 1):
                f.write(f"{i}. 파일명: {attachment['filename']}\n")
                f.write(f"   다운로드 함수: {attachment['url']}\n")
                if attachment.get('date_param'):
                    f.write(f"   날짜 파라미터: {attachment['date_param']}\n")
                f.write("\n")
            
            f.write("\n주의: JavaScript 기반 다운로드로 인해 자동 다운로드가 제한됩니다.\n")
            f.write("실제 파일 다운로드는 브라우저에서 수동으로 수행해야 합니다.\n")
        
        logger.info(f"첨부파일 정보 저장 완료: {attachments_info_path}")
    
    def get_detail_page_with_existing_browser(self, page, article_id: str) -> str:
        """기존 브라우저 페이지를 사용해서 상세 페이지 가져오기"""
        try:
            # JavaScript 함수로 상세 페이지 클릭
            try:
                # goDetail JavaScript 함수 실행
                page.evaluate(f"goDetail('{article_id}')")
                
                # 페이지 전환 대기 - URL 변경을 기다림
                page.wait_for_url("**/KcciNoticeDetail.asp**", timeout=10000)
                page.wait_for_load_state('networkidle', timeout=10000)
                
                # 추가 대기시간
                page.wait_for_timeout(2000)
                
            except Exception as e:
                logger.warning(f"JavaScript 함수 실행 또는 페이지 전환 실패: {e}")
                # 서울상공회의소는 직접 URL 접근이 어려움
                return ""
            
            # 페이지 내용 가져오기
            html_content = page.content()
            
            logger.info(f"상세 페이지 HTML 길이: {len(html_content)}")
            return html_content
            
        except Exception as e:
            logger.error(f"기존 브라우저로 상세 페이지 가져오기 실패: {e}")
            return ""
    
    def _save_basic_content(self, announcement: dict, folder_path: str):
        """기본 콘텐츠 저장 (상세 페이지 가져오기 실패 시)"""
        # 메타 정보 생성
        meta_info = self._create_meta_info(announcement)
        
        # 기본 본문 내용
        basic_content = "## 공고 내용\n\n상세 내용을 가져올 수 없습니다.\n\n"
        basic_content += "JavaScript 기반 ASP 사이트의 특성상 상세 페이지 접근이 제한됩니다.\n\n"
        basic_content += "실제 내용은 아래 URL에서 확인해주세요:\n\n"
        basic_content += f"- 원본 페이지: {self.list_url}\n"
        basic_content += f"- 기사 ID: {announcement.get('article_id', 'N/A')}\n\n"
        
        # 본문 저장
        content_path = os.path.join(folder_path, 'content.md')
        with open(content_path, 'w', encoding='utf-8') as f:
            f.write(meta_info + basic_content)
        
        logger.info(f"기본 내용 저장 완료: {content_path}")
        
        # 처리된 제목으로 추가
        self.add_processed_title(announcement['title'])
    
    def scrape_pages(self, max_pages: int = 3, output_base: str = 'output') -> bool:
        """페이지별 스크래핑 실행 - Playwright 기반"""
        logger.info(f"스크래핑 시작: 최대 {max_pages}페이지")
        
        # 기존 처리된 공고 로드
        processed_count = self.load_processed_titles()
        if processed_count is None:
            processed_count = 0
        logger.info(f"기존 처리된 공고 {processed_count}개 로드")
        
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                for page_num in range(1, max_pages + 1):
                    logger.info(f"페이지 {page_num} 처리 중")
                    
                    # 페이지 이동
                    page.goto(self.list_url)
                    page.wait_for_load_state('networkidle')
                    
                    if page_num > 1:
                        # JavaScript page() 함수 실행
                        page.evaluate(f"page('{page_num}')")
                        page.wait_for_load_state('networkidle')
                        page.wait_for_timeout(2000)
                    
                    # 현재 페이지 내용 파싱
                    html_content = page.content()
                    announcements = self.parse_list_page(html_content)
                    
                    if not announcements:
                        logger.warning(f"페이지 {page_num}에서 공고를 찾을 수 없습니다.")
                        continue
                    
                    logger.info(f"페이지 {page_num}에서 {len(announcements)}개 공고 발견")
                    
                    # 중복 체크
                    new_announcements = []
                    consecutive_duplicates = 0
                    
                    for announcement in announcements:
                        if self.is_title_processed(announcement['title']):
                            consecutive_duplicates += 1
                            logger.debug(f"중복 공고 건너뜀: {announcement['title']}")
                            if consecutive_duplicates >= 3:
                                logger.info("중복 공고 3개 연속 발견 - 조기 종료 신호")
                                break
                        else:
                            consecutive_duplicates = 0
                            new_announcements.append(announcement)
                    
                    logger.info(f"전체 {len(announcements)}개 중 새로운 공고 {len(new_announcements)}개, 이전 실행 중복 {consecutive_duplicates}개 발견")
                    
                    # 조기 종료 조건
                    if consecutive_duplicates >= 3:
                        logger.info("중복 공고 3개 연속 발견으로 조기 종료")
                        break
                    
                    # 새로운 공고 처리 (브라우저 페이지 재사용)
                    for i, announcement in enumerate(new_announcements, 1):
                        try:
                            self.process_announcement(announcement, i, output_base, page)
                        except Exception as e:
                            logger.error(f"공고 처리 실패 ({announcement['title']}): {e}")
                            continue
                    
                    # 페이지 간 대기
                    time.sleep(self.delay_between_requests)
                
                browser.close()
                
        except ImportError:
            logger.error("Playwright가 설치되지 않았습니다.")
            return False
        except Exception as e:
            logger.error(f"스크래핑 중 오류: {e}")
            return False
        
        # 처리된 제목 저장
        saved_count = self.save_processed_titles()
        if saved_count is None:
            saved_count = 0
        logger.info(f"처리된 제목 {saved_count}개 저장 완료 (이전: {processed_count}, 현재 세션: {saved_count - processed_count})")
        
        total_processed = saved_count - processed_count
        logger.info(f"스크래핑 완료: 총 {total_processed}개 새로운 공고 처리")
        
        return True

# 테스트용 함수
def test_seoulcci_scraper(pages=3):
    """SeoulCCI 스크래퍼 테스트"""
    import os
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    scraper = EnhancedSeoulCCIScraper()
    output_dir = "output/seoulcci"
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"SeoulCCI 스크래퍼 테스트 시작 - {pages}페이지")
    scraper.scrape_pages(max_pages=pages, output_base=output_dir)
    logger.info("SeoulCCI 스크래퍼 테스트 완료")

if __name__ == "__main__":
    test_seoulcci_scraper(3)