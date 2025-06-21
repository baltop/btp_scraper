#!/usr/bin/env python3
"""
IRIS 사이트 파일 다운로드 메커니즘 분석 스크립트
Playwright를 사용하여 실제 브라우저 환경에서 네트워크 요청 모니터링
"""

import asyncio
import json
import os
from playwright.async_api import async_playwright
from urllib.parse import urlparse, parse_qs
import time


class IrisDownloadAnalyzer:
    def __init__(self):
        self.base_url = "https://www.iris.go.kr"
        self.list_url = "https://www.iris.go.kr/contents/retrieveBsnsAncmBtinSituListView.do"
        self.network_requests = []
        self.network_responses = []
        self.cookies = []
        
    async def analyze_download_mechanism(self):
        """IRIS 사이트의 파일 다운로드 메커니즘 분석"""
        
        async with async_playwright() as p:
            # 헤드리스 모드를 False로 설정하여 실제 브라우저 환경 재현
            browser = await p.chromium.launch(
                headless=False,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            try:
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                )
                
                page = await context.new_page()
                
                # 네트워크 요청 모니터링 설정
                await self._setup_network_monitoring(page)
                
                print("🔍 IRIS 사이트 접속 중...")
                await page.goto(self.list_url, wait_until='networkidle')
                
                # 초기 쿠키 수집
                cookies = await context.cookies()
                self.cookies = cookies
                print(f"📋 초기 쿠키 수집: {len(cookies)}개")
                
                # 첫 번째 공고 찾기 및 클릭
                print("🔍 첫 번째 공고 찾는 중...")
                await self._find_and_click_first_announcement(page)
                
                # 상세 페이지 로딩 대기
                await page.wait_for_load_state('networkidle')
                
                # 첨부파일 다운로드 링크 찾기 및 분석
                print("📎 첨부파일 다운로드 링크 분석 중...")
                await self._analyze_download_links(page)
                
                # 실제 파일 다운로드 시도
                print("⬇️ 실제 파일 다운로드 시도 중...")
                await self._attempt_file_download(page)
                
                # 결과 분석 및 출력
                await self._analyze_results()
                
            except Exception as e:
                print(f"❌ 오류 발생: {e}")
                import traceback
                traceback.print_exc()
                
            finally:
                print("🔍 분석 완료. 브라우저를 5초 후 종료합니다...")
                await asyncio.sleep(5)
                await browser.close()
    
    async def _setup_network_monitoring(self, page):
        """네트워크 요청/응답 모니터링 설정"""
        
        async def handle_request(request):
            self.network_requests.append({
                'url': request.url,
                'method': request.method,
                'headers': dict(request.headers),
                'post_data': request.post_data,
                'timestamp': time.time()
            })
            
        async def handle_response(response):
            self.network_responses.append({
                'url': response.url,
                'status': response.status,
                'headers': dict(response.headers),
                'timestamp': time.time()
            })
            
        page.on('request', handle_request)
        page.on('response', handle_response)
    
    async def _find_and_click_first_announcement(self, page):
        """첫 번째 공고 찾기 및 클릭"""
        try:
            # 다양한 선택자로 공고 링크 찾기
            selectors = [
                'table.table-list tbody tr:first-child td a',
                'table tbody tr:first-child a',
                '.list-table tbody tr:first-child a',
                'tbody tr:first-child a[href*="retrieveBsnsAncmBtinSituDetailView"]'
            ]
            
            first_link = None
            for selector in selectors:
                first_link = await page.query_selector(selector)
                if first_link:
                    print(f"✅ 공고 링크 발견: {selector}")
                    break
            
            if not first_link:
                print("❌ 첫 번째 공고 링크를 찾을 수 없습니다.")
                # 페이지의 모든 링크 출력
                all_links = await page.query_selector_all('a')
                print(f"📋 페이지에서 발견된 모든 링크: {len(all_links)}개")
                for i, link in enumerate(all_links[:10]):  # 처음 10개만 출력
                    href = await link.get_attribute('href')
                    text = await link.text_content()
                    print(f"  {i+1}. {text[:50]} -> {href}")
                return
            
            # 링크 클릭
            await first_link.click()
            print("✅ 첫 번째 공고 클릭 완료")
            
        except Exception as e:
            print(f"❌ 공고 클릭 중 오류: {e}")
    
    async def _analyze_download_links(self, page):
        """첨부파일 다운로드 링크 분석"""
        try:
            # JavaScript에서 다운로드 함수 찾기
            download_links = await page.query_selector_all('a[onclick*="downloadAtchFile"], a[href*="download"]')
            
            if not download_links:
                print("❌ 다운로드 링크를 찾을 수 없습니다.")
                # 페이지 내용 확인
                content = await page.content()
                if 'downloadAtchFile' in content:
                    print("✅ downloadAtchFile 함수 발견")
                    # 함수 정의 추출
                    await page.evaluate("""
                        if (window.f_bsnsAncm_downloadAtchFile) {
                            console.log('f_bsnsAncm_downloadAtchFile 함수:', window.f_bsnsAncm_downloadAtchFile.toString());
                        }
                    """)
                return
            
            print(f"📎 다운로드 링크 {len(download_links)}개 발견")
            
            for i, link in enumerate(download_links):
                onclick = await link.get_attribute('onclick')
                href = await link.get_attribute('href')
                text = await link.text_content()
                
                print(f"  {i+1}. {text}")
                print(f"     onclick: {onclick}")
                print(f"     href: {href}")
                
        except Exception as e:
            print(f"❌ 다운로드 링크 분석 중 오류: {e}")
    
    async def _attempt_file_download(self, page):
        """실제 파일 다운로드 시도"""
        try:
            # 다운로드 링크 클릭 전 네트워크 요청 카운트
            before_count = len(self.network_requests)
            
            # 첨부파일 다운로드 링크 찾기 및 클릭
            download_link = await page.query_selector('a[onclick*="downloadAtchFile"]')
            if not download_link:
                download_link = await page.query_selector('a[href*="download"]')
            
            if download_link:
                print("📥 다운로드 링크 클릭...")
                
                # 다운로드 이벤트 모니터링
                async def handle_download(download):
                    print(f"📁 다운로드 시작: {download.suggested_filename}")
                    await download.save_as(f"/tmp/{download.suggested_filename}")
                    print(f"✅ 다운로드 완료: {download.suggested_filename}")
                
                page.on('download', handle_download)
                
                await download_link.click()
                
                # 다운로드 완료 대기
                await asyncio.sleep(3)
                
                # 다운로드 후 새로운 네트워크 요청 분석
                after_count = len(self.network_requests)
                new_requests = self.network_requests[before_count:after_count]
                
                print(f"📊 다운로드 관련 새로운 요청 {len(new_requests)}개:")
                for req in new_requests:
                    print(f"  - {req['method']} {req['url']}")
                    if req['post_data']:
                        print(f"    POST 데이터: {req['post_data']}")
                
            else:
                print("❌ 다운로드 링크를 찾을 수 없습니다.")
                
        except Exception as e:
            print(f"❌ 파일 다운로드 시도 중 오류: {e}")
    
    async def _analyze_results(self):
        """분석 결과 출력"""
        print("\n" + "="*80)
        print("📊 IRIS 사이트 파일 다운로드 메커니즘 분석 결과")
        print("="*80)
        
        # 1. 쿠키 정보 분석
        print("\n1️⃣ 쿠키 정보:")
        for cookie in self.cookies:
            if cookie['name'] in ['JSESSIONID', 'WMONID', 'SESSION']:
                print(f"  - {cookie['name']}: {cookie['value']}")
        
        # 2. 주요 네트워크 요청 분석
        print("\n2️⃣ 주요 네트워크 요청:")
        download_requests = [req for req in self.network_requests 
                           if 'download' in req['url'].lower() or 'atchFile' in req['url']]
        
        if download_requests:
            for req in download_requests:
                print(f"  URL: {req['url']}")
                print(f"  Method: {req['method']}")
                print(f"  Headers: {json.dumps(req['headers'], indent=4, ensure_ascii=False)}")
                if req['post_data']:
                    print(f"  POST Data: {req['post_data']}")
                print()
        else:
            print("  ❌ 다운로드 관련 요청을 찾을 수 없습니다.")
        
        # 3. JavaScript 함수 분석
        print("\n3️⃣ JavaScript 다운로드 함수 분석:")
        print("  - 함수명: f_bsnsAncm_downloadAtchFile")
        print("  - 예상 파라미터: atchFileId, atchFileSn")
        
        # 4. 추천 구현 방법
        print("\n4️⃣ 스크래퍼 구현 권장사항:")
        print("  1. 세션 유지를 위해 JSESSIONID 쿠키 보존")
        print("  2. 상세 페이지 접근 후 다운로드 링크에서 파라미터 추출")
        print("  3. JavaScript 함수 대신 직접 다운로드 URL 호출")
        print("  4. Referer 헤더 설정 필수")
        
        # 5. 파일 저장
        analysis_data = {
            'cookies': self.cookies,
            'network_requests': self.network_requests,
            'network_responses': self.network_responses,
            'timestamp': time.time()
        }
        
        with open('/tmp/iris_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n📁 상세 분석 결과가 /tmp/iris_analysis.json에 저장되었습니다.")


async def main():
    analyzer = IrisDownloadAnalyzer()
    await analyzer.analyze_download_mechanism()


if __name__ == "__main__":
    asyncio.run(main())