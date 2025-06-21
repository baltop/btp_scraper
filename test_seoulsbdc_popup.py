#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEOULSBDC 팝업 처리 테스트
"""

from playwright.sync_api import sync_playwright
import time

def test_popup_handling():
    """팝업 처리 테스트"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            print("메인 페이지 접근...")
            page.goto('https://www.seoulsbdc.or.kr/')
            page.wait_for_load_state('networkidle')
            print(f"페이지 제목: {page.title()}")
            
            # 팝업 처리
            print("\n팝업 처리 시도...")
            popup_selectors = [
                'button:has-text("닫기")',
                'button:has-text("close")',
                '.popup-close',
                '.modal-close',
                '.close-btn',
                'button[onclick*="close"]',
                'a[onclick*="close"]'
            ]
            
            for selector in popup_selectors:
                try:
                    popup_close = page.query_selector(selector)
                    if popup_close:
                        print(f"팝업 닫기 버튼 발견: {selector}")
                        popup_close.click()
                        time.sleep(1)
                        print("팝업 닫기 완료")
                        break
                except Exception as e:
                    print(f"팝업 닫기 시도 실패 ({selector}): {e}")
                    continue
            
            # JavaScript로 팝업 제거 시도
            try:
                page.evaluate("""
                    // 모든 팝업, 모달 숨기기
                    document.querySelectorAll('.modal, .popup, .overlay').forEach(el => {
                        el.style.display = 'none';
                        el.remove();
                    });
                    // z-index가 높은 요소들 숨기기
                    document.querySelectorAll('*').forEach(el => {
                        const zIndex = window.getComputedStyle(el).zIndex;
                        if (zIndex && parseInt(zIndex) > 100) {
                            el.style.display = 'none';
                        }
                    });
                """)
                print("JavaScript로 팝업 제거 시도 완료")
            except Exception as e:
                print(f"JavaScript 팝업 제거 실패: {e}")
            
            time.sleep(2)
            
            # 공지사항 클릭 시도
            print("\n공지사항 클릭 시도...")
            try:
                # 다양한 방법으로 공지사항 클릭 시도
                methods = [
                    ('text selector', 'a:has-text("공지사항")'),
                    ('href selector', 'a[href="#"]'),
                    ('onclick selector', 'a[onclick*="goNotice"]'),
                    ('onclick selector2', 'a[onclick*="notice"]'),
                ]
                
                for method_name, selector in methods:
                    try:
                        print(f"시도 중: {method_name} - {selector}")
                        element = page.query_selector(selector)
                        if element:
                            text = element.inner_text().strip()
                            onclick = element.get_attribute('onclick')
                            href = element.get_attribute('href')
                            print(f"  요소 발견: '{text}', onclick: {onclick}, href: {href}")
                            
                            # 강제 클릭 (force=True)
                            element.click(force=True)
                            time.sleep(3)
                            
                            # URL 변화 확인
                            current_url = page.url
                            print(f"  클릭 후 URL: {current_url}")
                            
                            # 게시판 요소 확인
                            tables = page.query_selector_all('table')
                            if len(tables) > 0:
                                rows = tables[0].query_selector_all('tr')
                                if len(rows) > 2:
                                    print(f"  ✅ 게시판 테이블 발견: {len(rows)}개 행")
                                    
                                    # 첫 번째 데이터 행 확인
                                    if len(rows) > 1:
                                        cells = rows[1].query_selector_all('td')
                                        print(f"  첫 번째 행: {len(cells)}개 셀")
                                        for i, cell in enumerate(cells[:3]):
                                            print(f"    셀 {i+1}: {cell.inner_text().strip()[:30]}")
                                    return True
                            else:
                                print(f"  테이블 없음 ({len(tables)}개)")
                        
                    except Exception as e:
                        print(f"  {method_name} 실패: {e}")
                        continue
                
                # JavaScript 직접 실행 시도
                print("\nJavaScript 직접 실행 시도...")
                try:
                    # 공지사항 관련 JavaScript 함수 찾기
                    js_functions = [
                        "goNotice()",
                        "moveNotice()",
                        "showNotice()",
                        "fn_notice()",
                        "goBoardList('B061')",
                        "location.href='/sb/main.do'"
                    ]
                    
                    for js_func in js_functions:
                        try:
                            print(f"JavaScript 실행: {js_func}")
                            page.evaluate(js_func)
                            time.sleep(2)
                            
                            current_url = page.url
                            print(f"  결과 URL: {current_url}")
                            
                            if current_url != 'https://www.seoulsbdc.or.kr/':
                                tables = page.query_selector_all('table')
                                if tables:
                                    print(f"  ✅ 이동 성공! 테이블 {len(tables)}개 발견")
                                    return True
                                    
                        except Exception as e:
                            print(f"  {js_func} 실패: {e}")
                            continue
                
                except Exception as e:
                    print(f"JavaScript 실행 실패: {e}")
                
                return False
                
            except Exception as e:
                print(f"공지사항 클릭 전체 실패: {e}")
                return False
            
        except Exception as e:
            print(f"전체 오류: {e}")
            return False
        finally:
            browser.close()

if __name__ == "__main__":
    success = test_popup_handling()
    if success:
        print("\n🎉 공지사항 접근 성공!")
    else:
        print("\n❌ 공지사항 접근 실패")