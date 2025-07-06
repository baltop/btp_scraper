#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GSIC 스크래퍼 디버그 스크립트
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

disable_warnings(InsecureRequestWarning)

def debug_gsic():
    """GSIC 상세 페이지 접근 디버그"""
    
    # 세션 생성
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    })
    
    # 1. 먼저 목록 페이지 접근
    list_url = "https://gsic.or.kr/home/kor/M837392473/board.do?deleteAt=N&idx=&eSearchValue3=&searchValue1=0&searchKeyword=&pageIndex=1"
    
    print("=== 1. 목록 페이지 접근 ===")
    try:
        response = session.get(list_url, verify=False, timeout=30)
        print(f"목록 페이지 Status: {response.status_code}")
        
        # 목록 파싱
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', class_='table_basics_area')
        
        if table:
            rows = table.find_all('tr')[1:]  # 헤더 제외
            print(f"발견된 행 수: {len(rows)}")
            
            # 첫 번째 공고 확인
            if rows:
                first_row = rows[0]
                cells = first_row.find_all('td')
                if len(cells) >= 3:
                    title_cell = cells[2]
                    title_link = title_cell.find('a')
                    if title_link:
                        title = title_link.get_text(strip=True)
                        onclick = title_link.get('onclick', '')
                        print(f"첫 번째 공고 제목: {title}")
                        print(f"onclick: {onclick}")
                        
                        # ID 추출
                        id_match = re.search(r"fn_edit\('detail',\s*'([^']+)'", onclick)
                        if id_match:
                            detail_id = id_match.group(1)
                            print(f"추출된 ID: {detail_id}")
                            
                            # 2. 상세 페이지 접근 시도
                            print("\n=== 2. 상세 페이지 접근 ===")
                            detail_url = f"https://gsic.or.kr/home/kor/M837392473/board.do?deleteAt=N&idx={detail_id}&eSearchValue3=&searchValue1=0&searchKeyword=&pageIndex=1&mode=detail"
                            print(f"상세 URL: {detail_url}")
                            
                            detail_response = session.get(detail_url, verify=False, timeout=30)
                            print(f"상세 페이지 Status: {detail_response.status_code}")
                            print(f"Content length: {len(detail_response.text)}")
                            
                            # 상세 페이지 파싱
                            detail_soup = BeautifulSoup(detail_response.text, 'html.parser')
                            
                            # 다양한 방법으로 내용 찾기
                            content_candidates = [
                                detail_soup.find('div', class_='contents'),
                                detail_soup.find('div', class_='content'),
                                detail_soup.find('div', class_='detail_content'),
                                detail_soup.find('div', id='contents'),
                                detail_soup.find('div', id='content')
                            ]
                            
                            for i, candidate in enumerate(content_candidates):
                                if candidate:
                                    print(f"Content candidate {i}: {candidate.name} class={candidate.get('class')} id={candidate.get('id')}")
                                    text = candidate.get_text(strip=True)[:200]
                                    print(f"  Text preview: {text}")
                            
                            # 테이블 찾기
                            content_tables = detail_soup.find_all('table', class_='table_area')
                            print(f"Content tables found: {len(content_tables)}")
                            
                            if content_tables:
                                for i, table in enumerate(content_tables[:2]):  # 처음 2개만
                                    print(f"\nTable {i}:")
                                    rows = table.find_all('tr')
                                    for j, row in enumerate(rows[:3]):  # 처음 3행만
                                        cells = row.find_all(['th', 'td'])
                                        if len(cells) >= 2:
                                            header = cells[0].get_text(strip=True)
                                            content = cells[1].get_text(strip=True)[:100]
                                            print(f"  Row {j}: {header} = {content}")
                            
                            # 첨부파일 찾기
                            print(f"\n=== 3. 첨부파일 찾기 ===")
                            attachment_links = detail_soup.find_all('a', href=True)
                            download_links = [link for link in attachment_links if 'download' in link.get('href', '').lower()]
                            print(f"Download links found: {len(download_links)}")
                            
                            for link in download_links[:5]:  # 처음 5개만
                                print(f"  {link.get('href')} - {link.get_text(strip=True)}")
                        
        else:
            print("테이블을 찾을 수 없습니다")
            
    except Exception as e:
        print(f"오류: {e}")

if __name__ == "__main__":
    debug_gsic()