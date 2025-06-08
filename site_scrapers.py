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
        
        # 공고 목록 찾기 - 보통 ul/li 구조
        list_container = soup.find('ul', class_=re.compile('list|board'))
        if not list_container:
            return announcements
            
        items = list_container.find_all('li')
        
        for item in items:
            try:
                # 제목 링크 찾기
                link = item.find('a')
                if not link:
                    continue
                    
                title = link.get_text(strip=True)
                href = link.get('href', '')
                
                if href:
                    detail_url = urljoin(self.base_url, href)
                else:
                    continue
                
                # 날짜 찾기
                date_elem = item.find(class_=re.compile('date|time'))
                date = date_elem.get_text(strip=True) if date_elem else ''
                
                announcements.append({
                    'title': title,
                    'url': detail_url,
                    'date': date
                })
                
            except Exception as e:
                continue
                
        return announcements
        
    def parse_detail_page(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 영역 찾기
        content_area = soup.find('div', class_=re.compile('content|view'))
        
        # 첨부파일 찾기
        attachments = []
        file_area = soup.find('div', class_=re.compile('file|attach'))
        if file_area:
            links = file_area.find_all('a')
            for link in links:
                file_name = link.get_text(strip=True)
                file_url = link.get('href', '')
                if file_url:
                    file_url = urljoin(self.base_url, file_url)
                    attachments.append({
                        'name': file_name,
                        'url': file_url
                    })
        
        content_md = ""
        if content_area:
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