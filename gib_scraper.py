from base_scraper import BaseScraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin, parse_qs, urlparse
import re
import os

class GIBScraper(BaseScraper):
    """경북바이오산업연구원(GIB) 전용 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://gib.re.kr"
        self.list_url = "https://gib.re.kr/module/bbs/list.php?mid=/news/notice"
        
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
        
        # 테이블 찾기
        table = soup.find('table')
        if not table:
            print("No table found")
            return announcements
            
        # tbody 또는 테이블의 모든 tr 찾기
        tbody = table.find('tbody')
        if tbody:
            rows = tbody.find_all('tr')
        else:
            rows = table.find_all('tr')[1:]  # 헤더 제외
        
        print(f"Found {len(rows)} rows in table")
        
        for i, row in enumerate(rows):
            try:
                cells = row.find_all('td')
                if len(cells) < 6:  # 순번, 상태, 제목, 파일, 글쓴이, 날짜, 조회
                    continue
                
                # 제목 셀에서 링크 찾기 (일반적으로 3번째 셀)
                title_cell = cells[2]  # 제목 셀
                link_elem = title_cell.find('a')
                
                if not link_elem:
                    # JavaScript 함수 호출 방식 확인
                    onclick = title_cell.get('onclick', '')
                    if not onclick:
                        # 부모 tr에서 onclick 확인
                        onclick = row.get('onclick', '')
                    
                    if onclick:
                        # onclick에서 goView 파라미터 추출
                        goview_match = re.search(r'goView\((\d+),\s*(\d+),\s*(\d+)\)', onclick)
                        if goview_match:
                            cur_row = goview_match.group(1)
                            rdno = goview_match.group(2)
                            rdnoorg = goview_match.group(3)
                            detail_url = f"{self.base_url}/module/bbs/view.php?mid=/news/notice&cur_row={cur_row}&rdno={rdno}&rdnoorg={rdnoorg}"
                        else:
                            print(f"Could not extract goView parameters from onclick: {onclick}")
                            continue
                    else:
                        print(f"No link or onclick found in row {i}")
                        continue
                else:
                    # 직접 링크가 있는 경우
                    href = link_elem.get('href', '')
                    onclick = link_elem.get('onclick', '')
                    
                    # JavaScript 호출인지 확인
                    if href.startswith('javascript:') or onclick:
                        # href나 onclick에서 goView 파라미터 추출
                        js_code = href if href.startswith('javascript:') else onclick
                        goview_match = re.search(r'goView\((\d+),\s*(\d+),\s*(\d+)\)', js_code)
                        if goview_match:
                            cur_row = goview_match.group(1)
                            rdno = goview_match.group(2)
                            rdnoorg = goview_match.group(3)
                            detail_url = f"{self.base_url}/module/bbs/view.php?mid=/news/notice&cur_row={cur_row}&rdno={rdno}&rdnoorg={rdnoorg}"
                        else:
                            print(f"Could not extract goView parameters from: {js_code}")
                            continue
                    elif href.startswith('http'):
                        detail_url = href
                    elif href.startswith('/'):
                        detail_url = self.base_url + href
                    elif href.startswith('?'):
                        detail_url = self.base_url + "/module/bbs/view.php" + href
                    else:
                        detail_url = urljoin(self.base_url, href)
                
                # 제목 추출
                title = title_cell.get_text(strip=True)
                # 파일 아이콘 등 제거
                title = re.sub(r'\s*첨부파일\s*있음\s*', '', title)
                
                # 상태 (2번째 셀)
                status = cells[1].get_text(strip=True) if len(cells) > 1 else ''
                
                # 글쓴이 (5번째 셀)
                writer = cells[4].get_text(strip=True) if len(cells) > 4 else ''
                
                # 날짜 (6번째 셀)
                date = cells[5].get_text(strip=True) if len(cells) > 5 else ''
                
                # 첨부파일 여부 확인 (4번째 셀 또는 제목에서)
                has_attachment = '첨부파일 있음' in row.get_text()
                
                announcements.append({
                    'title': title,
                    'url': detail_url,
                    'status': status,
                    'writer': writer,
                    'date': date,
                    'period': '',  # GIB에는 접수기간 컬럼이 별도로 없음
                    'has_attachment': has_attachment
                })
                
                print(f"Parsed: {title[:50]}...")
                
            except Exception as e:
                print(f"Error parsing row {i}: {e}")
                continue
                
        return announcements
        
    def parse_detail_page(self, html_content):
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 내용 찾기
        content_area = None
        
        # 가능한 본문 선택자들 (GIB 사이트 구조에 맞게 조정)
        content_selectors = [
            'div.bbs_content',  # GIB specific
            'div.bbs_B_content',
            'div.board_view_content',
            'div.view_content',
            'div.content',
            'td.content',
            'div#content',
            '.article_content',
            '.post_content'
        ]
        
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                print(f"Found content using selector: {selector}")
                break
        
        # 대안: 긴 텍스트가 있는 div 찾기
        if not content_area:
            divs = soup.find_all('div')
            for div in divs:
                text_length = len(div.get_text(strip=True))
                if text_length > 200:  # 충분히 긴 텍스트
                    content_area = div
                    print(f"Found content by text length: {text_length}")
                    break
        
        # 내용 추출
        if content_area:
            # 불필요한 요소 제거
            for tag in content_area.find_all(['script', 'style', 'nav', 'header', 'footer']):
                tag.decompose()
            
            content = self.h.handle(str(content_area))
        else:
            print("Warning: Could not find content area, using full body")
            body = soup.find('body')
            if body:
                content = self.h.handle(str(body))
            else:
                content = "내용을 찾을 수 없습니다."
        
        # 첨부파일 찾기
        attachments = []
        
        # GIB 특화: 먼저 첨부파일 영역 찾기
        attachment_areas = soup.find_all(['div'], class_=['div_attf_view_list', 'div_attf_view'])
        if attachment_areas:
            print(f"Found {len(attachment_areas)} attachment areas")
        
        # GIB 특화: downloadAttFile 함수 호출 찾기 (a 태그와 span 태그 모두 확인)
        download_links = soup.find_all(lambda tag: tag.get('onclick') and 'downloadAttFile' in tag.get('onclick', ''))
        
        for link in download_links:
            onclick = link.get('onclick', '')
            # downloadAttFile('md_bbs', '1', '5653', '1') 패턴에서 파라미터 추출
            match = re.search(r"downloadAttFile\(\s*['\"]([^'\"]*)['\"],\s*['\"]([^'\"]*)['\"],\s*['\"]([^'\"]*)['\"],\s*['\"]([^'\"]*)['\"]", onclick)
            if match:
                attf_flag = match.group(1)  # 'md_bbs'
                seno = match.group(2)       # board number
                atnum = match.group(3)      # record number
                atpath = match.group(4)     # attachment sequence
                
                file_name = link.get_text(strip=True)
                if not file_name:
                    file_name = f"attachment_{atpath}"
                
                # 특별한 다운로드 URL 구성 - GIB는 2단계 과정 필요
                download_info = {
                    'name': file_name,
                    'attf_flag': attf_flag,
                    'seno': seno,
                    'atnum': atnum,
                    'atpath': atpath,
                    'url': 'gib_download'  # 특별한 표시
                }
                
                attachments.append(download_info)
                print(f"Found attachment: {file_name} (params: {attf_flag}, {seno}, {atnum}, {atpath})")
        
        # 일반적인 다운로드 링크도 확인
        if not attachments:
            # 다양한 첨부파일 패턴 확인
            attachment_patterns = [
                'a[href*="download"]',
                'a[href*="file"]',
                'a[href*="attach"]',
                'a[onclick*="download"]',
                'a[onclick*="file"]'
            ]
            
            for pattern in attachment_patterns:
                links = soup.select(pattern)
                for link in links:
                    href = link.get('href', '')
                    onclick = link.get('onclick', '')
                    
                    if href and any(ext in href.lower() for ext in ['.pdf', '.hwp', '.doc', '.xlsx', '.zip', '.jpg', '.png']):
                        # 직접 다운로드 링크
                        file_url = urljoin(self.base_url, href)
                        file_name = link.get_text(strip=True) or href.split('/')[-1]
                    elif onclick:
                        # JavaScript 다운로드 함수
                        # 파일 ID나 파라미터 추출
                        file_id_match = re.search(r'[\'"]([^\'",]+)[\'"]', onclick)
                        if file_id_match:
                            file_id = file_id_match.group(1)
                            file_url = f"{self.base_url}/module/bbs/download.php?file_id={file_id}"
                            file_name = link.get_text(strip=True) or f"file_{file_id}"
                        else:
                            continue
                    else:
                        continue
                    
                    # 중복 제거
                    if not any(att.get('url') == file_url for att in attachments):
                        attachments.append({
                            'name': file_name,
                            'url': file_url
                        })
            
            # 파일 확장자가 포함된 모든 링크 찾기
            if not attachments:
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    href = link['href']
                    text = link.get_text(strip=True)
                    
                    # 파일 확장자 패턴 확인
                    if any(ext in href.lower() or ext in text.lower() for ext in ['.pdf', '.hwp', '.doc', '.xlsx', '.zip', '.jpg', '.png']):
                        file_url = urljoin(self.base_url, href)
                        file_name = text or href.split('/')[-1]
                        
                        # 중복 제거
                        if not any(att.get('url') == file_url for att in attachments):
                            attachments.append({
                                'name': file_name,
                                'url': file_url
                            })
        
        return {
            'content': content,
            'attachments': attachments
        }
    
    def download_file(self, url, save_path, attachment_info=None):
        """파일 다운로드 - GIB 특화 처리"""
        try:
            if url == 'gib_download' and attachment_info:
                # GIB 특화 2단계 다운로드 처리
                return self._download_gib_file(attachment_info, save_path)
            else:
                # 일반 다운로드
                return super().download_file(url, save_path)
                
        except Exception as e:
            print(f"Error downloading file: {e}")
            return False
    
    def _download_gib_file(self, attachment_info, save_path):
        """GIB 첨부파일 다운로드 (2단계 과정)"""
        try:
            print(f"GIB downloading: {attachment_info['name']}")
            
            # 1단계: download.php로 POST 요청
            download_url = f"{self.base_url}/lib/php/pub/download.php"
            
            # POST 데이터 구성
            post_data = {
                'attf_flag': attachment_info['attf_flag'],
                'seno': attachment_info['seno'],
                'atnum': attachment_info['atnum'],
                'atpath': attachment_info['atpath']
            }
            
            # 헤더 설정
            headers = self.headers.copy()
            headers.update({
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': self.base_url + '/module/bbs/view.php'
            })
            
            # 1단계 요청
            response = self.session.post(download_url, data=post_data, headers=headers, verify=self.verify_ssl)
            
            if response.status_code != 200:
                print(f"Step 1 failed with status: {response.status_code}")
                return False
            
            # 2단계: download_open.php로 자동 리다이렉트 또는 직접 호출
            download_open_url = f"{self.base_url}/lib/php/pub/download_open.php"
            
            # 2단계 요청 (같은 데이터로)
            response = self.session.post(download_open_url, data=post_data, headers=headers, stream=True, verify=self.verify_ssl)
            
            if response.status_code != 200:
                print(f"Step 2 failed with status: {response.status_code}")
                return False
            
            # Content-Disposition 헤더에서 실제 파일명 추출
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
                        try:
                            filename = filename.encode('latin-1').decode('euc-kr')
                        except:
                            pass
                    
                    # 파일명이 유효하면 save_path 업데이트
                    if filename and not filename.isspace():
                        save_dir = os.path.dirname(save_path)
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
            
        except Exception as e:
            print(f"Error in GIB file download: {e}")
            return False