# -*- coding: utf-8 -*-
from base_scraper import BaseScraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin, parse_qs, urlparse
import re
import os
import time
import base64

class GSIFScraper(BaseScraper):
    """강릉과학산업진흥원(GSIF) 전용 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://mybiz.gsipa.or.kr"
        self.list_url = "https://mybiz.gsipa.or.kr/gsipa/bbs_list.do?code=sub03a&keyvalue=sub03"
        
    def get_list_url(self, page_num):
        """페이지 번호에 따른 목록 URL 반환"""
        if page_num == 1:
            return self.list_url
        else:
            # 페이지당 15개씩, startPage 계산
            start_page = (page_num - 1) * 15
            # Base64 인코딩된 파라미터 생성
            params = f"startPage={start_page}&listNo=&table=cs_bbs_data&code=sub03a&search_item=&search_order=&url=sub03a&keyvalue=sub03"
            encoded = base64.b64encode(params.encode('utf-8')).decode('utf-8')
            return f"{self.base_url}/gsipa/bbs_list.do?bbs_data={encoded}||"
            
    def parse_list_page(self, html_content):
        """목록 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 테이블 찾기
        table = soup.find('table')
        if not table:
            return announcements
            
        # 모든 행 찾기
        rows = table.find_all('tr')
        
        for row in rows:
            try:
                tds = row.find_all('td')
                if len(tds) < 5:  # 헤더 행이거나 데이터가 부족한 경우 스킵
                    continue
                
                # 번호
                num = tds[0].get_text(strip=True)
                if not num.isdigit():  # 번호가 아닌 경우 스킵
                    continue
                
                # 제목 및 링크
                title_td = tds[1]
                link_elem = title_td.find('a')
                if not link_elem:
                    continue
                    
                title = link_elem.get_text(strip=True)
                
                # 상세 페이지 URL 추출
                onclick = link_elem.get('onclick', '')
                href = link_elem.get('href', '')
                
                detail_url = None
                if 'bbs_view.do' in onclick:
                    # onclick에서 URL 추출
                    match = re.search(r"location\.href='([^']+)'", onclick)
                    if match:
                        detail_url = urljoin(self.base_url, match.group(1))
                elif 'bbs_view.do' in href:
                    # href가 /로 시작하지 않으면 /gsipa/를 앞에 추가
                    if not href.startswith('http'):
                        if not href.startswith('/'):
                            href = '/gsipa/' + href
                        elif not href.startswith('/gsipa'):
                            href = '/gsipa' + href
                    detail_url = urljoin(self.base_url, href)
                
                if not detail_url:
                    continue
                
                # 작성자
                writer = tds[2].get_text(strip=True)
                
                # 날짜
                date = tds[3].get_text(strip=True)
                
                # 조회수
                views = tds[4].get_text(strip=True)
                
                announcements.append({
                    'num': num,
                    'title': title,
                    'url': detail_url,
                    'writer': writer,
                    'date': date,
                    'views': views
                })
                
            except Exception as e:
                print(f"Error parsing row: {e}")
                continue
                
        return announcements
        
    def parse_detail_page(self, html_content):
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 내용 찾기
        content_area = None
        
        # 테이블 구조에서 본문 찾기
        table = soup.find('table')
        if table:
            rows = table.find_all('tr')
            # img_td 클래스를 가진 td 찾기 (본문이 있는 곳)
            content_td = soup.find('td', class_='img_td')
            if content_td:
                content_area = content_td
            elif len(rows) >= 4:
                # 대체 방법: 4번째 행에서 찾기
                content_td = rows[3].find('td')
                if content_td:
                    content_area = content_td
                    
        # 첨부파일 찾기
        attachments = []
        
        # 파일 행 찾기 - th 태그에 "파일"이 포함된 행 찾기
        if table:
            for row in rows:
                th = row.find('th')
                if th and '파일' in th.get_text():
                    # 이 행에서 모든 링크 찾기
                    file_links = row.find_all('a')
                    for link in file_links:
                        file_name = link.get_text(strip=True)
                        file_url = link.get('href', '')
                        
                        if file_url and 'bbs_download.do' in file_url:
                            # 상대 경로를 절대 경로로 변환
                            if not file_url.startswith('http'):
                                if not file_url.startswith('/'):
                                    file_url = '/gsipa/' + file_url
                                elif not file_url.startswith('/gsipa'):
                                    file_url = '/gsipa' + file_url
                            file_url = urljoin(self.base_url, file_url)
                            
                            if file_name and not file_name.isspace():
                                attachments.append({
                                    'name': file_name,
                                    'url': file_url
                                })
                    break
        
        # 본문을 마크다운으로 변환
        content_md = ""
        if content_area:
            content_md = self.h.handle(str(content_area))
        
        return {
            'content': content_md,
            'attachments': attachments
        }
        
    def process_announcement(self, announcement, index, output_base='output'):
        """개별 공고 처리 - GSIF 맞춤형"""
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
            
        # 상세 내용 파싱
        detail = self.parse_detail_page(response.text)
        
        # 메타 정보 추가
        meta_info = f"""# {announcement['title']}

**번호**: {announcement.get('num', 'N/A')}  
**작성자**: {announcement.get('writer', 'N/A')}  
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
                print(f"  Attachment {i+1}: {attachment['name']}")
                file_name = self.sanitize_filename(attachment['name'])
                file_path = os.path.join(attachments_folder, file_name)
                self.download_file(attachment['url'], file_path)
        else:
            print("No attachments found")
                
        # 잠시 대기 (서버 부하 방지)
        time.sleep(1)