#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEOULSBDC 세션 후 직접 접근 테스트
"""

from playwright.sync_api import sync_playwright
import time

def test_direct_after_session():
    """세션 설정 후 직접 보드 접근 테스트"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            print("1. 메인 페이지로 세션 설정...")
            page.goto('https://www.seoulsbdc.or.kr/')
            page.wait_for_load_state('networkidle')
            time.sleep(2)
            
            # 팝업 제거
            try:
                page.evaluate("""
                    document.querySelectorAll('.modal, .popup, .overlay').forEach(el => {
                        el.style.display = 'none';
                        el.remove();
                    });
                    document.querySelectorAll('*').forEach(el => {
                        const zIndex = window.getComputedStyle(el).zIndex;
                        if (zIndex && parseInt(zIndex) > 100) {
                            el.style.display = 'none';
                        }
                    });
                """)
            except:
                pass
            
            print("2. 세션 설정 후 직접 보드 URL 접근...")
            page.goto('https://www.seoulsbdc.or.kr/bs/BS_LIST.do?boardCd=B061')
            page.wait_for_load_state('networkidle')
            time.sleep(3)
            
            print(f"현재 URL: {page.url}")
            print(f"페이지 제목: {page.title()}")
            
            # 페이지 내용 확인
            body_text = page.inner_text('body')
            print(f"페이지 내용 길이: {len(body_text)}")
            
            if "오류" in body_text or "허용되지 않는" in body_text:
                print("❌ 여전히 접근 차단됨")
                print(f"오류 메시지: {body_text[:200]}")
            else:
                print("✅ 접근 성공!")
                
                # 테이블 분석
                tables = page.query_selector_all('table')
                print(f"테이블 개수: {len(tables)}")
                
                for i, table in enumerate(tables):
                    rows = table.query_selector_all('tr')
                    print(f"테이블 {i+1}: {len(rows)}개 행")
                    
                    if len(rows) > 1:
                        # 헤더 확인
                        header_cells = rows[0].query_selector_all('th, td')
                        print(f"  헤더: {len(header_cells)}개 셀")
                        for j, cell in enumerate(header_cells):
                            text = cell.inner_text().strip()
                            print(f"    {j+1}: '{text}'")
                        
                        # 첫 번째 데이터 행 확인
                        if len(rows) > 1:
                            data_cells = rows[1].query_selector_all('td')
                            print(f"  첫 번째 데이터 행: {len(data_cells)}개 셀")
                            for j, cell in enumerate(data_cells[:5]):
                                text = cell.inner_text().strip()
                                link = cell.query_selector('a')
                                if link:
                                    onclick = link.get_attribute('onclick')
                                    print(f"    {j+1}: '{text}' [링크: {onclick}]")
                                else:
                                    print(f"    {j+1}: '{text}'")
                        
                        return True
                
            # 3. 다른 보드 코드들 시도
            print("\n3. 다른 보드 코드들 시도...")
            board_codes = ['B001', 'B002', 'B003', 'B004', 'B061', 'B062']
            
            for code in board_codes:
                test_url = f'https://www.seoulsbdc.or.kr/bs/BS_LIST.do?boardCd={code}'
                print(f"시도: {test_url}")
                
                page.goto(test_url)
                page.wait_for_load_state('networkidle')
                time.sleep(2)
                
                body_text = page.inner_text('body')
                if "오류" not in body_text and "허용되지 않는" not in body_text and len(body_text) > 100:
                    print(f"✅ 보드 코드 {code} 접근 성공!")
                    tables = page.query_selector_all('table')
                    if tables:
                        rows = tables[0].query_selector_all('tr')
                        print(f"  테이블: {len(rows)}개 행")
                        if len(rows) > 2:
                            return True
                else:
                    print(f"❌ 보드 코드 {code} 접근 실패")
            
            return False
            
        except Exception as e:
            print(f"오류 발생: {e}")
            return False
        finally:
            browser.close()

if __name__ == "__main__":
    success = test_direct_after_session()
    if success:
        print("\n🎉 보드 접근 성공!")
    else:
        print("\n❌ 보드 접근 실패")