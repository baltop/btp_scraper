from base_scraper import BaseScraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

class BTPScraper(BaseScraper):
    def __init__(self):
        self.base_url = "https://www.btp.or.kr"
        self.list_url = "https://www.btp.or.kr/kor/CMS/Board/Board.do?mCode=MN013"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.h = html2text.HTML2Text()
        self.h.ignore_links = False
        self.h.ignore_images = False
        
    def get_page(self, url):
        """페이지 가져오기"""
        try:
            response = self.session.get(url)
            response.encoding = 'utf-8'
            return response
        except Exception as e:
            print(f"Error fetching page: {e}")
            return None
            
    def parse_list_page(self, html_content):
        """목록 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        table = soup.find('table', class_='bdListTbl')
        if not table:
            return announcements
            
        tbody = table.find('tbody')
        if not tbody:
            return announcements
            
        rows = tbody.find_all('tr')
        
        for row in rows:
            try:
                # 링크 찾기
                link_elem = row.find('a', href=True)
                if not link_elem:
                    continue
                    
                # 제목
                title = link_elem.get_text(strip=True)
                
                # 상세 페이지 URL 구성
                href = link_elem['href']
                if href.startswith('?'):
                    # 상대 쿼리스트링인 경우 기본 URL에 붙이기
                    detail_url = self.list_url.split('?')[0] + href
                else:
                    detail_url = urljoin(self.base_url, href)
                
                # 상태
                status_elem = row.find('span', class_='status')
                status = status_elem.get_text(strip=True) if status_elem else ''
                
                # 작성자
                writer_elem = row.find('td', class_='writer')
                writer = writer_elem.get_text(strip=True) if writer_elem else ''
                
                # 날짜
                date_elem = row.find('td', class_='date')
                date = date_elem.get_text(strip=True) if date_elem else ''
                
                # 접수기간
                period_elem = row.find('td', class_='period')
                period = period_elem.get_text(strip=True) if period_elem else ''
                
                announcements.append({
                    'title': title,
                    'url': detail_url,
                    'status': status,
                    'writer': writer,
                    'date': date,
                    'period': period
                })
                
            except Exception as e:
                print(f"Error parsing row: {e}")
                continue
                
        return announcements
        
    def parse_detail_page(self, html_content):
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 내용 찾기 - 더 정확한 선택자 사용
        content_area = None
        
        # 가능한 본문 선택자들
        content_selectors = [
            'div.bbsViewCont',
            'div.boardView',
            'div.board_view',
            'div.view_content',
            'div.content_view',
            'td.content',
            'div#content',
            'article.content'
        ]
        
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                break
                
        # 첨부파일 찾기
        attachments = []
        
        # downloadRun.do 패턴의 링크 찾기 (부산테크노파크 특유의 다운로드 방식)
        download_links = soup.find_all('a', href=lambda x: x and 'downloadRun.do' in x)
        
        
        if download_links:
            for link in download_links:
                file_text = link.get_text(strip=True)
                file_url = link['href']
                
                # 파일명과 크기 분리
                # "파일명.확장자 (크기KB)" 형태에서 파일명만 추출
                import re
                # 여러 줄로 된 텍스트를 한 줄로 정리
                file_text = ' '.join(file_text.split())
                
                file_name_match = re.match(r'^(.+?)\s*\(\d+KB\)$', file_text)
                if file_name_match:
                    file_name = file_name_match.group(1).strip()
                else:
                    file_name = file_text.strip()
                
                # 상대 경로 처리
                if not file_url.startswith(('http://', 'https://')):
                    file_url = urljoin(self.base_url, file_url)
                    
                # 파일명 정리
                if file_name and not file_name.isspace():
                    attachments.append({
                        'name': file_name,
                        'url': file_url
                    })
        else:
            # 다른 일반적인 첨부파일 패턴도 시도
            file_patterns = [
                ('a', lambda x: x and any(ext in x.lower() for ext in ['.pdf', '.hwp', '.docx', '.xlsx', '.zip', '.ppt', '.pptx'])),
                ('a', lambda x: x and any(keyword in x.lower() for keyword in ['download', 'file', 'attach']))
            ]
            
            for tag, href_filter in file_patterns:
                links = soup.find_all(tag, href=href_filter)
                for link in links:
                    file_name = link.get_text(strip=True)
                    file_url = link.get('href', '')
                    
                    if not file_url:
                        continue
                        
                    # 상대 경로 처리
                    if not file_url.startswith(('http://', 'https://')):
                        file_url = urljoin(self.base_url, file_url)
                        
                    # 파일명 정리
                    if file_name and not file_name.isspace():
                        # 중복 방지
                        if not any(att['url'] == file_url for att in attachments):
                            attachments.append({
                                'name': file_name,
                                'url': file_url
                            })
        
        # 본문을 마크다운으로 변환
        content_md = ""
        if content_area:
            content_md = self.h.handle(str(content_area))
        else:
            # 전체 본문에서 헤더/푸터 제외하고 추출 시도
            main_content = soup.find('main') or soup.find('div', id='container')
            if main_content:
                content_md = self.h.handle(str(main_content))
                
        return {
            'content': content_md,
            'attachments': attachments
        }
        
    def download_file(self, url, save_path):
        """파일 다운로드"""
        try:
            print(f"Downloading from: {url}")
            
            # 세션에 Referer 헤더 추가 (일부 사이트에서 필요)
            download_headers = self.headers.copy()
            download_headers['Referer'] = self.base_url
            
            response = self.session.get(url, headers=download_headers, stream=True, timeout=30)
            response.raise_for_status()
            
            # Content-Disposition 헤더에서 실제 파일명 추출 시도
            content_disposition = response.headers.get('Content-Disposition', '')
            if content_disposition:
                import re
                filename_match = re.search(r'filename[^;=\n]*=(([\'"]).*?\2|[^;\n]*)', content_disposition)
                if filename_match:
                    filename = filename_match.group(1).strip('"\'')
                    # 인코딩 문제 해결
                    try:
                        filename = filename.encode('latin-1').decode('utf-8')
                    except:
                        pass
                    
                    # 파일명이 유효하면 save_path 업데이트
                    if filename and not filename.isspace():
                        save_dir = os.path.dirname(save_path)
                        # + 기호를 공백으로 변경
                        filename = filename.replace('+', ' ')
                        save_path = os.path.join(save_dir, self.sanitize_filename(filename))
            
            # 파일 저장
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        
            file_size = os.path.getsize(save_path)
            print(f"Downloaded: {save_path} ({file_size:,} bytes)")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"Network error downloading {url}: {e}")
            return False
        except Exception as e:
            print(f"Error downloading file {url}: {e}")
            return False
            
    def sanitize_filename(self, filename):
        """파일명 정리"""
        # URL 디코딩 (퍼센트 인코딩 제거)
        from urllib.parse import unquote
        filename = unquote(filename)
        
        # 특수문자 제거 (파일 시스템에서 허용하지 않는 문자)
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # 연속된 공백을 하나로
        filename = re.sub(r'\s+', ' ', filename)
        
        # 너무 긴 파일명 제한
        if len(filename) > 200:
            # 확장자 보존
            name_parts = filename.rsplit('.', 1)
            if len(name_parts) == 2:
                name, ext = name_parts
                filename = name[:200-len(ext)-1] + '.' + ext
            else:
                filename = filename[:200]
                
        return filename
        
    def process_announcement(self, announcement, index):
        """개별 공고 처리"""
        print(f"\nProcessing announcement {index}: {announcement['title']}")
        
        # 폴더 생성
        folder_title = self.sanitize_filename(announcement['title'])[:50]
        folder_name = f"{index:03d}_{folder_title}"
        folder_path = os.path.join('output', folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        # 상세 페이지 가져오기
        response = self.get_page(announcement['url'])
        if not response:
            return
            
        # 상세 내용 파싱
        detail = self.parse_detail_page(response.text)
        
        # 메타 정보 추가
        meta_info = f"""# {announcement['title']}

