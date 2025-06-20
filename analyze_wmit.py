#!/usr/bin/env python3
"""
WMIT 사이트 분석 스크립트
http://wmit.or.kr/announce/businessAnnounceList.do
"""

import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin, urlparse
from playwright.sync_api import sync_playwright


def analyze_with_requests():
    """requests를 사용한 분석"""
    print("=" * 50)
    print("1. requests를 사용한 분석")
    print("=" * 50)
    
    url = "http://wmit.or.kr/announce/businessAnnounceList.do"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        print(f"접근 URL: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        print(f"응답 코드: {response.status_code}")
        print(f"응답 인코딩: {response.encoding}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        
        # 인코딩 확인 및 설정
        if 'euc-kr' in response.headers.get('Content-Type', '').lower():
            response.encoding = 'euc-kr'
        elif response.encoding == 'ISO-8859-1':
            response.encoding = 'utf-8'
        
        html_content = response.text
        print(f"HTML 길이: {len(html_content)} 문자")
        
        # BeautifulSoup으로 파싱
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 페이지 제목
        title = soup.find('title')
        print(f"페이지 제목: {title.get_text().strip() if title else 'N/A'}")
        
        # 테이블 구조 분석
        print("\n--- 테이블 구조 분석 ---")
        tables = soup.find_all('table')
        print(f"테이블 개수: {len(tables)}")
        
        for i, table in enumerate(tables):
            print(f"\n테이블 {i+1}:")
            # 테이블 클래스나 ID 확인
            table_class = table.get('class', [])
            table_id = table.get('id', '')
            print(f"  클래스: {table_class}")
            print(f"  ID: {table_id}")
            
            # 헤더 확인
            thead = table.find('thead')
            if thead:
                headers = [th.get_text().strip() for th in thead.find_all(['th', 'td'])]
                print(f"  헤더: {headers}")
            
            # 본문 행 수 확인
            tbody = table.find('tbody') or table
            rows = tbody.find_all('tr')
            print(f"  행 수: {len(rows)}")
            
            # 첫 번째 행 분석 (데이터 행)
            if rows:
                first_row = rows[0]
                cells = first_row.find_all(['td', 'th'])
                print(f"  첫 번째 행 셀 수: {len(cells)}")
                
                # 각 셀의 내용 미리보기
                for j, cell in enumerate(cells[:5]):  # 최대 5개 셀만
                    cell_text = cell.get_text().strip()
                    print(f"    셀 {j+1}: {cell_text[:30]}...")
                    
                    # 링크 확인
                    links = cell.find_all('a')
                    if links:
                        for link in links:
                            href = link.get('href', '')
                            onclick = link.get('onclick', '')
                            print(f"      링크 href: {href}")
                            if onclick:
                                print(f"      링크 onclick: {onclick}")
        
        # 페이지네이션 분석
        print("\n--- 페이지네이션 분석 ---")
        # 일반적인 페이지네이션 패턴 찾기
        pagination_patterns = [
            'pagination', 'paging', 'page', 'nav', 'pageNav',
            'page_nav', 'board_page', 'list_page'
        ]
        
        pagination_found = False
        for pattern in pagination_patterns:
            # 클래스로 찾기
            paging_divs = soup.find_all(['div', 'ul', 'nav'], class_=re.compile(pattern, re.I))
            if paging_divs:
                print(f"페이지네이션 발견 (클래스 {pattern}): {len(paging_divs)}개")
                for div in paging_divs:
                    links = div.find_all('a')
                    print(f"  페이지 링크 수: {len(links)}")
                    for link in links[:5]:  # 최대 5개만
                        href = link.get('href', '')
                        onclick = link.get('onclick', '')
                        text = link.get_text().strip()
                        print(f"    {text}: href={href}, onclick={onclick}")
                pagination_found = True
                break
        
        if not pagination_found:
            # JavaScript 함수로 페이지네이션 찾기
            script_tags = soup.find_all('script')
            for script in script_tags:
                if script.string:
                    if 'page' in script.string.lower() or 'go' in script.string.lower():
                        print("JavaScript에서 페이지네이션 관련 함수 발견:")
                        lines = script.string.split('\n')
                        for line in lines:
                            if 'function' in line and ('page' in line.lower() or 'go' in line.lower()):
                                print(f"  {line.strip()}")
        
        # 첨부파일 패턴 분석
        print("\n--- 첨부파일 패턴 분석 ---")
        # 첨부파일 아이콘이나 링크 찾기
        file_patterns = ['attach', 'file', 'download', '첨부', '파일']
        for pattern in file_patterns:
            elements = soup.find_all(['img', 'a', 'span'], attrs={'src': re.compile(pattern, re.I)})
            elements.extend(soup.find_all(['img', 'a', 'span'], string=re.compile(pattern, re.I)))
            elements.extend(soup.find_all(['img', 'a', 'span'], class_=re.compile(pattern, re.I)))
            
            if elements:
                print(f"{pattern} 관련 요소 {len(elements)}개 발견")
                for elem in elements[:3]:  # 최대 3개만
                    print(f"  {elem.name}: {elem.get('src', elem.get('href', elem.get_text().strip()[:30]))}")
        
        # HTML 일부 저장 (디버깅용)
        with open('/home/baltop/work/bizsupnew/btp_scraper/wmit_requests.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"\nHTML 저장됨: wmit_requests.html")
        
        return True
        
    except Exception as e:
        print(f"requests 분석 실패: {e}")
        return False


def analyze_with_playwright():
    """Playwright를 사용한 분석"""
    print("\n" + "=" * 50)
    print("2. Playwright를 사용한 분석")
    print("=" * 50)
    
    url = "http://wmit.or.kr/announce/businessAnnounceList.do"
    
    try:
        with sync_playwright() as p:
            # 브라우저 실행
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            page = context.new_page()
            
            print(f"접근 URL: {url}")
            
            # 페이지 로드
            response = page.goto(url, wait_until='networkidle', timeout=30000)
            print(f"응답 코드: {response.status}")
            print(f"최종 URL: {page.url}")
            
            # 페이지 제목
            title = page.title()
            print(f"페이지 제목: {title}")
            
            # 페이지가 완전히 로드될 때까지 대기
            page.wait_for_load_state('networkidle')
            
            # 테이블 요소 확인
            print("\n--- 테이블 구조 분석 (Playwright) ---")
            tables = page.query_selector_all('table')
            print(f"테이블 개수: {len(tables)}")
            
            for i, table in enumerate(tables):
                print(f"\n테이블 {i+1}:")
                
                # 테이블 속성
                table_class = table.get_attribute('class') or ''
                table_id = table.get_attribute('id') or ''
                print(f"  클래스: {table_class}")
                print(f"  ID: {table_id}")
                
                # 행 수 확인
                rows = table.query_selector_all('tr')
                print(f"  행 수: {len(rows)}")
                
                # 헤더 확인
                header_cells = table.query_selector_all('thead th, thead td')
                if header_cells:
                    headers = [cell.inner_text().strip() for cell in header_cells]
                    print(f"  헤더: {headers}")
                
                # 첫 번째 데이터 행 분석
                data_rows = table.query_selector_all('tbody tr, tr')
                if data_rows:
                    first_row = data_rows[0] if len(data_rows) > 0 else None
                    if first_row:
                        cells = first_row.query_selector_all('td, th')
                        print(f"  첫 번째 행 셀 수: {len(cells)}")
                        
                        for j, cell in enumerate(cells[:5]):  # 최대 5개 셀만
                            cell_text = cell.inner_text().strip()
                            print(f"    셀 {j+1}: {cell_text[:30]}...")
                            
                            # 링크 확인
                            links = cell.query_selector_all('a')
                            for link in links:
                                href = link.get_attribute('href') or ''
                                onclick = link.get_attribute('onclick') or ''
                                link_text = link.inner_text().strip()
                                print(f"      링크: '{link_text}' href={href}")
                                if onclick:
                                    print(f"        onclick: {onclick}")
            
            # 페이지네이션 확인
            print("\n--- 페이지네이션 분석 (Playwright) ---")
            pagination_selectors = [
                '.pagination', '.paging', '.page', '.pageNav', '.page_nav',
                '.board_page', '.list_page', '[class*="page"]', '[class*="paging"]'
            ]
            
            pagination_found = False
            for selector in pagination_selectors:
                elements = page.query_selector_all(selector)
                if elements:
                    print(f"페이지네이션 발견 ({selector}): {len(elements)}개")
                    for elem in elements:
                        links = elem.query_selector_all('a')
                        print(f"  페이지 링크 수: {len(links)}")
                        for link in links[:5]:  # 최대 5개만
                            href = link.get_attribute('href') or ''
                            onclick = link.get_attribute('onclick') or ''
                            text = link.inner_text().strip()
                            print(f"    '{text}': href={href}")
                            if onclick:
                                print(f"      onclick={onclick}")
                    pagination_found = True
                    break
            
            # JavaScript 함수 확인
            if not pagination_found:
                print("페이지네이션 관련 JavaScript 함수 확인...")
                js_result = page.evaluate("""
                    () => {
                        const scripts = document.querySelectorAll('script');
                        const functions = [];
                        scripts.forEach(script => {
                            if (script.textContent) {
                                const lines = script.textContent.split('\\n');
                                lines.forEach(line => {
                                    if (line.includes('function') && 
                                        (line.toLowerCase().includes('page') || 
                                         line.toLowerCase().includes('go'))) {
                                        functions.push(line.trim());
                                    }
                                });
                            }
                        });
                        return functions;
                    }
                """)
                
                if js_result:
                    print("JavaScript 페이지네이션 함수:")
                    for func in js_result[:5]:  # 최대 5개만
                        print(f"  {func}")
            
            # 첨부파일 관련 요소 확인
            print("\n--- 첨부파일 패턴 분석 (Playwright) ---")
            file_selectors = [
                'img[src*="attach"]', 'img[src*="file"]', 'a[href*="download"]',
                '[class*="attach"]', '[class*="file"]', 'img[alt*="첨부"]'
            ]
            
            for selector in file_selectors:
                elements = page.query_selector_all(selector)
                if elements:
                    print(f"{selector} 패턴: {len(elements)}개 발견")
                    for elem in elements[:3]:  # 최대 3개만
                        src = elem.get_attribute('src') or ''
                        href = elem.get_attribute('href') or ''
                        alt = elem.get_attribute('alt') or ''
                        print(f"  src={src}, href={href}, alt={alt}")
            
            # 전체 HTML 저장
            html_content = page.content()
            with open('/home/baltop/work/bizsupnew/btp_scraper/wmit_playwright.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"\nHTML 저장됨: wmit_playwright.html")
            
            # 스크린샷 캡처
            page.screenshot(path='/home/baltop/work/bizsupnew/btp_scraper/wmit_screenshot.png')
            print("스크린샷 저장됨: wmit_screenshot.png")
            
            browser.close()
            return True
            
    except Exception as e:
        print(f"Playwright 분석 실패: {e}")
        return False


def compare_results():
    """두 방법으로 얻은 결과 비교"""
    print("\n" + "=" * 50)
    print("3. 결과 비교 및 권장사항")
    print("=" * 50)
    
    # 파일 크기 비교
    try:
        import os
        requests_size = os.path.getsize('/home/baltop/work/bizsupnew/btp_scraper/wmit_requests.html')
        playwright_size = os.path.getsize('/home/baltop/work/bizsupnew/btp_scraper/wmit_playwright.html')
        
        print(f"requests HTML 크기: {requests_size:,} bytes")
        print(f"Playwright HTML 크기: {playwright_size:,} bytes")
        
        if abs(requests_size - playwright_size) > 1000:
            print("⚠️  HTML 크기 차이가 큼 - JavaScript 렌더링이 필요할 수 있음")
        else:
            print("✅ HTML 크기 유사 - requests로 충분할 수 있음")
        
    except Exception as e:
        print(f"파일 크기 비교 실패: {e}")


if __name__ == "__main__":
    print("WMIT 사이트 분석 시작")
    print("URL: http://wmit.or.kr/announce/businessAnnounceList.do")
    
    # requests 분석
    requests_success = analyze_with_requests()
    
    time.sleep(2)  # 잠시 대기
    
    # Playwright 분석
    playwright_success = analyze_with_playwright()
    
    # 결과 비교
    if requests_success and playwright_success:
        compare_results()
    
    print("\n분석 완료!")
    print("생성된 파일:")
    print("- wmit_requests.html")
    print("- wmit_playwright.html")
    print("- wmit_screenshot.png")