# -*- coding: utf-8 -*-
"""
sitelist.csv에 있는 추가 사이트들을 위한 스크래퍼 모음
각 사이트는 구조가 다르므로 개별적으로 구현 필요
"""

from base_scraper import BaseScraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin, parse_qs, urlparse
import re
import os
import time
import json

class GEPAScraper(BaseScraper):
    """광주광역시 기업지원시스템(GEPA) 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "http://203.251.57.106:82"
        self.list_url = "http://203.251.57.106:82/jwsys_site/gepa/main.html"
        
    def get_list_url(self, page_num):
        # 추가 분석 필요
        return self.list_url
        
    def parse_list_page(self, html_content):
        # 구현 필요
        return []
        
    def parse_detail_page(self, html_content):
        # 구현 필요
        return {'content': '', 'attachments': []}


class DCBScraper(BaseScraper):
    """부산디자인진흥원(DCB) 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.dcb.or.kr"
        self.list_url = "https://www.dcb.or.kr/01_news/?mcode=0401010000"
        
    def get_list_url(self, page_num):
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&page={page_num}"
            
    def parse_list_page(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # DCB는 table 구조 사용
        board_container = soup.find('div', class_='board-text')
        if not board_container:
            # 대체 방법: table 직접 찾기
            table = soup.find('table', class_=re.compile('board|list'))
            if table:
                board_container = table
        
        if board_container:
            # 모든 tr 태그 찾기
            rows = board_container.find_all('tr')
            
            for row in rows:
                try:
                    tds = row.find_all('td')
                    if len(tds) < 2:
                        continue
                    
                    # 번호 셀 확인 (공지사항은 icon_notice.png)
                    num_td = tds[0]
                    num_text = num_td.get_text(strip=True)
                    
                    # 제목 셀에서 링크 찾기
                    title_td = None
                    for td in tds:
                        if td.find('a'):
                            title_td = td
                            break
                    
                    if not title_td:
                        continue
                        
                    link = title_td.find('a')
                    if not link:
                        continue
                    
                    title = link.get_text(strip=True)
                    href = link.get('href', '')
                    
                    if href:
                        # URL이 상대경로인 경우 절대경로로 변환
                        if href.startswith('/'):
                            detail_url = self.base_url + href
                        else:
                            detail_url = urljoin(self.base_url, href)
                    else:
                        continue
                    
                    # 날짜 찾기 (보통 마지막에서 두 번째 td)
                    date = ''
                    if len(tds) >= 4:
                        date = tds[-2].get_text(strip=True)
                    
                    # 파일 첨부 여부 확인
                    has_file = False
                    if title_td.find('img', alt='파일'):
                        has_file = True
                    
                    announcements.append({
                        'num': num_text,
                        'title': title,
                        'url': detail_url,
                        'date': date,
                        'has_file': has_file
                    })
                    
                except Exception as e:
                    continue
                    
        return announcements
        
    def parse_detail_page(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 영역 찾기 - DCB는 특정 구조 사용
        content_area = None
        
        # 방법 1: board-view 클래스 찾기
        content_area = soup.find('div', class_='board-view')
        
        # 방법 2: 본문이 있는 테이블 찾기
        if not content_area:
            tables = soup.find_all('table')
            for table in tables:
                # 본문은 보통 긴 텍스트가 있는 셀에 있음
                tds = table.find_all('td')
                for td in tds:
                    text_length = len(td.get_text(strip=True))
                    if text_length > 200:  # 본문으로 추정되는 긴 텍스트
                        content_area = td
                        break
                if content_area:
                    break
        
        # 첨부파일 찾기
        attachments = []
        
        # 방법 1: 파일 다운로드 링크 패턴으로 찾기
        file_patterns = [
            r'/_Bbs/board/download\.php',
            r'/download\.php',
            r'act_download',
            r'fileDown',
            r'file_down'
        ]
        
        for pattern in file_patterns:
            file_links = soup.find_all('a', href=re.compile(pattern))
            for link in file_links:
                file_name = link.get_text(strip=True)
                file_url = link.get('href', '')
                
                # 빈 파일명 처리
                if not file_name or file_name.isspace():
                    # href에서 파일명 추출 시도
                    if 'filename=' in file_url:
                        import urllib.parse
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(file_url).query)
                        if 'filename' in parsed:
                            file_name = parsed['filename'][0]
                    else:
                        file_name = "첨부파일"
                
                if file_url:
                    file_url = urljoin(self.base_url, file_url)
                    attachments.append({
                        'name': file_name,
                        'url': file_url
                    })
        
        # 방법 2: 첨부파일 영역에서 찾기
        file_areas = soup.find_all(['div', 'td'], class_=re.compile('file|attach|download'))
        for area in file_areas:
            links = area.find_all('a')
            for link in links:
                if link in [a for a in attachments]:  # 중복 제거
                    continue
                    
                file_name = link.get_text(strip=True)
                file_url = link.get('href', '')
                
                if file_url and file_name and not file_name.isspace():
                    file_url = urljoin(self.base_url, file_url)
                    attachments.append({
                        'name': file_name,
                        'url': file_url
                    })
        
        # 본문을 마크다운으로 변환
        content_md = ""
        if content_area:
            # 불필요한 스크립트나 스타일 태그 제거
            for tag in content_area.find_all(['script', 'style']):
                tag.decompose()
            content_md = self.h.handle(str(content_area))
        
        return {
            'content': content_md,
            'attachments': attachments
        }


class JBFScraper(BaseScraper):
    """전남바이오진흥원(JBF) 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "http://www.jbf.kr"
        self.list_url = "http://www.jbf.kr/main/board.action?cmsid=101050200000"
        
    def get_list_url(self, page_num):
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&pageIndex={page_num}"
            
    def parse_list_page(self, html_content):
        # 구현 필요
        return []
        
    def parse_detail_page(self, html_content):
        # 구현 필요
        return {'content': '', 'attachments': []}


class CEPAScraper(BaseScraper):
    """충남경제진흥원(CEPA) 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.cepa.or.kr"
        self.list_url = "https://www.cepa.or.kr/notice/notice.do?pm=6&ms=32"
        
    def get_list_url(self, page_num):
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&pageIndex={page_num}"
            
    def parse_list_page(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 테이블 구조 찾기
        table = soup.find('table', class_=re.compile('board|list'))
        if not table:
            return announcements
            
        rows = table.find_all('tr')
        
        for row in rows:
            try:
                tds = row.find_all('td')
                if len(tds) < 3:
                    continue
                
                # 제목 찾기
                title_td = None
                for td in tds:
                    if td.find('a'):
                        title_td = td
                        break
                        
                if not title_td:
                    continue
                    
                link = title_td.find('a')
                title = link.get_text(strip=True)
                
                # URL 추출
                href = link.get('href', '')
                onclick = link.get('onclick', '')
                
                if onclick and 'view' in onclick:
                    # JavaScript에서 파라미터 추출
                    match = re.search(r"view\(([^)]+)\)", onclick)
                    if match:
                        params = match.group(1)
                        # 파라미터 처리 로직
                        detail_url = f"{self.base_url}/notice/view.do?seq={params}"
                    else:
                        continue
                elif href:
                    detail_url = urljoin(self.base_url, href)
                else:
                    continue
                
                announcements.append({
                    'title': title,
                    'url': detail_url
                })
                
            except Exception as e:
                continue
                
        return announcements
        
    def parse_detail_page(self, html_content):
        # 구현 필요
        return {'content': '', 'attachments': []}


class CheongjuCCIScraper(BaseScraper):
    """청주상공회의소(CheongjuCCI) 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://cheongjucci.korcham.net"
        self.list_url = "https://cheongjucci.korcham.net/front/board/boardContentsListPage.do?boardId=10701&menuId=1561"
        
    def get_list_url(self, page_num):
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&pageIndex={page_num}"
            
    def parse_list_page(self, html_content):
        # 구현 필요
        return []
        
    def parse_detail_page(self, html_content):
        # 구현 필요
        return {'content': '', 'attachments': []}


class GIBScraper(BaseScraper):
    """경북바이오산업연구원(GIB) 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://gib.re.kr"
        self.list_url = "https://gib.re.kr/module/bbs/list.php?mid=/news/notice"
        
    def get_list_url(self, page_num):
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&page={page_num}"
            
    def parse_list_page(self, html_content):
        # 구현 필요
        return []
        
    def parse_detail_page(self, html_content):
        # 구현 필요
        return {'content': '', 'attachments': []}


class GBTPScraper(BaseScraper):
    """경북테크노파크(GBTP) 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://gbtp.or.kr"
        self.list_url = "https://gbtp.or.kr/user/board.do?bbsId=BBSMSTR_000000000023"
        
    def get_list_url(self, page_num):
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&pageIndex={page_num}"
            
    def parse_list_page(self, html_content):
        # 구현 필요
        return []
        
    def parse_detail_page(self, html_content):
        # 구현 필요
        return {'content': '', 'attachments': []}


class DGDPScraper(BaseScraper):
    """대구경북디자인진흥원(DGDP) 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://dgdp.or.kr"
        self.list_url = "https://dgdp.or.kr/notice/public"
        
    def get_list_url(self, page_num):
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}?page={page_num}"
            
    def parse_list_page(self, html_content):
        # 구현 필요
        return []
        
    def parse_detail_page(self, html_content):
        # 구현 필요
        return {'content': '', 'attachments': []}