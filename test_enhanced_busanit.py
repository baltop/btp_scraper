#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BUSANIT Enhanced 스크래퍼 테스트 스크립트
"""

import logging
import os
import sys
from enhanced_busanit_scraper import EnhancedBusanitScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('busanit_scraper.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def test_busanit_scraper(pages=3):
    """BUSANIT 스크래퍼 테스트"""
    logger.info("=== BUSANIT Enhanced 스크래퍼 테스트 시작 ===")
    
    try:
        # 스크래퍼 초기화
        scraper = EnhancedBusanitScraper()
        
        # 출력 디렉토리 설정
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        
        # 스크래핑 실행
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        
        logger.info("=== BUSANIT 스크래퍼 테스트 완료 ===")
        
        # 결과 검증
        verify_results(output_dir)
        
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}")
        raise

def verify_results(output_dir):
    """결과 검증"""
    logger.info("=== 결과 검증 시작 ===")
    
    # 공고 폴더들 확인
    announcement_folders = [d for d in os.listdir(output_dir) 
                          if os.path.isdir(os.path.join(output_dir, d)) and d.startswith(('001_', '002_', '003_'))]
    
    logger.info(f"총 {len(announcement_folders)}개 공고 폴더 생성됨")
    
    total_items = len(announcement_folders)
    successful_items = 0
    total_attachments = 0
    korean_files = 0
    url_check_passed = 0
    file_size_total = 0
    
    for folder_name in announcement_folders[:10]:  # 상위 10개만 검증
        folder_path = os.path.join(output_dir, folder_name)
        
        # content.md 파일 확인
        content_file = os.path.join(folder_path, 'content.md')
        if os.path.exists(content_file):
            successful_items += 1
            
            # 원본 URL 포함 확인
            with open(content_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if '**원본 URL**:' in content and 'busanit.or.kr' in content:
                    url_check_passed += 1
        
        # 첨부파일 확인
        attachments_dir = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_dir):
            attachment_files = os.listdir(attachments_dir)
            total_attachments += len(attachment_files)
            
            # 첨부파일 상세 분석
            for filename in attachment_files:
                # 한글 파일명 확인
                if any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename):
                    korean_files += 1
                
                # 파일 크기 확인
                att_path = os.path.join(attachments_dir, filename)
                if os.path.exists(att_path):
                    file_size = os.path.getsize(att_path)
                    file_size_total += file_size
                    logger.info(f"  - {filename}: {file_size:,} bytes")
                    
                    # 파일 형식 분석
                    file_ext = filename.lower().split('.')[-1] if '.' in filename else 'unknown'
                    logger.debug(f"    파일 형식: {file_ext}")
    
    # 결과 요약
    success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
    avg_file_size = file_size_total / total_attachments if total_attachments > 0 else 0
    
    logger.info("=== 검증 결과 요약 ===")
    logger.info(f"총 공고 수: {total_items}")
    logger.info(f"성공적 처리: {successful_items} ({success_rate:.1f}%)")
    logger.info(f"원본 URL 포함: {url_check_passed}")
    logger.info(f"총 첨부파일: {total_attachments}")
    logger.info(f"한글 파일명: {korean_files}")
    logger.info(f"총 파일 용량: {file_size_total:,} bytes")
    logger.info(f"평균 파일 크기: {avg_file_size:,.0f} bytes")
    
    # 첨부파일 타입 분석
    if total_attachments > 0:
        logger.info("=== 첨부파일 분석 ===")
        file_types = {}
        for folder_name in announcement_folders[:10]:
            attachments_dir = os.path.join(output_dir, folder_name, 'attachments')
            if os.path.exists(attachments_dir):
                for filename in os.listdir(attachments_dir):
                    ext = filename.lower().split('.')[-1] if '.' in filename else 'unknown'
                    file_types[ext] = file_types.get(ext, 0) + 1
        
        for ext, count in sorted(file_types.items()):
            logger.info(f"  {ext.upper()}: {count}개")
    
    if success_rate >= 80:
        logger.info("✅ 테스트 성공!")
    else:
        logger.warning(f"⚠️ 성공률이 낮습니다: {success_rate:.1f}%")

def test_single_page():
    """단일 페이지 테스트"""
    logger.info("=== 단일 페이지 테스트 ===")
    test_busanit_scraper(pages=1)

def test_three_pages():
    """3페이지 테스트"""
    logger.info("=== 3페이지 테스트 ===")
    test_busanit_scraper(pages=3)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='BUSANIT Enhanced 스크래퍼 테스트')
    parser.add_argument('--pages', type=int, default=3, help='테스트할 페이지 수 (기본값: 3)')
    parser.add_argument('--single', action='store_true', help='단일 페이지 테스트')
    
    args = parser.parse_args()
    
    if args.single:
        test_single_page()
    else:
        test_busanit_scraper(pages=args.pages)