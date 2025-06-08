# -*- coding: utf-8 -*-
from base_scraper import BaseScraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlencode
import re
import os
import time

class KIDPScraper(BaseScraper):
    """한국디자인진흥원(KIDP) 전용 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://kidp.or.kr"
        self.list_url = "https://kidp.or.kr/?menuno=1202"
        
    def get_list_url(self, page_num):
        """페이지 번호에 따른 목록 URL 반환"""
        # KIDP는 mode=list 파라미터가 필요
        if page_num == 1:
            return f"{self.list_url}&mode=list"
        else:
            return f"{self.list_url}&mode=list&page={page_num}"
            
    def parse_list_page(self, html_content):
        """목록 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 테이블 찾기 - board01-list 클래스나 summary 속성으로 찾기
        table = soup.find('table', class_='board01-list') or soup.find('table', attrs={'summary': lambda x: x and '번호' in x})
        if not table:
            # 모든 테이블을 확인하여 tbody가 있는 것 찾기
            tables = soup.find_all('table')
            for t in tables:
                if t.find('tbody') and len(t.find('tbody').find_all('tr')) > 0:
                    table = t
                    break
            
        if not table:
            return announcements
            
        tbody = table.find('tbody')
        if not tbody:
            return announcements
            
        rows = tbody.find_all('tr')
        
        for row in rows:
            try:
                tds = row.find_all('td')
                if len(tds) < 4:
                    continue
                
                # 번호
                num = tds[0].get_text(strip=True)
                
                # 제목 및 링크
                title_td = tds[1]
                link_elem = title_td.find('a')
                if not link_elem:
                    continue
                    
                title = link_elem.get_text(strip=True)
                
                # onclick에서 seq 추출
                onclick = link_elem.get('onclick', '')
                seq_match = re.search(r"submitForm\(this,'(\w+)',(\d+)\)", onclick)
                if seq_match:
                    action = seq_match.group(1)
                    seq = seq_match.group(2)
                    # 상세 페이지 URL 구성 - 실제 상세페이지 URL 패턴 사용
                    detail_url = f"{self.base_url}/?menuno=1202&bbsno={seq}&siteno=16&act=view&ztag=rO0ABXQAMzxjYWxsIHR5cGU9ImJvYXJkIiBubz0iNjIyIiBza2luPSJraWRwX2JicyI%2BPC9jYWxsPg%3D%3D"
                else:
                    continue
                
                # 날짜
                date = tds[2].get_text(strip=True)
                
                # 조회수
                views = tds[3].get_text(strip=True)
                
                # 첨부파일 여부
                has_attachment = False
                if len(tds) > 4:
                    # 첨부파일 아이콘 확인
                    file_img = tds[4].find('img')
                    if file_img:
                        has_attachment = True
                
                announcements.append({
                    'num': num,
                    'title': title,
                    'url': detail_url,
                    'date': date,
                    'views': views,
                    'has_attachment': has_attachment,
                    'seq': seq
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
        
        # 가능한 본문 선택자들
        content_selectors = [
            'div.board_view',
            'div.view_content',
            'div.board_content',
            'div.content_view',
            'td.content',
            'div.view_body',
            'div.bbs_content',
            'div.view_area'
        ]
        
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                break
                
        # 테이블 구조에서 본문 찾기
        if not content_area:
            view_table = soup.find('table', class_=['board_view', 'view'])
            if view_table:
                # 내용이 있는 td 찾기
                for tr in view_table.find_all('tr'):
                    th = tr.find('th')
                    if th and '내용' in th.get_text():
                        content_area = tr.find('td')
                        break
                        
        # 첨부파일 찾기
        attachments = []
        
        # 테이블에서 첨부파일 찾기 - KIDP는 테이블 구조 사용
        for tr in soup.find_all('tr'):
            th = tr.find('th')
            if th and '첨부파일' in th.get_text():
                file_area = tr.find('td')
                if file_area:
                    break
        else:
            file_area = None
                    
        if file_area:
            # 파일 링크 찾기
            file_links = file_area.find_all('a')
            for link in file_links:
                file_name = link.get_text(strip=True)
                
                # onclick 처리 - submitForm(this,'down',64274,'')
                onclick = link.get('onclick', '')
                if onclick and 'submitForm' in onclick:
                    # submitForm에서 파일 ID 추출
                    match = re.search(r"submitForm\(this,'down',(\d+)", onclick)
                    if match:
                        file_id = match.group(1)
                        # KIDP 파일 다운로드 URL 구성
                        file_url = f"{self.base_url}/?menuno=1202&bbsno={file_id}&siteno=16&act=down&ztag=rO0ABXQAMzxjYWxsIHR5cGU9ImJvYXJkIiBubz0iNjIyIiBza2luPSJraWRwX2JicyI%2BPC9jYWxsPg%3D%3D"
                        
                        # 파일명 정리 - (1) 등 제거
                        file_name = re.sub(r'\s*\(\d+\)\s*$', '', file_name)
                        
                        if file_name and not file_name.isspace():
                            attachments.append({
                                'name': file_name,
                                'url': file_url
                            })
        
        # 다른 패턴으로도 첨부파일 찾기
        if not attachments:
            # 직접 파일 링크 패턴
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
        
    def process_announcement(self, announcement, index, output_base='output'):
        """개별 공고 처리 - KIDP 맞춤형"""
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
**작성일**: {announcement.get('date', 'N/A')}  
**조회수**: {announcement.get('views', 'N/A')}  
**첨부파일**: {'있음' if announcement.get('has_attachment') else '없음'}  
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
                file_name = file_name.replace('+', ' ')
                
                if not file_name or file_name.isspace():
                    file_name = f"attachment_{i+1}"
                    
                file_path = os.path.join(attachments_folder, file_name)
                self.download_file(attachment['url'], file_path)
        else:
            print("No attachments found")
                
        # 잠시 대기 (서버 부하 방지)
        time.sleep(1)