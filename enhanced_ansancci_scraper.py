# -*- coding: utf-8 -*-
"""
AnsanCCI(안산상공회의소) 스크래퍼 - Enhanced 버전
"""

import re
import os
import time
import urllib.parse
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from enhanced_base_scraper import StandardTableScraper
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class EnhancedAnsanCCIScraper(StandardTableScraper):
    """안산상공회의소 공지사항 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://ansancci.korcham.net"
        self.list_url = "https://ansancci.korcham.net/front/board/boardContentsListPage.do?boardId=10184&menuId=2922"
        
        # AnsanCCI 특화 설정
        self.verify_ssl = False  # SSL 인증서 문제
        self.default_encoding = 'utf-8'  # 페이지 인코딩
        self.timeout = 30
        self.delay_between_requests = 2  # JavaScript 렌더링 고려
        self.use_playwright = True  # JavaScript 필수
        
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - JavaScript 기반이므로 기본 URL 반환"""
        return self.list_url
    
    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱 - 표준 테이블 구조 처리 (수정된 버전)"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 공지사항 테이블 찾기 - "게시판 리스트 화면" 클래스 또는 테이블 구조로 찾기
        main_table = None
        
        # 1. 특정 테이블 클래스로 찾기
        main_table = soup.find('table', {'class': '게시판 리스트 화면'})
        if not main_table:
            main_table = soup.find('table', string=re.compile('게시판'))
        
        # 2. 백업: 충분한 행이 있는 테이블 찾기
        if not main_table:
            tables = soup.find_all('table')
            for table in tables:
                tbody = table.find('tbody')
                if tbody:
                    rows = tbody.find_all('tr')
                    if len(rows) > 5:  # 충분한 행이 있는 테이블
                        main_table = table
                        break
        
        if not main_table:
            logger.warning("공지사항 테이블을 찾을 수 없습니다.")
            return announcements
        
        # tbody가 있으면 tbody 사용, 없으면 table 전체 사용
        tbody = main_table.find('tbody')
        if not tbody:
            tbody = main_table
        
        rows = tbody.find_all('tr')
        logger.info(f"총 {len(rows)}개 행 발견")
        
        for i, row in enumerate(rows):
            try:
                cells = row.find_all(['td', 'th'])
                if len(cells) < 3:  # 최소 3개 컬럼 필요
                    logger.debug(f"행 {i}: 컬럼 수 부족 ({len(cells)}개)")
                    continue
                
                # 헤더 행 건너뛰기 (th 태그가 있는 행)
                if row.find('th'):
                    logger.debug(f"행 {i}: 헤더 행 건너뛰기")
                    continue
                
                # 번호 (첫 번째 셀) - "공지" 이미지가 있을 수 있음
                post_num_cell = cells[0]
                post_num = post_num_cell.get_text(strip=True)
                
                # 제목 셀 찾기 - AnsanCCI는 첨부파일 컬럼이 있어서 3번째 셀
                if len(cells) >= 4:
                    title_cell = cells[2]  # 번호, 첨부파일, 제목, 작성일 구조
                else:
                    title_cell = cells[1]  # 기본 구조
                
                # a 태그에서 href 속성 확인 (JavaScript 함수 포함)
                link_elem = title_cell.find('a')
                if not link_elem:
                    logger.debug(f"행 {i}: 링크 요소를 찾을 수 없음")
                    continue
                
                # href에서 JavaScript 함수 또는 onclick에서 추출
                href_attr = link_elem.get('href', '')
                onclick_attr = link_elem.get('onclick', '')
                
                # JavaScript 함수에서 공고 ID 추출
                announcement_id = None
                
                # 1. href에서 contentsView 함수 찾기
                if href_attr and 'contentsView' in href_attr:
                    match = re.search(r"contentsView\(['\"](\d+)['\"]\)", href_attr)
                    if match:
                        announcement_id = match.group(1)
                
                # 2. onclick에서 contentsView 함수 찾기
                if not announcement_id and onclick_attr and 'contentsView' in onclick_attr:
                    match = re.search(r"contentsView\(['\"](\d+)['\"]\)", onclick_attr)
                    if match:
                        announcement_id = match.group(1)
                
                # 3. href에서 직접 ID 추출 (contentsId 파라미터)
                if not announcement_id and href_attr:
                    match = re.search(r"contentsId=(\d+)", href_attr)
                    if match:
                        announcement_id = match.group(1)
                
                if not announcement_id:
                    logger.debug(f"행 {i}: 공고 ID를 추출할 수 없음 - href: {href_attr}, onclick: {onclick_attr}")
                    continue
                
                # 제목 텍스트 추출
                title = link_elem.get_text(strip=True)
                if not title:
                    title = title_cell.get_text(strip=True)
                
                if not title:
                    logger.debug(f"행 {i}: 제목이 비어있음")
                    continue
                
                # 상세 페이지 URL 구성
                detail_url = f"{self.base_url}/front/board/boardContentsView.do?boardId=10184&menuId=2922&contentsId={announcement_id}"
                
                # 작성일 - AnsanCCI는 4번째 셀
                if len(cells) >= 4:
                    date = cells[3].get_text(strip=True)  # 번호, 첨부파일, 제목, 작성일 구조
                else:
                    date = cells[2].get_text(strip=True) if len(cells) > 2 else ""  # 기본 구조
                
                # 추가 정보 (있는 경우) - AnsanCCI 컬럼 구조 고려
                author = ""
                views = ""
                if len(cells) >= 4:
                    # AnsanCCI: 번호, 첨부파일, 제목, 작성일 (4컬럼)
                    pass  # 작성자/조회수 정보 없음
                else:
                    # 기본 구조
                    if len(cells) > 3:
                        author = cells[3].get_text(strip=True)
                    if len(cells) > 4:
                        views = cells[4].get_text(strip=True)
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'post_num': post_num,
                    'announcement_id': announcement_id,
                    'date': date,
                    'author': author,
                    'views': views
                }
                
                announcements.append(announcement)
                logger.debug(f"공고 추가: {title}")
                
            except Exception as e:
                logger.error(f"행 {i} 파싱 중 오류: {e}")
                continue
        
        logger.info(f"총 {len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> dict:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 기본값
        title = ""
        content = ""
        metadata = {}
        
        # 상세 페이지의 테이블 구조에서 정보 추출
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            
            for row in rows:
                cells = row.find_all(['th', 'td'])
                if len(cells) >= 2:
                    header = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    
                    if '제목' in header or '제목' == header:
                        title = value
                    elif '작성자' in header:
                        metadata['author'] = value
                    elif '작성일' in header or '등록일' in header:
                        metadata['date'] = value
                    elif '조회수' in header:
                        metadata['views'] = value
                    elif '내용' in header:
                        # 내용 셀에서 텍스트 추출
                        content_cell = cells[1]
                        content = content_cell.get_text(strip=True)
        
        # 본문 내용이 비어있으면 다른 방법으로 찾기
        if not content.strip():
            # 긴 텍스트 블록 찾기
            all_text_elements = soup.find_all(['div', 'td', 'p'])
            for element in all_text_elements:
                element_text = element.get_text(strip=True)
                if len(element_text) > 100:  # 100자 이상인 텍스트
                    if not any(keyword in element_text for keyword in ['메뉴', '로그인', '회원가입', '홈', '게시판']):
                        if len(element_text) > len(content):
                            content = element_text
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup)
        
        # 본문이 비어있으면 기본 텍스트
        if not content.strip():
            content = "공고 내용을 확인하려면 첨부파일을 다운로드하여 확인하세요."
        
        # 마크다운 형태로 정리
        if content and not content.startswith('##'):
            content = f"## 공고 내용\n\n{content}\n\n"
        
        result = {
            'title': title,
            'content': content,
            'attachments': attachments,
            'metadata': metadata
        }
        
        logger.info(f"상세 페이지 파싱 완료 - 제목: {title}, 내용: {len(content)}자, 첨부파일: {len(attachments)}개")
        return result
    
    def _extract_attachments(self, soup: BeautifulSoup) -> list:
        """첨부파일 추출 - AnsanCCI 특화 패턴"""
        attachments = []
        
        # 첨부파일 섹션 찾기
        attachment_sections = []
        
        # "첨부파일" 텍스트가 있는 요소 찾기
        for element in soup.find_all(string=re.compile(r'첨부파일', re.I)):
            parent = element.parent
            while parent and parent.name not in ['tr', 'div', 'section']:
                parent = parent.parent
            if parent:
                attachment_sections.append(parent)
        
        # 백업: 테이블에서 "첨부파일" 행 찾기
        if not attachment_sections:
            for table in soup.find_all('table'):
                for row in table.find_all('tr'):
                    row_text = row.get_text()
                    if '첨부파일' in row_text:
                        attachment_sections.append(row)
        
        # 각 첨부파일 섹션에서 파일 링크 추출
        for section in attachment_sections:
            links = section.find_all('a')
            for link in links:
                href = link.get('href', '')
                
                # 파일 다운로드 링크 패턴 확인
                if '/file/dext5uploaddata/' in href or 'download' in href.lower():
                    # 파일명 추출
                    link_text = link.get_text(strip=True)
                    
                    # URL에서 파일명 추출 시도
                    filename = ""
                    if href:
                        try:
                            # URL에서 파일명 추출
                            parsed_url = urllib.parse.urlparse(href)
                            path_parts = parsed_url.path.split('/')
                            if path_parts:
                                potential_filename = path_parts[-1]
                                # 파일 확장자가 있는지 확인
                                if '.' in potential_filename and len(potential_filename.split('.')[-1]) <= 4:
                                    filename = potential_filename
                            
                            # 파일명이 없으면 링크 텍스트 사용
                            if not filename:
                                filename = link_text
                            
                        except Exception as e:
                            logger.warning(f"파일명 추출 실패: {e}")
                            filename = link_text
                    
                    # 파일명이 비어있으면 기본값 사용
                    if not filename.strip():
                        filename = f"attachment_{len(attachments) + 1}"
                    
                    # 상대 URL을 절대 URL로 변환
                    if href.startswith('/'):
                        file_url = self.base_url + href
                    elif href.startswith('http'):
                        file_url = href
                    else:
                        file_url = urljoin(self.base_url, href)
                    
                    attachment = {
                        'filename': filename,
                        'url': file_url
                    }
                    attachments.append(attachment)
                    logger.info(f"첨부파일 발견: {filename}")
        
        return attachments
    
    def navigate_to_page(self, page_num: int) -> bool:
        """JavaScript를 사용하여 특정 페이지로 이동"""
        if not hasattr(self, 'playwright_page') or not self.playwright_page:
            return False
        
        try:
            if page_num == 1:
                # 첫 페이지는 이미 로드되어 있음
                return True
            else:
                # go_Page() 함수 실행
                script = f"go_Page({page_num})"
                logger.info(f"페이지 {page_num}로 이동: {script}")
                self.playwright_page.evaluate(script)
                
                # 페이지 로딩 대기
                time.sleep(3)
                
                # 페이지가 제대로 로드되었는지 확인
                current_page_text = self.playwright_page.content()
                if "페이지를 찾을 수 없습니다" in current_page_text or "오류" in current_page_text:
                    logger.error(f"페이지 {page_num} 로드 실패")
                    return False
                
                return True
                
        except Exception as e:
            logger.error(f"페이지 {page_num} 이동 중 오류: {e}")
            return False
    
    def navigate_to_detail(self, announcement_id: str) -> str:
        """JavaScript를 사용하여 상세 페이지로 이동"""
        if not hasattr(self, 'playwright_page') or not self.playwright_page:
            return ""
        
        try:
            # contentsView() 함수 실행
            script = f"contentsView('{announcement_id}')"
            logger.info(f"상세 페이지로 이동: {script}")
            self.playwright_page.evaluate(script)
            
            # 페이지 로딩 대기
            time.sleep(2)
            
            # 상세 페이지 HTML 반환
            return self.playwright_page.content()
            
        except Exception as e:
            logger.error(f"상세 페이지 이동 중 오류: {e}")
            return ""
    
    def scrape_pages(self, max_pages: int = 3, output_base: str = 'output'):
        """페이지별 스크래핑 (Playwright 사용)"""
        if not self.use_playwright:
            return super().scrape_pages(max_pages, output_base)
        
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("Playwright가 설치되지 않았습니다. pip install playwright 후 playwright install 실행하세요.")
            return False
        
        success = True
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()
            
            # 페이지 객체를 클래스 속성으로 저장
            self.playwright_page = page
            
            try:
                # 첫 페이지 로드
                logger.info(f"첫 페이지 로드: {self.list_url}")
                page.goto(self.list_url, timeout=30000)
                page.wait_for_load_state('networkidle')
                
                for page_num in range(1, max_pages + 1):
                    logger.info(f"=== 페이지 {page_num} 처리 시작 ===")
                    
                    # 페이지 이동 (첫 페이지가 아닌 경우)
                    if page_num > 1:
                        if not self.navigate_to_page(page_num):
                            logger.error(f"페이지 {page_num} 이동 실패")
                            success = False
                            continue
                    
                    # 현재 페이지 HTML 가져오기
                    html_content = page.content()
                    
                    # 공고 목록 파싱
                    announcements = self.parse_list_page(html_content)
                    
                    if not announcements:
                        logger.warning(f"페이지 {page_num}에서 공고를 찾을 수 없습니다.")
                        continue
                    
                    logger.info(f"페이지 {page_num}: {len(announcements)}개 공고 발견")
                    
                    # 각 공고 처리
                    for index, announcement in enumerate(announcements, 1):
                        global_index = (page_num - 1) * len(announcements) + index
                        
                        # 중복 제목 확인 (부모 클래스에 메소드가 있는지 확인)
                        if hasattr(self, 'is_duplicate_title') and self.is_duplicate_title(announcement['title']):
                            logger.info(f"중복 제목 건너뛰기: {announcement['title']}")
                            continue
                        
                        try:
                            # 상세 페이지로 이동
                            detail_html = self.navigate_to_detail(announcement['announcement_id'])
                            if not detail_html:
                                logger.error(f"상세 페이지 로드 실패: {announcement['title']}")
                                continue
                            
                            # 상세 내용 파싱
                            detail = self.parse_detail_page(detail_html)
                            
                            # 폴더 생성 및 파일 저장
                            self._save_announcement_content(announcement, detail, global_index, output_base)
                            
                            # 목록 페이지로 돌아가기
                            page.go_back()
                            page.wait_for_load_state('networkidle')
                            
                            # 다시 해당 페이지로 이동 (필요한 경우)
                            if page_num > 1:
                                self.navigate_to_page(page_num)
                            
                            # 요청 간 대기
                            time.sleep(self.delay_between_requests)
                            
                        except Exception as e:
                            logger.error(f"공고 처리 중 오류 ({announcement['title']}): {e}")
                            success = False
                            continue
                    
                    logger.info(f"=== 페이지 {page_num} 처리 완료 ===")
                
            except Exception as e:
                logger.error(f"스크래핑 중 전체 오류: {e}")
                success = False
            
            finally:
                browser.close()
                if hasattr(self, 'playwright_page'):
                    delattr(self, 'playwright_page')
        
        return success
    
    def _save_announcement_content(self, announcement: dict, detail: dict, index: int, output_base: str):
        """공고 내용을 파일로 저장"""
        try:
            # 폴더명 생성 (번호_제목)
            safe_title = self._sanitize_filename(announcement['title'])
            folder_name = f"{index:03d}_{safe_title}"
            folder_path = os.path.join(output_base, folder_name)
            
            # 폴더 생성
            os.makedirs(folder_path, exist_ok=True)
            
            # 메타 정보 생성
            meta_info = {
                '제목': announcement['title'],
                '공고번호': announcement['post_num'],
                '공고ID': announcement['announcement_id'],
                '작성일': announcement['date'],
                '작성자': announcement.get('author', ''),
                '조회수': announcement.get('views', ''),
                '원본URL': announcement['url'],
                '수집일시': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                '첨부파일수': len(detail['attachments'])
            }
            
            # 본문 내용 구성
            content = f"# {announcement['title']}\n\n"
            
            # 메타 정보 추가
            content += "## 공고 정보\n\n"
            for key, value in meta_info.items():
                if value:
                    content += f"- **{key}**: {value}\n"
            content += "\n"
            
            # 상세 내용 추가
            if detail['content']:
                content += detail['content']
            else:
                content += "## 공고 내용\n\n상세 내용을 확인하려면 첨부파일을 다운로드하여 확인하세요.\n\n"
            
            # 첨부파일 정보 추가
            if detail['attachments']:
                content += "\n## 첨부파일\n\n"
                for i, attachment in enumerate(detail['attachments'], 1):
                    content += f"{i}. {attachment['filename']}\n"
                content += "\n"
            
            # 원본 URL 추가
            content += f"\n---\n원본 페이지: {announcement['url']}\n"
            
            # 마크다운 파일 저장
            md_file_path = os.path.join(folder_path, "content.md")
            with open(md_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 첨부파일 폴더 생성
            attachments_dir = os.path.join(folder_path, "attachments")
            if detail['attachments']:
                os.makedirs(attachments_dir, exist_ok=True)
            
            # 첨부파일 다운로드
            downloaded_count = 0
            for i, attachment in enumerate(detail['attachments'], 1):
                try:
                    file_url = attachment['url']
                    filename = attachment['filename']
                    
                    # 파일명 정리
                    safe_filename = self._sanitize_filename(filename)
                    if not safe_filename:
                        safe_filename = f"attachment_{i}"
                    
                    file_path = os.path.join(attachments_dir, safe_filename)
                    
                    # 파일 다운로드
                    if self.download_file(file_url, file_path):
                        downloaded_count += 1
                        logger.info(f"첨부파일 다운로드 완료: {filename}")
                    else:
                        logger.error(f"첨부파일 다운로드 실패: {filename}")
                        
                except Exception as e:
                    logger.error(f"첨부파일 다운로드 중 오류 ({attachment['filename']}): {e}")
            
            logger.info(f"공고 저장 완료: {announcement['title']} (첨부파일 {downloaded_count}/{len(detail['attachments'])}개)")
            
        except Exception as e:
            logger.error(f"공고 저장 중 오류 ({announcement['title']}): {e}")
    
    def _sanitize_filename(self, filename: str) -> str:
        """파일명 정리 (특수문자 제거)"""
        if not filename:
            return ""
        
        # 윈도우 파일시스템에서 사용할 수 없는 문자 제거
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # 연속된 공백을 하나로 변경
        filename = re.sub(r'\s+', ' ', filename).strip()
        
        # 길이 제한 (윈도우 경로 제한 고려)
        if len(filename) > 100:
            filename = filename[:100] + "..."
        
        return filename
    
    def download_file(self, url: str, file_path: str) -> bool:
        """파일 다운로드"""
        try:
            logger.debug(f"파일 다운로드 시도: {url}")
            response = self.session.get(url, stream=True, timeout=self.timeout, verify=self.verify_ssl)
            response.raise_for_status()
            
            # 파일 저장
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            return True
            
        except Exception as e:
            logger.error(f"파일 다운로드 실패 ({url}): {e}")
            return False

# 테스트용 함수
def test_ansancci_scraper(pages=3):
    """AnsanCCI 스크래퍼 테스트"""
    import os
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    scraper = EnhancedAnsanCCIScraper()
    output_dir = "output/ansancci"
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"AnsanCCI 스크래퍼 테스트 시작 - {pages}페이지")
    scraper.scrape_pages(max_pages=pages, output_base=output_dir)
    logger.info("AnsanCCI 스크래퍼 테스트 완료")

if __name__ == "__main__":
    test_ansancci_scraper(3)