#!/usr/bin/env python3
"""
IRIS 사이트 AJAX 요청 테스트 및 실제 공고 데이터 분석
"""

import requests
import json
from bs4 import BeautifulSoup
import asyncio
from playwright.async_api import async_playwright


class IrisAjaxTester:
    def __init__(self):
        self.base_url = "https://www.iris.go.kr"
        self.list_url = "https://www.iris.go.kr/contents/retrieveBsnsAncmBtinSituListView.do"
        self.ajax_url = "https://www.iris.go.kr/contents/retrieveBsnsAncmBtinSituList.do"
        self.session = requests.Session()
        
        # 기본 헤더 설정
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
        })
    
    async def test_ajax_requests(self):
        """AJAX 요청 테스트"""
        print("🔍 IRIS AJAX 요청 테스트 시작...")
        
        # 1. 브라우저로 세션 설정
        session_info = await self._get_session_with_browser()
        
        # 2. 세션 정보로 AJAX 요청
        if session_info:
            await self._test_ajax_with_session(session_info)
        
        # 3. 직접 AJAX 요청 시도
        await self._test_direct_ajax()
    
    async def _get_session_with_browser(self):
        """브라우저로 세션 정보 획득"""
        print("🌐 브라우저로 세션 정보 획득 중...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            try:
                context = await browser.new_context()
                page = await context.new_page()
                
                # 초기 페이지 로드
                await page.goto(self.list_url)
                await page.wait_for_load_state('networkidle')
                
                # 쿠키 및 세션 정보 수집
                cookies = await context.cookies()
                
                # 세션 ID 찾기
                jsessionid = None
                for cookie in cookies:
                    if cookie['name'] == 'JSESSIONID':
                        jsessionid = cookie['value']
                        break
                
                print(f"✅ JSESSIONID: {jsessionid}")
                
                # 페이지에서 필요한 파라미터 추출
                form_data = await page.evaluate("""
                    () => {
                        const form = document.getElementById('bsnsAncmBtinSituListForm');
                        if (form) {
                            const formData = new FormData(form);
                            const result = {};
                            for (let [key, value] of formData.entries()) {
                                result[key] = value;
                            }
                            return result;
                        }
                        return {};
                    }
                """)
                
                return {
                    'jsessionid': jsessionid,
                    'cookies': cookies,
                    'form_data': form_data
                }
                
            finally:
                await browser.close()
    
    async def _test_ajax_with_session(self, session_info):
        """세션 정보를 사용한 AJAX 요청 테스트"""
        print("\n📡 세션 정보를 사용한 AJAX 요청 테스트:")
        
        # 쿠키 설정
        cookie_header = '; '.join([f"{cookie['name']}={cookie['value']}" for cookie in session_info['cookies']])
        
        headers = {
            'Cookie': cookie_header,
            'Referer': self.list_url,
            'Origin': self.base_url
        }
        
        # AJAX 요청 데이터 준비
        ajax_data = {
            'pageIndex': '1',
            'prgmId': '',
            'ancmSttArr': '',
            'pbofrTpArr': '',
            'blngGovdSeArr': '',
            'sorgnIdArr': '',
            'qualCndtArr': '',
            'techFildArr': '',
            'bsnsTl': '',
            'sorgnNm': '',
            'srchGbnCd': 'all'
        }
        
        # 기존 폼 데이터와 병합
        ajax_data.update(session_info['form_data'])
        
        try:
            response = requests.post(
                self.ajax_url,
                data=ajax_data,
                headers={**self.session.headers, **headers},
                verify=False,
                timeout=30
            )
            
            print(f"📊 응답 상태: {response.status_code}")
            print(f"📊 응답 헤더: {dict(response.headers)}")
            
            if response.status_code == 200:
                try:
                    json_data = response.json()
                    print("✅ JSON 응답 성공!")
                    
                    # 공고 목록 데이터 분석
                    await self._analyze_announcement_data(json_data)
                    
                    return json_data
                    
                except json.JSONDecodeError:
                    print("❌ JSON 파싱 실패")
                    print(f"응답 내용 (처음 500자): {response.text[:500]}")
            else:
                print(f"❌ 요청 실패: {response.status_code}")
                print(f"응답 내용: {response.text[:500]}")
                
        except Exception as e:
            print(f"❌ AJAX 요청 중 오류: {e}")
    
    async def _test_direct_ajax(self):
        """직접 AJAX 요청 테스트"""
        print("\n📡 직접 AJAX 요청 테스트:")
        
        # 간단한 AJAX 요청 데이터
        simple_data = {
            'pageIndex': '1',
            'prgmId': '',
            'srchGbnCd': 'all'
        }
        
        try:
            response = requests.post(
                self.ajax_url,
                data=simple_data,
                verify=False,
                timeout=30
            )
            
            print(f"📊 응답 상태: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    json_data = response.json()
                    print("✅ 직접 AJAX 요청 성공!")
                    await self._analyze_announcement_data(json_data)
                    
                except json.JSONDecodeError:
                    print("❌ JSON 파싱 실패")
                    print(f"응답 내용 (처음 1000자): {response.text[:1000]}")
            else:
                print(f"❌ 직접 요청 실패: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 직접 AJAX 요청 중 오류: {e}")
    
    async def _analyze_announcement_data(self, json_data):
        """공고 데이터 분석"""
        print("\n📋 공고 데이터 분석:")
        
        # JSON 구조 분석
        print(f"📊 JSON 키: {list(json_data.keys())}")
        
        # 페이지네이션 정보
        if 'paginationInfo' in json_data:
            page_info = json_data['paginationInfo']
            print(f"📄 페이지 정보:")
            print(f"  - 현재 페이지: {page_info.get('currentPageNo', 'N/A')}")
            print(f"  - 전체 페이지: {page_info.get('totalPageCount', 'N/A')}")
            print(f"  - 전체 게시물: {page_info.get('totalRecordCount', 'N/A')}")
        
        # 공고 목록 데이터
        if 'resultList' in json_data:
            announcements = json_data['resultList']
            print(f"📋 공고 수: {len(announcements)}")
            
            if announcements:
                print("\n✅ 첫 3개 공고 정보:")
                for i, announcement in enumerate(announcements[:3]):
                    print(f"  {i+1}. 공고:")
                    for key, value in announcement.items():
                        if isinstance(value, str) and len(value) > 100:
                            print(f"     {key}: {value[:100]}...")
                        else:
                            print(f"     {key}: {value}")
                    print()
                
                # 첫 번째 공고의 상세 페이지 접근 시도
                await self._test_detail_page_access(announcements[0])
        
        else:
            print("❌ 공고 목록을 찾을 수 없습니다.")
            print(f"📊 전체 JSON 구조: {json.dumps(json_data, indent=2, ensure_ascii=False)[:1000]}")
    
    async def _test_detail_page_access(self, announcement):
        """상세 페이지 접근 테스트"""
        print("\n🔍 상세 페이지 접근 테스트:")
        
        # 공고 ID나 키 값 찾기
        announcement_keys = ['ancmId', 'prgmId', 'id', 'ancmNo', 'bsnsAncmId']
        announcement_id = None
        
        for key in announcement_keys:
            if key in announcement:
                announcement_id = announcement[key]
                print(f"✅ 공고 ID 발견: {key} = {announcement_id}")
                break
        
        if not announcement_id:
            print("❌ 공고 ID를 찾을 수 없습니다.")
            print(f"사용 가능한 키: {list(announcement.keys())}")
            return
        
        # 상세 페이지 URL 구성 시도
        detail_urls = [
            f"{self.base_url}/contents/retrieveBsnsAncmBtinSituDetailView.do?ancmId={announcement_id}",
            f"{self.base_url}/contents/retrieveBsnsAncmBtinSituDetailView.do?prgmId={announcement_id}",
            f"{self.base_url}/contents/retrieveBsnsAncmBtinSituDetailView.do?id={announcement_id}"
        ]
        
        for detail_url in detail_urls:
            try:
                print(f"🔗 상세 페이지 접근 시도: {detail_url}")
                response = requests.get(detail_url, verify=False, timeout=30)
                
                if response.status_code == 200:
                    print("✅ 상세 페이지 접근 성공!")
                    
                    # 첨부파일 링크 찾기
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 다운로드 링크 찾기
                    download_links = soup.find_all('a', onclick=lambda x: x and 'download' in x.lower())
                    if not download_links:
                        download_links = soup.find_all('a', href=lambda x: x and 'download' in x.lower())
                    
                    if download_links:
                        print(f"📎 첨부파일 {len(download_links)}개 발견:")
                        for i, link in enumerate(download_links):
                            text = link.get_text(strip=True)
                            onclick = link.get('onclick', '')
                            href = link.get('href', '')
                            print(f"  {i+1}. {text}")
                            print(f"     onclick: {onclick}")
                            print(f"     href: {href}")
                            
                            # 다운로드 함수 파라미터 추출
                            if onclick:
                                await self._extract_download_params(onclick)
                    else:
                        print("❌ 첨부파일 링크를 찾을 수 없습니다.")
                    
                    break
                    
                else:
                    print(f"❌ 접근 실패: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ 상세 페이지 접근 중 오류: {e}")
    
    async def _extract_download_params(self, onclick_str):
        """다운로드 함수 파라미터 추출"""
        print(f"\n🔧 다운로드 함수 분석: {onclick_str}")
        
        # JavaScript 함수 호출에서 파라미터 추출
        import re
        
        # f_bsnsAncm_downloadAtchFile('param1', 'param2') 패턴
        pattern = r"f_bsnsAncm_downloadAtchFile\s*\(\s*'([^']+)'\s*,\s*'([^']+)'\s*\)"
        match = re.search(pattern, onclick_str)
        
        if match:
            param1, param2 = match.groups()
            print(f"✅ 다운로드 파라미터 추출:")
            print(f"  - 파라미터 1: {param1}")
            print(f"  - 파라미터 2: {param2}")
            
            # 다운로드 URL 구성 시도
            download_urls = [
                f"{self.base_url}/downloadAtchFile.do?atchFileId={param1}&atchFileSn={param2}",
                f"{self.base_url}/contents/downloadAtchFile.do?atchFileId={param1}&atchFileSn={param2}",
                f"{self.base_url}/common/downloadAtchFile.do?atchFileId={param1}&atchFileSn={param2}"
            ]
            
            for url in download_urls:
                print(f"🔗 다운로드 URL 시도: {url}")
                # 실제 다운로드는 하지 않고 헤더만 확인
                try:
                    response = requests.head(url, verify=False, timeout=10)
                    print(f"  응답 코드: {response.status_code}")
                    if response.status_code == 200:
                        content_disposition = response.headers.get('Content-Disposition', '')
                        if content_disposition:
                            print(f"  파일명: {content_disposition}")
                        print("✅ 다운로드 URL 확인됨!")
                        return url
                except Exception as e:
                    print(f"  ❌ 오류: {e}")
        
        return None


async def main():
    tester = IrisAjaxTester()
    await tester.test_ajax_requests()


if __name__ == "__main__":
    asyncio.run(main())