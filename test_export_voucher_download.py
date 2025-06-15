#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export Voucher 파일 다운로드 테스트
실제 다운로드 URL이 왜 0바이트를 반환하는지 확인
"""

import requests
import os
from enhanced_export_voucher_scraper import EnhancedExportVoucherScraper

def test_direct_download():
    """직접 다운로드 테스트"""
    print("Export Voucher 파일 다운로드 테스트")
    print("=" * 50)
    
    scraper = EnhancedExportVoucherScraper()
    scraper._initialize_session()
    
    # 테스트할 파일 URL들
    test_urls = [
        "https://www.exportvoucher.com/common.FileDownload.do?file_id=FILE_000000005287113&sec_code=J6QRc",
        "https://www.exportvoucher.com/common.FileDownload.do?file_id=FILE_000000005287114&sec_code=mUrOw"
    ]
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n🔍 테스트 {i}: {url}")
        
        try:
            # 다운로드 요청
            response = scraper.session.get(url, verify=scraper.verify_ssl, timeout=30)
            
            print(f"   Status: {response.status_code}")
            print(f"   Content-Length: {response.headers.get('content-length', 'Not specified')}")
            print(f"   Content-Type: {response.headers.get('content-type', 'Not specified')}")
            print(f"   Content-Disposition: {response.headers.get('content-disposition', 'Not specified')}")
            
            # 실제 내용 확인
            content = response.content
            print(f"   실제 바이트 수: {len(content)}")
            
            if len(content) > 0:
                # 처음 100바이트 확인 (텍스트인지 바이너리인지)
                preview = content[:100]
                try:
                    text_preview = preview.decode('utf-8')
                    print(f"   내용 미리보기: {text_preview[:50]}...")
                    if 'html' in text_preview.lower():
                        print("   ⚠️  HTML 응답 - 리다이렉트나 오류 페이지일 가능성")
                except:
                    print("   📄 바이너리 파일 - 정상적인 파일로 보임")
            else:
                print("   ❌ 빈 응답")
                
            # 응답 헤더 전체 출력
            print("   전체 헤더:")
            for key, value in response.headers.items():
                print(f"     {key}: {value}")
                
        except Exception as e:
            print(f"   ❌ 오류: {e}")

if __name__ == "__main__":
    test_direct_download()