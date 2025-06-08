# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
from base_scraper import BaseScraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin, parse_qs, urlparse, unquote
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
    
    def get_page(self, url):
        """페이지 가져오기 - MIRE는 EUC-KR 인코딩 사용"""
        try:
            response = self.session.get(url, verify=self.verify_ssl)
            response.encoding = 'euc-kr'  # MIRE는 EUC-KR 인코딩 사용
            return response
        except Exception as e:
            print(f"Error fetching page: {e}")
            return None
    
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
        
        # 모든 상세페이지 링크 찾기 (type=read 패턴)
        detail_links = soup.find_all('a', href=re.compile(r'type=read.*id=\d+'))
        
        for link in detail_links:
            try:
                # 제목
                title = link.get_text(strip=True)
                if not title or len(title) < 5:  # 너무 짧은 텍스트는 제외
                    continue
                    
                # 공지사항 제외 (선택적)
                if title == '공지':
                    continue
                
                # URL
                href = link.get('href', '')
                if not href:
                    continue
                    
                # PHP 세션 ID 포함
                if 'PHPSESSID' not in href:
                    if '?' in href:
                        href += f"&PHPSESSID={self.session_id}"
                    else:
                        href += f"?PHPSESSID={self.session_id}"
                detail_url = urljoin(self.base_url, href)
                
                # 부모 행에서 추가 정보 추출
                parent_tr = link.find_parent('tr')
                num = ''
                date = ''
                views = ''
                
                if parent_tr:
                    tds = parent_tr.find_all('td')
                    # TD 구조: 번호, 공백, 제목(링크), 공백, 작성자, 공백, 날짜, 공백, 조회수
                    for i, td in enumerate(tds):
                        text = td.get_text(strip=True)
                        # 번호 (숫자만)
                        if text.isdigit() and not num:
                            num = text
                        # 날짜 (YY.MM.DD 패턴)
                        elif len(text) == 8 and text[2] == '.' and text[5] == '.':
                            date = text
                        # 조회수 (마지막 숫자)
                        elif text.isdigit() and i > len(tds) - 3:
                            views = text
                
                # 중복 제거를 위해 URL 기반으로 체크
                if not any(a['url'] == detail_url for a in announcements):
                    announcements.append({
                        'num': num,
                        'title': title,
                        'url': detail_url,
                        'date': date,
                        'views': views
                    })
                    
            except Exception as e:
                continue
        
        # 정렬 (번호 역순으로)
        announcements.sort(key=lambda x: int(x['num']) if x['num'].isdigit() else 0, reverse=True)
                    
        return announcements
        
    def parse_detail_page(self, html_content):
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 내용 찾기
        content_area = None
        
        # 테이블 구조에서 본문 찾기
        content_table = soup.find('table', class_='tb2')
        if content_table:
            # 본문이 있는 TD 찾기 - 크게 한 개의 TD에 전체 내용이 들어있는 경우
            rows = content_table.find_all('tr')
            for row in rows:
                tds = row.find_all('td')
                if len(tds) == 1:  # TD가 하나만 있는 행
                    td = tds[0]
                    # 자식 요소가 많거나 텍스트가 긴 경우
                    if len(td.find_all()) > 5 or len(td.get_text(strip=True)) > 200:
                        content_area = td
                        break
        
        # 첨부파일 찾기 - type=download 패턴을 사용
        attachments = []
        
        # type=download 패턴으로 파일 링크 찾기
        file_links = soup.find_all('a', href=re.compile(r'type=download'))
        for link in file_links:
            file_name = link.get_text(strip=True)
            file_url = link.get('href', '')
            
            if file_url and file_name:
                # 세션 ID 추가
                if 'PHPSESSID' not in file_url:
                    if '?' in file_url:
                        file_url += f"&PHPSESSID={self.session_id}"
                    else:
                        file_url += f"?PHPSESSID={self.session_id}"
                        
                file_url = urljoin(self.base_url, file_url)
                
                attachments.append({
                    'name': file_name,
                    'url': file_url
                })
        
        # 본문을 마크다운으로 변환
        content_md = ""
        if content_area:
            content_md = self.h.handle(str(content_area))
        else:
            # content_area가 없으면 전체 테이블을 마크다운으로 변환
            if content_table:
                content_md = self.h.handle(str(content_table))
        
        return {
            'content': content_md,
            'attachments': attachments
        }