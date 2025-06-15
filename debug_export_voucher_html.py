#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export Voucher HTML 구조 디버깅
실제 HTML을 저장하고 분석
"""

from enhanced_export_voucher_scraper import EnhancedExportVoucherScraper
from bs4 import BeautifulSoup

def debug_html():
    """HTML 구조 분석"""
    print("Export Voucher HTML 구조 디버깅")
    print("=" * 50)
    
    scraper = EnhancedExportVoucherScraper()
    
    # 첫 번째 공고 URL
    url = "https://www.exportvoucher.com/portal/board/boardView?pageNo=1&bbs_id=1&ntt_id=9325&active_menu_cd=EZ005004000&search_type=SJ&search_text=&start_date=&end_date=&pageUnit=10"
    
    try:
        # 세션 초기화
        scraper._initialize_session()
        
        # 상세 페이지 접근
        response = scraper.session.get(url, verify=scraper.verify_ssl, timeout=10)
        
        if response.status_code == 200:
            # HTML을 파일로 저장
            with open('debug_export_voucher.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            print("✅ HTML 저장 완료: debug_export_voucher.html")
            
            # BeautifulSoup으로 파싱
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 체크박스 찾기
            checkboxes = soup.find_all('input', type='checkbox')
            print(f"📋 체크박스 개수: {len(checkboxes)}")
            
            # 모든 input 태그 찾기
            all_inputs = soup.find_all('input')
            print(f"📝 전체 input 태그 개수: {len(all_inputs)}")
            
            for i, inp in enumerate(all_inputs):
                print(f"  Input {i+1}: type='{inp.get('type')}', name='{inp.get('name')}', id='{inp.get('id')}'")
            
            # FileDownload.do 링크 찾기
            file_links = soup.find_all('a', href=lambda x: x and 'FileDownload.do' in x)
            print(f"📎 FileDownload.do 링크 개수: {len(file_links)}")
            
            for i, link in enumerate(file_links):
                href = link.get('href', '')
                text = link.get_text(strip=True)
                print(f"  링크 {i+1}: {text[:50]}...")
                print(f"    URL: {href}")
                print(f"    부모: {link.parent.name if link.parent else 'None'}")
                print()
                
        else:
            print(f"❌ 페이지 접근 실패: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_html()