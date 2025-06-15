#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export Voucher File2List API 테스트
실제 파일 목록과 현재 sec_code를 가져오기
"""

import requests
import json
from enhanced_export_voucher_scraper import EnhancedExportVoucherScraper

def test_file2list_api():
    """File2List API 테스트"""
    print("Export Voucher File2List API 테스트")
    print("=" * 50)
    
    scraper = EnhancedExportVoucherScraper()
    scraper._initialize_session()
    
    # 첫 번째 공고의 DOC ID
    doc_id = "DOC_000000002529310"
    
    # File2List API 호출
    api_url = "https://www.exportvoucher.com/common/File2List"
    
    try:
        print(f"🔍 API 호출: {api_url}")
        print(f"📋 DOC ID: {doc_id}")
        
        # GET 요청으로 파일 목록 가져오기
        response = scraper.session.get(
            api_url,
            params={'docId': doc_id},
            verify=scraper.verify_ssl,
            timeout=10
        )
        
        print(f"📡 응답 상태: {response.status_code}")
        print(f"📄 응답 길이: {len(response.text)} bytes")
        
        if response.status_code == 200:
            try:
                # JSON 파싱 시도
                file_data = response.json()
                print(f"✅ JSON 파싱 성공: {len(file_data)}개 파일")
                
                for i, file_info in enumerate(file_data, 1):
                    print(f"\n📎 파일 {i}:")
                    print(f"  - 파일명: {file_info.get('fileName', 'N/A')}")
                    print(f"  - 파일ID: {file_info.get('fileId', 'N/A')}")
                    print(f"  - sec_code: {file_info.get('secCode', 'N/A')}")
                    print(f"  - 파일 크기: {file_info.get('fileSize', 'N/A')}")
                    
                    # 실제 다운로드 URL 생성
                    if 'fileId' in file_info and 'secCode' in file_info:
                        download_url = f"https://www.exportvoucher.com/common.FileDownload.do?file_id={file_info['fileId']}&sec_code={file_info['secCode']}"
                        print(f"  - 다운로드 URL: {download_url}")
                        
                        # 실제 다운로드 테스트
                        print(f"  🔄 다운로드 테스트 중...")
                        test_response = scraper.session.get(download_url, verify=scraper.verify_ssl, timeout=30)
                        print(f"     상태: {test_response.status_code}")
                        print(f"     크기: {len(test_response.content)} bytes")
                        print(f"     Content-Type: {test_response.headers.get('content-type', 'N/A')}")
                        print(f"     Content-Disposition: {test_response.headers.get('content-disposition', 'N/A')}")
                
                return file_data
                
            except json.JSONDecodeError:
                print("❌ JSON 파싱 실패 - 텍스트 응답:")
                print(response.text[:500])
                
        else:
            print(f"❌ API 호출 실패: HTTP {response.status_code}")
            print(f"응답: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    
    return None

if __name__ == "__main__":
    result = test_file2list_api()
    if result:
        print(f"\n🎉 성공! {len(result)}개 파일 정보 획득")
    else:
        print("\n💡 다른 방법 필요")