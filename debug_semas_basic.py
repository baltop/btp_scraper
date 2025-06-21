#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEMAS 기본 접근 디버깅
"""

import requests
from bs4 import BeautifulSoup
import logging

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_semas_basic():
    """SEMAS 기본 접근 테스트"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    
    url = "https://semas.or.kr/web/board/webBoardList.kmdc?bCd=1&pNm=BOA0101"
    
    try:
        print(f"1. URL 접근 시도: {url}")
        response = session.get(url, verify=True, timeout=30)
        print(f"상태 코드: {response.status_code}")
        print(f"응답 길이: {len(response.text)}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        
        if response.status_code == 200:
            print("✅ 접근 성공!")
            
            # HTML 파싱
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 페이지 제목 확인
            title = soup.find('title')
            if title:
                print(f"페이지 제목: {title.get_text()}")
            
            # 테이블 찾기
            tables = soup.find_all('table')
            print(f"테이블 개수: {len(tables)}")
            
            if tables:
                for i, table in enumerate(tables):
                    rows = table.find_all('tr')
                    print(f"테이블 {i+1}: {len(rows)}개 행")
                    
                    if len(rows) > 1:
                        # 첫 번째 행 (헤더) 확인
                        header_row = rows[0]
                        headers = header_row.find_all(['th', 'td'])
                        print(f"  헤더: {[h.get_text(strip=True) for h in headers]}")
                        
                        # 두 번째 행 (첫 데이터) 확인
                        if len(rows) > 1:
                            data_row = rows[1]
                            data_cells = data_row.find_all('td')
                            print(f"  첫 데이터 행: {len(data_cells)}개 셀")
                            for j, cell in enumerate(data_cells[:5]):  # 처음 5개 셀만
                                text = cell.get_text(strip=True)
                                link = cell.find('a')
                                if link:
                                    href = link.get('href', '')
                                    print(f"    셀 {j+1}: '{text}' [링크: {href}]")
                                else:
                                    print(f"    셀 {j+1}: '{text}'")
                        return True
            else:
                print("❌ 테이블을 찾을 수 없습니다")
                
                # 전체 body 내용 일부 출력
                body = soup.find('body')
                if body:
                    body_text = body.get_text()[:500]
                    print(f"Body 내용 (처음 500자): {body_text}")
        else:
            print(f"❌ 접근 실패: HTTP {response.status_code}")
            print(f"응답 내용: {response.text[:500]}")
            
        return False
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False

if __name__ == "__main__":
    success = debug_semas_basic()
    if success:
        print("\n🎉 기본 접근 성공!")
    else:
        print("\n💥 기본 접근 실패!")