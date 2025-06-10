import requests
from bs4 import BeautifulSoup
import os
import re
from base_scraper import BaseScraper
from urllib.parse import urljoin, parse_qs, urlparse
import json
import time

class GBTPScraper(BaseScraper):
    """경북테크노파크 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://gbtp.or.kr"
        self.list_url = "https://gbtp.or.kr/user/board.do?bbsId=BBSMSTR_000000000023"
        self.verify_ssl = False  # SSL 인증서 문제가 있을 수 있음
        # 세션 초기화를 위해 메인 페이지 방문
        self._init_session()
        
    def _init_session(self):
        """세션 초기화"""
        try:
            # 메인 페이지 방문하여 세션 쿠키 획득
            response = self.session.get(self.base_url, verify=self.verify_ssl)
            print(f"Session initialized. Status: {response.status_code}")
        except Exception as e:
            print(f"Failed to initialize session: {e}")
        
    def get_list_url(self, page_num):
        """페이지 번호에 따른 목록 URL 반환"""
        if page_num == 1:
            return self.list_url
        return f"{self.list_url}&pageIndex={page_num}"
        
    def parse_list_page(self, html_content):
        """목록 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 테이블에서 공고 목록 찾기
        table = soup.find('table', class_='board-list') or soup.find('table')
        if not table:
            print("No table found in the page")
            return announcements
            
        rows = table.find('tbody').find_all('tr') if table.find('tbody') else table.find_all('tr')[1:]
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 6:  # 최소 6개 컬럼 필요
                continue
                
            try:
                # 번호 (첫 번째 td)
                number_cell = cells[0]
                number = number_cell.get_text(strip=True)
                
                # 상태 (두 번째 td)  
                status_cell = cells[1]
                status = status_cell.get_text(strip=True) if status_cell else ""
                
                # 제목 및 링크 (세 번째 td)
                title_cell = cells[2]
                title_link = title_cell.find('a')
                if not title_link:
                    continue
                    
                title = title_link.get_text(strip=True)
                
                # onclick 속성에서 파라미터 추출
                onclick = title_link.get('onclick', '')
                if onclick:
                    # fn_detail('10107','1') 형태에서 파라미터 추출
                    match = re.search(r"fn_detail\('([^']+)',\s*'([^']+)'\)", onclick)
                    if match:
                        bbs_seq = match.group(1)
                        page_index = match.group(2)
                        # JavaScript 기반 접근이므로 POST 요청이 필요할 수 있음
                        # 일단 기존 board.do 패턴으로 시도
                        detail_url = f"{self.base_url}/user/board.do?bbsId=BBSMSTR_000000000023&flag=view&bbsSeq={bbs_seq}&pageIndex={page_index}"
                    else:
                        print(f"Could not parse onclick: {onclick}")
                        continue
                else:
                    print(f"No onclick found for title: {title}")
                    continue
                
                # 공고기간 (네 번째 td)
                period_cell = cells[3]
                period = period_cell.get_text(strip=True) if period_cell else ""
                
                # 조회수 (다섯 번째 td)
                hits_cell = cells[4]
                hits = hits_cell.get_text(strip=True) if hits_cell else ""
                
                # 첨부파일 여부 (여섯 번째 td)
                file_cell = cells[5]
                has_attachment = bool(file_cell.find('i', class_='far fa-file-download') or file_cell.find('i', class_='fa-file-download'))
                
                # 작성자 (일곱 번째 td, 있는 경우)
                writer = ""
                if len(cells) > 6:
                    writer_cell = cells[6]
                    writer = writer_cell.get_text(strip=True) if writer_cell else ""
                
                announcement = {
                    'number': number,
                    'title': title,
                    'url': detail_url,
                    'status': status,
                    'period': period,
                    'hits': hits,
                    'writer': writer,
                    'has_attachment': has_attachment,
                    'onclick': onclick  # onclick 속성 포함
                }
                
                announcements.append(announcement)
                
            except Exception as e:
                print(f"Error parsing row: {e}")
                continue
                
        return announcements
        
    def parse_detail_page(self, html_content):
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 내용 추출
        content = ""
        
        # 일반적인 상세 페이지 선택자들 시도
        content_selectors = [
            '.board-view .view-content',
            '.board-view .content', 
            '.view-content',
            '.content-area',
            '.board-content',
            '#content',
            '.view-area',
            '#contentDiv',  # GBTP 특정 선택자
            '.sub_wrap .content',
            '.board_view_cont'
        ]
        
        content_element = None
        for selector in content_selectors:
            content_element = soup.select_one(selector)
            if content_element:
                break
                
        if content_element:
            # HTML을 마크다운으로 변환
            content = self.h.handle(str(content_element))
        else:
            # 폴백: 전체 본문에서 헤더/푸터 제외하고 추출
            body = soup.find('body')
            if body:
                # 스크립트, 스타일, 네비게이션 등 제거
                for tag in body(['script', 'style', 'nav', 'header', 'footer']):
                    tag.decompose()
                content = self.h.handle(str(body))
            else:
                content = "본문을 찾을 수 없습니다."
        
        # 첨부파일 링크 찾기
        attachments = []
        
        # 첨부파일 다운로드 링크 찾기 (fn_egov_downFile 함수 사용)
        # href나 onclick에서 fn_egov_downFile 호출을 찾기
        download_links = soup.find_all('a', href=re.compile(r'javascript:.*fn_egov_downFile')) if soup.find_all('a', href=re.compile(r'javascript:.*fn_egov_downFile')) else []
        onclick_links = soup.find_all('a', onclick=re.compile(r'fn_egov_downFile')) if soup.find_all('a', onclick=re.compile(r'fn_egov_downFile')) else []
        
        # 모든 잠재적 다운로드 링크 수집
        all_download_links = download_links + onclick_links
        
        for link in all_download_links:
            href = link.get('href', '')
            onclick = link.get('onclick', '')
            
            # fn_egov_downFile('atchFileId', 'fileSn') 형태에서 파라미터 추출
            pattern = r"fn_egov_downFile\('([^']+)',\s*'([^']+)'\)"
            match = re.search(pattern, href + onclick)
            
            if match:
                atch_file_id = match.group(1)
                file_sn = match.group(2)
                
                # 다운로드 URL 생성
                download_url = f"{self.base_url}/cmm/fms/FileDown.do?atchFileId={atch_file_id}&fileSn={file_sn}"
                
                # 파일명 추출 (링크 텍스트에서)
                file_name = link.get_text(strip=True)
                
                # 아이콘 제거 및 정리
                file_name = re.sub(r'^\s*\[?붙임\d*\]?\s*', '', file_name)  # [붙임1] 등 제거
                file_name = file_name.strip()
                
                if not file_name or file_name in ['다운로드', '첨부파일', '']:
                    file_name = f"attachment_{file_sn}"
                
                attachments.append({
                    'name': file_name,
                    'url': download_url,
                    'atch_file_id': atch_file_id,
                    'file_sn': file_sn
                })
        
        # 추가 검색: class="view_file_download"가 있는 링크들
        if not attachments:
            view_file_links = soup.find_all('a', class_='view_file_download')
            for link in view_file_links:
                onclick = link.get('onclick', '')
                match = re.search(r"fn_egov_downFile\('([^']+)',\s*'([^']+)'\)", onclick)
                if match:
                    atch_file_id = match.group(1)
                    file_sn = match.group(2)
                    download_url = f"{self.base_url}/cmm/fms/FileDown.do?atchFileId={atch_file_id}&fileSn={file_sn}"
                    
                    file_name = link.get_text(strip=True)
                    file_name = re.sub(r'^\s*\[?붙임\d*\]?\s*', '', file_name)
                    file_name = file_name.strip()
                    
                    if not file_name:
                        file_name = f"attachment_{file_sn}"
                        
                    attachments.append({
                        'name': file_name,
                        'url': download_url,
                        'atch_file_id': atch_file_id,
                        'file_sn': file_sn
                    })
        
        # 최후의 수단: 모든 onclick 속성에서 fn_egov_downFile 찾기
        if not attachments:
            all_elements = soup.find_all(onclick=re.compile(r'fn_egov_downFile'))
            for element in all_elements:
                onclick = element.get('onclick', '')
                match = re.search(r"fn_egov_downFile\('([^']+)',\s*'([^']+)'\)", onclick)
                if match:
                    atch_file_id = match.group(1)
                    file_sn = match.group(2)
                    download_url = f"{self.base_url}/cmm/fms/FileDown.do?atchFileId={atch_file_id}&fileSn={file_sn}"
                    
                    file_name = element.get_text(strip=True)
                    file_name = re.sub(r'^\s*\[?붙임\d*\]?\s*', '', file_name)
                    file_name = file_name.strip()
                    
                    if not file_name:
                        file_name = f"attachment_{file_sn}"
                        
                    attachments.append({
                        'name': file_name,
                        'url': download_url,
                        'atch_file_id': atch_file_id,
                        'file_sn': file_sn
                    })
        
        return {
            'content': content,
            'attachments': attachments
        }
        
    def process_announcement(self, announcement, index, output_base='output'):
        """GBTP 전용 공고 처리 (JavaScript 실행이 필요한 사이트)"""
        print(f"\nProcessing announcement {index}: {announcement['title']}")
        
        # 폴더 생성
        folder_title = self.sanitize_filename(announcement['title'])[:50]
        folder_name = f"{index:03d}_{folder_title}"
        folder_path = os.path.join(output_base, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        # onclick에서 파라미터 추출
        onclick = announcement.get('onclick', '')
        if onclick:
            match = re.search(r"fn_detail\('([^']+)',\s*'([^']+)'\)", onclick)
            if match:
                bbs_seq = match.group(1)
                page_index = match.group(2)
                
                content_found = False
                detail_content = ""
                attachments = []
                
                # POST 요청으로 상세 페이지 접근 시도
                try:
                    # 먼저 목록 페이지에서 세션 확보
                    list_response = self.get_page(self.list_url)
                    
                    # POST 데이터로 상세 페이지 요청
                    detail_data = {
                        'bbsId': 'BBSMSTR_000000000023',
                        'flag': 'view',
                        'bbsSeq': bbs_seq,
                        'pageIndex': page_index
                    }
                    
                    detail_url = f"{self.base_url}/user/board.do"
                    
                    print(f"Attempting POST to: {detail_url} with bbsSeq={bbs_seq}")
                    response = self.session.post(detail_url, data=detail_data, verify=self.verify_ssl)
                    
                    if response and response.status_code == 200:
                        # 실제 상세 페이지인지 확인 (fn_egov_downFile 함수나 특정 클래스 존재 확인)
                        if ("fn_egov_downFile" in response.text or 
                            "view_file_download" in response.text or
                            len(response.text) > 10000):  # 상세 페이지는 더 많은 내용을 가짐
                            
                            detail = self.parse_detail_page(response.text)
                            detail_content = detail['content']
                            attachments = detail['attachments']
                            content_found = True
                            print(f"✓ Found detail content via POST: {len(detail_content)} chars, {len(attachments)} attachments")
                        else:
                            print("POST response seems to be list page, not detail page")
                    
                except Exception as e:
                    print(f"Error with POST request: {e}")
                
                # POST가 실패하면 기존 GET 방식들 시도
                if not content_found:
                    url_patterns = [
                        f"{self.base_url}/user/board.do?bbsId=BBSMSTR_000000000023&flag=view&bbsSeq={bbs_seq}&pageIndex={page_index}",
                        f"{self.base_url}/user/board.do?bbsId=BBSMSTR_000000000023&flag=view&bbsSeq={bbs_seq}",
                        f"{self.base_url}/user/boardDetail.do?bbsId=BBSMSTR_000000000023&bbsSeq={bbs_seq}",
                    ]
                    
                    for url in url_patterns:
                        print(f"Trying GET URL: {url}")
                        try:
                            response = self.get_page(url)
                            if response and response.status_code == 200:
                                # 실제 상세 페이지인지 확인
                                if ("fn_egov_downFile" in response.text or 
                                    "view_file_download" in response.text or
                                    ("페이지를 찾을 수 없습니다" not in response.text and len(response.text) > 5000)):
                                    
                                    detail = self.parse_detail_page(response.text)
                                    detail_content = detail['content']
                                    attachments = detail['attachments']
                                    content_found = True
                                    print(f"✓ Found content via GET: {len(detail_content)} chars, {len(attachments)} attachments")
                                    break
                        except Exception as e:
                            print(f"Error with URL {url}: {e}")
                            continue
                
                # 내용을 찾지 못한 경우 기본 정보만 저장
                if not content_found:
                    print("Could not find detail content, saving basic info only")
                    detail_content = f"**공고 제목**: {announcement['title']}\n\n**상세 내용**: 상세 내용을 가져올 수 없습니다.\n\n**참고**: JavaScript 기반 사이트로 직접 접근이 제한될 수 있습니다."
                    attachments = []
                
                # 메타 정보 추가
                meta_info = f"""# {announcement['title']}

**작성자**: {announcement.get('writer', 'N/A')}  
**작성일**: {announcement.get('date', 'N/A')}  
**접수기간**: {announcement.get('period', 'N/A')}  
**상태**: {announcement.get('status', 'N/A')}  
**원본 URL**: {announcement.get('url', 'N/A')}

---

"""
                
                # 본문 저장
                content_path = os.path.join(folder_path, 'content.md')
                with open(content_path, 'w', encoding='utf-8') as f:
                    f.write(meta_info + detail_content)
                    
                print(f"Saved content to: {content_path}")
                
                # 첨부파일 다운로드
                if attachments:
                    print(f"Found {len(attachments)} attachment(s)")
                    attachments_folder = os.path.join(folder_path, 'attachments')
                    os.makedirs(attachments_folder, exist_ok=True)
                    
                    for i, attachment in enumerate(attachments):
                        print(f"  Attachment {i+1}: {attachment['name']}")
                        # 파일명 정리
                        file_name = self.sanitize_filename(attachment['name'])
                        
                        if not file_name or file_name.isspace():
                            file_name = f"attachment_{i+1}"
                            
                        file_path = os.path.join(attachments_folder, file_name)
                        self.download_file(attachment['url'], file_path)
                else:
                    print("No attachments found")
                
                # 잠시 대기 (서버 부하 방지)
                time.sleep(1)
            else:
                print(f"Could not parse onclick: {onclick}")
        else:
            print(f"No onclick found for: {announcement['title']}")

if __name__ == "__main__":
    scraper = GBTPScraper()
    scraper.scrape_pages(max_pages=4, output_base='output/gbtp')