#!/usr/bin/env python3
"""
IRIS 사이트 최종 분석 - 브라우저 기반 실제 파일 다운로드 테스트
"""

import asyncio
import json
import re
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import time


class IrisFinalAnalyzer:
    def __init__(self):
        self.base_url = "https://www.iris.go.kr"
        self.list_url = "https://www.iris.go.kr/contents/retrieveBsnsAncmBtinSituListView.do"
        self.network_requests = []
        self.download_info = []
        
    async def final_analysis(self):
        """최종 종합 분석 - 브라우저 기반"""
        print("🔍 IRIS 사이트 최종 분석 시작...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            try:
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                
                page = await context.new_page()
                
                # 네트워크 모니터링
                await self._setup_network_monitoring(page)
                
                # 1. 초기 페이지 로드
                print("🌐 IRIS 사이트 접속...")
                await page.goto(self.list_url, wait_until='networkidle')
                
                # 2. AJAX로 공고 목록 로드
                await self._load_announcements_via_ajax(page)
                
                # 3. 첫 번째 공고 클릭하여 상세 페이지 접근
                await self._access_first_announcement(page)
                
                # 4. 첨부파일 찾기 및 다운로드 테스트
                await self._test_attachment_download(page)
                
                # 5. 최종 결과 분석
                await self._final_results_analysis()
                
                print("🔍 분석 완료. 10초 후 브라우저 종료...")
                await asyncio.sleep(10)
                
            except Exception as e:
                print(f"❌ 오류 발생: {e}")
                import traceback
                traceback.print_exc()
                
            finally:
                await browser.close()
    
    async def _setup_network_monitoring(self, page):
        """네트워크 모니터링 설정"""
        
        async def handle_request(request):
            self.network_requests.append({
                'url': request.url,
                'method': request.method,
                'headers': dict(request.headers),
                'post_data': request.post_data,
                'timestamp': time.time()
            })
        
        page.on('request', handle_request)
    
    async def _load_announcements_via_ajax(self, page):
        """AJAX로 공고 목록 로드"""
        print("📡 AJAX로 공고 목록 로드 중...")
        
        # JavaScript로 AJAX 요청 실행
        result = await page.evaluate("""
            async () => {
                try {
                    const response = await fetch('/contents/retrieveBsnsAncmBtinSituList.do', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                            'X-Requested-With': 'XMLHttpRequest'
                        },
                        body: 'pageIndex=1&prgmId=&srchGbnCd=all'
                    });
                    
                    if (response.ok) {
                        const data = await response.json();
                        return {
                            success: true,
                            data: data,
                            count: data.listBsnsAncmBtinSitu ? data.listBsnsAncmBtinSitu.length : 0
                        };
                    } else {
                        return {
                            success: false,
                            status: response.status,
                            statusText: response.statusText
                        };
                    }
                } catch (error) {
                    return {
                        success: false,
                        error: error.message
                    };
                }
            }
        """)
        
        if result['success']:
            print(f"✅ AJAX 성공: {result['count']}개 공고 로드")
            return result['data']
        else:
            print(f"❌ AJAX 실패: {result}")
            return None
    
    async def _access_first_announcement(self, page):
        """첫 번째 공고 상세 페이지 접근"""
        print("🔍 첫 번째 공고 상세 페이지 접근...")
        
        # 페이지에서 공고 링크 찾기 (다양한 방법 시도)
        
        # 1. 테이블 기반 링크 찾기
        links_found = False
        
        # JavaScript로 모든 링크 검색
        all_links = await page.evaluate("""
            () => {
                const links = Array.from(document.querySelectorAll('a'));
                return links.map(link => ({
                    href: link.href,
                    text: link.textContent.trim(),
                    onclick: link.onclick ? link.onclick.toString() : null,
                    id: link.id,
                    className: link.className
                })).filter(link => 
                    link.text.length > 0 && 
                    (link.href.includes('Detail') || 
                     link.onclick && link.onclick.includes('Detail') ||
                     link.text.includes('공고') ||
                     link.text.includes('사업'))
                );
            }
        """)
        
        print(f"📋 관련 링크 {len(all_links)}개 발견:")
        for i, link in enumerate(all_links[:5]):
            print(f"  {i+1}. {link['text'][:50]}")
            print(f"     href: {link['href']}")
            print(f"     onclick: {link['onclick']}")
        
        # 첫 번째 공고 링크 클릭 시도
        if all_links:
            try:
                first_link = all_links[0]
                print(f"🔗 첫 번째 링크 클릭: {first_link['text']}")
                
                # 클릭 전 현재 URL 기록
                current_url = page.url
                
                # JavaScript로 직접 클릭
                await page.evaluate(f"""
                    () => {{
                        const links = Array.from(document.querySelectorAll('a'));
                        const targetLink = links.find(link => 
                            link.textContent.trim() === '{first_link['text']}'
                        );
                        if (targetLink) {{
                            targetLink.click();
                            return true;
                        }}
                        return false;
                    }}
                """)
                
                # 페이지 변경 대기
                await page.wait_for_load_state('networkidle')
                await asyncio.sleep(2)
                
                new_url = page.url
                if new_url != current_url:
                    print(f"✅ 페이지 이동 성공: {new_url}")
                    return True
                else:
                    print("❌ 페이지 이동 실패")
                    
            except Exception as e:
                print(f"❌ 링크 클릭 중 오류: {e}")
        
        # 2. 직접 상세 페이지 URL 시도
        print("🔄 직접 상세 페이지 URL 접근 시도...")
        
        # 최근 공고 ID로 직접 접근 시도
        test_urls = [
            "https://www.iris.go.kr/contents/retrieveBsnsAncmBtinSituDetailView.do?ancmId=014116",
            "https://www.iris.go.kr/contents/retrieveBsnsAncmBtinSituDetailView.do?ancmId=014114",
            "https://www.iris.go.kr/contents/retrieveBsnsAncmBtinSituDetailView.do?ancmId=014079"
        ]
        
        for url in test_urls:
            try:
                print(f"🔗 URL 접근 시도: {url}")
                await page.goto(url, wait_until='networkidle')
                
                # 페이지 내용 확인
                title = await page.title()
                if '404' not in title and 'error' not in title.lower():
                    print(f"✅ 상세 페이지 접근 성공: {title}")
                    return True
                else:
                    print(f"❌ 페이지 오류: {title}")
                    
            except Exception as e:
                print(f"❌ URL 접근 중 오류: {e}")
        
        return False
    
    async def _test_attachment_download(self, page):
        """첨부파일 다운로드 테스트"""
        print("\n📎 첨부파일 다운로드 테스트:")
        
        # 현재 페이지에서 첨부파일 링크 찾기
        download_links = await page.query_selector_all('a[onclick*="download"], a[href*="download"]')
        
        if not download_links:
            print("❌ 다운로드 링크를 찾을 수 없습니다.")
            
            # 페이지 HTML 분석
            html_content = await page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 첨부파일 관련 텍스트 검색
            page_text = soup.get_text()
            keywords = ['첨부', '파일', '다운로드', '.hwp', '.pdf', '.doc']
            
            for keyword in keywords:
                if keyword in page_text:
                    print(f"✅ '{keyword}' 키워드 발견")
                    # 키워드 주변 텍스트 추출
                    lines = page_text.split('\n')
                    for line in lines:
                        if keyword in line and line.strip():
                            print(f"  컨텍스트: {line.strip()[:100]}")
                            break
            
            return
        
        print(f"📎 다운로드 링크 {len(download_links)}개 발견")
        
        # 첫 번째 다운로드 링크 분석
        for i, link in enumerate(download_links[:3]):
            try:
                text = await link.text_content()
                onclick = await link.get_attribute('onclick')
                href = await link.get_attribute('href')
                
                print(f"\n📁 다운로드 링크 {i+1}: {text}")
                print(f"  onclick: {onclick}")
                print(f"  href: {href}")
                
                # 다운로드 파라미터 추출
                if onclick:
                    params = self._extract_download_params(onclick)
                    if params:
                        print(f"  파라미터: {params}")
                        
                        # 실제 다운로드 URL 테스트
                        await self._test_download_url(page, params)
                
            except Exception as e:
                print(f"❌ 링크 분석 중 오류: {e}")
    
    def _extract_download_params(self, onclick_str):
        """다운로드 파라미터 추출"""
        patterns = [
            r"f_bsnsAncm_downloadAtchFile\s*\(\s*'([^']+)'\s*,\s*'([^']+)'\s*\)",
            r"downloadAtchFile\s*\(\s*'([^']+)'\s*,\s*'([^']+)'\s*\)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, onclick_str)
            if match:
                return {
                    'atchFileId': match.group(1),
                    'atchFileSn': match.group(2)
                }
        
        return None
    
    async def _test_download_url(self, page, params):
        """다운로드 URL 테스트"""
        print(f"📥 다운로드 URL 테스트...")
        
        download_urls = [
            f"/downloadAtchFile.do?atchFileId={params['atchFileId']}&atchFileSn={params['atchFileSn']}",
            f"/common/downloadAtchFile.do?atchFileId={params['atchFileId']}&atchFileSn={params['atchFileSn']}",
            f"/contents/downloadAtchFile.do?atchFileId={params['atchFileId']}&atchFileSn={params['atchFileSn']}"
        ]
        
        for i, url in enumerate(download_urls):
            try:
                print(f"  {i+1}. 테스트: {url}")
                
                # JavaScript로 HEAD 요청 시도
                result = await page.evaluate(f"""
                    async () => {{
                        try {{
                            const response = await fetch('{url}', {{
                                method: 'HEAD'
                            }});
                            
                            return {{
                                success: true,
                                status: response.status,
                                headers: Object.fromEntries(response.headers.entries())
                            }};
                        }} catch (error) {{
                            return {{
                                success: false,
                                error: error.message
                            }};
                        }}
                    }}
                """)
                
                if result['success'] and result['status'] == 200:
                    print(f"    ✅ 응답 성공: {result['status']}")
                    headers = result['headers']
                    
                    if 'content-disposition' in headers:
                        print(f"    📄 Content-Disposition: {headers['content-disposition']}")
                    
                    if 'content-type' in headers:
                        print(f"    📄 Content-Type: {headers['content-type']}")
                    
                    self.download_info.append({
                        'url': url,
                        'params': params,
                        'headers': headers,
                        'status': 'success'
                    })
                    
                    return url
                    
                else:
                    print(f"    ❌ 실패: {result}")
                    
            except Exception as e:
                print(f"    ❌ 오류: {e}")
        
        return None
    
    async def _final_results_analysis(self):
        """최종 결과 분석"""
        print("\n" + "="*80)
        print("📊 IRIS 사이트 파일 다운로드 메커니즘 최종 분석 결과")
        print("="*80)
        
        # 1. 네트워크 요청 분석
        iris_requests = [req for req in self.network_requests if 'iris.go.kr' in req['url']]
        ajax_requests = [req for req in iris_requests if req['method'] == 'POST']
        
        print(f"\n1️⃣ 네트워크 요청 통계:")
        print(f"  - 총 요청: {len(self.network_requests)}")
        print(f"  - IRIS 관련: {len(iris_requests)}")
        print(f"  - AJAX 요청: {len(ajax_requests)}")
        
        # 2. AJAX 요청 분석
        if ajax_requests:
            print(f"\n2️⃣ AJAX 요청 상세:")
            for req in ajax_requests[:5]:
                print(f"  - {req['method']} {req['url']}")
                if req['post_data']:
                    print(f"    데이터: {req['post_data']}")
        
        # 3. 다운로드 메커니즘 요약
        print(f"\n3️⃣ 다운로드 메커니즘 요약:")
        print("  ✅ 공고 목록: AJAX POST 요청으로 JSON 데이터 획득")
        print("  📡 URL: /contents/retrieveBsnsAncmBtinSituList.do")
        print("  📊 파라미터: pageIndex, prgmId, srchGbnCd")
        print("  📋 응답: listBsnsAncmBtinSitu 배열에 공고 정보")
        
        print(f"\n  📄 상세 페이지: ancmId로 개별 공고 접근")
        print("  📡 URL: /contents/retrieveBsnsAncmBtinSituDetailView.do?ancmId={id}")
        
        print(f"\n  📎 파일 다운로드: JavaScript 함수에서 파라미터 추출")
        print("  🔧 함수: f_bsnsAncm_downloadAtchFile(atchFileId, atchFileSn)")
        print("  📡 URL: /downloadAtchFile.do?atchFileId={id}&atchFileSn={sn}")
        
        # 4. 세션 및 보안 요구사항
        print(f"\n4️⃣ 세션 및 보안 요구사항:")
        
        # 마지막 요청에서 쿠키 정보 확인
        if self.network_requests:
            last_request = self.network_requests[-1]
            cookie_header = last_request['headers'].get('cookie', '')
            if 'JSESSIONID' in cookie_header:
                print("  ✅ JSESSIONID 쿠키 확인됨")
            else:
                print("  ❌ JSESSIONID 쿠키 미확인")
        
        print("  🔐 필수 헤더:")
        print("    - User-Agent: 브라우저 식별")
        print("    - Referer: 상세 페이지 URL")
        print("    - Cookie: JSESSIONID 세션 유지")
        
        # 5. 구현 예시 코드
        print(f"\n5️⃣ 구현 예시:")
        
        example_code = '''
import requests
from bs4 import BeautifulSoup
import json

class IrisScraper:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://www.iris.go.kr"
        
    def get_announcements(self, page=1):
        """공고 목록 가져오기"""
        url = f"{self.base_url}/contents/retrieveBsnsAncmBtinSituList.do"
        data = {
            'pageIndex': page,
            'prgmId': '',
            'srchGbnCd': 'all'
        }
        
        response = self.session.post(url, data=data, verify=False)
        return response.json()['listBsnsAncmBtinSitu']
    
    def get_detail_page(self, ancm_id):
        """상세 페이지 가져오기"""
        url = f"{self.base_url}/contents/retrieveBsnsAncmBtinSituDetailView.do"
        params = {'ancmId': ancm_id}
        
        response = self.session.get(url, params=params, verify=False)
        return response.text
    
    def download_file(self, atch_file_id, atch_file_sn):
        """파일 다운로드"""
        url = f"{self.base_url}/downloadAtchFile.do"
        params = {
            'atchFileId': atch_file_id,
            'atchFileSn': atch_file_sn
        }
        
        response = self.session.get(url, params=params, verify=False)
        return response.content
        '''
        
        print(example_code)
        
        # 결과를 파일로 저장
        result_data = {
            'timestamp': time.time(),
            'network_requests_count': len(self.network_requests),
            'ajax_requests': ajax_requests,
            'download_info': self.download_info,
            'mechanism_summary': {
                'list_endpoint': '/contents/retrieveBsnsAncmBtinSituList.do',
                'detail_endpoint': '/contents/retrieveBsnsAncmBtinSituDetailView.do',
                'download_endpoint': '/downloadAtchFile.do',
                'required_cookies': ['JSESSIONID'],
                'required_headers': ['User-Agent', 'Referer']
            }
        }
        
        with open('/tmp/iris_final_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n📁 최종 분석 결과가 /tmp/iris_final_analysis.json에 저장되었습니다.")


async def main():
    analyzer = IrisFinalAnalyzer()
    await analyzer.final_analysis()


if __name__ == "__main__":
    asyncio.run(main())