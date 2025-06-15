#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DJBEA 첨부파일 구조 상세 분석
"""

import os
import sys
import requests
from urllib3.exceptions import InsecureRequestWarning
import logging
from bs4 import BeautifulSoup
import re
import json

# SSL 경고 비활성화
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 현재 디렉토리를 Python path에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_djbea_scraper import EnhancedDJBEAScraper

def analyze_djbea_attachments():
    """DJBEA 첨부파일 구조 상세 분석"""
    scraper = EnhancedDJBEAScraper()
    
    # 여러 공고 분석
    test_urls = [
        "https://www.djbea.or.kr/pms/st/st_0205/view_new?BBSCTT_SEQ=7952&BBSCTT_TY_CD=ST_0205",  # 로컬상품 개발
        "https://www.djbea.or.kr/pms/st/st_0205/view_new?BBSCTT_SEQ=7940&BBSCTT_TY_CD=ST_0205",  # 공공연구성과
        "https://www.djbea.or.kr/pms/st/st_0205/view_new?BBSCTT_SEQ=7938&BBSCTT_TY_CD=ST_0205",  # 해외조달시장
    ]
    
    for i, url in enumerate(test_urls):
        print(f"\n{'='*80}")
        print(f"Analyzing announcement {i+1}: {url}")
        print("-" * 80)
        
        try:
            # 페이지 가져오기
            response = scraper.get_page(url)
            if not response:
                print("Failed to get page")
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1. A2mUpload 스크립트 분석
            print("1. A2mUpload 분석:")
            file_group_id = None
            scripts = soup.find_all('script')
            for script in scripts:
                script_text = script.string if script.string else ""
                if 'A2mUpload' in script_text:
                    print(f"   - A2mUpload 스크립트 발견")
                    # targetAtchFileId 추출
                    match = re.search(r'targetAtchFileId\s*:\s*[\'"]([^\'"]+)[\'"]', script_text)
                    if match:
                        file_group_id = match.group(1)
                        print(f"   - targetAtchFileId: {file_group_id}")
                        break
                    else:
                        print(f"   - A2mUpload 있지만 targetAtchFileId 없음")
            
            if not file_group_id:
                print("   - A2mUpload 스크립트 없음")
            
            # 2. A2mUpload API 호출 테스트
            if file_group_id:
                print("2. A2mUpload API 테스트:")
                try:
                    file_list_url = f"{scraper.base_url}/pms/dextfile/common-fileList.do"
                    data = {'targetAtchFileId': file_group_id}
                    
                    api_response = scraper.session.post(file_list_url, data=data, verify=scraper.verify_ssl, timeout=10)
                    print(f"   - API Status: {api_response.status_code}")
                    print(f"   - API Response: {api_response.text[:200]}...")
                    
                    if api_response.status_code == 200:
                        try:
                            files_data = json.loads(api_response.text)
                            print(f"   - JSON 파싱 성공: {len(files_data) if isinstance(files_data, list) else 'Not a list'}")
                            if isinstance(files_data, list):
                                for j, file_info in enumerate(files_data):
                                    print(f"     File {j+1}: {file_info}")
                        except json.JSONDecodeError as e:
                            print(f"   - JSON 파싱 실패: {e}")
                except Exception as e:
                    print(f"   - API 호출 오류: {e}")
            else:
                print("2. A2mUpload API: 파일 그룹 ID 없음")
            
            # 3. dext5-multi-container 분석
            print("3. dext5-multi-container 분석:")
            dext_container = soup.find('div', id='dext5-multi-container')
            if dext_container:
                print("   - dext5-multi-container 발견")
                tables = dext_container.find_all('table')
                print(f"   - 테이블 {len(tables)}개 발견")
                
                for j, table in enumerate(tables):
                    rows = table.find_all('tr')
                    print(f"     Table {j+1}: {len(rows)} rows")
                    
                    for k, row in enumerate(rows):
                        cells = row.find_all('td')
                        if cells:
                            cell_texts = [cell.get_text(strip=True) for cell in cells]
                            print(f"       Row {k+1}: {cell_texts}")
            else:
                print("   - dext5-multi-container 없음")
            
            # 4. 직접 파일 링크 분석
            print("4. 직접 파일 링크 분석:")
            file_links = soup.find_all('a', href=re.compile(r'\.(pdf|hwp|doc|docx|xls|xlsx|zip|rar)', re.I))
            if file_links:
                print(f"   - 파일 링크 {len(file_links)}개 발견")
                for j, link in enumerate(file_links):
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    print(f"     Link {j+1}: {text} -> {href}")
            else:
                print("   - 직접 파일 링크 없음")
            
            # 5. JavaScript 다운로드 링크 분석
            print("5. JavaScript 다운로드 링크 분석:")
            js_download_links = soup.find_all('a', onclick=re.compile('download|fileDown|fnDown'))
            if js_download_links:
                print(f"   - JS 다운로드 링크 {len(js_download_links)}개 발견")
                for j, link in enumerate(js_download_links):
                    onclick = link.get('onclick', '')
                    text = link.get_text(strip=True)
                    print(f"     JS Link {j+1}: {text} -> {onclick}")
            else:
                print("   - JavaScript 다운로드 링크 없음")
            
            # 6. 파일 관련 텍스트 패턴 분석
            print("6. 텍스트 패턴 분석:")
            page_text = soup.get_text()
            file_patterns = [
                r'붙임[.\s]*([^.\s]+\.(pdf|hwp|doc|docx|xls|xlsx|zip|rar))',
                r'첨부[.\s]*([^.\s]+\.(pdf|hwp|doc|docx|xls|xlsx|zip|rar))',
                r'파일명?[:\s]*([^.\s]+\.(pdf|hwp|doc|docx|xls|xlsx|zip|rar))'
            ]
            
            found_patterns = False
            for pattern in file_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    found_patterns = True
                    print(f"   - 패턴 '{pattern}' 매치:")
                    for match in matches:
                        if isinstance(match, tuple):
                            print(f"     -> {match[0]}")
                        else:
                            print(f"     -> {match}")
            
            if not found_patterns:
                print("   - 파일 패턴 매치 없음")
            
        except Exception as e:
            print(f"Error analyzing {url}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    analyze_djbea_attachments()