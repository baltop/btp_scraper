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
        
        # 목록 컨테이너 찾기
        list_container = soup.find('ul', class_='generic')
        if not list_container:
            return announcements
            
        # 각 공고 항목 찾기
        items = list_container.find_all('li')
        
        for item in items:
            try:
                # 번호
                num_div = item.find('div', class_='generic')
                num = num_div.get_text(strip=True) if num_div else ''
                
                # 제목 및 링크
                title_link = item.find('a')
                if not title_link:
                    continue
                    
                title = title_link.get_text(strip=True)
                
                # 상세보기 링크 찾기
                detail_link = item.find('a', text=re.compile('상세보기'))
                if detail_link:
                    detail_url = detail_link.get('href', '')
                    if detail_url and not detail_url.startswith('http'):
                        detail_url = urljoin(self.base_url, detail_url)
                else:
                    # onclick 이벤트에서 URL 추출 시도
                    onclick = title_link.get('onclick', '')
                    if onclick:
                        # JavaScript 함수에서 파라미터 추출
                        match = re.search(r"location\.href='([^']+)'", onclick)
                        if match:
                            detail_url = urljoin(self.base_url, match.group(1))
                        else:
                            continue
                    else:
                        continue
                
                # 메타 정보 추출
                meta_info = {}
                
                # 등록일 찾기
                date_elem = item.find(text=re.compile('등록일'))
                if date_elem:
                    date_text = date_elem.find_next().get_text(strip=True)
                    meta_info['date'] = date_text
                
                # 주관기관 찾기
                org_elem = item.find(text=re.compile('주관기관'))
                if org_elem:
                    org_text = org_elem.find_next().get_text(strip=True)
                    meta_info['organization'] = org_text
                
                # 공고기간 찾기
                period_elem = item.find(text=re.compile('공고기간'))
                if period_elem:
                    period_text = period_elem.find_next().get_text(strip=True)
                    meta_info['period'] = period_text
                
                # 조회수 찾기
                views_elem = item.find(text=re.compile('조회수'))
                if views_elem:
                    views_text = views_elem.find_next().get_text(strip=True)
                    meta_info['views'] = views_text
                
                # 첨부파일 여부 확인
                has_attachment = bool(item.find('img', alt=re.compile('다운로드|첨부')))
                
                announcements.append({
                    'num': num,
                    'title': title,
                    'url': detail_url,
                    'has_attachment': has_attachment,
                    **meta_info
                })
                
            except Exception as e:
                print(f"Error parsing item: {e}")
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
            'div.bbs_content'
        ]
        
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                break
                
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
        
        # 첨부파일 테이블 찾기
        file_table = soup.find('table', class_=re.compile('file|attach'))
        if file_table:
            file_rows = file_table.find_all('tr')
            for row in file_rows:
                # 파일명과 크기 추출
                file_name_elem = row.find('a') or row.find('span', class_='file_name')
                if file_name_elem:
                    file_name = file_name_elem.get_text(strip=True)
                    
                    # 파일 다운로드 링크 찾기
                    file_link = row.find('a', href=True)
                    if file_link:
                        file_url = file_link.get('href', '')
                        if not file_url.startswith('http'):
                            file_url = urljoin(self.base_url, file_url)
                    else:
                        # JavaScript 다운로드 함수 확인
                        onclick = file_name_elem.get('onclick', '')
                        if onclick:
                            # 파일 ID 추출
                            match = re.search(r"download\('([^']+)'", onclick)
                            if match:
                                file_id = match.group(1)
                                file_url = f"{self.base_url}/download?fileId={file_id}"
                            else:
                                continue
                        else:
                            continue
                    
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