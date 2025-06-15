#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export Voucher AJAX 파일 목록 API 테스트
DOC_ID를 사용해서 첨부파일 목록 가져오기
"""

import requests
import json
from enhanced_export_voucher_scraper import EnhancedExportVoucherScraper

def test_ajax_api():
    """AJAX API로 첨부파일 목록 가져오기"""
    print("Export Voucher AJAX API 테스트")
    print("=" * 50)
    
    scraper = EnhancedExportVoucherScraper()
    scraper._initialize_session()
    
    # HTML에서 발견한 DOC ID
    doc_id = "DOC_000000002529310"
    
    # 가능한 AJAX 엔드포인트들 시도
    possible_endpoints = [
        f"/portal/file/list?docId={doc_id}",
        f"/portal/file/fileList?docId={doc_id}",
        f"/common/file/list?docId={doc_id}",
        f"/file/list?docId={doc_id}",
        f"/api/file/list?docId={doc_id}",
        f"/portal/board/fileList?docId={doc_id}",
        f"/portal/board/attachList?docId={doc_id}",
    ]
    
    for endpoint in possible_endpoints:
        url = f"https://www.exportvoucher.com{endpoint}"
        print(f"\n🔍 테스트 중: {url}")
        
        try:
            # GET 요청
            response = scraper.session.get(url, verify=scraper.verify_ssl, timeout=10)
            print(f"   GET {response.status_code}: {len(response.text)} bytes")
            
            if response.status_code == 200 and response.text:
                print(f"   응답: {response.text[:200]}...")
                
                # JSON 파싱 시도
                try:
                    data = response.json()
                    print(f"   ✅ JSON 파싱 성공: {data}")
                except:
                    pass
            
            # POST 요청도 시도
            response = scraper.session.post(url, data={'docId': doc_id}, verify=scraper.verify_ssl, timeout=10)
            print(f"   POST {response.status_code}: {len(response.text)} bytes")
            
            if response.status_code == 200 and response.text:
                print(f"   응답: {response.text[:200]}...")
                
                # JSON 파싱 시도
                try:
                    data = response.json()
                    print(f"   ✅ JSON 파싱 성공: {data}")
                    return data  # 성공하면 반환
                except:
                    pass
                    
        except Exception as e:
            print(f"   ❌ 오류: {e}")
    
    print("\n❌ 모든 엔드포인트 시도 실패")
    return None

if __name__ == "__main__":
    result = test_ajax_api()
    if result:
        print(f"\n🎉 성공적으로 데이터 발견: {result}")
    else:
        print(f"\n💡 다른 방법을 시도해야 함")