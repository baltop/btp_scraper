import requests
from bs4 import BeautifulSoup
import os
import time
import html2text
from urllib.parse import urljoin, urlparse, parse_qs
import re
from base_scraper import BaseScraper

class CCIScraper(BaseScraper):
    """청주상공회의소 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://cheongjucci.korcham.net"
        self.list_ajax_url = "https://cheongjucci.korcham.net/front/board/boardContentsList.do"
        self.detail_base_url = "https://cheongjucci.korcham.net/front/board/boardContentsView.do"
        self.board_id = "10701"
        self.menu_id = "1561"
        
    def get_list_url(self, page_num):
        """페이지 번호에 따른 목록 AJAX URL 반환"""
        return f"{self.list_ajax_url}?boardId={self.board_id}&menuId={self.menu_id}&miv_pageNo={page_num}&miv_pageSize=10"
    
    def parse_list_page(self, html_content):
        """목록 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 테이블에서 공고 목록 찾기
        table = soup.find('table')
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
            if len(cells) < 2:
                continue
                
            # 번호 (첫 번째 열)
            number_cell = cells[0]
            # 공지사항 아이콘이 있는지 확인
            notice_img = number_cell.find('img', alt='공지')
            if notice_img:
                number = "공지"
            else:
                number = number_cell.get_text(strip=True)
                
            # 제목 및 링크 (두 번째 열)
            title_cell = cells[1]
            title_link = title_cell.find('a')
            if not title_link:
                continue
                
            title = title_link.get_text(strip=True)
            
            # JavaScript 링크에서 contId 추출
            onclick = title_link.get('href', '')
            if not onclick or onclick == 'javascript:void(0)':
                onclick = title_link.get('onclick', '')
            
            # contentsView('116475') 형태에서 ID 추출
            cont_id_match = re.search(r"contentsView\('(\d+)'\)", onclick)
            if not cont_id_match:
                print(f"Could not extract contId from: {onclick}")
                continue
                
            cont_id = cont_id_match.group(1)
            detail_url = f"{self.detail_base_url}?contId={cont_id}&boardId={self.board_id}&menuId={self.menu_id}"
            
            announcement = {
                'number': number,
                'title': title,
                'url': detail_url,
                'cont_id': cont_id,
                'writer': 'N/A',  # 목록에서는 작성자 정보 없음
                'date': 'N/A',    # 목록에서는 작성일 정보 없음
                'status': '진행' if number == "공지" else '일반'
            }
            
            announcements.append(announcement)
            print(f"  Found: {number} - {title}")
            
        return announcements
    
    def parse_detail_page(self, html_content):
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        content = ""
        attachments = []
        
        # 1. 기본 정보 추출 (제목, 작성자, 작성일 등)
        board_view = soup.find('div', class_='boardveiw')
        if board_view:
            table = board_view.find('table')
            if table:
                rows = table.find_all('tr')
                
                # 메타데이터 수집
                meta_data = {}
                for row in rows:
                    th = row.find('th')
                    td = row.find('td')
                    if th and td:
                        key = th.get_text(strip=True)
                        value = td.get_text(strip=True)
                        if key in ['제목', '작성자', '작성일', '조회수']:
                            meta_data[key] = value
                
                # 메타데이터를 content에 추가
                if meta_data.get('제목'):
                    content += f"# {meta_data['제목']}\n\n"
                
                content += "## 공고 정보\n\n"
                for key, value in meta_data.items():
                    if key != '제목':
                        content += f"- **{key}**: {value}\n"
                content += "\n"
        
        # 2. 첨부파일 추출
        file_view = soup.find('ul', class_='file_view')
        if file_view:
            file_links = file_view.find_all('li')
            for li in file_links:
                link = li.find('a')
                if link:
                    file_url = link.get('href')
                    file_name = link.get('title') or link.get_text(strip=True)
                    
                    # 상대 URL을 절대 URL로 변환
                    if file_url:
                        file_url = urljoin(self.base_url, file_url)
                        attachments.append({
                            'name': file_name,
                            'url': file_url
                        })
        
        # 3. 본문 내용 추출
        content_cell = soup.find('td', class_='td_p')
        if content_cell:
            # HTML 내용을 마크다운으로 변환
            content += "## 공고 내용\n\n"
            
            # 복잡한 HTML 구조를 정리
            # 먼저 불필요한 스타일 속성 제거
            for element in content_cell.find_all(True):
                if element.name in ['style', 'script']:
                    element.decompose()
                else:
                    # 스타일 속성 제거
                    if element.has_attr('style'):
                        del element['style']
                    # 기타 불필요한 속성 제거
                    for attr in ['class', 'id', 'width', 'height', 'cellspacing', 'cellpadding', 'border']:
                        if element.has_attr(attr):
                            del element[attr]
            
            # HTML을 마크다운으로 변환
            content_html = str(content_cell)
            content_md = self.h.handle(content_html)
            
            # 과도한 공백 정리
            content_md = re.sub(r'\n\s*\n\s*\n', '\n\n', content_md)
            content_md = re.sub(r'&nbsp;', ' ', content_md)
            
            content += content_md
        else:
            content += "본문 내용을 추출할 수 없습니다.\n"
        
        return {
            'content': content,
            'attachments': attachments
        }
    
    def get_page(self, url):
        """페이지 가져오기 (세션 관리 포함)"""
        try:
            # CCI 사이트는 때때로 추가 헤더가 필요할 수 있음
            headers = self.headers.copy()
            headers.update({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            })
            
            response = self.session.get(url, headers=headers, verify=self.verify_ssl)
            response.raise_for_status()
            
            # 인코딩 설정
            if response.encoding is None or response.encoding == 'ISO-8859-1':
                response.encoding = 'utf-8'
                
            return response
        except Exception as e:
            print(f"Error fetching page {url}: {e}")
            return None