#!/usr/bin/env python3
"""
음성상공회의소 HTML 구조 디버깅
"""
import requests
from bs4 import BeautifulSoup
import re

def debug_html_structure():
    """HTML 구조 디버깅"""
    
    list_url = "https://eumseongcci.korcham.net/front/board/boardContentsListPage.do?boardId=10585&menuId=871"
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    try:
        response = session.get(list_url, verify=False)
        response.encoding = 'utf-8'
        
        print(f"응답 코드: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        print(f"응답 길이: {len(response.text)} 문자")
        
        # HTML 일부 출력
        html_sample = response.text[:2000]
        print(f"\nHTML 시작 부분:")
        print(html_sample)
        print("\n" + "="*50)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 모든 테이블 찾기
        tables = soup.find_all('table')
        print(f"\n전체 테이블 수: {len(tables)}")
        
        for i, table in enumerate(tables):
            print(f"\n--- 테이블 {i+1} ---")
            print(f"클래스: {table.get('class', 'None')}")
            print(f"요약: {table.get('summary', 'None')}")
            
            # tbody 확인
            tbody = table.find('tbody')
            if tbody:
                rows = tbody.find_all('tr')
                print(f"tbody 행 수: {len(rows)}")
                
                # 첫 번째 행 분석
                if rows:
                    first_row = rows[0]
                    cells = first_row.find_all(['td', 'th'])
                    print(f"첫 번째 행 셀 수: {len(cells)}")
                    
                    for j, cell in enumerate(cells):
                        cell_text = cell.get_text(strip=True)[:50]
                        cell_class = cell.get('class', [])
                        print(f"  셀 {j+1} (class: {cell_class}): {cell_text}")
                        
                        # 링크 확인
                        links = cell.find_all('a')
                        for link in links:
                            href = link.get('href', '')
                            onclick = link.get('onclick', '')
                            link_text = link.get_text(strip=True)
                            print(f"    링크: {link_text}")
                            print(f"    href: {href}")
                            if onclick:
                                print(f"    onclick: {onclick}")
            else:
                print("tbody 없음")
                # 직접 tr 찾기
                rows = table.find_all('tr')
                print(f"직접 tr 행 수: {len(rows)}")
        
        # JavaScript contentsView 함수 찾기
        script_tags = soup.find_all('script')
        for script in script_tags:
            script_content = script.get_text()
            if 'contentsView' in script_content:
                print(f"\n--- contentsView 함수 발견 ---")
                # contentsView 함수 추출
                match = re.search(r'function contentsView\([^}]+\}', script_content, re.DOTALL)
                if match:
                    print(f"contentsView 함수:\n{match.group(0)}")
                break
        
        # boardContentsViewUrl 변수 찾기
        for script in script_tags:
            script_content = script.get_text()
            if 'boardContentsViewUrl' in script_content:
                match = re.search(r'boardContentsViewUrl\s*=\s*["\']([^"\']+)["\']', script_content)
                if match:
                    print(f"\nboardContentsViewUrl: {match.group(1)}")
                break
        
        # 특정 contentsView 링크들 찾기
        print(f"\n--- contentsView 링크 찾기 ---")
        all_links = soup.find_all('a', href=True)
        contentsview_links = [link for link in all_links if 'contentsView' in link.get('href', '')]
        
        print(f"contentsView 링크 수: {len(contentsview_links)}")
        for i, link in enumerate(contentsview_links[:5]):  # 처음 5개만
            href = link.get('href', '')
            text = link.get_text(strip=True)
            print(f"  {i+1}: {text}")
            print(f"      href: {href}")
            
            # contId 추출
            match = re.search(r"contentsView\('(\d+)'\)", href)
            if match:
                cont_id = match.group(1)
                print(f"      contId: {cont_id}")
        
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_html_structure()