**작성자**: {announcement['writer']}  
**작성일**: {announcement['date']}  
**접수기간**: {announcement['period']}  
**상태**: {announcement['status']}  
**원본 URL**: {announcement['url']}

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
                # 원본 파일명 사용 (이미 파싱 단계에서 정리됨)
                file_name = attachment['name']
                
                # 파일명 정리
                file_name = self.sanitize_filename(file_name)
                
                # + 기호를 공백으로 변경
                file_name = file_name.replace('+', ' ')
                
                if not file_name or file_name.isspace():
                    file_name = f"attachment_{i+1}"
                    
                file_path = os.path.join(attachments_folder, file_name)
                self.download_file(attachment['url'], file_path)
        else:
            print("No attachments found")
                
        # 잠시 대기 (서버 부하 방지)
        time.sleep(1)
        
    def get_next_page_url(self, current_page_html, current_page_num):
        """다음 페이지 URL 가져오기"""
        soup = BeautifulSoup(current_page_html, 'html.parser')
        
        # 페이지네이션 찾기
        pagination = soup.find('div', class_='pagelist') or soup.find('div', class_='paging')
        
        if not pagination:
            return None
            
        # 다음 페이지 링크 찾기
        next_page = current_page_num + 1
        
        # JavaScript 함수 호출 패턴 찾기
        page_links = pagination.find_all('a')
        for link in page_links:
            if str(next_page) in link.get_text():
                onclick = link.get('onclick')
                if onclick and 'goPage' in onclick:
                    # goPage(2) 같은 패턴에서 숫자 추출
                    match = re.search(r'goPage\((\d+)\)', onclick)
                    if match:
                        page_num = match.group(1)
                        # POST 요청으로 페이지 변경하는 경우
                        return f"{self.list_url}&page={page_num}"
                        
                href = link.get('href')
                if href:
                    return urljoin(self.base_url, href)
                    
        return None
        
    def scrape_pages(self, max_pages=4):
        """여러 페이지 스크래핑"""
        announcement_count = 0
        
        for page_num in range(1, max_pages + 1):
            print(f"\n{'='*50}")
            print(f"Processing page {page_num}")
            print(f"{'='*50}")
            
            # 페이지 URL 구성
            if page_num == 1:
                page_url = self.list_url
            else:
                page_url = f"{self.list_url}&page={page_num}"
                
            # 페이지 가져오기
            response = self.get_page(page_url)
            if not response:
                print(f"Failed to fetch page {page_num}")
                break
                
            # 목록 파싱
            announcements = self.parse_list_page(response.text)
            
            if not announcements:
                print(f"No announcements found on page {page_num}")
                break
                
            print(f"Found {len(announcements)} announcements on page {page_num}")
            
            # 각 공고 처리
            for ann in announcements:
                announcement_count += 1
                self.process_announcement(ann, announcement_count)
                
            # 다음 페이지가 있는지 확인
            if page_num < max_pages:
                time.sleep(2)  # 페이지 간 대기
                
        print(f"\n{'='*50}")
        print(f"Scraping completed. Total announcements processed: {announcement_count}")
        print(f"{'='*50}")

if __name__ == "__main__":
    scraper = BTPScraper()
    scraper.scrape_pages(max_pages=4)