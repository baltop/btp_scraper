import requests
from bs4 import BeautifulSoup
import os
import time
import html2text
from urllib.parse import urljoin, urlparse, parse_qs
import re
from base_scraper import BaseScraper

class DCBScraper(BaseScraper):
    """대구경북디자인센터 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.dcb.or.kr"
        self.list_url = "https://www.dcb.or.kr/01_news/?mcode=0401010000"
        
    def get_list_url(self, page_num):
        """페이지 번호에 따른 목록 URL 반환"""
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&page={page_num}"
    
    def parse_list_page(self, html_content):
        """목록 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 테이블에서 공고 목록 찾기 (board-text 영역 안의 table)
        board_text = soup.find('div', class_='board-text')
        if not board_text:
            print("Board text div not found")
            return []
            
        table = board_text.find('table')
        if not table:
            print("Table not found")
            return []
            
        tbody = table.find('tbody')
        if not tbody:
            print("Table body not found")
            return []
            
        rows = tbody.find_all('tr')
        print(f"Found {len(rows)} rows in table")
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 7:
                continue
                
            # 번호 (첫 번째 열) - Notice 이미지나 숫자
            number_cell = cells[0]
            number_img = number_cell.find('img')
            if number_img and number_img.get('alt') == 'Notice':
                # Notice 행은 건너뛰기 (고정된 공지사항) - 실제로는 포함하자
                number = "Notice"
            else:
                number = number_cell.get_text(strip=True)
                
            # 분류 (두 번째 열)
            category_cell = cells[1]
            category = category_cell.get_text(strip=True)
            
            # 제목 및 링크 (세 번째 열)
            title_cell = cells[2]
            title_link = title_cell.find('a')
            if not title_link:
                continue
                
            title = title_link.get_text(strip=True)
            detail_url = title_link.get('href')
            
            # 절대 URL로 변환
            if detail_url:
                detail_url = urljoin(self.base_url, detail_url)
            else:
                continue
                
            # 상태 (네 번째 열)
            status_cell = cells[3]
            status_span = status_cell.find('span')
            status = status_span.get_text(strip=True) if status_span else status_cell.get_text(strip=True)
            
            # 작성자 (다섯 번째 열)
            writer_cell = cells[4]
            writer = writer_cell.get_text(strip=True)
            
            # 조회수 (여섯 번째 열)
            views_cell = cells[5]
            views = views_cell.get_text(strip=True)
            
            # 작성일 (일곱 번째 열)
            date_cell = cells[6] if len(cells) > 6 else None
            date = date_cell.get_text(strip=True) if date_cell else "N/A"
            
            # 첨부파일 여부 확인 (파일 아이콘이 있는지 확인)
            has_attachment = bool(title_cell.find('img', alt='파일'))
            
            announcement = {
                'number': number,
                'category': category,
                'title': title,
                'url': detail_url,
                'status': status,
                'writer': writer,
                'views': views,
                'date': date,
                'has_attachment': has_attachment
            }
            
            announcements.append(announcement)
            print(f"  Found: {number} - {title}")
            
        return announcements
    
    def parse_detail_page(self, html_content):
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 내용 추출
        content = ""
        attachments = []
        
        # 1. 제목 추출
        title_elem = soup.find('h4', class_='view_title')
        if title_elem:
            content += f"# {title_elem.get_text(strip=True)}\n\n"
        
        # 2. 메타 정보 추출
        meta_info = soup.find('div', class_='listInfo')
        if meta_info:
            content += "## 공고 정보\n\n"
            info_items = meta_info.find_all('li')
            for item in info_items:
                content += f"- {item.get_text(strip=True)}\n"
            content += "\n"
        
        # 3. 첨부파일 정보 추출 (우선 view-info 영역에서 추출)
        view_info = soup.find('div', class_='view-info')
        if view_info:
            info_cont = view_info.find('div', class_='info-cont')
            if info_cont:
                file_links = info_cont.find_all('a')
                for link in file_links:
                    file_url = link.get('href')
                    file_name_span = link.find('span')
                    
                    if file_url and file_name_span:
                        # 절대 URL로 변환
                        file_url = urljoin(self.base_url, file_url)
                        file_name = file_name_span.get_text(strip=True)
                        
                        attachments.append({
                            'name': file_name,
                            'url': file_url
                        })
        
        # 4. 대체 방법: file 클래스에서 추출 (view-info가 없는 경우)
        if not attachments:
            file_list = soup.find('div', class_='file')
            if file_list:
                file_links = file_list.find_all('a')
                for link in file_links:
                    file_url = link.get('href')
                    file_name = link.find('span')
                    
                    if file_url and file_name:
                        # 절대 URL로 변환
                        file_url = urljoin(self.base_url, file_url)
                        file_name = file_name.get_text(strip=True)
                        
                        attachments.append({
                            'name': file_name,
                            'url': file_url
                        })
        
        # 5. 본문 내용 추출 (PDF 뷰어 또는 일반 텍스트)
        view_box = soup.find('div', class_='viewBox')
        if view_box:
            # PDF 뷰어가 있는 경우
            pdf_iframes = view_box.find_all('iframe', class_='isPDFifrm')
            if pdf_iframes:
                content += "## 공고 내용\n\n"
                content += "본 공고는 PDF 형태로 제공됩니다. 상세 내용은 첨부파일을 참조하시기 바랍니다.\n\n"
            else:
                # 일반 텍스트 내용
                content += "## 공고 내용\n\n"
                text_content = view_box.get_text(strip=True)
                if text_content:
                    content += text_content + "\n\n"
        
        # 6. 이전글/다음글 정보 (선택사항)
        nav_info = soup.find('nav', class_='listNavi')
        if nav_info:
            content += "## 관련 공고\n\n"
            nav_links = nav_info.find_all('a')
            for link in nav_links:
                nav_text = link.get_text(strip=True)
                if nav_text:
                    content += f"- {nav_text}\n"
            content += "\n"
        
        # HTML을 마크다운으로 변환
        if not content.strip():
            # 기본 내용이 없으면 전체 페이지에서 메인 콘텐츠 영역 찾기
            main_content = soup.find('div', id='sub_content')
            if main_content:
                content = self.h.handle(str(main_content))
            else:
                content = "내용을 추출할 수 없습니다."
        
        return {
            'content': content,
            'attachments': attachments
        }