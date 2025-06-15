#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SMTECH 파일 다운로드 전용 테스트
"""

import requests
from bs4 import BeautifulSoup
import os
import re
from urllib.parse import unquote
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_smtech_download():
    """SMTECH 파일 다운로드 직접 테스트"""
    
    # SSL 경고 무시
    import urllib3
    urllib3.disable_warnings()
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
    })
    
    base_url = "https://www.smtech.go.kr"
    
    # 1. 첫 번째 공고 상세 페이지 가져오기
    detail_url = "https://www.smtech.go.kr/front/ifg/no/notice02_detail.do?buclYy=&ancmId=S02808&buclCd=S9111&dtlAncmSn=1&schdSe=MO5005&aplySn=1&searchCondition=&searchKeyword=&pageIndex=1"
    
    print("1. 상세 페이지 접근 중...")
    response = session.get(detail_url, verify=False)
    print(f"응답 상태: {response.status_code}")
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 2. 첨부파일 링크 찾기
        print("\n2. 첨부파일 링크 검색 중...")
        js_links = soup.find_all('a', href=lambda x: x and 'cfn_AtchFileDownload' in str(x))
        
        for i, link in enumerate(js_links, 1):
            href = link.get('href', '')
            text = link.get_text().strip()
            print(f"  {i}. {text}")
            print(f"     JavaScript: {href}")
            
            # 파일 ID 추출
            match = re.search(r"cfn_AtchFileDownload\s*\(\s*['\"]([^'\"]+)['\"]", href)
            if match:
                file_id = match.group(1)
                print(f"     파일 ID: {file_id}")
                
                # 3. 파일 다운로드 시도
                print(f"\n3. 파일 다운로드 시도: {text}")
                
                download_endpoints = [
                    "/front/comn/AtchFileDownload.do",
                    "/front/comn/fileDownload.do",
                    "/comn/AtchFileDownload.do",
                    "/front/fileDownload.do"
                ]
                
                success = False
                for endpoint in download_endpoints:
                    print(f"\n   시도: {endpoint}")
                    
                    # GET 방식
                    try:
                        get_url = f"{base_url}{endpoint}?atchFileId={file_id}"
                        print(f"   GET: {get_url}")
                        
                        dl_response = session.get(get_url, verify=False, stream=True)
                        print(f"   응답 상태: {dl_response.status_code}")
                        print(f"   Content-Type: {dl_response.headers.get('Content-Type', 'N/A')}")
                        print(f"   Content-Disposition: {dl_response.headers.get('Content-Disposition', 'N/A')}")
                        
                        if dl_response.status_code == 200:
                            content_type = dl_response.headers.get('Content-Type', '')
                            content_disp = dl_response.headers.get('Content-Disposition', '')
                            
                            if ('application' in content_type or 'attachment' in content_disp):
                                # 파일명 추출
                                filename = extract_filename(dl_response, text)
                                
                                # 파일 저장
                                save_dir = "./test_downloads"
                                os.makedirs(save_dir, exist_ok=True)
                                save_path = os.path.join(save_dir, filename)
                                
                                with open(save_path, 'wb') as f:
                                    for chunk in dl_response.iter_content(chunk_size=8192):
                                        if chunk:
                                            f.write(chunk)
                                
                                file_size = os.path.getsize(save_path)
                                print(f"   ✓ 다운로드 성공: {save_path} ({file_size:,} bytes)")
                                success = True
                                break
                            else:
                                print(f"   × HTML 응답 (파일이 아님)")
                                # HTML 응답 내용 일부 출력
                                content_preview = dl_response.text[:200]
                                print(f"   응답 내용: {content_preview}...")
                        
                    except Exception as e:
                        print(f"   GET 오류: {e}")
                    
                    # POST 방식
                    try:
                        post_url = f"{base_url}{endpoint}"
                        print(f"   POST: {post_url}")
                        
                        dl_response = session.post(post_url, data={'atchFileId': file_id}, verify=False, stream=True)
                        print(f"   응답 상태: {dl_response.status_code}")
                        print(f"   Content-Type: {dl_response.headers.get('Content-Type', 'N/A')}")
                        print(f"   Content-Disposition: {dl_response.headers.get('Content-Disposition', 'N/A')}")
                        
                        if dl_response.status_code == 200:
                            content_type = dl_response.headers.get('Content-Type', '')
                            content_disp = dl_response.headers.get('Content-Disposition', '')
                            
                            if ('application' in content_type or 'attachment' in content_disp):
                                # 파일명 추출
                                filename = extract_filename(dl_response, text)
                                
                                # 파일 저장
                                save_dir = "./test_downloads"
                                os.makedirs(save_dir, exist_ok=True)
                                save_path = os.path.join(save_dir, filename)
                                
                                with open(save_path, 'wb') as f:
                                    for chunk in dl_response.iter_content(chunk_size=8192):
                                        if chunk:
                                            f.write(chunk)
                                
                                file_size = os.path.getsize(save_path)
                                print(f"   ✓ 다운로드 성공: {save_path} ({file_size:,} bytes)")
                                success = True
                                break
                            else:
                                print(f"   × HTML 응답 (파일이 아님)")
                        
                    except Exception as e:
                        print(f"   POST 오류: {e}")
                
                if success:
                    print(f"\n✓ 파일 다운로드 성공!")
                    break
                else:
                    print(f"\n× 모든 방식 실패")
                
                # 첫 번째 파일만 테스트
                break
    else:
        print(f"상세 페이지 접근 실패: {response.status_code}")

def extract_filename(response, default_name):
    """Content-Disposition에서 파일명 추출"""
    content_disposition = response.headers.get('content-disposition', '')
    
    if content_disposition:
        filename_match = re.search(r'filename=([^;]+)', content_disposition)
        if filename_match:
            filename = filename_match.group(1).strip().strip('"')
            try:
                decoded = unquote(filename)
                if decoded and not decoded.isspace():
                    return sanitize_filename(decoded)
            except:
                pass
    
    return sanitize_filename(default_name)

def sanitize_filename(filename):
    """파일명 정리"""
    # 윈도우에서 사용할 수 없는 문자들 제거
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename.strip()

if __name__ == "__main__":
    test_smtech_download()