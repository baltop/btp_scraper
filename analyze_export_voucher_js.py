#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export Voucher JavaScript 분석
ftFile2.js를 가져와서 파일 로딩 메커니즘 분석
"""

import requests
from enhanced_export_voucher_scraper import EnhancedExportVoucherScraper

def analyze_js():
    """JavaScript 파일 분석"""
    print("Export Voucher JavaScript 분석")
    print("=" * 50)
    
    scraper = EnhancedExportVoucherScraper()
    scraper._initialize_session()
    
    # ftFile2.js 파일 다운로드
    js_url = "https://www.exportvoucher.com/static/script/v_ad/ftFile2.js?v=3"
    
    try:
        response = scraper.session.get(js_url, verify=scraper.verify_ssl, timeout=10)
        
        if response.status_code == 200:
            # JavaScript 파일 저장
            with open('ftFile2.js', 'w', encoding='utf-8') as f:
                f.write(response.text)
            print("✅ ftFile2.js 저장 완료")
            
            # 파일 관련 함수나 AJAX 호출 찾기
            content = response.text
            
            # AJAX 호출 패턴 찾기
            ajax_patterns = [
                'ajax',
                '$.ajax',
                '$.post',
                '$.get',
                'XMLHttpRequest',
                'fetch'
            ]
            
            print("\n📡 AJAX 호출 패턴 검색:")
            for pattern in ajax_patterns:
                if pattern in content:
                    print(f"  ✅ {pattern} 발견")
                    # 해당 패턴 주변 코드 출력
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if pattern in line:
                            start = max(0, i-2)
                            end = min(len(lines), i+3)
                            print(f"    라인 {i+1}: {line.strip()}")
                            for j in range(start, end):
                                if j != i:
                                    print(f"      {j+1}: {lines[j].strip()}")
                            print()
                            break
                else:
                    print(f"  ❌ {pattern} 없음")
            
            # 파일 다운로드 관련 키워드 찾기
            file_keywords = [
                'FileDownload',
                'downloadFile',
                'file_id',
                'sec_code',
                'docId',
                'DOC_'
            ]
            
            print("\n📄 파일 다운로드 관련 키워드:")
            for keyword in file_keywords:
                if keyword in content:
                    print(f"  ✅ {keyword} 발견")
                    # 해당 키워드 주변 코드 출력
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if keyword in line:
                            print(f"    라인 {i+1}: {line.strip()}")
                            break
                else:
                    print(f"  ❌ {keyword} 없음")
                    
        else:
            print(f"❌ JavaScript 파일 다운로드 실패: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    analyze_js()