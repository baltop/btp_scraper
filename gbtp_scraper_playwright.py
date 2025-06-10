import os
import time
import re
import html2text
from pathlib import Path
from urllib.parse import urljoin
from base_scraper import BaseScraper

class GBTPPlaywrightScraper(BaseScraper):
    """경북테크노파크 스크래퍼 - Playwright 버전 (JavaScript 실행 지원)"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://gbtp.or.kr"
        self.list_url = "https://gbtp.or.kr/user/board.do?bbsId=BBSMSTR_000000000023"
        self.playwright = None
        self.browser = None
        self.page = None
        self.h = html2text.HTML2Text()
        self.h.ignore_links = False
        self.h.ignore_images = False
        
    def _init_playwright(self):
        """Playwright 초기화"""
        try:
            from playwright.sync_api import sync_playwright
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=True,  # headless=False로 변경하면 브라우저 창이 보임
                args=['--ignore-certificate-errors', '--disable-web-security']
            )
            self.page = self.browser.new_page()
            
            # 사용자 에이전트 설정
            self.page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            
            print("Playwright initialized successfully")
            return True
        except ImportError:
            print("Playwright not installed. Please install with: pip install playwright")
            print("And then run: playwright install chromium")
            return False
        except Exception as e:
            print(f"Failed to initialize Playwright: {e}")
            return False
    
    def _close_playwright(self):
        """Playwright 정리"""
        try:
            if self.page:
                self.page.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            print("Playwright closed successfully")
        except Exception as e:
            print(f"Error closing Playwright: {e}")
    
    def get_list_url(self, page_num):
        """페이지 번호에 따른 목록 URL 반환"""
        if page_num == 1:
            return self.list_url
        return f"{self.list_url}&pageIndex={page_num}"
        
    def parse_list_page_playwright(self, page_num):
        """Playwright로 목록 페이지 파싱"""
        try:
            url = self.get_list_url(page_num)
            print(f"Loading list page: {url}")
            
            self.page.goto(url, wait_until="networkidle", timeout=30000)
            
            # 테이블이 로드될 때까지 대기
            self.page.wait_for_selector('table.board-list, table', timeout=10000)
            
            announcements = []
            
            # 테이블 행들 가져오기
            rows = self.page.query_selector_all('table tbody tr, table tr')
            
            for i, row in enumerate(rows):
                try:
                    cells = row.query_selector_all('td')
                    if len(cells) < 6:  # 최소 6개 컬럼 필요
                        continue
                    
                    # 번호 (첫 번째 td)
                    number_cell = cells[0]
                    number = number_cell.inner_text().strip()
                    
                    # 숫자가 아니면 헤더 행이므로 스킵
                    if not number.isdigit():
                        continue
                    
                    # 상태 (두 번째 td)
                    status_cell = cells[1]
                    status = status_cell.inner_text().strip()
                    
                    # 제목 및 링크 (세 번째 td)
                    title_cell = cells[2]
                    title_link = title_cell.query_selector('a')
                    if not title_link:
                        continue
                        
                    title = title_link.inner_text().strip()
                    onclick = title_link.get_attribute('onclick') or ''
                    
                    # onclick 속성에서 파라미터 추출
                    if onclick:
                        match = re.search(r"fn_detail\('([^']+)',\s*'([^']+)'\)", onclick)
                        if match:
                            bbs_seq = match.group(1)
                            page_index = match.group(2)
                        else:
                            print(f"Could not parse onclick: {onclick}")
                            continue
                    else:
                        print(f"No onclick found for title: {title}")
                        continue
                    
                    # 공고기간 (네 번째 td)
                    period_cell = cells[3]
                    period = period_cell.inner_text().strip()
                    
                    # 조회수 (다섯 번째 td)
                    hits_cell = cells[4]
                    hits = hits_cell.inner_text().strip()
                    
                    # 첨부파일 여부 (여섯 번째 td)
                    file_cell = cells[5]
                    file_icon = file_cell.query_selector('i.fa-file-download, i.far.fa-file-download')
                    has_attachment = bool(file_icon)
                    
                    # 작성자 (일곱 번째 td, 있는 경우)
                    writer = ""
                    if len(cells) > 6:
                        writer_cell = cells[6]
                        writer = writer_cell.inner_text().strip()
                    
                    announcement = {
                        'number': number,
                        'title': title,
                        'bbs_seq': bbs_seq,
                        'page_index': page_index,
                        'status': status,
                        'period': period,
                        'hits': hits,
                        'writer': writer,
                        'has_attachment': has_attachment,
                        'onclick': onclick
                    }
                    
                    announcements.append(announcement)
                    
                except Exception as e:
                    print(f"Error parsing row {i}: {e}")
                    continue
            
            return announcements
            
        except Exception as e:
            print(f"Error parsing list page: {e}")
            return []
    
    def get_detail_page_content(self, bbs_seq, page_index):
        """JavaScript 실행으로 상세 페이지 내용 가져오기"""
        try:
            print(f"Getting detail page for bbsSeq={bbs_seq}, pageIndex={page_index}")
            
            # JavaScript 함수 실행
            self.page.evaluate(f"fn_detail('{bbs_seq}', '{page_index}')")
            
            # 페이지 내용이 변경될 때까지 대기
            time.sleep(2)
            
            # 상세 페이지 내용 추출
            content = ""
            attachments = []
            
            # 본문 내용 추출 시도
            content_selectors = [
                '#contentDiv',
                '.board-view .view-content',
                '.board-view .content',
                '.view-content',
                '.content-area',
                '.board-content'
            ]
            
            content_element = None
            for selector in content_selectors:
                content_element = self.page.query_selector(selector)
                if content_element:
                    break
            
            if content_element:
                content_html = content_element.inner_html()
                content = self.h.handle(content_html)
            else:
                # 전체 페이지에서 추출
                body_html = self.page.query_selector('body').inner_html()
                content = self.h.handle(body_html)
            
            # 첨부파일 링크 찾기
            download_links = self.page.query_selector_all('a[onclick*="fn_egov_downFile"], a[href*="fn_egov_downFile"], .view_file_download')
            
            for link in download_links:
                try:
                    onclick = link.get_attribute('onclick') or ''
                    href = link.get_attribute('href') or ''
                    
                    # fn_egov_downFile('atchFileId', 'fileSn') 패턴 추출
                    pattern = r"fn_egov_downFile\('([^']+)',\s*'([^']+)'\)"
                    match = re.search(pattern, onclick + href)
                    
                    if match:
                        atch_file_id = match.group(1)
                        file_sn = match.group(2)
                        
                        # 다운로드 URL 생성
                        download_url = f"{self.base_url}/cmm/fms/FileDown.do?atchFileId={atch_file_id}&fileSn={file_sn}"
                        
                        # 파일명 추출
                        file_name = link.inner_text().strip()
                        
                        # 파일명 정리 ([붙임1] 등 제거)
                        file_name = re.sub(r'^\s*\[?붙임\d*\]?\s*', '', file_name).strip()
                        
                        if not file_name or file_name in ['다운로드', '첨부파일', '']:
                            file_name = f"attachment_{file_sn}"
                        
                        attachments.append({
                            'name': file_name,
                            'url': download_url,
                            'atch_file_id': atch_file_id,
                            'file_sn': file_sn
                        })
                        
                except Exception as e:
                    print(f"Error parsing attachment link: {e}")
                    continue
            
            return {
                'content': content,
                'attachments': attachments
            }
            
        except Exception as e:
            print(f"Error getting detail page content: {e}")
            return {'content': '', 'attachments': []}
    
    def download_file_playwright(self, atch_file_id, file_sn, save_path):
        """Playwright를 사용한 파일 다운로드 - JavaScript 함수 실행"""
        try:
            print(f"Downloading file: atchFileId={atch_file_id}, fileSn={file_sn}")
            
            # 다운로드 디렉토리 생성
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # JavaScript 함수로 다운로드 시도
            with self.page.expect_download(timeout=30000) as download_info:
                self.page.evaluate(f"fn_egov_downFile('{atch_file_id}', '{file_sn}')")
            
            download = download_info.value
            
            # 파일 저장
            download.save_as(save_path)
            
            file_size = os.path.getsize(save_path)
            print(f"Downloaded: {save_path} ({file_size:,} bytes)")
            return True
            
        except Exception as e:
            print(f"Error downloading file (JS method) {atch_file_id}/{file_sn}: {e}")
            
            # 대안: 직접 URL 접근 시도
            try:
                print("Trying direct URL access...")
                url = f"{self.base_url}/cmm/fms/FileDown.do?atchFileId={atch_file_id}&fileSn={file_sn}"
                
                # HTTP 요청으로 다운로드 시도
                import requests
                response = requests.get(url, verify=False, timeout=30)
                
                if response.status_code == 200:
                    with open(save_path, 'wb') as f:
                        f.write(response.content)
                    
                    file_size = os.path.getsize(save_path)
                    print(f"Downloaded via HTTP: {save_path} ({file_size:,} bytes)")
                    return True
                else:
                    print(f"HTTP download failed: {response.status_code}")
                    return False
                    
            except Exception as e2:
                print(f"Alternative download method also failed: {e2}")
                return False
    
    def process_announcement_playwright(self, announcement, index, output_base='output'):
        """Playwright를 사용한 공고 처리"""
        print(f"\nProcessing announcement {index}: {announcement['title']}")
        
        # 폴더 생성
        folder_title = self.sanitize_filename(announcement['title'])[:50]
        folder_name = f"{index:03d}_{folder_title}"
        folder_path = os.path.join(output_base, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        # 상세 페이지 내용 가져오기
        detail = self.get_detail_page_content(announcement['bbs_seq'], announcement['page_index'])
        
        print(f"Detail content length: {len(detail['content'])}, attachments: {len(detail['attachments'])}")
        
        # 메타 정보 생성
        meta_info = f"""# {announcement['title']}

