#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DIP 스크래퍼 테스트 스크립트
"""

import os
import sys
import logging
from enhanced_dip_scraper import EnhancedDipScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def test_dip_scraper(pages=3):
    """DIP 스크래퍼 테스트"""
    logger.info("=== DIP 스크래퍼 테스트 시작 ===")
    
    # 스크래퍼 초기화
    scraper = EnhancedDipScraper()
    # 테스트를 위해 중복 검사 비활성화
    scraper.enable_duplicate_check = False
    
    # 출력 디렉토리 설정
    output_dir = "output/dip"
    os.makedirs(output_dir, exist_ok=True)
    
    # 스크래핑 실행
    try:
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        logger.info("=== DIP 스크래퍼 테스트 완료 ===")
        
        # 결과 검증
        verify_results(output_dir)
        
    except Exception as e:
        logger.error(f"테스트 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

def verify_results(output_dir):
    """결과 검증"""
    logger.info("=== 결과 검증 시작 ===")
    
    try:
        # 출력 디렉토리 내 폴더 개수 확인
        if not os.path.exists(output_dir):
            logger.warning(f"출력 디렉토리가 존재하지 않습니다: {output_dir}")
            return
        
        announcement_folders = [d for d in os.listdir(output_dir) 
                              if os.path.isdir(os.path.join(output_dir, d)) and not d.startswith('.')]
        
        total_items = len(announcement_folders)
        successful_items = 0
        total_attachments = 0
        korean_files = 0
        file_size_total = 0
        url_check_passed = 0
        
        logger.info(f"총 {total_items}개 공고 폴더 발견")
        
        for folder_name in announcement_folders:
            folder_path = os.path.join(output_dir, folder_name)
            
            # content.md 파일 확인
            content_file = os.path.join(folder_path, 'content.md')
            if os.path.exists(content_file):
                successful_items += 1
                
                # 원본 URL 포함 확인
                try:
                    with open(content_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if '**원본 URL**:' in content and 'dip.or.kr' in content:
                            url_check_passed += 1
                except Exception as e:
                    logger.warning(f"파일 읽기 오류 {content_file}: {e}")
            
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
                        try:
                            file_size = os.path.getsize(att_path)
                            file_size_total += file_size
                            logger.debug(f"첨부파일: {filename} ({file_size:,} bytes)")
                        except Exception as e:
                            logger.warning(f"파일 크기 확인 오류 {att_path}: {e}")
        
        # 성공률 계산
        success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
        url_success_rate = (url_check_passed / successful_items) * 100 if successful_items > 0 else 0
        korean_rate = (korean_files / total_attachments) * 100 if total_attachments > 0 else 0
        
        logger.info("=== 검증 결과 요약 ===")
        logger.info(f"총 공고 수: {total_items}")
        logger.info(f"성공적 처리: {successful_items} ({success_rate:.1f}%)")
        logger.info(f"원본 URL 포함: {url_check_passed} ({url_success_rate:.1f}%)")
        logger.info(f"총 첨부파일: {total_attachments}")
        logger.info(f"한글 파일명: {korean_files} ({korean_rate:.1f}%)")
        logger.info(f"총 파일 용량: {file_size_total:,} bytes")
        
        if success_rate >= 80:
            logger.info("✅ 테스트 통과! (성공률 80% 이상)")
        else:
            logger.warning("⚠️ 테스트 부분 통과 (성공률 80% 미만)")
        
        if total_attachments > 0:
            logger.info("✅ 첨부파일 다운로드 기능 정상 작동")
        else:
            logger.warning("⚠️ 첨부파일이 다운로드되지 않았습니다")
        
    except Exception as e:
        logger.error(f"결과 검증 중 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='DIP 스크래퍼 테스트')
    parser.add_argument('--pages', type=int, default=3, help='테스트할 페이지 수 (기본: 3)')
    parser.add_argument('--single', action='store_true', help='단일 페이지만 테스트')
    
    args = parser.parse_args()
    
    pages = 1 if args.single else args.pages
    test_dip_scraper(pages)