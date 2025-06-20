#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIMST HTML 구조 디버깅 스크립트
"""

import requests
import urllib3
import ssl
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.ssl_ import create_urllib3_context
from bs4 import BeautifulSoup

# SSL 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SSLAdapter(HTTPAdapter):
    """SSL 호환성 문제 해결을 위한 커스텀 어댑터"""
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        context.set_ciphers("DEFAULT:@SECLEVEL=1")
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = context
        return super().init_poolmanager(*args, **kwargs)

def debug_kimst_html():
    """KIMST HTML 구조 디버깅"""
    url = "https://www.kimst.re.kr/u/news/inform_01/pjtAnuc.do"
    
    # 세션 설정
    session = requests.Session()
    session.mount("https://", SSLAdapter())
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.8,en;q=0.6',
    })
    
    try:
        print("KIMST 페이지 가져오는 중...")
        response = session.get(url, verify=False, timeout=30)
        response.raise_for_status()
        
        print(f"응답 코드: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        
        # HTML 저장
        with open('kimst_debug.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("HTML 저장 완료: kimst_debug.html")
        
        # BeautifulSoup으로 파싱
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 테이블 찾기
        tables = soup.find_all('table')
        print(f"\n발견된 테이블 수: {len(tables)}")
        
        for i, table in enumerate(tables):
            print(f"\n=== 테이블 {i+1} ===")
            
            # rowgroup 확인
            rowgroups = table.find_all('rowgroup')
            print(f"rowgroup 수: {len(rowgroups)}")
            
            # tbody 확인
            tbodies = table.find_all('tbody')
            print(f"tbody 수: {len(tbodies)}")
            
            # tr 확인
            trs = table.find_all('tr')
            print(f"tr 수: {len(trs)}")
            
            if rowgroups:
                for j, rg in enumerate(rowgroups):
                    rows = rg.find_all('row')
                    cells = rg.find_all('cell')
                    print(f"  rowgroup {j+1}: row={len(rows)}, cell={len(cells)}")
                    
                    # 첫 번째 행의 내용 출력
                    if rows:
                        first_row = rows[0]
                        first_cells = first_row.find_all('cell')
                        if first_cells:
                            cell_texts = [cell.get_text(strip=True)[:30] for cell in first_cells[:3]]
                            print(f"    첫 번째 행: {cell_texts}")
            
            if tbodies:
                for j, tb in enumerate(tbodies):
                    trs_in_tbody = tb.find_all('tr')
                    print(f"  tbody {j+1}: tr={len(trs_in_tbody)}")
                    
                    if trs_in_tbody:
                        first_tr = trs_in_tbody[0]
                        tds = first_tr.find_all('td')
                        if tds:
                            td_texts = [td.get_text(strip=True)[:30] for td in tds[:3]]
                            print(f"    첫 번째 행: {td_texts}")
        
        # 링크 확인
        links = soup.find_all('a', href=lambda x: x and 'iris.go.kr' in x)
        print(f"\nIRIS 링크 수: {len(links)}")
        
        if links:
            print("첫 번째 IRIS 링크:")
            first_link = links[0]
            print(f"  텍스트: {first_link.get_text(strip=True)[:50]}")
            print(f"  href: {first_link.get('href', '')[:80]}")
        
        # link 요소 확인 (KIMST 특화)
        link_elements = soup.find_all('link')
        print(f"\nlink 요소 수: {len(link_elements)}")
        
        # 전체 구조 샘플 출력
        print(f"\n=== HTML 샘플 (첫 1000자) ===")
        print(response.text[:1000])
        
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_kimst_html()