#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GIPA Enhanced 스크래퍼 테스트 스크립트
"""

import logging
import os
import sys
from enhanced_gipa_scraper import EnhancedGIPAScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('gipa_scraper.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def test_gipa_scraper(pages=3):
    """GIPA 스크래퍼 테스트"""
    logger.info("=== GIPA Enhanced 스크래퍼 테스트 시작 ===")
    
    try:
        # 스크래퍼 초기화
        scraper = EnhancedGIPAScraper()
        
        # 출력 디렉토리 설정 - output/gipa
        output_dir = "output/gipa"
        os.makedirs(output_dir, exist_ok=True)
        
        # 스크래핑 실행
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        
        logger.info("=== GIPA 스크래퍼 테스트 완료 ===")
        
        # 결과 검증
        verify_results(output_dir)
        
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}")
        raise

def verify_results(output_dir):
    """결과 검증"""
    logger.info("=== 결과 검증 시작 ===")
    
    if not os.path.exists(output_dir):
        logger.error(f"출력 디렉토리가 존재하지 않습니다: {output_dir}")
        return
    
    # 공고 폴더 수집
    announcement_folders = [d for d in os.listdir(output_dir) 
                          if os.path.isdir(os.path.join(output_dir, d))]
    
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
            with open(content_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if '**원본 URL**:' in content and 'gipa.or.kr' in content:
                    url_check_passed += 1
        
        # 첨부파일 검증
        attachments_dir = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_dir):
            for filename in os.listdir(attachments_dir):
                total_attachments += 1
                
                # 한글 파일명 검증
                has_korean = any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename)
                if has_korean:
                    korean_files += 1
                
                # 파일 크기 검증
                file_path = os.path.join(attachments_dir, filename)
                if os.path.isfile(file_path):
                    file_size = os.path.getsize(file_path)
                    file_size_total += file_size
                    
                    # 파일 크기가 0이면 경고
                    if file_size == 0:
                        logger.warning(f"빈 파일 발견: {filename}")
    
    # 성공률 계산
    success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
    url_success_rate = (url_check_passed / successful_items) * 100 if successful_items > 0 else 0
    
    logger.info("=== 검증 결과 요약 ===")
    logger.info(f"총 공고 수: {total_items}")
    logger.info(f"성공적 처리: {successful_items} ({success_rate:.1f}%)")
    logger.info(f"원본 URL 포함: {url_check_passed} ({url_success_rate:.1f}%)")
    logger.info(f"총 첨부파일: {total_attachments}")
    logger.info(f"한글 파일명: {korean_files}")
    logger.info(f"총 파일 용량: {file_size_total:,} bytes")
    
    # 첨부파일이 있는 공고 예시 출력
    if total_attachments > 0:
        logger.info("=== 첨부파일 예시 ===")
        count = 0
        for folder_name in announcement_folders:
            if count >= 3:  # 최대 3개만 출력
                break
            attachments_dir = os.path.join(output_dir, folder_name, 'attachments')
            if os.path.exists(attachments_dir):
                files = os.listdir(attachments_dir)
                if files:
                    logger.info(f"폴더: {folder_name}")
                    for file in files[:2]:  # 폴더당 최대 2개 파일만 출력
                        file_path = os.path.join(attachments_dir, file)
                        file_size = os.path.getsize(file_path)
                        logger.info(f"  - {file} ({file_size:,} bytes)")
                    count += 1
    
    # 성공률이 80% 이상이면 통과
    if success_rate >= 80:
        logger.info("✅ 테스트 통과 (성공률 80% 이상)")
    else:
        logger.warning(f"⚠️ 테스트 주의 (성공률 {success_rate:.1f}%)")
    
    return success_rate >= 80

if __name__ == "__main__":
    test_gipa_scraper(pages=3)