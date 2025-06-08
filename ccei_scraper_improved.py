# -*- coding: utf-8 -*-
from base_scraper import BaseScraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import re
import os

class CCEIScraper(BaseScraper):
    """충북창조경제혁신센터 전용 스크래퍼 - 개선된 버전"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://ccei.creativekorea.or.kr"
        self.list_url = "https://ccei.creativekorea.or.kr/chungbuk/custom/notice_list.do"
        self.api_url = "https://ccei.creativekorea.or.kr/chungbuk/custom/noticeList.json"
        # Store list data for file information
        self._list_data_cache = {}
        
    def get_list_url(self, page_num):
        """페이지 번호에 따른 목록 URL 반환"""
        return self.list_url
        
    def get_list_data(self, page_num):
        """AJAX로 목록 데이터 가져오기"""
        data = {
            'pn': str(page_num),
            'boardGubun': '',
            'keyword': '',
            'title': ''
        }
        
        response = self.session.post(self.api_url, data=data)
        if response.status_code == 200:
            try:
                json_data = response.json()
                # Cache the data for file information
                if json_data and 'result' in json_data:
                    items = json_data.get('result', {}).get('list', [])
                    for item in items:
                        seq = str(item.get('SEQ', ''))
                        if seq:
                            self._list_data_cache[seq] = item
                return json_data
            except:
                print(f"Error parsing JSON response")
                return None
        return None
        
    def parse_list_page(self, html_content):
        """목록 페이지 파싱 - AJAX 방식으로 변경"""
        if isinstance(html_content, int):
            page_num = html_content
        else:
            page_num = 1
            
        announcements = []
        
        # AJAX로 데이터 가져오기
        json_data = self.get_list_data(page_num)
        if not json_data or 'result' not in json_data:
            return announcements
            
        result = json_data.get('result', {})
        items = result.get('list', [])
        
        for item in items:
            try:
                title = item.get('TITLE', '').strip()
                if not title:
                    continue
                
                seq = item.get('SEQ', '')
                if seq:
                    detail_url = f"{self.base_url}/chungbuk/custom/notice_view.do?no={seq}"
                else:
                    continue
                
                organization = item.get('COUNTRY_NM', '통합')
                date = item.get('REG_DATE', '')
                views = item.get('HIT', '0')
                has_file = item.get('FILE', '') != ''
                is_recommend = item.get('RECOMMEND_WHETHER', '') == 'Y'
                
                # Store file information
                file_data = item.get('FILE', '')
                
                announcements.append({
                    'title': title,
                    'url': detail_url,
                    'organization': organization,
                    'date': date,
                    'views': views,
                    'has_file': has_file,
                    'is_recommend': is_recommend,
                    'seq': seq,
                    'file_data': file_data  # Store raw file data
                })
                
            except Exception as e:
                print(f"Error parsing item: {e}")
                continue
                
        return announcements
        
    def parse_detail_page(self, html_content, url=None):
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract SEQ from the page URL if provided
        seq = None
        if url:
            match = re.search(r'no=(\d+)', url)
            if match:
                seq = match.group(1)
        
        # If not found in URL, try to extract from the page
        if not seq:
            # Try to find in JavaScript or hidden fields
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    match = re.search(r'var\s+seq\s*=\s*["\']?(\d+)["\']?', script.string)
                    if match:
                        seq = match.group(1)
                        break
        
        # 본문 내용 찾기
        content_area = None
        
        # 가능한 본문 선택자들
        content_selectors = [
            'div.view_cont',
            'div.board_view',
            'div.view_content',
            'div.content',
            'td.content',
            'div.view_body',
            'div.board_content',
            'div.bbs_content',
            'div.vw_article'  # CCEI specific
        ]
        
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                break
                
        # 테이블 구조에서 본문 찾기
        if not content_area:
            view_table = soup.find('table', class_=['view', 'board_view'])
            if view_table:
                for tr in view_table.find_all('tr'):
                    th = tr.find('th')
                    if th and '내용' in th.get_text():
                        content_area = tr.find('td')
                        break
                        
        # 첨부파일 찾기 - CCEI는 list API에서 파일 정보를 가져와야 함
        attachments = []
        
        # Get file data from cache if we have the SEQ
        if seq and seq in self._list_data_cache:
            item_data = self._list_data_cache[seq]
            file_data = item_data.get('FILE', '')
            
            if file_data:
                file_uuids = file_data.split(',')
                print(f"Found {len(file_uuids)} files from cached data for SEQ {seq}")
                
                # For each UUID, create download URL
                for i, uuid in enumerate(file_uuids):
                    if uuid.strip():
                        file_url = f"{self.base_url}/chungbuk/json/common/fileDown.download?uuid={uuid.strip()}"
                        # We don't have filename info here, so we'll get it during download
                        attachments.append({
                            'name': f'attachment_{i+1}',  # Placeholder name
                            'url': file_url,
                            'uuid': uuid.strip()
                        })
        
        # 본문을 마크다운으로 변환
        content_md = ""
        if content_area:
            content_md = self.h.handle(str(content_area))
        else:
            # 전체 페이지에서 헤더/푸터 제외하고 추출 시도
            main_content = soup.find('div', class_='content_wrap') or soup.find('div', id='content')
            if main_content:
                content_md = self.h.handle(str(main_content))
                
        return {
            'content': content_md,
            'attachments': attachments,
            'seq': seq
        }
    
    def download_file(self, url, save_path):
        """파일 다운로드 - CCEI 특화 처리"""
        try:
            print(f"Downloading from: {url}")
            response = self.session.get(url, stream=True)
            response.raise_for_status()
            
            # Extract filename from Content-Disposition header
            content_disp = response.headers.get('Content-Disposition', '')
            filename = None
            
            if content_disp:
                # Extract filename from header
                match = re.search(r'filename="([^"]+)"', content_disp)
                if match:
                    raw_filename = match.group(1)
                    # Decode filename (CCEI uses ISO-8859-1 encoding)
                    try:
                        filename = raw_filename.encode('iso-8859-1').decode('utf-8')
                    except:
                        filename = raw_filename
            
            # If we got a proper filename, update the save path
            if filename and filename != save_path:
                # Keep the directory but use the actual filename
                save_dir = os.path.dirname(save_path)
                save_path = os.path.join(save_dir, filename)
                print(f"Using actual filename: {filename}")
            
            # Download the file
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            print(f"Successfully downloaded: {save_path}")
            return True
            
        except Exception as e:
            print(f"Error downloading file from {url}: {e}")
            return False
        
    def scrape_pages(self, max_pages=4, output_base='output'):
        """여러 페이지 스크래핑 - AJAX 방식 대응"""
        announcement_count = 0
        
        for page_num in range(1, max_pages + 1):
            print(f"\n{'='*50}")
            print(f"Processing page {page_num}")
            print(f"{'='*50}")
            
            # AJAX 방식으로 공고 목록 가져오기
            announcements = self.parse_list_page(page_num)
            
            if not announcements:
                print(f"No announcements found on page {page_num}")
                continue
                
            print(f"Found {len(announcements)} announcements on page {page_num}")
            
            # 각 공고 처리
            for announcement in announcements:
                announcement_count += 1
                # Pass file_data to process_announcement
                if 'file_data' in announcement:
                    # Store in cache for parse_detail_page to use
                    seq = str(announcement.get('seq', ''))
                    if seq and announcement['file_data']:
                        self._list_data_cache[seq] = {
                            'FILE': announcement['file_data']
                        }
                
                self.process_announcement(announcement, announcement_count, output_base)
                
        print(f"\n{'='*50}")
        print(f"Scraping completed. Total announcements processed: {announcement_count}")
        print(f"{'='*50}")
    
    def process_announcement(self, announcement, index, output_base='output'):
        """개별 공고 처리 - CCEI 특화"""
        print(f"\nProcessing announcement {index}: {announcement['title']}")
        
        # 폴더 생성
        folder_title = self.sanitize_filename(announcement['title'])[:50]
        folder_name = f"{index:03d}_{folder_title}"
        folder_path = os.path.join(output_base, 'ccei', folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        # 상세 페이지 가져오기
        response = self.get_page(announcement['url'])
        if not response:
            return
            
        # 상세 내용 파싱 - URL 전달
        detail = self.parse_detail_page(response.text, announcement['url'])
        
        # 메타 정보 추가
        meta_info = f"""# {announcement['title']}

