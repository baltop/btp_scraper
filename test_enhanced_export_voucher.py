#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export Voucher Enhanced 스크래퍼 테스트
3페이지까지 테스트하고 파일 다운로드 확인
"""

import os
import sys
import logging
import shutil
from enhanced_export_voucher_scraper import EnhancedExportVoucherScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_export_voucher.log', encoding='utf-8')
    ]
)

def verify_results(output_dir):
    """결과 검증"""
    print("\n=== 결과 검증 ===")
    
    if not os.path.exists(output_dir):
        print(f"❌ 출력 디렉토리가 존재하지 않습니다: {output_dir}")
        return False
    
    total_items = 0
    successful_items = 0
    url_check_passed = 0
    korean_files = 0
    
    for item_dir in os.listdir(output_dir):
        item_path = os.path.join(output_dir, item_dir)
        if os.path.isdir(item_path):
            total_items += 1
            
            # content.md 파일 확인
            content_file = os.path.join(item_path, 'content.md')
            if os.path.exists(content_file):
                successful_items += 1
                
                # content.md 내용 확인
                with open(content_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # 원본 URL 포함 확인
                if '**원본 URL**:' in content and 'exportvoucher.com' in content:
                    url_check_passed += 1
                
                print(f"✅ {item_dir}: content.md 존재 ({len(content)} 문자)")
            else:
                print(f"❌ {item_dir}: content.md 없음")
            
            # 첨부파일 확인
            attachments_dir = os.path.join(item_path, 'attachments')
            if os.path.exists(attachments_dir):
                att_files = os.listdir(attachments_dir)
                if att_files:
                    print(f"  📎 첨부파일 {len(att_files)}개:")
                    for att_file in att_files:
                        att_path = os.path.join(attachments_dir, att_file)
                        if os.path.exists(att_path):
                            file_size = os.path.getsize(att_path)
                            
                            # 한글 파일명 확인
                            has_korean = any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in att_file)
                            if has_korean:
                                korean_files += 1
                            
                            print(f"    - {att_file} ({file_size:,} bytes)")
                        else:
                            print(f"    - ❌ {att_file} (파일 없음)")
    
    print(f"\n📊 전체 통계:")
    print(f"  - 총 아이템: {total_items}개")
    print(f"  - 성공한 아이템: {successful_items}개")
    print(f"  - URL 포함 확인: {url_check_passed}개")
    print(f"  - 한글 파일명: {korean_files}개")
    
    if successful_items > 0:
        success_rate = (successful_items / total_items) * 100
        print(f"  - 성공률: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("✅ 테스트 성공!")
            return True
        else:
            print("⚠️ 성공률이 낮습니다.")
            return False
    else:
        print("❌ 테스트 실패!")
        return False

def main():
    """메인 테스트 함수"""
    print("Export Voucher Enhanced 스크래퍼 테스트 시작")
    print("=" * 50)
    
    # 출력 디렉토리 설정
    output_dir = os.path.join("output", "export_voucher")
    
    # 기존 출력 디렉토리 삭제 (새로운 테스트를 위해)
    if os.path.exists(output_dir):
        print(f"기존 출력 디렉토리 삭제: {output_dir}")
        shutil.rmtree(output_dir)
    
    # 스크래퍼 초기화
    try:
        scraper = EnhancedExportVoucherScraper()
        print("✅ 스크래퍼 초기화 성공")
    except Exception as e:
        print(f"❌ 스크래퍼 초기화 실패: {e}")
        return False
    
    # 테스트 실행 (3페이지)
    try:
        print("\n📥 Export Voucher 스크래핑 시작 (3페이지)")
        success = scraper.scrape_pages(
            max_pages=3,
            output_base=output_dir
        )
        
        if success:
            print("✅ 스크래핑 완료")
        else:
            print("⚠️ 스크래핑 중 일부 오류 발생")
            
    except Exception as e:
        print(f"❌ 스크래핑 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 결과 검증
    return verify_results(output_dir)

if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n🎉 Export Voucher Enhanced 스크래퍼 테스트 성공!")
        sys.exit(0)
    else:
        print("\n💥 Export Voucher Enhanced 스크래퍼 테스트 실패!")
        sys.exit(1)