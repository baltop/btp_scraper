#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JBTP 스크래퍼 테스트 스크립트
"""

import os
import sys
import logging
from enhanced_jbtp_scraper import EnhancedJbtpScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('jbtp_scraper.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def test_jbtp_scraper(pages=3):
    """JBTP 스크래퍼 테스트 - 기본값 3페이지"""
    logger.info("JBTP 스크래퍼 테스트 시작")
    
    # 스크래퍼 초기화
    scraper = EnhancedJbtpScraper()
    
    # 출력 디렉토리 설정 - 표준 형식
    output_dir = "output/jbtp"
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # 스크래핑 실행
        logger.info(f"{pages}페이지까지 스크래핑 시작")
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        
        # 결과 검증
        verify_results(output_dir)
        
    except Exception as e:
        logger.error(f"스크래핑 중 오류 발생: {e}")
        raise

def verify_results(output_dir):
    """결과 검증 - 첨부파일 검증 필수"""
    logger.info("=== 결과 검증 시작 ===")
    
    if not os.path.exists(output_dir):
        logger.error(f"출력 디렉토리가 존재하지 않습니다: {output_dir}")
        return
    
    # 공고 폴더들 찾기
    announcement_folders = [d for d in os.listdir(output_dir) 
                          if os.path.isdir(os.path.join(output_dir, d)) and d != '__pycache__']
    
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
                    if '**원본 URL**:' in content and 'jbtp.or.kr' in content:
                        url_check_passed += 1
            except Exception as e:
                logger.warning(f"content.md 파일 읽기 실패 {folder_name}: {e}")
        
        # 첨부파일 검증
        attachments_dir = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_dir):
            for filename in os.listdir(attachments_dir):
                total_attachments += 1
                
                # 한글 파일명 검증
                if any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename):
                    korean_files += 1
                
                # 파일 크기 검증
                att_path = os.path.join(attachments_dir, filename)
                if os.path.isfile(att_path):
                    file_size = os.path.getsize(att_path)
                    file_size_total += file_size
                    
                    logger.debug(f"첨부파일: {filename} ({file_size:,} bytes)")
    
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
    
    # 첨부파일이 있는 경우 상세 정보 출력
    if total_attachments > 0:
        logger.info("=== 첨부파일 상세 정보 ===")
        for folder_name in announcement_folders[:5]:  # 처음 5개만 확인
            folder_path = os.path.join(output_dir, folder_name)
            attachments_dir = os.path.join(folder_path, 'attachments')
            
            if os.path.exists(attachments_dir):
                files = os.listdir(attachments_dir)
                if files:
                    logger.info(f"폴더 {folder_name}: {len(files)}개 파일")
                    for filename in files[:3]:  # 처음 3개 파일만
                        att_path = os.path.join(attachments_dir, filename)
                        if os.path.isfile(att_path):
                            file_size = os.path.getsize(att_path)
                            logger.info(f"  - {filename} ({file_size:,} bytes)")
    
    # 검증 결과 평가
    if success_rate >= 80:
        logger.info("✅ 검증 성공: 80% 이상 성공률 달성")
        return True
    else:
        logger.warning(f"⚠️ 검증 경고: 성공률이 80% 미만입니다 ({success_rate:.1f}%)")
        return False

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='JBTP 스크래퍼 테스트')
    parser.add_argument('--pages', type=int, default=3, help='테스트할 페이지 수 (기본값: 3)')
    parser.add_argument('--single', action='store_true', help='1페이지만 테스트')
    
    args = parser.parse_args()
    
    if args.single:
        pages = 1
    else:
        pages = args.pages
    
    try:
        test_jbtp_scraper(pages)
        logger.info("테스트 완료!")
    except Exception as e:
        logger.error(f"테스트 실패: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()