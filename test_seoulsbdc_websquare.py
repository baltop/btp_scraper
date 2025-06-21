#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEOULSBDC WebSquare 사이트 접근 테스트
"""

import requests
from bs4 import BeautifulSoup
import time

def test_websquare_access():
    session = requests.Session()
    
    # 헤더 설정
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    session.headers.update(headers)
    
    try:
        # 1. 메인 페이지에서 WebSquare 정보 수집
        print("1. WebSquare 정보 수집...")
        response = session.get('https://www.seoulsbdc.or.kr/main.do', verify=False)
        
        # 스크립트에서 경로 정보 추출
        content = response.text
        print(f"Content length: {len(content)}")
        
        # XML 파일 경로 찾기
        if "movePage" in content:
            import re
            move_page_match = re.search(r'movePage = "([^"]+)"', content)
            if move_page_match:
                move_page = move_page_match.group(1)
                print(f"Found movePage: {move_page}")
        
        # 2. WebSquare XML 파일 접근 시도
        print("2. WebSquare XML 접근 시도...")
        xml_urls = [
            '/ui/main/main.xml',
            '/websquare/ui/main/main.xml',
            '/ui/bs/bsList.xml',
            '/websquare/ui/bs/bsList.xml'
        ]
        
        for xml_url in xml_urls:
            full_url = f'https://www.seoulsbdc.or.kr{xml_url}'
            response = session.get(full_url, verify=False)
            print(f"XML URL {xml_url}: {response.status_code}")
            if response.status_code == 200:
                print(f"✅ XML 접근 성공: {xml_url}")
                break
        
        # 3. 게시판 관련 경로 탐색
        print("3. 게시판 경로 탐색...")
        board_urls = [
            '/board/list.do?boardCd=B061',
            '/bbs/list.do?boardCd=B061',
            '/bs/list.do?boardCd=B061',
            '/ui/bs/list.xml?boardCd=B061',
            '/board/BS_LIST.do?boardCd=B061'
        ]
        
        for board_url in board_urls:
            full_url = f'https://www.seoulsbdc.or.kr{board_url}'
            response = session.get(full_url, verify=False)
            print(f"Board URL {board_url}: {response.status_code}")
            if response.status_code == 200 and "오류발생" not in response.text:
                print(f"✅ 게시판 접근 성공: {board_url}")
                print(f"Response length: {len(response.text)}")
                # HTML 파싱 시도
                soup = BeautifulSoup(response.text, 'html.parser')
                if soup.find('table') or soup.find('ul'):
                    print("✅ HTML 구조 발견")
                return True
        
        # 4. sitemap이나 robots.txt 확인
        print("4. sitemap/robots.txt 확인...")
        for path in ['/sitemap.xml', '/robots.txt']:
            response = session.get(f'https://www.seoulsbdc.or.kr{path}', verify=False)
            if response.status_code == 200:
                print(f"✅ {path} 발견")
                print(response.text[:500])
        
        return False
        
    except Exception as e:
        print(f"오류 발생: {e}")
        return False

if __name__ == "__main__":
    test_websquare_access()