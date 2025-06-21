#!/usr/bin/env python3
"""
IRIS 사이트 페이지 구조 분석 및 실제 공고 접근
"""

import asyncio
import json
import re
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup


class IrisPageAnalyzer:
    def __init__(self):
        self.base_url = "https://www.iris.go.kr"
        self.list_url = "https://www.iris.go.kr/contents/retrieveBsnsAncmBtinSituListView.do"
        
    async def analyze_page_structure(self):
        """IRIS 사이트 페이지 구조 분석"""
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            
            try:
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                
                page = await context.new_page()
                
                # 네트워크 요청 모니터링
                requests = []
                
                async def handle_request(request):
                    requests.append({
                        'url': request.url,
                        'method': request.method,
                        'headers': dict(request.headers),
                        'post_data': request.post_data
                    })
                
                page.on('request', handle_request)
                
                print("🔍 IRIS 사이트 접속 중...")
                await page.goto(self.list_url)
                await page.wait_for_load_state('networkidle')
                
                # 페이지 HTML 내용 추출
                html_content = await page.content()
                soup = BeautifulSoup(html_content, 'html.parser')
                
                print("📄 페이지 제목:", await page.title())
                
                # 1. 공고 목록 테이블 찾기
                await self._analyze_announcement_list(page, soup)
                
                # 2. 페이지 스크립트 분석
                await self._analyze_page_scripts(page, soup)
                
                # 3. 실제 공고 접근 시도
                await self._access_actual_announcement(page)
                
                # 4. 네트워크 요청 분석
                self._analyze_network_requests(requests)
                
                print("🔍 분석 완료. 10초 후 브라우저 종료...")
                await asyncio.sleep(10)
                
            except Exception as e:
                print(f"❌ 오류 발생: {e}")
                import traceback
                traceback.print_exc()
                
            finally:
                await browser.close()
    
    async def _analyze_announcement_list(self, page, soup):
        """공고 목록 분석"""
        print("\n1️⃣ 공고 목록 분석:")
        
        # 다양한 테이블 선택자 시도
        table_selectors = [
            'table.table-list',
            'table.list-table',
            'table[summary*="공고"]',
            'table[summary*="목록"]',
            'table:has(thead)',
            'table:has(tbody)',
            'table'
        ]
        
        table = None
        for selector in table_selectors:
            table = soup.select_one(selector)
            if table:
                print(f"✅ 테이블 발견: {selector}")
                break
        
        if not table:
            print("❌ 공고 목록 테이블을 찾을 수 없습니다.")
            # 모든 테이블 확인
            all_tables = soup.find_all('table')
            print(f"📋 총 {len(all_tables)}개의 테이블 발견")
            for i, t in enumerate(all_tables):
                print(f"  테이블 {i+1}: {t.get('class', '')}, {t.get('summary', '')}")
            return
        
        # 테이블 헤더 분석
        thead = table.find('thead')
        if thead:
            headers = [th.get_text(strip=True) for th in thead.find_all('th')]
            print(f"📋 테이블 헤더: {headers}")
        
        # 테이블 행 분석
        tbody = table.find('tbody')
        if tbody:
            rows = tbody.find_all('tr')
            print(f"📋 공고 행 수: {len(rows)}")
            
            # 첫 번째 행 상세 분석
            if rows:
                first_row = rows[0]
                cells = first_row.find_all(['td', 'th'])
                print(f"📋 첫 번째 행 셀 수: {len(cells)}")
                
                for i, cell in enumerate(cells):
                    text = cell.get_text(strip=True)[:50]
                    links = cell.find_all('a')
                    print(f"  셀 {i+1}: {text}")
                    for link in links:
                        href = link.get('href', '')
                        onclick = link.get('onclick', '')
                        print(f"    링크: href='{href}', onclick='{onclick}'")
    
    async def _analyze_page_scripts(self, page, soup):
        """페이지 스크립트 분석"""
        print("\n2️⃣ JavaScript 함수 분석:")
        
        # 모든 스크립트 태그 확인
        scripts = soup.find_all('script')
        print(f"📋 스크립트 태그 수: {len(scripts)}")
        
        # 다운로드 관련 함수 찾기
        download_functions = []
        for script in scripts:
            if script.string:
                content = script.string
                if 'downloadAtchFile' in content or 'download' in content.lower():
                    download_functions.append(content)
        
        if download_functions:
            print("✅ 다운로드 관련 JavaScript 함수 발견:")
            for i, func in enumerate(download_functions):
                lines = func.split('\n')
                relevant_lines = [line.strip() for line in lines 
                                if 'download' in line.lower() or 'atchFile' in line]
                print(f"  함수 {i+1}:")
                for line in relevant_lines[:10]:  # 처음 10줄만 출력
                    print(f"    {line}")
        
        # 페이지에서 JavaScript 함수 실행하여 확인
        try:
            result = await page.evaluate("""
                () => {
                    let functions = [];
                    for (let prop in window) {
                        if (typeof window[prop] === 'function' && prop.includes('download')) {
                            functions.push(prop);
                        }
                    }
                    return functions;
                }
            """)
            print(f"📋 전역 다운로드 함수: {result}")
        except Exception as e:
            print(f"❌ JavaScript 함수 검사 중 오류: {e}")
    
    async def _access_actual_announcement(self, page):
        """실제 공고 접근 시도"""
        print("\n3️⃣ 실제 공고 접근 시도:")
        
        # 공고 링크 클릭 시도
        try:
            # 다양한 선택자로 공고 링크 찾기
            selectors = [
                'a[href*="retrieveBsnsAncmBtinSituDetailView"]',
                'a[onclick*="retrieveBsnsAncmBtinSituDetailView"]',
                'tbody tr:first-child a',
                'table a:first-of-type'
            ]
            
            for selector in selectors:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    href = await element.get_attribute('href')
                    onclick = await element.get_attribute('onclick')
                    
                    print(f"✅ 공고 링크 발견: {selector}")
                    print(f"  텍스트: {text}")
                    print(f"  href: {href}")
                    print(f"  onclick: {onclick}")
                    
                    # 링크 클릭
                    print("🔗 공고 링크 클릭...")
                    await element.click()
                    await page.wait_for_load_state('networkidle')
                    
                    # 상세 페이지 분석
                    await self._analyze_detail_page(page)
                    return
            
            print("❌ 공고 링크를 찾을 수 없습니다.")
            
        except Exception as e:
            print(f"❌ 공고 접근 중 오류: {e}")
    
    async def _analyze_detail_page(self, page):
        """상세 페이지 분석"""
        print("\n4️⃣ 상세 페이지 분석:")
        
        try:
            current_url = page.url
            print(f"📄 현재 URL: {current_url}")
            
            # 첨부파일 영역 찾기
            html_content = await page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 첨부파일 관련 요소 찾기
            attachment_selectors = [
                'a[onclick*="downloadAtchFile"]',
                'a[href*="download"]',
                'a[onclick*="download"]',
                '*[class*="attach"]',
                '*[class*="file"]'
            ]
            
            for selector in attachment_selectors:
                elements = soup.select(selector)
                if elements:
                    print(f"✅ 첨부파일 요소 발견: {selector} ({len(elements)}개)")
                    for i, elem in enumerate(elements[:3]):  # 처음 3개만 출력
                        print(f"  {i+1}. {elem.get_text(strip=True)}")
                        print(f"     href: {elem.get('href', '')}")
                        print(f"     onclick: {elem.get('onclick', '')}")
            
            # 실제 다운로드 링크 클릭 시도
            download_link = await page.query_selector('a[onclick*="downloadAtchFile"]')
            if download_link:
                print("📥 다운로드 링크 클릭 시도...")
                
                # 다운로드 이벤트 리스너 설정
                download_info = []
                
                async def handle_download(download):
                    info = {
                        'filename': download.suggested_filename,
                        'url': download.url
                    }
                    download_info.append(info)
                    print(f"📁 다운로드 시작: {download.suggested_filename}")
                    print(f"📁 다운로드 URL: {download.url}")
                
                page.on('download', handle_download)
                
                await download_link.click()
                await asyncio.sleep(2)
                
                if download_info:
                    print("✅ 다운로드 성공!")
                    for info in download_info:
                        print(f"  파일명: {info['filename']}")
                        print(f"  URL: {info['url']}")
                else:
                    print("❌ 다운로드 이벤트가 발생하지 않았습니다.")
            
        except Exception as e:
            print(f"❌ 상세 페이지 분석 중 오류: {e}")
    
    def _analyze_network_requests(self, requests):
        """네트워크 요청 분석"""
        print("\n5️⃣ 네트워크 요청 분석:")
        
        # 다운로드 관련 요청 필터링
        download_requests = [req for req in requests 
                           if 'download' in req['url'].lower() or 'atchFile' in req['url']]
        
        if download_requests:
            print(f"✅ 다운로드 관련 요청 {len(download_requests)}개 발견:")
            for req in download_requests:
                print(f"  URL: {req['url']}")
                print(f"  Method: {req['method']}")
                if req['post_data']:
                    print(f"  POST Data: {req['post_data']}")
        else:
            print("❌ 다운로드 관련 요청을 찾을 수 없습니다.")
        
        # 주요 요청 타입 분석
        post_requests = [req for req in requests if req['method'] == 'POST']
        print(f"📋 POST 요청 수: {len(post_requests)}")
        
        for req in post_requests:
            if 'iris.go.kr' in req['url']:
                print(f"  - {req['url']}")
                if req['post_data']:
                    print(f"    Data: {req['post_data']}")


async def main():
    analyzer = IrisPageAnalyzer()
    await analyzer.analyze_page_structure()


if __name__ == "__main__":
    asyncio.run(main())