**작성자**: {announcement.get('writer', 'N/A')}  
**작성일**: N/A  
**접수기간**: {announcement.get('period', 'N/A')}  
**상태**: {announcement.get('status', 'N/A')}  
**조회수**: {announcement.get('hits', 'N/A')}  
**원본 사이트**: GBTP (경북테크노파크)

---

"""
        
        # 본문 저장
        content_path = os.path.join(folder_path, 'content.md')
        with open(content_path, 'w', encoding='utf-8') as f:
            f.write(meta_info + detail['content'])
        
        print(f"Saved content to: {content_path}")
        
        # 첨부파일 다운로드
        if detail['attachments']:
            print(f"Found {len(detail['attachments'])} attachment(s)")
            attachments_folder = os.path.join(folder_path, 'attachments')
            os.makedirs(attachments_folder, exist_ok=True)
            
            for i, attachment in enumerate(detail['attachments']):
                print(f"  Attachment {i+1}: {attachment['name']}")
                
                # 파일명 정리
                file_name = self.sanitize_filename(attachment['name'])
                if not file_name or file_name.isspace():
                    file_name = f"attachment_{i+1}"
                
                file_path = os.path.join(attachments_folder, file_name)
                
                # 파일 다운로드
                success = self.download_file_playwright(
                    attachment['atch_file_id'], 
                    attachment['file_sn'], 
                    file_path
                )
                if not success:
                    print(f"    Failed to download: {attachment['name']}")
        else:
            print("No attachments found")
        
        # 목록 페이지로 돌아가기
        self.page.goto(self.get_list_url(1), wait_until="networkidle")
        time.sleep(1)  # 안정성을 위한 대기
    
    def scrape_pages_playwright(self, max_pages=4, output_base='output'):
        """Playwright를 사용한 페이지 스크래핑"""
        if not self._init_playwright():
            print("Playwright 초기화 실패. 기본 스크래퍼로 전환하거나 Playwright를 설치하세요.")
            return
        
        try:
            announcement_count = 0
            
            for page_num in range(1, max_pages + 1):
                print(f"\n{'='*50}")
                print(f"Processing page {page_num}")
                print(f"{'='*50}")
                
                # 목록 페이지 파싱
                announcements = self.parse_list_page_playwright(page_num)
                
                if not announcements:
                    print(f"No announcements found on page {page_num}")
                    break
                
                print(f"Found {len(announcements)} announcements on page {page_num}")
                
                # 각 공고 처리
                for ann in announcements:
                    announcement_count += 1
                    self.process_announcement_playwright(ann, announcement_count, output_base)
                
                # 다음 페이지로 이동 전 대기
                if page_num < max_pages:
                    time.sleep(2)
            
            print(f"\n{'='*50}")
            print(f"Scraping completed. Total announcements processed: {announcement_count}")
            print(f"{'='*50}")
            
        except Exception as e:
            print(f"Error during scraping: {e}")
        finally:
            self._close_playwright()
    
    # 기존 BaseScraper 메소드들 (호환성을 위해 유지)
    def parse_list_page(self, html_content):
        """기존 메소드 - Playwright 버전에서는 사용하지 않음"""
        return []
    
    def parse_detail_page(self, html_content):
        """기존 메소드 - Playwright 버전에서는 사용하지 않음"""
        return {'content': '', 'attachments': []}

if __name__ == "__main__":
    scraper = GBTPPlaywrightScraper()
    scraper.scrape_pages_playwright(max_pages=1, output_base='output/gbtp_playwright')