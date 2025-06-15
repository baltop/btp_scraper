#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced DJBEA 첨부파일 구조 테스트 스크립트
"""

import os
import sys
import requests
from urllib3.exceptions import InsecureRequestWarning
import logging

# SSL 경고 비활성화
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 현재 디렉토리를 Python path에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_djbea_scraper import EnhancedDJBEAScraper

def test_enhanced_djbea_attachment():
    """Enhanced DJBEA 첨부파일 테스트"""
    scraper = EnhancedDJBEAScraper()
    
    # 테스트할 공고 URL (사용자가 언급한 첫 번째 공고)
    test_url = "https://www.djbea.or.kr/pms/st/st_0205/view_new?BBSCTT_SEQ=7952&BBSCTT_TY_CD=ST_0205"
    
    print(f"Testing Enhanced DJBEA attachment parsing...")
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
                if attachment.get('verified'):
                    print(f"     Status: Verified")
                elif attachment.get('estimated'):
                    print(f"     Status: Estimated URL")
                if attachment.get('patterns'):
                    print(f"     Patterns: {len(attachment['patterns'])} URLs")
                print()
                
            # 첫 번째 첨부파일 다운로드 테스트
            if detail['attachments']:
                print("Testing download of first attachment...")
                test_attachment = detail['attachments'][0]
                test_file_path = f"test_enhanced_{scraper.sanitize_filename(test_attachment['name'])}"
                
                success = scraper._download_djbea_file(test_attachment, test_file_path)
                if success and os.path.exists(test_file_path):
                    file_size = os.path.getsize(test_file_path)
                    print(f"Download successful! File size: {file_size} bytes")
                    # 테스트 파일 삭제
                    os.remove(test_file_path)
                else:
                    print("Download failed or file not created")
        else:
            print("\nNo attachments found - testing hardcoded file extraction...")
            
            # 하드코딩된 파일 추출 테스트
            hardcoded_files = scraper._extract_hardcoded_djbea_files()
            print(f"Hardcoded files found: {len(hardcoded_files)}")
            
            for i, file_info in enumerate(hardcoded_files):
                print(f"  {i+1}. {file_info['name']}")
                print(f"     URL: {file_info['url']}")
                if file_info.get('verified'):
                    print(f"     Status: Verified")
                else:
                    print(f"     Status: Estimated")
            
            if hardcoded_files:
                print("\nTesting download of first hardcoded file...")
                test_file = hardcoded_files[0]
                test_file_path = f"test_hardcoded_{scraper.sanitize_filename(test_file['name'])}"
                
                success = scraper._download_djbea_file(test_file, test_file_path)
                if success and os.path.exists(test_file_path):
                    file_size = os.path.getsize(test_file_path)
                    print(f"Download successful! File size: {file_size} bytes")
                    # 테스트 파일 삭제
                    os.remove(test_file_path)
                else:
                    print("Download failed or file not created")
            
        print("\n" + "="*80)
        print("Enhanced DJBEA attachment test completed")
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_enhanced_djbea_attachment()