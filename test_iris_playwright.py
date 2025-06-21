#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IRIS 파일 다운로드 Playwright 분석
실제 브라우저에서 다운로드가 어떻게 이루어지는지 확인
"""

import time
import os
from playwright.sync_api import sync_playwright

def test_iris_download_with_playwright():
    """IRIS 파일 다운로드 실제 브라우저 테스트"""
    
    with sync_playwright() as p:
        # 브라우저 실행
        browser = p.chromium.launch(headless=False, slow_mo=1000)
        context = browser.new_context()
        
        # 네트워크 모니터링 설정
        page = context.new_page()
        
        requests = []
        responses = []
        
        # 네트워크 이벤트 리스너
        def on_request(request):
            if 'download' in request.url.lower() or 'atchFile' in request.url:
                print(f"📤 요청: {request.method} {request.url}")
                print(f"   헤더: {request.headers}")
                requests.append({
                    'method': request.method,
                    'url': request.url,
                    'headers': dict(request.headers)
                })
        
        def on_response(response):
            if 'download' in response.url.lower() or 'atchFile' in response.url:
                print(f"📥 응답: {response.status} {response.url}")
                print(f"   헤더: {response.headers}")
                print(f"   Content-Type: {response.headers.get('content-type', 'unknown')}")
                responses.append({
                    'status': response.status,
                    'url': response.url,
                    'headers': dict(response.headers)
                })
        
        page.on('request', on_request)
        page.on('response', on_response)
        
        try:
            print("1. IRIS 메인 페이지 접속...")
            page.goto('https://www.iris.go.kr', timeout=30000)
            time.sleep(2)
            
            print("2. 공고 목록 페이지 접속...")
            page.goto('https://www.iris.go.kr/contents/retrieveBsnsAncmBtinSituListView.do', timeout=30000)
            time.sleep(3)
            
            print("3. 특정 공고 직접 접속...")
            # 알려진 공고 ID로 직접 접속
            page.goto('https://www.iris.go.kr/contents/retrieveBsnsAncmView.do', timeout=30000)
            
            # POST 데이터를 JavaScript로 전송
            page.evaluate("""
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = '/contents/retrieveBsnsAncmView.do';
                
                const ancmId = document.createElement('input');
                ancmId.type = 'hidden';
                ancmId.name = 'ancmId';
                ancmId.value = '014116';
                form.appendChild(ancmId);
                
                const pageIndex = document.createElement('input');
                pageIndex.type = 'hidden';
                pageIndex.name = 'pageIndex';
                pageIndex.value = '1';
                form.appendChild(pageIndex);
                
                document.body.appendChild(form);
                form.submit();
            """)
            time.sleep(5)
            
            print("4. 첨부파일 찾기...")
            # 첨부파일 링크 찾기
            download_links = page.locator('a[onclick*="downloadAtchFile"], a[onclick*="f_bsnsAncm_downloadAtchFile"]')
            
            if download_links.count() > 0:
                print(f"   {download_links.count()}개 다운로드 링크 발견")
                
                for i in range(min(3, download_links.count())):  # 처음 3개만 테스트
                    try:
                        link = download_links.nth(i)
                        onclick = link.get_attribute('onclick')
                        text = link.text_content()
                        
                        print(f"\n5.{i+1} 파일 다운로드 시도: {text}")
                        print(f"     onclick: {onclick}")
                        
                        # 다운로드 시작
                        with page.expect_download(timeout=10000) as download_info:
                            link.click()
                        
                        download = download_info.value
                        print(f"     다운로드 성공!")
                        print(f"     파일명: {download.suggested_filename}")
                        print(f"     경로: {download.path()}")
                        
                        # 임시 파일로 저장
                        temp_path = f"/tmp/iris_test_{i+1}_{download.suggested_filename}"
                        download.save_as(temp_path)
                        
                        if os.path.exists(temp_path):
                            file_size = os.path.getsize(temp_path)
                            print(f"     저장됨: {temp_path} ({file_size:,} bytes)")
                        
                    except Exception as e:
                        print(f"     다운로드 실패: {e}")
                        continue
                    
                    time.sleep(2)
            else:
                print("   첨부파일 링크를 찾을 수 없음")
                
        except Exception as e:
            print(f"오류 발생: {e}")
        
        finally:
            print("\n=== 수집된 네트워크 정보 ===")
            print(f"총 {len(requests)}개 다운로드 요청:")
            for req in requests:
                print(f"  {req['method']} {req['url']}")
            
            print(f"\n총 {len(responses)}개 다운로드 응답:")
            for resp in responses:
                print(f"  {resp['status']} {resp['url']}")
                print(f"    Content-Type: {resp['headers'].get('content-type', 'unknown')}")
            
            print("\n브라우저를 10초 후 종료합니다...")
            time.sleep(10)
            browser.close()

if __name__ == "__main__":
    test_iris_download_with_playwright()