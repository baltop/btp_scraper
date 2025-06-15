#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DJBEA HWP 파일 다운로드 테스트
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

def test_hwp_download():
    """HWP 파일 다운로드 상세 테스트"""
    scraper = EnhancedDJBEAScraper()
    
    # 알려진 HWP 파일 URL들
    hwp_urls = [
        "https://www.djbea.or.kr/pms/resources/pmsfile/2025/N5400003/3e271938020d8a.hwp",
        "https://www.djbea.or.kr/pms/resources/pmsfile/2025/N5400003/3e271938020d8a1.hwp",
        "https://www.djbea.or.kr/pms/resources/pmsfile/2025/N5400003/3e271938020d8b.hwp"
    ]
    
    print("HWP 파일 다운로드 상세 테스트")
    print("="*80)
    
    for i, url in enumerate(hwp_urls):
        print(f"\n{i+1}. Testing URL: {url}")
        print("-" * 60)
        
        try:
            # HEAD 요청으로 파일 존재 확인
            print("HEAD 요청 테스트:")
            head_response = scraper.session.head(url, verify=scraper.verify_ssl, timeout=10)
            print(f"  Status: {head_response.status_code}")
            print(f"  Headers: {dict(head_response.headers)}")
            
            if head_response.status_code != 200:
                print(f"  -> HEAD 요청 실패, 다음 URL로...")
                continue
            
            # GET 요청으로 실제 다운로드 시도
            print("GET 요청 테스트:")
            get_response = scraper.session.get(url, verify=scraper.verify_ssl, timeout=30)
            print(f"  Status: {get_response.status_code}")
            print(f"  Content-Length: {len(get_response.content)}")
            print(f"  Content-Type: {get_response.headers.get('content-type', 'Unknown')}")
            
            if get_response.status_code == 200:
                # 파일 내용 분석
                content = get_response.content
                print(f"  File size: {len(content)} bytes")
                
                # HWP 파일 시그니처 확인
                if content.startswith(b'HWP Document File'):
                    print("  -> 올바른 HWP 파일 시그니처")
                elif content.startswith(b'\\x0D\\x0A\\x0D\\x0A'):
                    print("  -> HWP 파일일 가능성 높음")
                elif content.startswith(b'<'):
                    print("  -> HTML 응답 (에러 페이지일 가능성)")
                    print(f"  -> 내용 미리보기: {content[:200]}")
                else:
                    print(f"  -> 알 수 없는 파일 형식, 첫 32바이트: {content[:32]}")
                
                # 테스트 파일로 저장
                test_filename = f"test_hwp_{i+1}.hwp"
                with open(test_filename, 'wb') as f:
                    f.write(content)
                print(f"  -> 테스트 파일 저장: {test_filename}")
                
                # 파일 크기 재확인
                actual_size = os.path.getsize(test_filename)
                print(f"  -> 저장된 파일 크기: {actual_size} bytes")
                
                # 테스트 파일 삭제
                os.remove(test_filename)
                print(f"  -> 테스트 파일 삭제됨")
                
                if actual_size > 1000:  # 1KB 이상이면 성공으로 간주
                    print(f"  ✅ 다운로드 성공!")
                    break
                else:
                    print(f"  ❌ 파일 크기가 너무 작음")
            else:
                print(f"  ❌ GET 요청 실패")
                
        except Exception as e:
            print(f"  ❌ 오류 발생: {e}")
    
    print(f"\n{'='*80}")
    print("HWP 다운로드 테스트 완료")

if __name__ == "__main__":
    test_hwp_download()