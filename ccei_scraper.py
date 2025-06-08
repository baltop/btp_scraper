# -*- coding: utf-8 -*-
from base_scraper import BaseScraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import re
import os

class CCEIScraper(BaseScraper):
    """충북창조경제혁신센터 전용 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://ccei.creativekorea.or.kr"
        self.list_url = "https://ccei.creativekorea.or.kr/chungbuk/custom/notice_list.do"
        self.api_url = "https://ccei.creativekorea.or.kr/chungbuk/custom/noticeList.json"
        self.list_cache = {}  # 리스트 데이터 캐시
        
    def get_list_url(self, page_num):
        """페이지 번호에 따른 목록 URL 반환"""
        # CCEI는 AJAX를 사용하므로 기본 URL 반환
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
                return response.json()
            except:
                print(f"Error parsing JSON response")
                return None
        return None
        
    def parse_list_page(self, html_content):
        """목록 페이지 파싱 - AJAX 방식으로 변경"""
        # HTML 대신 직접 페이지 번호를 받아서 처리
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
                # 제목
                title = item.get('TITLE', '').strip()
                if not title:
                    continue
                
                # SEQ로 상세 URL 구성
                seq = item.get('SEQ', '')
                if seq:
                    detail_url = f"{self.base_url}/chungbuk/custom/notice_view.do?no={seq}"
                else:
                    continue
                
                # 기타 정보
                organization = item.get('COUNTRY_NM', '통합')
                date = item.get('REG_DATE', '')
                views = item.get('HIT', '0')
                has_file = item.get('FILE', '') != ''
                is_recommend = item.get('RECOMMEND_WHETHER', '') == 'Y'
                
                # 리스트 캐시에 저장
                self.list_cache[seq] = item
                
                announcements.append({
                    'title': title,
                    'url': detail_url,
                    'organization': organization,
                    'date': date,
                    'views': views,
                    'has_file': has_file,
                    'is_recommend': is_recommend,
                    'seq': seq,
                    'files': item.get('FILE', '')
                })
                
            except Exception as e:
                print(f"Error parsing item: {e}")
                continue
                
        return announcements
        
    def parse_detail_page(self, html_content, url=None):
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # URL에서 SEQ 추출
        seq = None
        if url:
            match = re.search(r'no=(\d+)', url)
            if match:
                seq = match.group(1)
        
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
            'div.bbs_content'
        ]
        
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                break
                
        # 테이블 구조에서 본문 찾기
        if not content_area:
            view_table = soup.find('table', class_=['view', 'board_view'])
            if view_table:
                # 내용이 있는 td 찾기
                for tr in view_table.find_all('tr'):
                    th = tr.find('th')
                    if th and '내용' in th.get_text():
                        content_area = tr.find('td')
                        break
                        
        # 첨부파일 찾기
        attachments = []
        
        # 캐시된 리스트 데이터에서 파일 정보 가져오기
        if seq and seq in self.list_cache:
            files = self.list_cache[seq].get('FILE', '')
            if files:
                # 파일 UUID들이 쉼표로 구분되어 있음
                file_uuids = [f.strip() for f in files.split(',') if f.strip()]
                for uuid in file_uuids:
                    # 다운로드 URL 생성
                    file_url = f"{self.base_url}/chungbuk/json/common/fileDown.download?uuid={uuid}"
                    attachments.append({
                        'name': f'첨부파일_{uuid[:8]}',  # 임시 파일명
                        'url': file_url,
                        'uuid': uuid
                    })
        
        # CCEI 특유의 파일 다운로드 패턴
        # /chungbuk/json/common/fileDown.download?uuid= 패턴
        file_links = soup.find_all('a', href=lambda x: x and 'fileDown.download' in x)
        for link in file_links:
            file_name = link.get_text(strip=True)
            file_url = link.get('href', '')
            
            # 파일명에서 "첨부파일" 텍스트 제거
            if file_name.startswith('첨부파일'):
                file_name = file_name.replace('첨부파일', '').strip()
            
            # 상대 경로 처리
            if file_url and not file_url.startswith(('http://', 'https://')):
                file_url = urljoin(self.base_url, file_url)
                
            # 파일명과 URL이 유효한 경우만 추가
            if file_name and not file_name.isspace() and file_url:
                attachments.append({
                    'name': file_name,
                    'url': file_url
                })
        
        # 다른 패턴으로도 첨부파일 찾기
        if not attachments:
            # 첨부파일 영역 찾기
            file_areas = soup.find_all(['div', 'td'], class_=lambda x: x and 'file' in str(x).lower())
            for area in file_areas:
                area_links = area.find_all('a', href=True)
                for link in area_links:
                    file_name = link.get_text(strip=True)
                    file_url = link.get('href', '')
                    
                    # onclick 속성 확인
                    onclick = link.get('onclick', '')
                    if onclick and 'download' in onclick.lower():
                        # JavaScript 함수에서 파라미터 추출
                        match = re.search(r"download[^(]*\('([^']+)'(?:,\s*'([^']+)')?\)", onclick)
                        if match:
                            file_id = match.group(1)
                            file_url = f"{self.base_url}/chungbuk/fileDown.do?seq={file_id}"
                    
                    # 상대 경로 처리
                    if file_url and not file_url.startswith(('http://', 'https://')):
                        file_url = urljoin(self.base_url, file_url)
                        
                    # 파일명 정리
                    if file_name and not file_name.isspace():
                        # 중복 제거
                        if not any(att['url'] == file_url for att in attachments):
                            attachments.append({
                                'name': file_name,
                                'url': file_url
                            })
        
        # 파일 확장자 패턴으로도 찾기
        if not attachments:
            # 파일 다운로드 링크 패턴
            download_patterns = [
                'a[href*="download"]',
                'a[href*="fileDown"]',
                'a[onclick*="download"]',
                'a[href*=".hwp"]',
                'a[href*=".pdf"]',
                'a[href*=".docx"]',
                'a[href*=".xlsx"]',
                'a[href*=".zip"]'
            ]
            
            for pattern in download_patterns:
                links = soup.select(pattern)
                for link in links:
                    file_name = link.get_text(strip=True)
                    file_url = link.get('href', '')
                    
                    if file_url and file_name:
                        # 상대 경로 처리
                        if not file_url.startswith(('http://', 'https://')):
                            file_url = urljoin(self.base_url, file_url)
                            
                        # 중복 제거
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
            # 전체 페이지에서 헤더/푸터 제외하고 추출 시도
            main_content = soup.find('div', class_='content_wrap') or soup.find('div', id='content')
            if main_content:
                content_md = self.h.handle(str(main_content))
                
        return {
            'content': content_md,
            'attachments': attachments
        }
        
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
                self.process_announcement(announcement, announcement_count, output_base)
                
        print(f"\n{'='*50}")
        print(f"Scraping completed. Total announcements processed: {announcement_count}")
        print(f"{'='*50}")
    
    def process_announcement(self, announcement, index, output_base='output'):
        """개별 공고 처리 - CCEI 맞춤형"""
        print(f"\nProcessing announcement {index}: {announcement['title']}")
        
        # 폴더 생성
        folder_title = self.sanitize_filename(announcement['title'])[:50]
        folder_name = f"{index:03d}_{folder_title}"
        folder_path = os.path.join(output_base, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        # 상세 페이지 가져오기
        response = self.get_page(announcement['url'])
        if not response:
            return
            
        # 상세 내용 파싱 (URL 전달)
        detail = self.parse_detail_page(response.text, announcement['url'])
        
        # 메타 정보 추가
        meta_info = f"""# {announcement['title']}

**조직**: {announcement.get('organization', 'N/A')}  
**작성일**: {announcement.get('date', 'N/A')}  
**조회수**: {announcement.get('views', 'N/A')}  
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
                # 실제 파일 다운로드시 파일명을 Content-Disposition에서 가져옴
                response = self.session.get(attachment['url'], headers=self.headers, stream=True)
                if response.status_code == 200:
                    # Content-Disposition에서 파일명 추출
                    content_disp = response.headers.get('Content-Disposition', '')
                    if 'filename=' in content_disp:
                        match = re.search(r'filename="?([^"\n]+)"?', content_disp)
                        if match:
                            filename = match.group(1)
                            # ISO-8859-1로 인코딩된 경우 디코딩
                            try:
                                filename = filename.encode('iso-8859-1').decode('utf-8')
                            except:
                                pass
                            attachment['name'] = filename
                
                print(f"  Attachment {i+1}: {attachment['name']}")
                file_name = self.sanitize_filename(attachment['name'])
                file_path = os.path.join(attachments_folder, file_name)
                
                # 파일 저장
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                print(f"    Downloaded: {file_path}")
        else:
            print("No attachments found")
                
        # 잠시 대기 (서버 부하 방지)
        import time
        time.sleep(1)