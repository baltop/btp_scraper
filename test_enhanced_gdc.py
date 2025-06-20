# -*- coding: utf-8 -*-
"""
GDC 향상된 스크래퍼 테스트 스크립트
"""

import os
import sys
import logging
from datetime import datetime

# 스크래퍼 import
from enhanced_gdc_scraper import EnhancedGdcScraper

def setup_logging():
    """로깅 설정"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

def test_gdc_scraper(pages=3):
    """GDC 스크래퍼 테스트"""
    print(f"=== GDC 스크래퍼 테스트 시작 (최대 {pages}페이지) ===")
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    scraper = EnhancedGdcScraper()
    output_dir = "output/gdc"
    
    try:
        # 출력 디렉토리 생성
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"출력 디렉토리: {output_dir}")
        
        # 스크래핑 실행
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        
        print(f"\n=== 테스트 완료 ===")
        print(f"결과 확인: {output_dir}")
        
        # 결과 검증
        verify_results(output_dir)
        
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}")
        raise

def verify_results(output_dir):
    """결과 검증"""
    print(f"\n=== 결과 검증 ===")
    
    if not os.path.exists(output_dir):
        print("❌ 출력 디렉토리가 존재하지 않습니다")
        return
    
    # 공고 폴더들 확인
    announcement_folders = [d for d in os.listdir(output_dir) 
                          if os.path.isdir(os.path.join(output_dir, d))]
    
    total_items = len(announcement_folders)
    successful_items = 0
    total_attachments = 0
    korean_files = 0
    file_size_total = 0
    url_check_passed = 0
    
    print(f"📂 총 공고 폴더 수: {total_items}")
    
    for folder_name in announcement_folders:
        folder_path = os.path.join(output_dir, folder_name)
        
        # content.md 파일 확인
        content_file = os.path.join(folder_path, 'content.md')
        if os.path.exists(content_file):
            successful_items += 1
            
            # 원본 URL 포함 확인
            with open(content_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if '**원본 URL**:' in content and 'gdc.or.kr' in content:
                    url_check_passed += 1
        
        # 첨부파일 검증
        attachments_dir = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_dir):
            for filename in os.listdir(attachments_dir):
                att_path = os.path.join(attachments_dir, filename)
                if os.path.isfile(att_path):
                    total_attachments += 1
                    
                    # 한글 파일명 검증
                    has_korean = any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename)
                    if has_korean:
                        korean_files += 1
                    
                    # 파일 크기 검증
                    file_size = os.path.getsize(att_path)
                    file_size_total += file_size
                    
                    print(f"  📎 {filename} ({file_size:,} bytes)")
    
    # 성공률 계산
    success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
    url_success_rate = (url_check_passed / total_items) * 100 if total_items > 0 else 0
    
    print(f"\n=== 검증 결과 요약 ===")
    print(f"📋 총 공고 수: {total_items}")
    print(f"✅ 성공적 처리: {successful_items} ({success_rate:.1f}%)")
    print(f"🔗 원본 URL 포함: {url_check_passed} ({url_success_rate:.1f}%)")
    print(f"📎 총 첨부파일: {total_attachments}")
    print(f"🇰🇷 한글 파일명: {korean_files}")
    print(f"💾 총 파일 용량: {file_size_total:,} bytes")
    
    if success_rate >= 80:
        print("✅ 테스트 성공!")
    else:
        print("❌ 테스트 실패: 성공률이 80% 미만입니다")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='GDC 스크래퍼 테스트')
    parser.add_argument('--pages', type=int, default=3, help='테스트할 페이지 수 (기본값: 3)')
    parser.add_argument('--single', action='store_true', help='단일 페이지만 테스트')
    
    args = parser.parse_args()
    
    pages = 1 if args.single else args.pages
    test_gdc_scraper(pages)