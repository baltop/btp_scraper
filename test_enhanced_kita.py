#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KITA Enhanced 스크래퍼 테스트 스크립트
"""

import logging
import os
import sys
from enhanced_kita_scraper import EnhancedKitaScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('kita_scraper.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def test_kita_scraper(pages=3):
    """KITA 스크래퍼 테스트"""
    logger.info("=== KITA Enhanced 스크래퍼 테스트 시작 ===")
    
    try:
        # 스크래퍼 초기화
        scraper = EnhancedKitaScraper()
        
        # 출력 디렉토리 설정
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        
        # 스크래핑 실행
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        
        logger.info("=== KITA 스크래퍼 테스트 완료 ===")
        
        # 결과 검증
        verify_results(output_dir)
        
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}")
        raise

def verify_results(output_dir):
    """결과 검증"""
    logger.info("=== 결과 검증 시작 ===")
    
    # KITA 폴더 확인 (중복된 경우 kita (1) 등으로 생성될 수 있음)
    kita_dir = None
    for folder_name in os.listdir(output_dir):
        if folder_name.startswith('kita'):
            kita_dir = os.path.join(output_dir, folder_name)
            break
    
    if not kita_dir or not os.path.exists(kita_dir):
        logger.error("KITA 출력 폴더가 생성되지 않았습니다")
        return
    
    # 공고 폴더들 확인
    announcement_folders = [d for d in os.listdir(kita_dir) 
                          if os.path.isdir(os.path.join(kita_dir, d))]
    
    logger.info(f"총 {len(announcement_folders)}개 공고 폴더 생성됨")
    
    total_items = len(announcement_folders)
    successful_items = 0
    total_attachments = 0
    korean_files = 0
    url_check_passed = 0
    
    for folder_name in announcement_folders[:5]:  # 상위 5개만 검증
        folder_path = os.path.join(kita_dir, folder_name)
        
        # content.md 파일 확인
        content_file = os.path.join(folder_path, 'content.md')
        if os.path.exists(content_file):
            successful_items += 1
            
            # 원본 URL 포함 확인
            with open(content_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if '**원본 URL**:' in content and 'kita.net' in content:
                    url_check_passed += 1
        
        # 첨부파일 확인
        attachments_dir = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_dir):
            attachment_files = os.listdir(attachments_dir)
            total_attachments += len(attachment_files)
            
            # 한글 파일명 확인
            for filename in attachment_files:
                if any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename):
                    korean_files += 1
                
                # 파일 크기 확인
                att_path = os.path.join(attachments_dir, filename)
                file_size = os.path.getsize(att_path)
                logger.info(f"  - {filename}: {file_size:,} bytes")
    
    # 결과 요약
    success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
    
    logger.info("=== 검증 결과 요약 ===")
    logger.info(f"총 공고 수: {total_items}")
    logger.info(f"성공적 처리: {successful_items} ({success_rate:.1f}%)")
    logger.info(f"원본 URL 포함: {url_check_passed}")
    logger.info(f"총 첨부파일: {total_attachments}")
    logger.info(f"한글 파일명: {korean_files}")
    
    if success_rate >= 80:
        logger.info("✅ 테스트 성공!")
    else:
        logger.warning(f"⚠️ 성공률이 낮습니다: {success_rate:.1f}%")

def test_single_page():
    """단일 페이지 테스트"""
    logger.info("=== 단일 페이지 테스트 ===")
    test_kita_scraper(pages=1)

def test_three_pages():
    """3페이지 테스트"""
    logger.info("=== 3페이지 테스트 ===")
    test_kita_scraper(pages=3)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='KITA Enhanced 스크래퍼 테스트')
    parser.add_argument('--pages', type=int, default=3, help='테스트할 페이지 수 (기본값: 3)')
    parser.add_argument('--single', action='store_true', help='단일 페이지 테스트')
    
    args = parser.parse_args()
    
    if args.single:
        test_single_page()
    else:
        test_kita_scraper(pages=args.pages)