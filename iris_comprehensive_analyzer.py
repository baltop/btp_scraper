#!/usr/bin/env python3
"""
IRIS 사이트 종합 분석 - AJAX 및 동적 콘텐츠 포함
"""

import asyncio
import json
import re
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import time


class IrisComprehensiveAnalyzer:
    def __init__(self):
        self.base_url = "https://www.iris.go.kr"
        self.list_url = "https://www.iris.go.kr/contents/retrieveBsnsAncmBtinSituListView.do"
        self.all_requests = []
        self.all_responses = []
        
    async def comprehensive_analysis(self):
        """IRIS 사이트 종합 분석"""
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-web-security']
            )
            
            try:
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    java_script_enabled=True
                )
                
                page = await context.new_page()
                
                # 네트워크 모니터링 설정
                await self._setup_comprehensive_monitoring(page)
                
                print("🔍 IRIS 사이트 접속 중...")
                await page.goto(self.list_url, wait_until='networkidle', timeout=60000)
                
                # 페이지 완전 로드 대기
                await asyncio.sleep(5)
                
                # 1. 페이지 기본 정보 분석
                await self._analyze_basic_info(page)
                
                # 2. AJAX 요청 확인
                await self._trigger_ajax_requests(page)
                
                # 3. 동적 콘텐츠 로드 대기
                await self._wait_for_dynamic_content(page)
                
                # 4. 공고 목록 재분석
                await self._reanalyze_announcements(page)
                
                # 5. 실제 공고 접근 및 파일 다운로드 테스트
                await self._test_file_download_process(page)
                
                # 6. 종합 결과 분석
                await self._comprehensive_results_analysis()
                
                print("🔍 분석 완료. 브라우저를 15초 후 종료...")
                await asyncio.sleep(15)
                
            except Exception as e:
                print(f"❌ 오류 발생: {e}")
                import traceback
                traceback.print_exc()
                
            finally:
                await browser.close()
    
    async def _setup_comprehensive_monitoring(self, page):
        """종합 네트워크 모니터링 설정"""
        
        async def handle_request(request):
            self.all_requests.append({
                'url': request.url,
                'method': request.method,
                'headers': dict(request.headers),
                'post_data': request.post_data,
                'resource_type': request.resource_type,
                'timestamp': time.time()
            })
            
        async def handle_response(response):
            self.all_responses.append({
                'url': response.url,
                'status': response.status,
                'headers': dict(response.headers),
                'timestamp': time.time()
            })
            
        page.on('request', handle_request)
        page.on('response', handle_response)
        
        # 콘솔 메시지 모니터링
        page.on('console', lambda msg: print(f"🖥️ Console: {msg.text}"))
    
    async def _analyze_basic_info(self, page):
        """페이지 기본 정보 분석"""
        print("\n1️⃣ 페이지 기본 정보:")
        
        title = await page.title()
        url = page.url
        print(f"📄 제목: {title}")
        print(f"🌐 URL: {url}")
        
        # 페이지 로딩 상태 확인
        ready_state = await page.evaluate("document.readyState")
        print(f"📋 문서 상태: {ready_state}")
        
        # jQuery 확인
        jquery_version = await page.evaluate("""
            () => {
                if (typeof jQuery !== 'undefined') {
                    return jQuery.fn.jquery;
                } else if (typeof $ !== 'undefined' && $.fn) {
                    return $.fn.jquery;
                }
                return null;
            }
        """)
        print(f"📋 jQuery 버전: {jquery_version}")
    
    async def _trigger_ajax_requests(self, page):
        """AJAX 요청 트리거"""
        print("\n2️⃣ AJAX 요청 트리거:")
        
        # 페이지 스크롤 (Lazy loading 트리거)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)
        
        # 검색 폼이 있는지 확인하고 실행
        search_form = await page.query_selector('form')
        if search_form:
            print("✅ 검색 폼 발견, 기본 검색 실행...")
            search_button = await page.query_selector('input[type="submit"], button[type="submit"]')
            if search_button:
                await search_button.click()
                await page.wait_for_load_state('networkidle')
        
        # 페이지네이션 버튼 확인
        pagination_links = await page.query_selector_all('a[href*="page"], a[onclick*="page"]')
        if pagination_links:
            print(f"✅ 페이지네이션 링크 {len(pagination_links)}개 발견")
    
    async def _wait_for_dynamic_content(self, page):
        """동적 콘텐츠 로드 대기"""
        print("\n3️⃣ 동적 콘텐츠 로드 대기:")
        
        # 테이블이 나타날 때까지 대기
        try:
            await page.wait_for_selector('table, .list-container, .board-list', timeout=10000)
            print("✅ 목록 컨테이너 로드 완료")
        except:
            print("❌ 목록 컨테이너 로드 실패")
        
        # 추가 대기 시간
        await asyncio.sleep(3)
        
        # 현재 페이지의 모든 요소 다시 확인
        all_elements = await page.evaluate("""
            () => {
                const elements = document.querySelectorAll('*');
                let result = {
                    total: elements.length,
                    tables: document.querySelectorAll('table').length,
                    links: document.querySelectorAll('a').length,
                    forms: document.querySelectorAll('form').length
                };
                return result;
            }
        """)
        print(f"📋 페이지 요소: {all_elements}")
    
    async def _reanalyze_announcements(self, page):
        """공고 목록 재분석"""
        print("\n4️⃣ 공고 목록 재분석:")
        
        # 페이지 HTML 다시 가져오기
        html_content = await page.content()
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 다양한 목록 구조 찾기
        list_selectors = [
            'table',
            '.list-container',
            '.board-list',
            'ul.list',
            'div[class*="list"]',
            'tbody tr',
            'li:has(a)'
        ]
        
        found_lists = []
        for selector in list_selectors:
            elements = soup.select(selector)
            if elements:
                found_lists.append((selector, len(elements)))
                print(f"✅ {selector}: {len(elements)}개 발견")
        
        if not found_lists:
            print("❌ 목록 구조를 찾을 수 없습니다.")
            
            # 모든 텍스트 내용 검색
            all_text = soup.get_text()
            if '공고' in all_text or '사업' in all_text:
                print("✅ 페이지에 공고 관련 텍스트 발견")
                # 공고 관련 키워드 주변 텍스트 추출
                lines = all_text.split('\n')
                relevant_lines = [line.strip() for line in lines 
                                if line.strip() and ('공고' in line or '사업' in line)][:10]
                for line in relevant_lines:
                    print(f"  - {line}")
        
        # 링크 분석
        all_links = soup.find_all('a', href=True)
        detail_links = [link for link in all_links 
                       if ('Detail' in link.get('href', '') or 
                           'detail' in link.get('href', '') or
                           'view' in link.get('href', ''))]
        
        if detail_links:
            print(f"✅ 상세 페이지 링크 {len(detail_links)}개 발견:")
            for i, link in enumerate(detail_links[:5]):  # 처음 5개만
                href = link.get('href', '')
                text = link.get_text(strip=True)[:50]
                print(f"  {i+1}. {text} -> {href}")
        
        return detail_links
    
    async def _test_file_download_process(self, page):
        """파일 다운로드 프로세스 테스트"""
        print("\n5️⃣ 파일 다운로드 프로세스 테스트:")
        
        # 상세 페이지 링크 찾기
        detail_links = await page.query_selector_all('a[href*="Detail"], a[href*="detail"], a[href*="view"]')
        
        if not detail_links:
            print("❌ 상세 페이지 링크를 찾을 수 없습니다.")
            
            # JavaScript로 모든 링크 검색
            all_links = await page.evaluate("""
                () => {
                    const links = Array.from(document.querySelectorAll('a[href]'));
                    return links.map(link => ({
                        href: link.href,
                        text: link.textContent.trim(),
                        onclick: link.onclick ? link.onclick.toString() : null
                    })).filter(link => link.text.length > 0);
                }
            """)
            
            print(f"📋 페이지의 모든 링크 ({len(all_links)}개):")
            for i, link in enumerate(all_links[:10]):  # 처음 10개만
                print(f"  {i+1}. {link['text'][:50]} -> {link['href']}")
                if link['onclick']:
                    print(f"      onclick: {link['onclick'][:100]}")
            
            return
        
        print(f"✅ 상세 페이지 링크 {len(detail_links)}개 발견")
        
        # 첫 번째 상세 페이지 접근
        try:
            first_link = detail_links[0]
            link_text = await first_link.text_content()
            link_href = await first_link.get_attribute('href')
            
            print(f"🔗 첫 번째 공고 접근: {link_text}")
            print(f"📄 링크: {link_href}")
            
            # 네트워크 요청 카운트
            before_count = len(self.all_requests)
            
            await first_link.click()
            await page.wait_for_load_state('networkidle')
            
            # 새로운 네트워크 요청 분석
            new_requests = self.all_requests[before_count:]
            print(f"📊 새로운 네트워크 요청 {len(new_requests)}개:")
            for req in new_requests[-10:]:  # 마지막 10개만
                print(f"  - {req['method']} {req['url']}")
            
            # 상세 페이지에서 첨부파일 찾기
            await self._analyze_attachments_in_detail(page)
            
        except Exception as e:
            print(f"❌ 상세 페이지 접근 중 오류: {e}")
    
    async def _analyze_attachments_in_detail(self, page):
        """상세 페이지에서 첨부파일 분석"""
        print("\n📎 첨부파일 분석:")
        
        # 첨부파일 관련 요소 찾기
        attachment_selectors = [
            'a[onclick*="download"]',
            'a[href*="download"]',
            'a[onclick*="atchFile"]',
            'a[onclick*="file"]',
            '.attach a',
            '.file a',
            'a:has-text("다운로드")',
            'a:has-text("첨부")'
        ]
        
        found_attachments = []
        for selector in attachment_selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    found_attachments.extend(elements)
                    print(f"✅ {selector}: {len(elements)}개 발견")
            except:
                pass
        
        if not found_attachments:
            print("❌ 첨부파일 링크를 찾을 수 없습니다.")
            
            # 페이지 전체 텍스트에서 파일 관련 키워드 검색
            page_text = await page.text_content('body')
            file_keywords = ['첨부', '다운로드', '파일', 'hwp', 'pdf', 'doc']
            for keyword in file_keywords:
                if keyword in page_text:
                    print(f"✅ '{keyword}' 키워드 발견")
            
            return
        
        # 첨부파일 링크 상세 분석
        print(f"📎 총 {len(found_attachments)}개의 첨부파일 링크 발견:")
        
        for i, attachment in enumerate(found_attachments[:5]):  # 처음 5개만
            try:
                text = await attachment.text_content()
                href = await attachment.get_attribute('href')
                onclick = await attachment.get_attribute('onclick')
                
                print(f"  {i+1}. {text.strip()}")
                print(f"     href: {href}")
                print(f"     onclick: {onclick}")
                
                # 실제 다운로드 시도
                if i == 0:  # 첫 번째 파일만 다운로드 시도
                    await self._attempt_download(page, attachment)
                
            except Exception as e:
                print(f"     ❌ 분석 오류: {e}")
    
    async def _attempt_download(self, page, attachment):
        """실제 다운로드 시도"""
        print("\n📥 실제 다운로드 시도:")
        
        try:
            # 다운로드 이벤트 모니터링
            download_started = False
            
            async def handle_download(download):
                nonlocal download_started
                download_started = True
                print(f"✅ 다운로드 시작: {download.suggested_filename}")
                print(f"📄 다운로드 URL: {download.url}")
                
                # 다운로드 저장 (실제로는 취소)
                try:
                    await download.cancel()
                    print("✅ 다운로드 취소 (테스트 목적)")
                except:
                    pass
            
            page.on('download', handle_download)
            
            # 네트워크 요청 모니터링
            before_count = len(self.all_requests)
            
            # 링크 클릭
            await attachment.click()
            await asyncio.sleep(3)
            
            # 다운로드 후 네트워크 요청 분석
            after_count = len(self.all_requests)
            download_requests = self.all_requests[before_count:after_count]
            
            if download_requests:
                print(f"📊 다운로드 관련 네트워크 요청 {len(download_requests)}개:")
                for req in download_requests:
                    print(f"  - {req['method']} {req['url']}")
                    print(f"    Headers: {json.dumps({k: v for k, v in req['headers'].items() if k.lower() in ['referer', 'cookie', 'user-agent']}, indent=2)}")
                    if req['post_data']:
                        print(f"    POST Data: {req['post_data']}")
            
            if not download_started and not download_requests:
                print("❌ 다운로드가 시작되지 않았습니다.")
                
        except Exception as e:
            print(f"❌ 다운로드 시도 중 오류: {e}")
    
    async def _comprehensive_results_analysis(self):
        """종합 결과 분석"""
        print("\n" + "="*80)
        print("📊 IRIS 사이트 종합 분석 결과")
        print("="*80)
        
        # 1. 네트워크 요청 통계
        print(f"\n1️⃣ 네트워크 요청 통계:")
        print(f"  - 총 요청 수: {len(self.all_requests)}")
        print(f"  - 총 응답 수: {len(self.all_responses)}")
        
        # 도메인별 요청 분석
        domains = {}
        for req in self.all_requests:
            domain = req['url'].split('/')[2] if '://' in req['url'] else 'unknown'
            domains[domain] = domains.get(domain, 0) + 1
        
        print(f"  - 도메인별 요청:")
        for domain, count in sorted(domains.items(), key=lambda x: x[1], reverse=True):
            print(f"    {domain}: {count}개")
        
        # 2. IRIS 관련 요청 분석
        iris_requests = [req for req in self.all_requests if 'iris.go.kr' in req['url']]
        print(f"\n2️⃣ IRIS 관련 요청 ({len(iris_requests)}개):")
        
        for req in iris_requests:
            print(f"  - {req['method']} {req['url']}")
            if req['post_data']:
                print(f"    POST Data: {req['post_data']}")
        
        # 3. 다운로드 관련 요청
        download_requests = [req for req in self.all_requests 
                           if any(keyword in req['url'].lower() 
                                 for keyword in ['download', 'atchfile', 'file'])]
        
        if download_requests:
            print(f"\n3️⃣ 다운로드 관련 요청 ({len(download_requests)}개):")
            for req in download_requests:
                print(f"  - {req['method']} {req['url']}")
                if req['headers'].get('referer'):
                    print(f"    Referer: {req['headers']['referer']}")
        
        # 4. 쿠키 정보 (마지막 요청에서)
        if iris_requests:
            last_request = iris_requests[-1]
            cookie_header = last_request['headers'].get('cookie', '')
            if cookie_header:
                print(f"\n4️⃣ 쿠키 정보:")
                cookies = cookie_header.split('; ')
                for cookie in cookies:
                    if '=' in cookie:
                        name, value = cookie.split('=', 1)
                        if name in ['JSESSIONID', 'WMONID', 'SESSION']:
                            print(f"  - {name}: {value}")
        
        # 5. 구현 권장사항
        print(f"\n5️⃣ 스크래퍼 구현 권장사항:")
        print("  1. 세션 관리: JSESSIONID 쿠키 보존 필수")
        print("  2. User-Agent 설정: 브라우저 환경 모방")
        print("  3. Referer 헤더: 상세 페이지에서 다운로드 시 필수")
        print("  4. 페이지 로딩: 동적 콘텐츠 로딩 대기 필요")
        print("  5. 에러 처리: 네트워크 타임아웃 및 재시도 로직 구현")
        
        # 분석 결과 저장
        analysis_result = {
            'timestamp': time.time(),
            'total_requests': len(self.all_requests),
            'iris_requests': len(iris_requests),
            'download_requests': len(download_requests),
            'domains': domains,
            'sample_requests': iris_requests[:10],  # 샘플 요청
            'recommendations': [
                "세션 관리: JSESSIONID 쿠키 보존 필수",
                "User-Agent 설정: 브라우저 환경 모방",
                "Referer 헤더: 상세 페이지에서 다운로드 시 필수",
                "페이지 로딩: 동적 콘텐츠 로딩 대기 필요",
                "에러 처리: 네트워크 타임아웃 및 재시도 로직 구현"
            ]
        }
        
        with open('/tmp/iris_comprehensive_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n📁 상세 분석 결과가 /tmp/iris_comprehensive_analysis.json에 저장되었습니다.")


async def main():
    analyzer = IrisComprehensiveAnalyzer()
    await analyzer.comprehensive_analysis()


if __name__ == "__main__":
    asyncio.run(main())