**기관**: {announcement.get('organization', 'N/A')}  
**작성일**: {announcement.get('date', 'N/A')}  
**조회수**: {announcement.get('views', 'N/A')}  
**원본 URL**: {announcement['url']}

---

"""
        
        # 본문 저장
        content_path = os.path.join(folder_path, 'content.md')
        with open(content_path, 'w', encoding='utf-8') as f:
            f.write(meta_info + detail['content'])
        print(f"Saved content to: {os.path.join('output', 'ccei', folder_name, 'content.md')}")
        
        # 첨부파일 다운로드
        if detail['attachments']:
            attachments_path = os.path.join(folder_path, 'attachments')
            os.makedirs(attachments_path, exist_ok=True)
            
            for attachment in detail['attachments']:
                # For CCEI, use the UUID as temporary filename
                temp_filename = attachment.get('uuid', attachment['name'])
                if not temp_filename.endswith(('.hwp', '.pdf', '.docx', '.xlsx', '.zip')):
                    temp_filename += '.download'  # Add extension for safety
                    
                file_path = os.path.join(attachments_path, temp_filename)
                
                if self.download_file(attachment['url'], file_path):
                    # File will be renamed by download_file method
                    print(f"Downloaded: {attachment['name']}")
                else:
                    print(f"Failed to download: {attachment['name']}")
        else:
            print("No attachments found")