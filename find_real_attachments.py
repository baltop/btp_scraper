#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DJBEA 실제 첨부파일 패턴 탐지
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

def find_real_attachments():
    """실제 첨부파일 패턴 탐지"""
    scraper = EnhancedDJBEAScraper()
    
    # 여러 공고의 다양한 패턴 시도
    test_seqs = ['7952', '7951', '7950', '7949', '7948', '7947', '7946', '7945']
    
    print("DJBEA 실제 첨부파일 패턴 탐지")
    print("="*80)
    
    for seq in test_seqs:
        url = f"https://www.djbea.or.kr/pms/st/st_0205/view_new?BBSCTT_SEQ={seq}&BBSCTT_TY_CD=ST_0205"
        print(f"\n분석 중: SEQ={seq}")
        print("-" * 40)
        
        try:
            response = scraper.get_page(url)
            if not response:
                print("  페이지 가져오기 실패")
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1. JavaScript에서 파일 경로 패턴 찾기
            scripts = soup.find_all('script')
            for script in scripts:
                script_text = script.string if script.string else ""
                
                # 파일 경로 패턴 찾기
                file_patterns = re.findall(r'/pms/[^\\s\'"]+\\.(pdf|hwp|doc|docx|xls|xlsx)', script_text, re.IGNORECASE)
                if file_patterns:
                    print(f"  JS에서 파일 패턴 발견: {file_patterns}")
                
                # 파일 ID나 해시 패턴 찾기
                hash_patterns = re.findall(r'([a-f0-9]{12,})', script_text)
                if hash_patterns:
                    unique_hashes = list(set(hash_patterns))[:3]  # 처음 3개만
                    print(f"  JS에서 해시 패턴 발견: {unique_hashes}")
            
            # 2. 특정 파일 경로 패턴 시도해보기
            potential_paths = [
                f"/pms/resources/pmsfile/2025/N5400003/",
                f"/pms/resources/pmsfile/2025/",
                f"/pms/resources/file/",
                f"/pms/file/",
                f"/pms/download/"
            ]
            
            potential_files = [
                f"{seq}.pdf", f"{seq}.hwp",
                f"file_{seq}.pdf", f"file_{seq}.hwp",
                f"attach_{seq}.pdf", f"attach_{seq}.hwp",
                "모집공고.pdf", "모집공고.hwp", "공고문.pdf", "공고문.hwp"
            ]
            
            found_files = []
            for path in potential_paths:
                for filename in potential_files:
                    test_url = f"{scraper.base_url}{path}{filename}"
                    try:
                        head_response = scraper.session.head(test_url, verify=scraper.verify_ssl, timeout=3)
                        if head_response.status_code == 200:
                            content_type = head_response.headers.get('content-type', '')
                            size = head_response.headers.get('content-length', 'Unknown')
                            found_files.append({
                                'url': test_url,
                                'content_type': content_type,
                                'size': size
                            })
                            print(f"  ✓ 파일 발견: {filename} ({size} bytes, {content_type})")
                    except:
                        pass
            
            # 3. A2mUpload API 다시 시도 (다른 파라미터로)
            api_endpoints = [
                "/pms/dextfile/common-fileList.do",
                "/pms/common/file/list.do",
                "/pms/file/list.do"
            ]
            
            api_params = [
                {'targetAtchFileId': seq},
                {'fileGroupId': seq},
                {'bbscttSeq': seq},
                {'boardSeq': seq},
                {'BBSCTT_SEQ': seq}
            ]
            
            for endpoint in api_endpoints:
                for params in api_params:
                    try:
                        api_url = f"{scraper.base_url}{endpoint}"
                        api_response = scraper.session.post(api_url, data=params, verify=scraper.verify_ssl, timeout=5)
                        if api_response.status_code == 200 and len(api_response.text) > 10:
                            try:
                                json_data = json.loads(api_response.text)
                                if isinstance(json_data, list) and json_data:
                                    print(f"  ✓ API 응답: {endpoint} with {params}")
                                    print(f"    데이터: {json_data}")
                            except:
                                if 'file' in api_response.text.lower():
                                    print(f"  ✓ API 응답 (non-JSON): {endpoint} with {params}")
                                    print(f"    응답: {api_response.text[:100]}...")
                    except:
                        pass
            
            if not found_files:
                print("  첨부파일 없음")
                
        except Exception as e:
            print(f"  오류: {e}")

if __name__ == "__main__":
    find_real_attachments()