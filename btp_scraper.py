from base_scraper import BaseScraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

class BTPScraper(BaseScraper):
    """부산테크노파크 전용 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.btp.or.kr"
        self.list_url = "https://www.btp.or.kr/kor/CMS/Board/Board.do?mCode=MN013"
        
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