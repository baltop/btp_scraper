#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""충남경제진흥원(CEPA) 지원사업 공고 스크래퍼"""

from base_scraper import BaseScraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin, parse_qs
import re
import time

class CEPAScraper(BaseScraper):
    """충남경제진흥원(CEPA) 웹 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.cepa.or.kr"
        self.list_url = "https://www.cepa.or.kr/notice/notice.do?pm=6&ms=32"
        self.verify_ssl = False  # SSL 검증 비활성화
        
    def get_list_url(self, page_num):
        """페이지별 목록 URL 생성"""
        return "{}&page={}".format(self.list_url, page_num)
        
    def parse_list_page(self, html_content):
        """목록 페이지 파싱하여 공고 정보 추출"""
        soup = BeautifulSoup(html_content, 'html.parser')
        items = []
        
        # 게시판 테이블 찾기 - tbody를 직접 찾기
        tbody = soup.find('tbody')
        if not tbody:
            print("tbody를 찾을 수 없습니다.")
            return items
        
        for row in tbody.find_all('tr'):
            # 제목 컬럼 찾기 - class="tbl-subject"인 td를 찾기
            title_cell = row.find('td', class_='tbl-subject')
            if not title_cell:
                # 대체 방법: 링크가 있는 td 찾기
                for td in row.find_all('td'):
                    if td.find('a'):
                        title_cell = td
                        break
            
            if title_cell:
                # 링크 찾기
                link_tag = title_cell.find('a')
                if link_tag:
                    title = link_tag.get_text(strip=True)
                    
                    # href 속성 확인
                    href = link_tag.get('href', '')
                    onclick = link_tag.get('onclick', '')
                    
                    if onclick:
                        # JavaScript 함수에서 파라미터 추출
                        match = re.search(r"fn_view\('([^']+)'\)", onclick)
                        if match:
                            notice_id = match.group(1)
                            detail_url = "{}/notice/noticeView.do?noticeSeq={}".format(self.base_url, notice_id)
                            items.append({'title': title, 'url': detail_url})
                    elif href and not href.startswith('#'):
                        if href.startswith('http'):
                            detail_url = href
                        else:
                            detail_url = urljoin(self.base_url, href)
                        items.append({'title': title, 'url': detail_url})
        
        return items
        
    def parse_detail_page(self, html_content):
        """상세 페이지 파싱하여 내용과 첨부파일 추출"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 내용 찾기
        content_area = soup.find('td', class_='board-content')
        if not content_area:
            content_area = soup.find('div', class_='view_content')
        if not content_area:
            content_area = soup.find('div', class_='board_view')
        
        content = ""
        if content_area:
            # HTML을 마크다운으로 변환
            content = self.h.handle(str(content_area))
        else:
            print("본문 영역을 찾을 수 없습니다.")
            
        # 첨부파일 찾기
        attachments = []
        
        # 첨부파일 영역 찾기 - 다양한 패턴 시도
        file_areas = []
        
        # 패턴 1: 파일 영역 클래스
        for class_name in ['file', 'attach', 'attachment', 'file_list']:
            file_area = soup.find('div', class_=class_name)
            if file_area:
                file_areas.append(file_area)
        
        # 패턴 2: 첨부파일 제목이 있는 영역
        for td in soup.find_all('td'):
            text = td.get_text()
            if '첨부' in text and td.find('i', class_='fa-file-text-o'):
                file_areas.append(td)
        
        # 파일 링크 추출
        for area in file_areas:
            for link in area.find_all('a'):
                file_name = link.get_text(strip=True)
                href = link.get('href', '')
                onclick = link.get('onclick', '')
                
                if onclick:
                    # JavaScript 함수에서 파일 다운로드 파라미터 추출
                    match = re.search(r"fn_download\('([^']+)'\)", onclick)
                    if match:
                        file_id = match.group(1)
                        file_url = "{}/notice/download.do?fileSeq={}".format(self.base_url, file_id)
                        if file_name:
                            attachments.append({'name': file_name, 'url': file_url})
                elif href and not href.startswith('#'):
                    if href.startswith('http'):
                        file_url = href
                    else:
                        file_url = urljoin(self.base_url, href)
                    
                    if file_name and '/download' in file_url:
                        attachments.append({'name': file_name, 'url': file_url})
        
        return {'content': content, 'attachments': attachments}