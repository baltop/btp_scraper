#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ATCENTER Enhanced 스크래퍼 테스트
"""

import os
import sys
import logging
from enhanced_atcenter_scraper import EnhancedAtcenterScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def test_atcenter_scraper(pages=3):
    """ATCENTER 스크래퍼 테스트"""
    logger.info("=== ATCENTER Enhanced 스크래퍼 테스트 시작 ===")
    
    # 출력 디렉토리 설정
    output_dir = "output/atcenter"
    os.makedirs(output_dir, exist_ok=True)
    
    # 스크래퍼 초기화
    scraper = EnhancedAtcenterScraper()
    
    try:
        logger.info(f"{pages}페이지까지 스크래핑 시작")
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        
        logger.info("=== 스크래핑 완료 ===")
        
        # 결과 검증
        verify_results(output_dir)
        
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

def verify_results(output_dir):
    """결과 검증"""
    logger.info("=== 결과 검증 시작 ===")
    
    try:
        # 공고 폴더 확인
        if not os.path.exists(output_dir):
            logger.error("출력 디렉토리가 존재하지 않습니다")
            return
        
        announcement_folders = [d for d in os.listdir(output_dir) 
                              if os.path.isdir(os.path.join(output_dir, d))]
        
        total_items = len(announcement_folders)
        successful_items = 0
        url_check_passed = 0
        atcenter_check_passed = 0
        total_attachments = 0
        korean_files = 0
        file_size_total = 0
        
        logger.info(f"총 {total_items}개 공고 폴더 발견")
        
        for folder_name in announcement_folders:
            folder_path = os.path.join(output_dir, folder_name)
            
            # content.md 파일 확인
            content_file = os.path.join(folder_path, 'content.md')
            if os.path.exists(content_file):
                successful_items += 1
                
                # content.md 내용 확인
                with open(content_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # 원본 URL 포함 확인
                    if '**원본 URL**:' in content and 'at.or.kr' in content:
                        url_check_passed += 1
                    
                    # ATCENTER 연동 확인
                    if 'ATCENTER 목록 URL' in content or 'at.or.kr' in content:
                        atcenter_check_passed += 1
            
            # 첨부파일 확인
            attachments_dir = os.path.join(folder_path, 'attachments')
            if os.path.exists(attachments_dir):
                for filename in os.listdir(attachments_dir):
                    total_attachments += 1
                    
                    # 한글 파일명 확인
                    has_korean = any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename)
                    if has_korean:
                        korean_files += 1
                    
                    # 파일 크기 확인
                    att_path = os.path.join(attachments_dir, filename)
                    file_size = os.path.getsize(att_path)
                    file_size_total += file_size
        
        # 성공률 계산
        success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
        url_rate = (url_check_passed / total_items) * 100 if total_items > 0 else 0
        atcenter_rate = (atcenter_check_passed / total_items) * 100 if total_items > 0 else 0
        
        # 결과 출력
        logger.info("=== 검증 결과 요약 ===")
        logger.info(f"총 공고 수: {total_items}")
        logger.info(f"성공적 처리: {successful_items} ({success_rate:.1f}%)")
        logger.info(f"원본 URL 포함: {url_check_passed} ({url_rate:.1f}%)")
        logger.info(f"ATCENTER 연동 확인: {atcenter_check_passed} ({atcenter_rate:.1f}%)")
        logger.info(f"총 첨부파일: {total_attachments}")
        logger.info(f"한글 파일명: {korean_files}")
        logger.info(f"총 파일 용량: {file_size_total:,} bytes")
        
        # ATCENTER 특화 검증
        logger.info("\n=== ATCENTER 특화 검증 ===")
        logger.info(f"농업기술실용화재단 처리: {'✅' if atcenter_rate >= 90 else '❌'}")
        logger.info(f"ATCENTER 연동 성공률: {atcenter_rate:.1f}%")
        
        # 성공 여부 판단
        if success_rate >= 80:
            logger.info("✅ 테스트 통과 (성공률 80% 이상)")
        else:
            logger.warning("⚠️ 테스트 주의 (성공률 80% 미만)")
        
        # 샘플 확인
        if announcement_folders:
            sample_folder = announcement_folders[0]
            sample_path = os.path.join(output_dir, sample_folder)
            content_file = os.path.join(sample_path, 'content.md')
            
            if os.path.exists(content_file):
                logger.info(f"\n=== 샘플 확인: {sample_folder} ===")
                with open(content_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    preview = content[:500] + "..." if len(content) > 500 else content
                    logger.info(f"내용 미리보기:\n{preview}")
        
        return success_rate >= 80
        
    except Exception as e:
        logger.error(f"검증 중 오류 발생: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='ATCENTER 스크래퍼 테스트')
    parser.add_argument('--pages', type=int, default=3, help='스크래핑할 페이지 수 (기본값: 3)')
    
    args = parser.parse_args()
    
    test_atcenter_scraper(args.pages)