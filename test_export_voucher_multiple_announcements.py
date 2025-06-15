#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export Voucher 여러 공고 첨부파일 확인
다른 공고들도 첨부파일이 있는지 확인
"""

import logging
from enhanced_export_voucher_scraper import EnhancedExportVoucherScraper

# 디버그 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_multiple_announcements():
    """여러 공고의 첨부파일 확인"""
    print("Export Voucher 여러 공고 첨부파일 확인")
    print("=" * 50)
    
    scraper = EnhancedExportVoucherScraper()
    
    # 테스트할 공고들 (처음 5개)
    test_announcements = [
        {
            'title': '[모집공고] 2025년 산업부 수출바우처사업 (산업 글로벌_관세 대응 바우처(추경)) 참여기업 모집',
            'url': 'https://www.exportvoucher.com/portal/board/boardView?pageNo=1&bbs_id=1&ntt_id=9325&active_menu_cd=EZ005004000&search_type=SJ&search_text=&start_date=&end_date=&pageUnit=10',
            'ntt_id': '9325'
        },
        {
            'title': '2025년 상반기 협약만료 수행기관 협약연장 계획 공지',
            'url': 'https://www.exportvoucher.com/portal/board/boardView?pageNo=1&bbs_id=1&ntt_id=9280&active_menu_cd=EZ005004000&search_type=SJ&search_text=&start_date=&end_date=&pageUnit=10',
            'ntt_id': '9280'
        },
        {
            'title': '[상시모집] 수출지원기반활용사업(수출바우처) 수행기관 모집',
            'url': 'https://www.exportvoucher.com/portal/board/boardView?pageNo=1&bbs_id=1&ntt_id=8410&active_menu_cd=EZ005004000&search_type=SJ&search_text=&start_date=&end_date=&pageUnit=10',
            'ntt_id': '8410'
        },
        {
            'title': '2025년 중기부 소관 수출지원기반활용사업 수출바우처 참여기업 3차 모집공고',
            'url': 'https://www.exportvoucher.com/portal/board/boardView?pageNo=1&bbs_id=1&ntt_id=9350&active_menu_cd=EZ005004000&search_type=SJ&search_text=&start_date=&end_date=&pageUnit=10',
            'ntt_id': '9350'
        }
    ]
    
    try:
        for i, announcement in enumerate(test_announcements, 1):
            print(f"\n🔍 공고 {i}: {announcement['title'][:50]}...")
            print(f"📋 ntt_id: {announcement['ntt_id']}")
            
            # 상세 페이지 접근
            response = scraper.session.get(announcement['url'], verify=scraper.verify_ssl, timeout=10)
            
            if response.status_code == 200:
                # 상세 페이지 파싱
                detail_data = scraper.parse_detail_page(response.text)
                
                print(f"📄 본문 길이: {len(detail_data['content'])}")
                print(f"📎 첨부파일 개수: {len(detail_data['attachments'])}")
                
                if detail_data['attachments']:
                    for j, attachment in enumerate(detail_data['attachments'], 1):
                        print(f"  파일 {j}: {attachment['name']}")
                        print(f"    URL: {attachment['url']}")
                        print(f"    파일ID: {attachment.get('file_id', 'N/A')}")
                        print(f"    크기: {attachment.get('file_size', 'N/A')} bytes")
                else:
                    print(f"  ⚠️  첨부파일 없음")
            else:
                print(f"❌ 접근 실패: HTTP {response.status_code}")
                
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_multiple_announcements()