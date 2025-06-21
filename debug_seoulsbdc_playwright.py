#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEOULSBDC Playwright 디버깅 스크립트
"""

from playwright.sync_api import sync_playwright
import time

def debug_seoulsbdc_access():
    """SEOULSBDC 사이트 접근 디버깅"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # 헤드리스 비활성화로 시각적 확인
        page = browser.new_page()
        
        try:
            print("1. 메인 페이지 접근...")
            page.goto('https://www.seoulsbdc.or.kr/')
            page.wait_for_load_state('networkidle')
            print(f"페이지 제목: {page.title()}")
            
            # 스크린샷
            page.screenshot(path='debug_seoulsbdc_main.png')
            print("메인 페이지 스크린샷 저장됨: debug_seoulsbdc_main.png")
            
            # 페이지 대기
            time.sleep(3)
            
            # 공지사항 링크 찾기
            print("\n2. 공지사항 링크 찾기...")
            notice_links = page.query_selector_all('a')
            for link in notice_links:
                text = link.inner_text()
                if '공지' in text:
                    print(f"발견된 링크: '{text}' - href: {link.get_attribute('href')}")
            
            # 특정 텍스트가 포함된 링크 시도
            possible_selectors = [
                'a:has-text("공지사항")',
                'a:has-text("공지")',
                'a[href*="notice"]',
                'a[href*="board"]',
                'a[href*="bs"]'
            ]
            
            for selector in possible_selectors:
                try:
                    element = page.query_selector(selector)
                    if element:
                        text = element.inner_text()
                        href = element.get_attribute('href')
                        print(f"선택자 '{selector}' 발견: '{text}' - {href}")
                        
                        # 클릭 시도
                        print(f"클릭 시도: {text}")
                        element.click()
                        page.wait_for_load_state('networkidle')
                        
                        # 결과 확인
                        new_url = page.url
                        new_title = page.title()
                        print(f"이동된 URL: {new_url}")
                        print(f"이동된 페이지 제목: {new_title}")
                        
                        # 스크린샷
                        page.screenshot(path=f'debug_seoulsbdc_after_{selector.replace(":", "_").replace("(", "_").replace(")", "_")}.png')
                        
                        # 게시판 테이블 확인
                        tables = page.query_selector_all('table')
                        print(f"테이블 개수: {len(tables)}")
                        
                        if tables:
                            for i, table in enumerate(tables):
                                rows = table.query_selector_all('tr')
                                print(f"테이블 {i+1}: {len(rows)}개 행")
                                if len(rows) > 1:
                                    # 첫 번째 데이터 행 확인
                                    first_data_row = rows[1] if len(rows) > 1 else None
                                    if first_data_row:
                                        cells = first_data_row.query_selector_all('td')
                                        print(f"첫 번째 데이터 행: {len(cells)}개 셀")
                                        for j, cell in enumerate(cells[:5]):  # 처음 5개 셀만
                                            print(f"  셀 {j+1}: {cell.inner_text().strip()}")
                        
                        break
                        
                except Exception as e:
                    print(f"선택자 '{selector}' 오류: {e}")
                    continue
            
            # 사용자 입력 대기 (수동 확인용)
            input("\n수동 확인을 위해 엔터 키를 누르세요...")
            
        except Exception as e:
            print(f"오류 발생: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    debug_seoulsbdc_access()