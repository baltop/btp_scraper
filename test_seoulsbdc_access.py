#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEOULSBDC 사이트 접근 테스트
"""

import requests
from bs4 import BeautifulSoup
import time

def test_seoulsbdc_access():
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
        # 1. 메인 페이지 접근하여 세션 초기화
        print("1. 메인 페이지 접근...")
        response = session.get('https://www.seoulsbdc.or.kr/main.do', verify=False)
        print(f"메인 페이지 상태 코드: {response.status_code}")
        
        # 쿠키 확인
        print(f"쿠키: {session.cookies}")
        
        # 잠시 대기
        time.sleep(2)
        
        # 2. 게시판 접근 시도
        print("2. 게시판 접근 시도...")
        board_url = 'https://www.seoulsbdc.or.kr/bs/BS_LIST.do?boardCd=B061'
        response = session.get(board_url, verify=False)
        print(f"게시판 상태 코드: {response.status_code}")
        print(f"응답 길이: {len(response.text)}")
        
        # HTML 내용 확인
        if "오류발생" in response.text:
            print("❌ 오류 발생 - 접근 차단됨")
        else:
            print("✅ 접근 성공")
            
        # 응답 내용 일부 출력
        print("\n--- 응답 내용 (처음 500자) ---")
        print(response.text[:500])
        
        # 3. 다른 접근 방법 시도 - POST 요청
        print("\n3. POST 요청으로 시도...")
        post_data = {
            'boardCd': 'B061'
        }
        response = session.post('https://www.seoulsbdc.or.kr/bs/BS_LIST.do', 
                               data=post_data, verify=False)
        print(f"POST 상태 코드: {response.status_code}")
        
        if "오류발생" not in response.text and len(response.text) > 1000:
            print("✅ POST 요청 성공")
            return True
        else:
            print("❌ POST 요청도 실패")
            
        # 4. 다른 보드 코드로 시도
        print("\n4. 다른 게시판 코드로 시도...")
        for board_code in ['B001', 'B002', 'B003', 'B061']:
            test_url = f'https://www.seoulsbdc.or.kr/bs/BS_LIST.do?boardCd={board_code}'
            response = session.get(test_url, verify=False)
            if "오류발생" not in response.text:
                print(f"✅ 게시판 {board_code} 접근 성공")
                print(f"URL: {test_url}")
                break
        else:
            print("❌ 모든 게시판 접근 실패")
            
        return False
        
    except Exception as e:
        print(f"오류 발생: {e}")
        return False

if __name__ == "__main__":
    test_seoulsbdc_access()