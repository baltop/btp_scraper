#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POHANGCCI 사이트 구조 디버깅
"""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def debug_pohangcci():
    """POHANGCCI 사이트 실제 구조 분석"""
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # headless=False로 브라우저 표시
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # 사이트 접속
            url = "http://pohangcci.korcham.net/front/board/boardContentsListPage.do?boardId=10275&menuId=1440"
            print(f"접속 중: {url}")
            
            await page.goto(url, wait_until='networkidle')
            await asyncio.sleep(3)  # 페이지 로딩 대기
            
            # 페이지 타이틀 확인
            title = await page.title()
            print(f"페이지 타이틀: {title}")
            
            # 테이블 찾기
            tables = await page.query_selector_all('table')
            print(f"테이블 개수: {len(tables)}")
            
            for i, table in enumerate(tables):
                rows = await table.query_selector_all('tr')
                print(f"테이블 {i+1}: {len(rows)}개 행")
                
                if len(rows) > 3:  # 헤더 + 데이터가 있는 테이블
                    print(f"  상세 분석 중...")
                    
                    # 첫 번째 데이터 행 분석
                    for j, row in enumerate(rows[:5]):  # 처음 5개 행만
                        cells = await row.query_selector_all('td')
                        if len(cells) >= 2:
                            print(f"    행 {j+1}: {len(cells)}개 셀")
                            
                            # 각 셀의 내용 확인
                            for k, cell in enumerate(cells):
                                text = await cell.inner_text()
                                html = await cell.inner_html()
                                print(f"      셀 {k+1}: '{text[:50]}...'")
                                
                                # 링크가 있는지 확인
                                links = await cell.query_selector_all('a')
                                if links:
                                    for link in links:
                                        href = await link.get_attribute('href')
                                        onclick = await link.get_attribute('onclick')
                                        text = await link.inner_text()
                                        print(f"        링크: href='{href}', onclick='{onclick}', text='{text[:30]}'")
            
            # JavaScript 함수 확인
            print("\n=== JavaScript 함수 테스트 ===")
            try:
                # contentsView 함수 존재 확인
                result = await page.evaluate("typeof contentsView")
                print(f"contentsView 함수: {result}")
                
                # go_Page 함수 존재 확인
                result = await page.evaluate("typeof go_Page")
                print(f"go_Page 함수: {result}")
                
            except Exception as e:
                print(f"JavaScript 함수 확인 실패: {e}")
            
            # 스크린샷 저장
            await page.screenshot(path='pohangcci_debug.png')
            print("스크린샷 저장: pohangcci_debug.png")
            
            # 사용자 입력 대기 (브라우저에서 수동 확인 가능)
            print("\n브라우저에서 사이트를 확인한 후 Enter를 눌러주세요...")
            input()
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_pohangcci())