#!/usr/bin/env python3
"""
WMIT 사이트 스크롤 테스트 - 실제 테이블까지 스크롤
"""

from playwright.sync_api import sync_playwright
import time

def test_wmit_with_scroll():
    """Playwright로 WMIT 사이트 스크롤 테스트"""
    url = "http://wmit.or.kr/announce/businessAnnounceList.do"
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)  # 시각적 확인을 위해 headless=False
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            page = context.new_page()
            
            print(f"접근 URL: {url}")
            page.goto(url, wait_until='networkidle', timeout=30000)
            
            # 페이지 로드 완료 대기
            page.wait_for_load_state('networkidle')
            time.sleep(2)
            
            # 테이블이 있는 위치까지 스크롤
            print("테이블 위치로 스크롤...")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            time.sleep(2)
            
            # 테이블 스크린샷
            table = page.query_selector('table.tbl.text-center')
            if table:
                print("테이블 발견! 스크린샷 촬영...")
                table.screenshot(path='/home/baltop/work/bizsupnew/btp_scraper/wmit_table.png')
                print("테이블 스크린샷 저장: wmit_table.png")
                
                # 테이블 데이터 분석
                rows = table.query_selector_all('tbody tr')
                print(f"데이터 행 수: {len(rows)}")
                
                if rows:
                    print("\n첫 번째 공고 정보:")
                    first_row = rows[0]
                    cells = first_row.query_selector_all('td')
                    
                    for i, cell in enumerate(cells):
                        cell_text = cell.inner_text().strip()
                        print(f"  {i+1}. {cell_text}")
                        
                        # 링크 확인
                        link = cell.query_selector('a')
                        if link:
                            href = link.get_attribute('href') or ''
                            onclick = link.get_attribute('onclick') or ''
                            print(f"     -> 링크: {href}")
                            if onclick:
                                print(f"     -> onclick: {onclick}")
            
            # 페이지네이션 확인
            print("\n페이지네이션 확인...")
            pagination = page.query_selector('.pagination')
            if pagination:
                links = pagination.query_selector_all('a')
                print(f"페이지네이션 링크 수: {len(links)}")
                
                for i, link in enumerate(links):
                    text = link.inner_text().strip()
                    onclick = link.get_attribute('onclick') or ''
                    if onclick:
                        print(f"  {i+1}. '{text}' -> {onclick}")
            
            # 전체 페이지 스크린샷
            page.screenshot(path='/home/baltop/work/bizsupnew/btp_scraper/wmit_fullpage.png', full_page=True)
            print("전체 페이지 스크린샷 저장: wmit_fullpage.png")
            
            input("분석 완료. 엔터를 누르면 브라우저가 종료됩니다...")
            browser.close()
            
    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    test_wmit_with_scroll()