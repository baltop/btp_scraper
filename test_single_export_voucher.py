#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export Voucher 단일 공고 디버깅용 테스트
첫 번째 공고의 첨부파일이 왜 안 나오는지 확인
"""

import logging
from enhanced_export_voucher_scraper import EnhancedExportVoucherScraper

# 디버그 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_single_announcement():
    """첫 번째 공고만 테스트"""
    print("Export Voucher 첫 번째 공고 디버깅 테스트")
    print("=" * 50)
    
    scraper = EnhancedExportVoucherScraper()
    
    # 첫 번째 공고 URL (브라우저에서 확인한 URL)
    url = "https://www.exportvoucher.com/portal/board/boardView?pageNo=1&bbs_id=1&ntt_id=9325&active_menu_cd=EZ005004000&search_type=SJ&search_text=&start_date=&end_date=&pageUnit=10"
    
    print(f"테스트 URL: {url}")
    
    try:
        # 세션 초기화
        scraper._initialize_session()
        
        # 상세 페이지 접근
        response = scraper.session.get(url, verify=scraper.verify_ssl, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ 페이지 접근 성공: HTTP {response.status_code}")
            
            # 상세 페이지 파싱
            detail_data = scraper.parse_detail_page(response.text)
            
            print(f"📄 본문 길이: {len(detail_data['content'])}")
            print(f"📎 첨부파일 개수: {len(detail_data['attachments'])}")
            
            for i, attachment in enumerate(detail_data['attachments'], 1):
                print(f"  - 첨부파일 {i}: {attachment['name']}")
                print(f"    URL: {attachment['url']}")
                
        else:
            print(f"❌ 페이지 접근 실패: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_single_announcement()