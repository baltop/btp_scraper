#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export Voucher 단일 공고 전체 처리 테스트
process_announcement 메소드가 왜 실패하는지 확인
"""

import logging
import os
import shutil
from enhanced_export_voucher_scraper import EnhancedExportVoucherScraper

# 상세 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_single_processing():
    """단일 공고 전체 처리 테스트"""
    print("Export Voucher 단일 공고 전체 처리 테스트")
    print("=" * 50)
    
    # 테스트 출력 디렉토리
    output_dir = "output_test/export_voucher_single"
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    scraper = EnhancedExportVoucherScraper()
    
    # 첫 번째 공고 (첨부파일이 있는 것으로 확인됨)
    announcement = {
        'title': '[모집공고] 2025년 산업부 수출바우처사업 (산업 글로벌_관세 대응 바우처(추경)) 참여기업 모집',
        'url': 'https://www.exportvoucher.com/portal/board/boardView?pageNo=1&bbs_id=1&ntt_id=9325&active_menu_cd=EZ005004000&search_type=SJ&search_text=&start_date=&end_date=&pageUnit=10',
        'date': '2025-05-16',
        'views': '115618',
        'number': '',
        'has_attachment': False,
        'onclick': 'goDetail(9325)',
        'href': 'javascript:void(0)'
    }
    
    try:
        print(f"📋 공고 처리: {announcement['title'][:50]}...")
        print(f"🔗 URL: {announcement['url']}")
        
        # process_announcement 호출
        result = scraper.process_announcement(announcement, 1, output_dir)
        
        if result:
            print(f"✅ 처리 성공!")
            print(f"📄 본문 파일: {result.get('content_file', 'N/A')}")
            print(f"📎 첨부파일 개수: {len(result.get('attachments', []))}")
            
            for i, attachment in enumerate(result.get('attachments', []), 1):
                print(f"  파일 {i}: {attachment.get('name', 'N/A')}")
                print(f"    성공: {attachment.get('download_success', False)}")
                print(f"    경로: {attachment.get('local_path', 'N/A')}")
                
                # 파일 크기 확인
                local_path = attachment.get('local_path')
                if local_path and os.path.exists(local_path):
                    file_size = os.path.getsize(local_path)
                    print(f"    크기: {file_size:,} bytes")
                else:
                    print(f"    크기: 파일 없음")
            
            return True
        else:
            print(f"❌ 처리 실패: result is None")
            return False
            
    except Exception as e:
        print(f"❌ 처리 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_single_processing()
    if success:
        print("\n🎉 테스트 성공!")
    else:
        print("\n💥 테스트 실패!")