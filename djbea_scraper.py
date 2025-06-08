# -*- coding: utf-8 -*-
from base_scraper import BaseScraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin, parse_qs, urlparse
import re
import os
import time

class DJBEAScraper(BaseScraper):
    """대전일자리경제진흥원(DJBEA) 전용 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.djbea.or.kr"
        self.list_url = "https://www.djbea.or.kr/pms/st/st_0205/list"
        self.verify_ssl = False  # SSL 인증서 문제 회피
        
    def get_list_url(self, page_num):
        """페이지 번호에 따른 목록 URL 반환"""
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}?cPage={page_num}"
            
    def parse_list_page(self, html_content):
        """목록 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # Check if page shows "no posts" message
        page_text = soup.get_text()
        if '게시글이 없습니다' in page_text or '등록된 게시물이 없습니다' in page_text:
            print("No posts found on this page (게시글이 없습니다)")
            return announcements
        
        # Try multiple strategies to find the list container
        
        # Strategy 1: Look for table-based list (common in Korean government sites)
        table = soup.find('table', class_=re.compile('list|board|bbs'))
        if table:
            tbody = table.find('tbody')
            if tbody:
                rows = tbody.find_all('tr')
                for row in rows:
                    try:
                        # Skip header rows
                        if row.find('th'):
                            continue
                            
                        cells = row.find_all('td')
                        if len(cells) < 3:  # Need at least number, title, date
                            continue
                        
                        # Extract data from cells
                        num = cells[0].get_text(strip=True)
                        
                        # Find title and link
                        title_cell = cells[1]  # Usually second cell
                        title_link = title_cell.find('a')
                        if not title_link:
                            continue
                            
                        title = title_link.get_text(strip=True)
                        
                        # Extract URL
                        href = title_link.get('href', '')
                        onclick = title_link.get('onclick', '')
                        
                        # Prioritize onclick over href for javascript:void(0) links
                        if onclick and (not href or href == '#' or 'javascript:' in href):
                            # Extract from JavaScript function
                            # Common patterns: doViewNew('7950', 'ST_0205'), goView('123'), fnView('123')
                            match = re.search(r"doViewNew\s*\(\s*['\"]?(\d+)['\"]?\s*,\s*['\"]?([^'\"]+)['\"]?\s*\)", onclick)
                            if match:
                                seq = match.group(1)
                                board_type = match.group(2)
                                detail_url = f"{self.base_url}/pms/st/st_0205/view_new?BBSCTT_SEQ={seq}&BBSCTT_TY_CD={board_type}"
                            else:
                                match = re.search(r"(?:goView|fnView|viewDetail)\s*\(\s*['\"]?(\d+)['\"]?\s*\)", onclick)
                                if match:
                                    seq = match.group(1)
                                    detail_url = f"{self.base_url}/pms/st/st_0205/view?seq={seq}"
                                else:
                                    match = re.search(r"location\.href\s*=\s*['\"]([^'\"]+)['\"]", onclick)
                                    if match:
                                        detail_url = urljoin(self.base_url, match.group(1))
                                    else:
                                        continue
                        elif href and href != '#' and 'javascript:' not in href:
                            detail_url = urljoin(self.base_url, href)
                        else:
                            continue
                        
                        # Extract metadata
                        meta_info = {}
                        
                        # Date (usually 3rd or 4th cell)
                        if len(cells) > 2:
                            meta_info['date'] = cells[2].get_text(strip=True)
                        
                        # Views (usually last or second to last cell)
                        if len(cells) > 3:
                            meta_info['views'] = cells[-1].get_text(strip=True)
                        
                        # Check for attachment icon
                        has_attachment = bool(row.find('img', src=re.compile('file|attach|clip')))
                        
                        announcements.append({
                            'num': num,
                            'title': title,
                            'url': detail_url,
                            'has_attachment': has_attachment,
                            **meta_info
                        })
                        
                    except Exception as e:
                        print(f"Error parsing table row: {e}")
                        continue
        
        # Strategy 2: Look for ul/li based list
        if not announcements:
            # Try multiple ul patterns
            list_containers = soup.find_all('ul', class_=re.compile('list|board|bbs|basic'))
            for list_container in list_containers:
                if not list_container:
                    continue
                items = list_container.find_all('li')
                
                for item in items:
                    try:
                        # Find title and link
                        title_link = item.find('a')
                        if not title_link:
                            continue
                            
                        title = title_link.get_text(strip=True)
                        
                        # Extract URL (similar logic as above)
                        href = title_link.get('href', '')
                        onclick = title_link.get('onclick', '')
                        
                        # Prioritize onclick over href for javascript:void(0) links
                        if onclick and (not href or href == '#' or 'javascript:' in href):
                            # Extract from JavaScript function
                            # Common patterns: doViewNew('7950', 'ST_0205'), goView('123'), fnView('123')
                            match = re.search(r"doViewNew\s*\(\s*['\"]?(\d+)['\"]?\s*,\s*['\"]?([^'\"]+)['\"]?\s*\)", onclick)
                            if match:
                                seq = match.group(1)
                                board_type = match.group(2)
                                detail_url = f"{self.base_url}/pms/st/st_0205/view_new?BBSCTT_SEQ={seq}&BBSCTT_TY_CD={board_type}"
                            else:
                                match = re.search(r"(?:goView|fnView|viewDetail)\s*\(\s*['\"]?(\d+)['\"]?\s*\)", onclick)
                                if match:
                                    seq = match.group(1)
                                    detail_url = f"{self.base_url}/pms/st/st_0205/view?seq={seq}"
                                else:
                                    continue
                        elif href and href != '#' and 'javascript:' not in href:
                            detail_url = urljoin(self.base_url, href)
                        else:
                            continue
                        
                        # Extract metadata
                        meta_info = {}
                        
                        # Look for date
                        date_match = re.search(r'(\d{4}[-./]\d{2}[-./]\d{2})', item.get_text())
                        if date_match:
                            meta_info['date'] = date_match.group(1)
                        
                        announcements.append({
                            'num': len(announcements) + 1,
                            'title': title,
                            'url': detail_url,
                            'has_attachment': False,
                            **meta_info
                        })
                        
                    except Exception as e:
                        print(f"Error parsing list item: {e}")
                        continue
        
        # Strategy 3: Look for div-based list
        if not announcements:
            # Look for repeated div patterns
            list_items = soup.find_all('div', class_=re.compile('item|article|post'))
            for item in list_items:
                try:
                    title_elem = item.find(['h3', 'h4', 'h5', 'a', 'span'], class_=re.compile('title|subject'))
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    
                    # Find link
                    if title_elem.name == 'a':
                        link = title_elem
                    else:
                        link = item.find('a')
                    
                    if not link:
                        continue
                    
                    href = link.get('href', '')
                    if href and href != '#':
                        detail_url = urljoin(self.base_url, href)
                    else:
                        continue
                    
                    announcements.append({
                        'num': len(announcements) + 1,
                        'title': title,
                        'url': detail_url,
                        'has_attachment': False
                    })
                    
                except Exception as e:
                    print(f"Error parsing div item: {e}")
                    continue
        
        return announcements
        
    def parse_detail_page(self, html_content):
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 내용 찾기
        content_area = None
        
        # 상세 내용 영역 찾기 - 다양한 패턴 시도
        content_selectors = [
            'div.board_view',
            'div.view_content',
            'div.content_area',
            'div.board_content',
            'div.bbs_content',
            'div.view_cont',
            'div.view_area',
            'div#content',
            'td.content',
            'div.detail_content',
            'div[class*="view"]',
            'div[class*="content"]',
            'table.board_view td'
        ]
        
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                # Check if it has substantial content
                text = content_area.get_text(strip=True)
                if len(text) > 50:  # Arbitrary threshold
                    break
                else:
                    content_area = None
        
        # If no content area found, look for the main text area
        if not content_area:
            # Try to find the largest text block
            all_divs = soup.find_all('div')
            max_text_div = None
            max_text_len = 0
            
            for div in all_divs:
                # Skip navigation and header divs
                if div.get('class'):
                    class_str = ' '.join(div.get('class'))
                    if any(skip in class_str for skip in ['nav', 'header', 'footer', 'menu', 'gnb', 'lnb']):
                        continue
                
                text = div.get_text(strip=True)
                if len(text) > max_text_len and len(text) > 100:
                    max_text_len = len(text)
                    max_text_div = div
            
            if max_text_div:
                content_area = max_text_div
                
        # 공고 요약 정보 찾기
        summary_area = soup.find('div', class_='summary') or soup.find('div', class_='board_summary')
        
        # PDF iframe 확인
        pdf_iframe = soup.find('iframe', src=re.compile(r'\.pdf'))
        if pdf_iframe and not content_area:
            # PDF가 본문인 경우
            pdf_url = pdf_iframe.get('src', '')
            if pdf_url and not pdf_url.startswith('http'):
                pdf_url = urljoin(self.base_url, pdf_url)
            content_area = f"본문 내용은 PDF 파일로 제공됩니다: {pdf_url}"
        
        # 첨부파일 찾기
        attachments = []
        
        # Strategy 1: Look for file table
        file_tables = soup.find_all('table', class_=re.compile('file|attach|download'))
        for file_table in file_tables:
            file_rows = file_table.find_all('tr')
            for row in file_rows:
                # Skip header rows
                if row.find('th'):
                    continue
                    
                # Find file link
                file_link = row.find('a', href=True)
                if file_link:
                    file_name = file_link.get_text(strip=True)
                    file_url = file_link.get('href', '')
                    
                    if not file_url.startswith('http'):
                        file_url = urljoin(self.base_url, file_url)
                    
                    if file_name and file_url:
                        attachments.append({
                            'name': file_name,
                            'url': file_url
                        })
        
        # Strategy 2: Look for download links with JavaScript
        if not attachments:
            download_links = soup.find_all('a', onclick=re.compile('download|fileDown'))
            for link in download_links:
                file_name = link.get_text(strip=True)
                onclick = link.get('onclick', '')
                
                # Extract file ID or parameters from onclick
                # Common patterns: fnDownload('123'), fileDownload('123', '456')
                match = re.search(r"(?:fnDownload|fileDownload|download)\s*\(\s*['\"]?([^'\"]+)['\"]?", onclick)
                if match:
                    file_id = match.group(1)
                    # Construct download URL based on common patterns
                    file_url = f"{self.base_url}/pms/common/file/download?fileId={file_id}"
                    
                    if file_name:
                        attachments.append({
                            'name': file_name,
                            'url': file_url
                        })
        
        # Strategy 3: Look for any links with file extensions
        if not attachments:
            all_links = soup.find_all('a', href=re.compile(r'\.(pdf|hwp|doc|docx|xls|xlsx|zip|rar)', re.I))
            for link in all_links:
                file_name = link.get_text(strip=True) or link.get('href', '').split('/')[-1]
                file_url = link.get('href', '')
                
                if not file_url.startswith('http'):
                    file_url = urljoin(self.base_url, file_url)
                
                if file_name and file_url:
                    attachments.append({
                        'name': file_name,
                        'url': file_url
                    })
        
        # 본문을 마크다운으로 변환
        content_md = ""
        if summary_area:
            content_md += "## 요약\n" + self.h.handle(str(summary_area)) + "\n\n"
        
        if content_area:
            if isinstance(content_area, str):
                content_md += content_area
            else:
                content_md += self.h.handle(str(content_area))
        else:
            content_md += "본문 내용을 찾을 수 없습니다."
        
        return {
            'content': content_md,
            'attachments': attachments
        }
        
    def process_announcement(self, announcement, index, output_base='output'):
        """개별 공고 처리 - DJBEA 맞춤형"""
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
**등록일**: {announcement.get('date', 'N/A')}  
**주관기관**: {announcement.get('organization', 'N/A')}  
**공고기간**: {announcement.get('period', 'N/A')}  
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
                file_path = os.path.join(attachments_folder, file_name)
                self.download_file(attachment['url'], file_path)
        else:
            print("No attachments found")
                
        # 잠시 대기 (서버 부하 방지)
        time.sleep(1)