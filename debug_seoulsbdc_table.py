#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEOULSBDC 테이블 구조 분석
"""

from playwright.sync_api import sync_playwright
import time

def debug_table_structure():
    """테이블 구조 분석"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            print("메인 페이지 접근...")
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
            
            # 공지사항 페이지로 이동
            print("공지사항 페이지로 이동...")
            page.evaluate("location.href='/sb/main.do'")
            page.wait_for_load_state('networkidle')
            time.sleep(3)
            
            print(f"현재 URL: {page.url}")
            print(f"페이지 제목: {page.title()}")
            
            # 모든 테이블 분석
            tables = page.query_selector_all('table')
            print(f"\n총 테이블 개수: {len(tables)}")
            
            for i, table in enumerate(tables):
                print(f"\n=== 테이블 {i+1} ===")
                
                # 테이블 속성 확인
                table_id = table.get_attribute('id')
                table_class = table.get_attribute('class')
                print(f"ID: {table_id}, Class: {table_class}")
                
                # 행 분석
                rows = table.query_selector_all('tr')
                print(f"총 행 개수: {len(rows)}")
                
                if len(rows) > 0:
                    # 헤더 행 분석
                    header_row = rows[0]
                    header_cells = header_row.query_selector_all('th, td')
                    print(f"헤더 셀 개수: {len(header_cells)}")
                    print("헤더 내용:")
                    for j, cell in enumerate(header_cells):
                        text = cell.inner_text().strip()
                        print(f"  {j+1}: '{text}'")
                
                # 데이터 행 분석 (최대 3개)
                data_rows = rows[1:4]  # 첫 3개 데이터 행
                print(f"데이터 행 분석 (최대 3개):")
                
                for row_idx, row in enumerate(data_rows):
                    cells = row.query_selector_all('td')
                    print(f"  행 {row_idx+1}: {len(cells)}개 셀")
                    
                    for cell_idx, cell in enumerate(cells[:6]):  # 최대 6개 셀
                        text = cell.inner_text().strip()
                        
                        # 링크 확인
                        link = cell.query_selector('a')
                        if link:
                            href = link.get_attribute('href')
                            onclick = link.get_attribute('onclick')
                            print(f"    셀 {cell_idx+1}: '{text}' [링크: href={href}, onclick={onclick}]")
                        else:
                            print(f"    셀 {cell_idx+1}: '{text}'")
                    
                    if len(cells) > 6:
                        print(f"    ... 총 {len(cells)}개 셀")
                
                print("-" * 50)
            
            # 페이지네이션 확인
            print("\n페이지네이션 분석:")
            pagination_selectors = [
                '.pagination',
                '.paging', 
                '.page',
                'a[onclick*="page"]',
                'a[onclick*="Page"]'
            ]
            
            for selector in pagination_selectors:
                elements = page.query_selector_all(selector)
                if elements:
                    print(f"선택자 '{selector}': {len(elements)}개 요소")
                    for elem in elements[:3]:  # 처음 3개만
                        text = elem.inner_text().strip()
                        onclick = elem.get_attribute('onclick')
                        href = elem.get_attribute('href')
                        print(f"  '{text}' - onclick: {onclick}, href: {href}")
            
        except Exception as e:
            print(f"오류 발생: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    debug_table_structure()