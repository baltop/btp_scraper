#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export Voucher 완전한 다운로드 테스트
첫 번째 공고의 파일을 실제로 다운로드해서 크기 확인
"""

import logging
import os
import shutil
from enhanced_export_voucher_scraper import EnhancedExportVoucherScraper

# 디버그 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_full_download():
    """완전한 다운로드 테스트"""
    print("Export Voucher 완전한 다운로드 테스트")
    print("=" * 50)
    
    # 테스트 출력 디렉토리
    output_dir = "output_test/export_voucher_test"
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    scraper = EnhancedExportVoucherScraper()
    
    # 첫 번째 공고만 처리
    announcement = {
        'title': '[모집공고] 2025년 산업부 수출바우처사업 (산업 글로벌_관세 대응 바우처(추경)) 참여기업 모집',
        'url': 'https://www.exportvoucher.com/portal/board/boardView?pageNo=1&bbs_id=1&ntt_id=9325&active_menu_cd=EZ005004000&search_type=SJ&search_text=&start_date=&end_date=&pageUnit=10',
        'date': '2025-05-16',
        'views': '115614',
        'number': '중요'
    }
    
    try:
        print(f"📋 공고 처리: {announcement['title'][:50]}...")
        
        # 상세 페이지 처리
        detail_result = scraper.process_announcement(announcement, 1, output_dir)
        
        if detail_result:
            print(f"✅ 상세 처리 성공: {detail_result['content_file']}")
            print(f"📎 첨부파일 개수: {len(detail_result['attachments'])}")
            
            for i, attachment in enumerate(detail_result['attachments'], 1):
                print(f"  파일 {i}: {attachment['name']}")
                if attachment['download_success']:
                    file_size = os.path.getsize(attachment['local_path'])
                    print(f"    ✅ 다운로드 성공: {file_size:,} bytes")
                    print(f"    📁 저장 위치: {attachment['local_path']}")
                else:
                    print(f"    ❌ 다운로드 실패")
                    
            # 결과 요약
            successful_downloads = sum(1 for att in detail_result['attachments'] if att['download_success'])
            total_files = len(detail_result['attachments'])
            
            print(f"\n📊 결과 요약:")
            print(f"  - 총 첨부파일: {total_files}개")
            print(f"  - 다운로드 성공: {successful_downloads}개")
            print(f"  - 성공률: {(successful_downloads/total_files)*100:.1f}%" if total_files > 0 else "  - 성공률: N/A")
            
            return successful_downloads > 0
        else:
            print("❌ 상세 처리 실패")
            return False
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_full_download()
    if success:
        print("\n🎉 테스트 성공!")
    else:
        print("\n💥 테스트 실패!")