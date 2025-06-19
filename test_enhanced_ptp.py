#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced PTP 스크래퍼 테스트 스크립트
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_ptp_scraper import EnhancedPtpScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('ptp_scraper.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def test_ptp_scraper(pages=3):
    """PTP 스크래퍼 테스트 - 기본 3페이지"""
    logger.info("=== Enhanced PTP 스크래퍼 테스트 시작 ===")
    
    # 출력 디렉토리 설정 (표준 규칙: output/사이트명)
    output_dir = "output/ptp"
    os.makedirs(output_dir, exist_ok=True)
    
    # 스크래퍼 초기화
    scraper = EnhancedPtpScraper()
    # 테스트를 위해 중복 체크 비활성화
    scraper.enable_duplicate_check = False
    
    try:
        # 스크래핑 실행
        logger.info(f"PTP 사이트 스크래핑 시작 - {pages}페이지")
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        
        logger.info("=== 스크래핑 완료 ===")
        
        # 결과 검증
        verify_results(output_dir)
        
    except Exception as e:
        logger.error(f"스크래핑 중 오류 발생: {e}")
        raise
    
    finally:
        logger.info("=== PTP 테스트 완료 ===")

def verify_results(output_dir):
    """결과 검증 - 첨부파일 다운로드 상태 필수 확인"""
    logger.info("=== 결과 검증 시작 ===")
    
    if not os.path.exists(output_dir):
        logger.error(f"출력 디렉토리가 존재하지 않습니다: {output_dir}")
        return
    
    # 공고 폴더 목록
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
                    if '**원본 URL**:' in content and 'ptp.or.kr' in content:
                        url_check_passed += 1
            except Exception as e:
                logger.warning(f"content.md 읽기 실패 {folder_name}: {e}")
        
        # 첨부파일 검증
        attachments_dir = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_dir):
            try:
                attachment_files = os.listdir(attachments_dir)
                folder_attachments = len(attachment_files)
                total_attachments += folder_attachments
                
                logger.info(f"  {folder_name}: {folder_attachments}개 첨부파일")
                
                for filename in attachment_files:
                    att_path = os.path.join(attachments_dir, filename)
                    
                    # 한글 파일명 확인
                    has_korean = any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename)
                    if has_korean:
                        korean_files += 1
                        logger.info(f"    한글 파일명: {filename}")
                    
                    # 파일 크기 확인
                    if os.path.exists(att_path):
                        file_size = os.path.getsize(att_path)
                        file_size_total += file_size
                        if file_size == 0:
                            logger.warning(f"    빈 파일: {filename}")
                        else:
                            logger.info(f"    파일 크기: {filename} ({file_size:,} bytes)")
                    
            except Exception as e:
                logger.error(f"첨부파일 검증 오류 {folder_name}: {e}")
    
    # 성공률 계산
    success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
    url_success_rate = (url_check_passed / total_items) * 100 if total_items > 0 else 0
    
    # 결과 출력
    logger.info("=" * 50)
    logger.info("=== 검증 결과 요약 ===")
    logger.info(f"총 공고 수: {total_items}")
    logger.info(f"성공적 처리: {successful_items} ({success_rate:.1f}%)")
    logger.info(f"URL 포함 확인: {url_check_passed} ({url_success_rate:.1f}%)")
    logger.info(f"총 첨부파일: {total_attachments}개")
    logger.info(f"한글 파일명: {korean_files}개")
    logger.info(f"총 파일 용량: {file_size_total:,} bytes ({file_size_total/1024/1024:.1f} MB)")
    
    # 첨부파일이 있는 공고 비율
    folders_with_attachments = sum(1 for folder in announcement_folders 
                                 if os.path.exists(os.path.join(output_dir, folder, 'attachments')))
    attachment_rate = (folders_with_attachments / total_items) * 100 if total_items > 0 else 0
    logger.info(f"첨부파일 보유 공고: {folders_with_attachments}개 ({attachment_rate:.1f}%)")
    
    # 품질 평가
    if success_rate >= 80:
        logger.info("✅ 스크래핑 품질: 우수")
    elif success_rate >= 60:
        logger.info("⚠️  스크래핑 품질: 양호")
    else:
        logger.warning("❌ 스크래핑 품질: 개선 필요")
    
    logger.info("=" * 50)

def main():
    parser = argparse.ArgumentParser(description='Enhanced PTP 스크래퍼 테스트')
    parser.add_argument('--pages', type=int, default=3, help='테스트할 페이지 수 (기본: 3)')
    parser.add_argument('--single', action='store_true', help='단일 페이지만 테스트')
    
    args = parser.parse_args()
    
    if args.single:
        pages = 1
    else:
        pages = args.pages
    
    test_ptp_scraper(pages)

if __name__ == "__main__":
    main()