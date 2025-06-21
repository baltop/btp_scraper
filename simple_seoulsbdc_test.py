#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEOULSBDC 간단한 접근 테스트
"""

from playwright.sync_api import sync_playwright
import time

def simple_seoulsbdc_test():
    """SEOULSBDC 간단한 접근 테스트"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            print("메인 페이지 접근...")
            page.goto('https://www.seoulsbdc.or.kr/')
            page.wait_for_load_state('networkidle')
            print(f"페이지 제목: {page.title()}")
            
            # 직접 게시판 URL 시도
            print("\n직접 게시판 URL 접근 시도...")
            try:
                page.goto('https://www.seoulsbdc.or.kr/bs/BS_LIST.do?boardCd=B061')
                page.wait_for_load_state('networkidle')
                print(f"게시판 페이지 제목: {page.title()}")
                print(f"현재 URL: {page.url}")
                
                # 페이지 내용 확인
                body_text = page.inner_text('body')
                print(f"페이지 내용 길이: {len(body_text)}")
                
                if "오류" in body_text or "허용되지 않는" in body_text:
                    print("❌ 직접 접근 차단됨")
                    print(f"오류 메시지: {body_text[:200]}")
                else:
                    print("✅ 직접 접근 성공!")
                    
                    # 테이블 찾기
                    tables = page.query_selector_all('table')
                    print(f"테이블 개수: {len(tables)}")
                    
                    if tables:
                        for i, table in enumerate(tables):
                            rows = table.query_selector_all('tr')
                            if len(rows) > 1:
                                print(f"테이블 {i+1}: {len(rows)}개 행")
                                # 첫 번째 데이터 행 확인
                                first_row = rows[1]
                                cells = first_row.query_selector_all('td')
                                print(f"  첫 번째 행: {len(cells)}개 셀")
                                for j, cell in enumerate(cells[:3]):
                                    text = cell.inner_text().strip()
                                    print(f"    셀 {j+1}: {text[:50]}")
                
            except Exception as e:
                print(f"직접 접근 실패: {e}")
            
            # 메인 페이지에서 네비게이션 시도
            print("\n메인 페이지에서 네비게이션...")
            page.goto('https://www.seoulsbdc.or.kr/')
            page.wait_for_load_state('networkidle')
            
            # 다양한 링크 시도
            link_patterns = [
                'a:has-text("공지사항")',
                'a:has-text("알림")',
                'a:has-text("소식")',
                'a[href*="board"]',
                'a[href*="notice"]',
                'a[href*="bs"]'
            ]
            
            for pattern in link_patterns:
                try:
                    link = page.query_selector(pattern)
                    if link:
                        text = link.inner_text().strip()
                        href = link.get_attribute('href')
                        print(f"발견: '{text}' -> {href}")
                        
                        # 클릭 시도
                        link.click()
                        page.wait_for_load_state('networkidle')
                        
                        current_url = page.url
                        print(f"이동됨: {current_url}")
                        
                        # 게시판인지 확인
                        tables = page.query_selector_all('table')
                        if tables and len(tables) > 0:
                            rows = tables[0].query_selector_all('tr')
                            if len(rows) > 3:  # 헤더 + 최소 2개 데이터 행
                                print(f"✅ 게시판 발견! {len(rows)}개 행")
                                return True
                        
                        # 다시 메인 페이지로
                        page.goto('https://www.seoulsbdc.or.kr/')
                        page.wait_for_load_state('networkidle')
                        
                except Exception as e:
                    print(f"패턴 '{pattern}' 오류: {e}")
                    continue
            
            return False
            
        except Exception as e:
            print(f"전체 오류: {e}")
            return False
        finally:
            browser.close()

if __name__ == "__main__":
    success = simple_seoulsbdc_test()
    if success:
        print("\n🎉 접근 방법 발견!")
    else:
        print("\n❌ 접근 방법을 찾지 못했습니다.")