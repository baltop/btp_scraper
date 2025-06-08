# -*- coding: utf-8 -*-
from base_scraper import BaseScraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin, parse_qs, urlparse
import re
import os
import time
import requests

class MIREScraper(BaseScraper):
    """환동해산업연구원(MIRE) 전용 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "http://mire.re.kr"
        self.list_url = "http://mire.re.kr/sub4_4.php"
        self.session_id = None
        self._get_session_id()
    
    def _get_session_id(self):
        """동적으로 세션 ID를 가져오는 메소드"""
        try:
            # 초기 페이지 접속하여 세션 ID 획득
            response = self.session.get(self.list_url, headers=self.headers, verify=self.verify_ssl)
            
            # 쿠키에서 PHPSESSID 추출
            if 'PHPSESSID' in response.cookies:
                self.session_id = response.cookies['PHPSESSID']
                print(f"새로운 세션 ID 획득: {self.session_id}")
            else:
                # URL에서 PHPSESSID 추출 시도
                final_url = response.url
                parsed_url = urlparse(final_url)
                params = parse_qs(parsed_url.query)
                if 'PHPSESSID' in params:
                    self.session_id = params['PHPSESSID'][0]
                    print(f"URL에서 세션 ID 획득: {self.session_id}")
                else:
                    # 기본값 사용
                    self.session_id = "default_session_id"
                    print("세션 ID를 찾을 수 없어 기본값 사용")
        except Exception as e:
            print(f"세션 ID 획득 실패: {e}")
            self.session_id = "default_session_id"
        
    def get_list_url(self, page_num):
        """페이지 번호에 따른 목록 URL 반환"""
        if page_num == 1:
            return f"{self.list_url}?PHPSESSID={self.session_id}"
        else:
            return f"{self.list_url}?PHPSESSID={self.session_id}&page={page_num}"
            
    def parse_list_page(self, html_content):
        """목록 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 공고 테이블 찾기
        tables = soup.find_all('table', class_='tb2')
        for table in tables:
            rows = table.find_all('tr')
            
            for row in rows:
                try:
                    tds = row.find_all('td')
                    if len(tds) < 4:
                        continue
                    
                    # 번호
                    num_text = tds[0].get_text(strip=True)
                    if not num_text or num_text == '번호':
                        continue
                    
                    # 제목 및 링크
                    title_td = tds[1]
                    link_elem = title_td.find('a')
                    if not link_elem:
                        continue
                        
                    title = link_elem.get_text(strip=True)
                    
                    # 상세 페이지 URL 추출
                    href = link_elem.get('href', '')
                    if href:
                        # PHP 세션 ID 포함
                        if 'PHPSESSID' not in href:
                            if '?' in href:
                                href += f"&PHPSESSID={self.session_id}"
                            else:
                                href += f"?PHPSESSID={self.session_id}"
                        detail_url = urljoin(self.base_url, href)
                    else:
                        continue
                    
                    # 날짜
                    date = tds[2].get_text(strip=True) if len(tds) > 2 else ''
                    
                    # 조회수
                    views = tds[3].get_text(strip=True) if len(tds) > 3 else ''
                    
                    announcements.append({
                        'num': num_text,
                        'title': title,
                        'url': detail_url,
                        'date': date,
                        'views': views
                    })
                    
                except Exception as e:
                    continue
                    
        return announcements
        
    def parse_detail_page(self, html_content):
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 내용 찾기
        content_area = None
        
        # 테이블 구조에서 본문 찾기
        content_table = soup.find('table', class_='tb2')
        if content_table:
            # 본문이 있는 TD 찾기
            tds = content_table.find_all('td')
            for td in tds:
                # 본문은 보통 긴 텍스트가 있는 TD
                if len(td.get_text(strip=True)) > 100:
                    content_area = td
                    break
        
        # 첨부파일 찾기
        attachments = []
        
        # 첨부파일 링크 찾기
        file_links = soup.find_all('a', href=re.compile(r'download|file|attach'))
        for link in file_links:
            file_name = link.get_text(strip=True)
            file_url = link.get('href', '')
            
            if file_url:
                # 세션 ID 추가
                if 'PHPSESSID' not in file_url:
                    if '?' in file_url:
                        file_url += f"&PHPSESSID={self.session_id}"
                    else:
                        file_url += f"?PHPSESSID={self.session_id}"
                        
                file_url = urljoin(self.base_url, file_url)
                
                if file_name and not file_name.isspace():
                    attachments.append({
                        'name': file_name,
                        'url': file_url
                    })
        
        # 본문을 마크다운으로 변환
        content_md = ""
        if content_area:
            content_md = self.h.handle(str(content_area))
        
        return {
            'content': content_md,
            'attachments': attachments
        }