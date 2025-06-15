#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced DGDP 스크래퍼 테스트
"""

import os
import sys
import logging
import time
from enhanced_dgdp_scraper import EnhancedDGDPScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('dgdp_scraper.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def test_dgdp_scraper(pages=3):
    """DGDP 스크래퍼 테스트 - 3페이지까지"""
    logger.info("=== Enhanced DGDP 스크래퍼 테스트 시작 ===")
    
    # 출력 디렉토리 설정
    output_dir = "output/dgdp"
    os.makedirs(output_dir, exist_ok=True)
    
    # 스크래퍼 초기화
    scraper = EnhancedDGDPScraper()
    
    try:
        # 스크래핑 실행
        start_time = time.time()
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        end_time = time.time()
        
        logger.info(f"스크래핑 완료 - 소요시간: {end_time - start_time:.2f}초")
        
        # 결과 검증
        verify_results(output_dir)
        
    except Exception as e:
        logger.error(f"스크래퍼 실행 중 오류: {e}")
        raise
    
    logger.info("=== Enhanced DGDP 스크래퍼 테스트 완료 ===")

def verify_results(output_dir):
    """결과 검증"""
    logger.info("=== 결과 검증 시작 ===")
    
    if not os.path.exists(output_dir):
        logger.error(f"출력 디렉토리가 존재하지 않습니다: {output_dir}")
        return
    
    # 생성된 폴더들 확인
    folders = [d for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d))]
    folders.sort()
    
    logger.info(f"총 {len(folders)}개 공고 폴더 생성됨")
    
    total_items = len(folders)
    successful_items = 0
    content_check_passed = 0
    attachment_check_passed = 0
    url_check_passed = 0
    korean_files = 0
    total_attachments = 0
    
    for folder in folders:
        folder_path = os.path.join(output_dir, folder)
        
        # 1. content.md 파일 확인
        content_file = os.path.join(folder_path, 'content.md')
        if os.path.exists(content_file):
            content_check_passed += 1
            
            # content.md 내용 확인
            with open(content_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 원본 URL 포함 확인
            if '**원본 URL**:' in content and 'dgdp.or.kr' in content:
                url_check_passed += 1
        
        # 2. 첨부파일 확인
        attachments_folder = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_folder):
            attachment_files = [f for f in os.listdir(attachments_folder) if os.path.isfile(os.path.join(attachments_folder, f))]
            
            if attachment_files:
                attachment_check_passed += 1
                total_attachments += len(attachment_files)
                
                # 한글 파일명 확인
                for filename in attachment_files:
                    # 한글이 포함된 파일명 확인
                    has_korean = any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename)
                    if has_korean:
                        korean_files += 1
                    
                    # 파일 크기 확인
                    att_path = os.path.join(attachments_folder, filename)
                    file_size = os.path.getsize(att_path)
                    logger.info(f"  - {filename} ({file_size:,} bytes)")
        
        # 성공적인 처리 판정 (content.md 존재하면 성공)
        if os.path.exists(content_file):
            successful_items += 1
    
    # 결과 요약
    success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
    
    logger.info("=== 검증 결과 요약 ===")
    logger.info(f"총 처리 항목: {total_items}개")
    logger.info(f"성공 항목: {successful_items}개 ({success_rate:.1f}%)")
    logger.info(f"Content 파일 생성: {content_check_passed}개")
    logger.info(f"첨부파일 보유 공고: {attachment_check_passed}개")
    logger.info(f"총 첨부파일 수: {total_attachments}개")
    logger.info(f"한글 파일명: {korean_files}개")
    logger.info(f"원본 URL 포함: {url_check_passed}개")
    
    # 상세 폴더 정보
    logger.info("=== 생성된 폴더 목록 ===")
    for i, folder in enumerate(folders[:10], 1):  # 처음 10개만 출력
        logger.info(f"{i:2d}. {folder}")
    
    if len(folders) > 10:
        logger.info(f"... 외 {len(folders) - 10}개 추가")
    
    # 첨부파일 상세 정보
    if attachment_check_passed > 0:
        logger.info("=== 첨부파일 상세 정보 ===")
        count = 0
        for folder in folders:
            if count >= 5:  # 처음 5개 폴더만
                break
            
            attachments_folder = os.path.join(output_dir, folder, 'attachments')
            if os.path.exists(attachments_folder):
                attachment_files = [f for f in os.listdir(attachments_folder) if os.path.isfile(os.path.join(attachments_folder, f))]
                if attachment_files:
                    logger.info(f"📁 {folder}:")
                    for filename in attachment_files:
                        att_path = os.path.join(attachments_folder, filename)
                        file_size = os.path.getsize(att_path)
                        logger.info(f"  📄 {filename} ({file_size:,} bytes)")
                    count += 1
    
    logger.info("=== 결과 검증 완료 ===")

if __name__ == "__main__":
    test_dgdp_scraper()