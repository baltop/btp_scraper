#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DJBEA 실제 HWP 파일 찾기
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
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 현재 디렉토리를 Python path에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_djbea_scraper import EnhancedDJBEAScraper

def find_real_hwp_files():
    """실제 HWP 파일 찾기"""
    scraper = EnhancedDJBEAScraper()
    
    # 알려진 해시들과 다양한 패턴 시도
    hashes = ['3e271938020d8a', '3e26f97016f64f', '3e240871e236ba']
    
    # 다양한 경로 패턴들
    path_patterns = [
        "/pms/resources/pmsfile/2025/N5400003/{}.hwp",
        "/pms/resources/pmsfile/2025/{}.hwp", 
        "/pms/resources/pmsfile/{}.hwp",
        "/pms/resources/file/2025/{}.hwp",
        "/pms/file/2025/{}.hwp",
        "/pms/dextfile/2025/{}.hwp",
        "/pms/resources/pmsfile/2025/N5400003/{}1.hwp",  # 숫자 변형
        "/pms/resources/pmsfile/2025/N5400003/{}a.hwp",  # 문자 변형
        "/pms/resources/pmsfile/2025/N5400003/{}b.hwp",
        "/pms/resources/pmsfile/2025/N5400003/{}_1.hwp",
        "/pms/resources/pmsfile/2025/N5400003/{}_2.hwp",
    ]
    
    # 파일명 패턴들
    filename_patterns = [
        "모집공고.hwp",
        "공고문.hwp", 
        "사업공고.hwp",
        "지원사업공고.hwp",
        "첨부파일.hwp",
        "붙임.hwp",
        "붙임1.hwp",
        "붙임2.hwp",
        "attachment.hwp",
        "file.hwp"
    ]
    
    print("DJBEA 실제 HWP 파일 찾기")
    print("="*80)
    
    real_files_found = []
    
    # 1. 해시 기반 패턴들 시도
    for hash_val in hashes:
        print(f"\n해시 {hash_val}에 대한 패턴 탐색:")
        for pattern in path_patterns:
            test_url = f"{scraper.base_url}{pattern.format(hash_val)}"
            
            try:
                response = scraper.session.head(test_url, verify=scraper.verify_ssl, timeout=3)
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    content_length = response.headers.get('content-length', '0')
                    
                    # HTML 에러 페이지가 아닌지 확인 (48332 바이트는 에러 페이지)
                    if content_length != '48332' and 'text/html' not in content_type:
                        print(f"  ✅ 실제 파일 발견: {test_url}")
                        print(f"     크기: {content_length} bytes, 타입: {content_type}")
                        
                        # 실제 다운로드해서 확인
                        get_response = scraper.session.get(test_url, verify=scraper.verify_ssl, timeout=10)
                        if get_response.status_code == 200 and len(get_response.content) > 1000:
                            content = get_response.content
                            if not content.startswith(b'<!DOCTYPE') and not content.startswith(b'<html'):
                                real_files_found.append({
                                    'url': test_url,
                                    'hash': hash_val,
                                    'size': len(content),
                                    'content_type': content_type,
                                    'signature': content[:16].hex()
                                })
                                print(f"     실제 파일 확인됨! 시그니처: {content[:16].hex()}")
                            else:
                                print(f"     HTML 에러 페이지였음")
                    elif content_length == '48332':
                        print(f"  ❌ HTML 에러 페이지: {test_url}")
                    
            except Exception as e:
                pass
    
    # 2. 일반적인 파일명 패턴들 시도
    print(f"\n일반적인 파일명 패턴 탐색:")
    base_paths = [
        "/pms/resources/pmsfile/2025/N5400003/",
        "/pms/resources/pmsfile/2025/",
        "/pms/resources/file/2025/",
        "/pms/file/2025/"
    ]
    
    for base_path in base_paths:
        for filename in filename_patterns:
            test_url = f"{scraper.base_url}{base_path}{filename}"
            
            try:
                response = scraper.session.head(test_url, verify=scraper.verify_ssl, timeout=3)
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    content_length = response.headers.get('content-length', '0')
                    
                    if content_length != '48332' and 'text/html' not in content_type:
                        print(f"  ✅ 실제 파일 발견: {test_url}")
                        print(f"     크기: {content_length} bytes, 타입: {content_type}")
                        
                        real_files_found.append({
                            'url': test_url,
                            'filename': filename,
                            'size': content_length,
                            'content_type': content_type
                        })
                        
            except Exception as e:
                pass
    
    print(f"\n{'='*80}")
    print(f"실제 HWP 파일 발견 결과: {len(real_files_found)}개")
    
    if real_files_found:
        for i, file_info in enumerate(real_files_found):
            print(f"{i+1}. {file_info['url']}")
            print(f"   크기: {file_info['size']} bytes")
            print(f"   타입: {file_info['content_type']}")
            if 'signature' in file_info:
                print(f"   시그니처: {file_info['signature']}")
            print()
    else:
        print("실제 HWP 파일을 찾을 수 없습니다.")
        print("가능한 원인:")
        print("1. DJBEA 사이트에서 HWP 파일을 제공하지 않음")
        print("2. 다른 URL 패턴이나 다운로드 방식 사용")
        print("3. 로그인이나 세션이 필요한 파일")

if __name__ == "__main__":
    find_real_hwp_files()