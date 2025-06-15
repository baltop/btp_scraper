#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DJBEA HWP 파일 응답 내용 상세 분석
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

def debug_hwp_content():
    """HWP 파일 응답 내용 상세 분석"""
    scraper = EnhancedDJBEAScraper()
    
    # HWP 파일 URL들
    hwp_urls = [
        "https://www.djbea.or.kr/pms/resources/pmsfile/2025/N5400003/3e271938020d8a.hwp",
        "https://www.djbea.or.kr/pms/resources/pmsfile/2025/N5400003/3e26f97016f64f.hwp",
        "https://www.djbea.or.kr/pms/resources/pmsfile/2025/N5400003/3e240871e236ba.hwp"
    ]
    
    print("DJBEA HWP 파일 응답 내용 상세 분석")
    print("="*80)
    
    for i, url in enumerate(hwp_urls):
        print(f"\n{i+1}. {url}")
        print("-" * 60)
        
        try:
            response = scraper.session.get(url, verify=scraper.verify_ssl, timeout=30)
            content = response.content
            
            print(f"Status Code: {response.status_code}")
            print(f"Content-Type: {response.headers.get('content-type')}")
            print(f"Content-Length: {len(content)} bytes")
            print(f"Content-Disposition: {response.headers.get('content-disposition', 'N/A')}")
            
            # 첫 500바이트 내용 분석
            print(f"첫 500바이트 내용:")
            first_500 = content[:500]
            try:
                # 텍스트로 디코딩 시도
                text_content = first_500.decode('utf-8', errors='ignore')
                print(f"  텍스트 내용: {repr(text_content)}")
            except:
                pass
            
            print(f"  16진수: {first_500.hex()[:100]}...")
            
            # HTML 태그 개수 확인
            html_tag_count = content.count(b'<') + content.count(b'>')
            content_ratio = html_tag_count / len(content) if len(content) > 0 else 0
            print(f"  HTML 태그 비율: {content_ratio:.4f} ({html_tag_count}개 태그)")
            
            # 특정 패턴 확인
            patterns_to_check = [
                (b'<!DOCTYPE', 'DOCTYPE 선언'),
                (b'<html', 'HTML 시작 태그'),
                (b'<head>', 'HEAD 태그'),
                (b'<body>', 'BODY 태그'),
                (b'HWP Document File', 'HWP 시그니처'),
                (b'\xD0\xCF\x11\xE0', 'OLE 시그니처'),
                (b'%PDF', 'PDF 시그니처'),
                (b'\x0D\x0A\x0D\x0A', 'HWP 패턴'),
            ]
            
            print("  패턴 검사:")
            for pattern, desc in patterns_to_check:
                if pattern in content:
                    print(f"    ✓ {desc} 발견")
                else:
                    print(f"    ✗ {desc} 없음")
            
            # 파일 시작 부분의 바이너리 시그니처 확인
            if len(content) >= 4:
                signature = content[:4]
                print(f"  파일 시그니처 (첫 4바이트): {signature.hex()}")
                
                # 알려진 파일 시그니처들
                signatures = {
                    b'%PDF': 'PDF 파일',
                    b'\x0D\x0A\x0D\x0A': 'HWP 파일',
                    b'\xD0\xCF\x11\xE0': 'Microsoft Office 파일 (OLE)',
                    b'PK\x03\x04': 'ZIP/Office 2007+ 파일',
                    b'HWP ': 'HWP 문서',
                }
                
                for sig, desc in signatures.items():
                    if content.startswith(sig):
                        print(f"    → {desc} 시그니처 확인")
                        break
                else:
                    print(f"    → 알려진 시그니처 없음")
            
            # 실제 다운로드 시도 결과 확인
            print(f"  다운로드 시도 결과:")
            
            # 현재 validation 로직 시뮬레이션
            content_type = response.headers.get('content-type', '').lower()
            is_html_response = 'text/html' in content_type
            
            print(f"    is_html_response: {is_html_response}")
            
            if is_html_response:
                if len(content) > 10000:
                    html_tag_count = content.count(b'<') + content.count(b'>')
                    content_ratio = html_tag_count / len(content) if len(content) > 0 else 1
                    
                    print(f"    HTML 태그 비율: {content_ratio:.4f}")
                    
                    if content_ratio < 0.01:
                        print(f"    → 이진 파일로 판단 (태그 비율 낮음)")
                    elif b'<!DOCTYPE' not in content[:200] and b'<html' not in content[:200]:
                        print(f"    → DOCTYPE 없음으로 판단")
                    else:
                        print(f"    → HTML 파일로 판단")
                else:
                    print(f"    → 파일 크기 부족 (10KB 미만)")
            
        except Exception as e:
            print(f"오류: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_hwp_content()