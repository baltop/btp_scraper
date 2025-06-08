#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""전남바이오진흥원(JBF) 지원사업 공고 스크래퍼"""

from base_scraper import BaseScraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin, parse_qs
import re
import time
import html2text

class JBFScraper(BaseScraper):
    """전남바이오진흥원(JBF) 웹 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "http://www.jbf.kr"
        self.list_url = "http://www.jbf.kr/main/board.action?cmsid=101050200000"
        self.verify_ssl = False  # SSL 검증 비활성화
        
    def get_list_url(self, page_num):
        """페이지별 목록 URL 생성"""
        return "{}&pageIndex={}".format(self.list_url, page_num)
        
    def parse_list_page(self, html_content):
        """목록 페이지 파싱하여 공고 정보 추출"""
        soup = BeautifulSoup(html_content, 'html.parser')
        items = []
        
        # 게시판 테이블 찾기
        table = soup.find('table', class_='basic_table')
        
        if not table:
            print("테이블을 찾을 수 없습니다.")
            return items
        
        # 테이블의 tbody 찾기
        tbody = table.find('tbody')
        if not tbody:
            tbody = table
        
        for row in tbody.find_all('tr'):
            # 제목 컬럼 찾기 - class='tl'인 td 태그
            title_cell = row.find('td', class_='tl')
            
            if title_cell:
                # 링크 찾기
                link_tag = title_cell.find('a')
                if link_tag:
                    title = link_tag.get_text(strip=True)
                    
                    # href 속성 확인
                    href = link_tag.get('href', '')
                    if href and not href.startswith('#'):
                        if href.startswith('http'):
                            detail_url = href
                        else:
                            # board.action이 있으면 /main/을 추가해야 함
                            if 'board.action' in href and not href.startswith('/main/'):
                                href = '/main/' + href.lstrip('/')
                            detail_url = urljoin(self.base_url, href)
                        items.append({'title': title, 'url': detail_url})
        
        return items
        
    def parse_detail_page(self, html_content):
        """상세 페이지 파싱하여 내용과 첨부파일 추출"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 내용 찾기
        content_area = soup.find('div', class_='table_con')
        if not content_area:
            content_area = soup.find('div', class_='view_con')
        if not content_area:
            content_area = soup.find('div', class_='board_view')
        if not content_area:
            content_area = soup.find('td', class_='content')
        
        content = ""
        if content_area:
            # HTML을 마크다운으로 변환
            content = self.h.handle(str(content_area))
        else:
            print("본문 영역을 찾을 수 없습니다.")
            # 전체 HTML 일부 출력
            print("HTML 길이:", len(html_content))
            
        # 첨부파일 찾기
        attachments = []
        
        # 첨부파일 영역 찾기 - 다양한 패턴 시도
        file_areas = []
        
        # 패턴 1: 파일 영역 클래스
        file_area = soup.find('div', class_='file')
        if file_area:
            file_areas.append(file_area)
        
        # 패턴 2: 첨부파일 제목이 있는 영역
        for th in soup.find_all('th'):
            if '첨부파일' in th.get_text():
                # 같은 tr 내의 td 찾기
                parent_tr = th.find_parent('tr')
                if parent_tr:
                    td = parent_tr.find('td')
                    if td:
                        file_areas.append(td)
        
        # 파일 링크 추출
        for area in file_areas:
            for link in area.find_all('a'):
                file_name = link.get_text(strip=True)
                href = link.get('href', '')
                onclick = link.get('onclick', '')
                
                if onclick:
                    # JavaScript 함수에서 파일 다운로드 파라미터 추출
                    # 예: fn_fileDown('파일ID')
                    match = re.search(r"fn_fileDown\('([^']+)'\)", onclick)
                    if match:
                        file_id = match.group(1)
                        file_url = "{}/main/fileDown.action?file_id={}".format(self.base_url, file_id)
                        if file_name:
                            attachments.append({'name': file_name, 'url': file_url})
                elif href and not href.startswith('#'):
                    if href.startswith('http'):
                        file_url = href
                    else:
                        file_url = urljoin(self.base_url, href)
                    
                    if file_name:
                        attachments.append({'name': file_name, 'url': file_url})
        
        return {'content': content, 'attachments': attachments}