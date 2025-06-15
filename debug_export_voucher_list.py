#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export Voucher 목록 페이지 디버깅
어떤 공고들이 있고 URL이 제대로 생성되는지 확인
"""

from enhanced_export_voucher_scraper import EnhancedExportVoucherScraper

def debug_list_page():
    """목록 페이지 디버깅"""
    print("Export Voucher 목록 페이지 디버깅")
    print("=" * 50)
    
    scraper = EnhancedExportVoucherScraper()
    
    # 첫 페이지 가져오기
    list_url = scraper.get_list_url(1)
    print(f"목록 URL: {list_url}")
    
    try:
        response = scraper.session.get(list_url, verify=scraper.verify_ssl, timeout=10)
        
        if response.status_code == 200:
            # 목록 파싱
            announcements = scraper.parse_list_page(response.text)
            print(f"총 {len(announcements)}개 공고 발견")
            
            for i, announcement in enumerate(announcements, 1):
                print(f"\n공고 {i}:")
                print(f"  제목: {announcement['title']}")
                print(f"  번호: {announcement['number']}")
                print(f"  URL: {announcement['url']}")
                print(f"  날짜: {announcement['date']}")
                print(f"  조회수: {announcement['views']}")
                print(f"  href: {announcement.get('href', 'N/A')}")
                print(f"  onclick: {announcement.get('onclick', 'N/A')}")
                
                # URL이 없는 경우만 처음 5개 확인
                if not announcement['url'] and i <= 5:
                    print(f"  ❌ URL 생성 실패")
        else:
            print(f"❌ 목록 페이지 접근 실패: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_list_page()