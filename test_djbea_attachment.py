#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DJBEA 첨부파일 구조 테스트 스크립트
"""

import os
import sys
import requests
from urllib3.exceptions import InsecureRequestWarning

# SSL 경고 비활성화
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# 현재 디렉토리를 Python path에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from djbea_scraper import DJBEAScraper

def test_djbea_attachment():
    """DJBEA 첨부파일 테스트"""
    scraper = DJBEAScraper()
    
    # 테스트할 공고 URL
    test_url = "https://www.djbea.or.kr/pms/st/st_0205/view_new?BBSCTT_SEQ=7952&BBSCTT_TY_CD=ST_0205"
    
    print(f"Testing DJBEA attachment parsing...")
    print(f"URL: {test_url}")
    print("-" * 80)
    
    try:
        # 페이지 가져오기
        response = scraper.get_page(test_url)
        if not response:
            print("Failed to get page")
            return
            
        print(f"Page fetched successfully (status: {response.status_code})")
        
        # 상세 페이지 파싱
        detail = scraper.parse_detail_page(response.text)
        
        print(f"\nContent length: {len(detail['content'])} characters")
        print(f"Found {len(detail['attachments'])} attachment(s)")
        
        if detail['attachments']:
            print("\nAttachments found:")
            for i, attachment in enumerate(detail['attachments']):
                print(f"  {i+1}. {attachment['name']}")
                print(f"     URL: {attachment['url']}")
                if 'size' in attachment:
                    print(f"     Size: {attachment['size']}")
                if 'file_id' in attachment:
                    print(f"     File ID: {attachment['file_id']}")
                if attachment.get('estimated'):
                    print(f"     Status: Estimated URL")
                print()
                
            # PDF 파일 다운로드 테스트 (두 번째 파일이 PDF)
            if len(detail['attachments']) > 1:
                print("Testing download of second attachment (PDF)...")
                test_attachment = detail['attachments'][1]
                test_file_path = f"test_{scraper.sanitize_filename(test_attachment['name'])}"
                
                success = scraper.download_djbea_file(test_attachment, test_file_path)
                if success and os.path.exists(test_file_path):
                    file_size = os.path.getsize(test_file_path)
                    print(f"Download successful! File size: {file_size} bytes")
                    # 테스트 파일 삭제
                    os.remove(test_file_path)
                else:
                    print("Download failed or file not created")
        else:
            print("\nNo attachments found")
            
        # HTML에서 dext5 컨테이너 및 스크립트 확인
        from bs4 import BeautifulSoup
        import re
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # dext5 컨테이너 확인
        dext_container = soup.find('div', id='dext5-multi-container')
        if dext_container:
            print(f"\ndext5-multi-container found!")
            tables = dext_container.find_all('table')
            print(f"Tables in container: {len(tables)}")
            
            for i, table in enumerate(tables):
                rows = table.find_all('tr')
                print(f"  Table {i+1}: {len(rows)} rows")
                
                for j, row in enumerate(rows):
                    cells = row.find_all('td')
                    if cells:
                        cell_texts = [cell.get_text(strip=True) for cell in cells]
                        print(f"    Row {j+1}: {cell_texts}")
        else:
            print("\ndext5-multi-container NOT found")
            
        # A2mUpload 스크립트에서 파일 그룹 ID 찾기
        print(f"\nLooking for A2mUpload configuration...")
        script_sections = soup.find_all('script')
        file_group_id = None
        
        for i, script in enumerate(script_sections):
            script_text = script.get_text() if script.string else ""
            if 'A2mUpload' in script_text:
                print(f"Found A2mUpload in script {i+1}")
                # targetAtchFileId 추출
                match = re.search(r'targetAtchFileId\s*:\s*[\'"]([^\'"]+)[\'"]', script_text)
                if match:
                    file_group_id = match.group(1)
                    print(f"Found targetAtchFileId: {file_group_id}")
                    break
                else:
                    print("A2mUpload found but no targetAtchFileId")
        
        if not file_group_id:
            print("No targetAtchFileId found in any script")
            
        # 파일 목록 API 직접 테스트
        if file_group_id:
            print(f"\nTesting file list API with group ID: {file_group_id}")
            try:
                file_list_url = f"{scraper.base_url}/pms/dextfile/common-fileList.do"
                data = {'targetAtchFileId': file_group_id}
                
                response_api = scraper.session.post(file_list_url, data=data, verify=scraper.verify_ssl, timeout=10)
                print(f"API Response Status: {response_api.status_code}")
                print(f"API Response Content: {response_api.text[:500]}...")
                
                if response_api.status_code == 200:
                    import json
                    try:
                        files_data = json.loads(response_api.text)
                        print(f"Parsed JSON: {files_data}")
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e}")
            except Exception as e:
                print(f"API test error: {e}")
            
        print("\n" + "="*80)
        print("Test completed")
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_djbea_attachment()