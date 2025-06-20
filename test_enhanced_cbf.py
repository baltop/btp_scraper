#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CBF (춘천바이오산업진흥원) 스크래퍼 테스트
"""

import os
import sys
import logging
import re

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_cbf_scraper import EnhancedCbfScraper

def setup_logging():
    """로깅 설정"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )

def test_cbf_scraper(pages=3):
    """CBF 스크래퍼 테스트"""
    logger = logging.getLogger(__name__)
    logger.info(f"{pages}페이지 테스트 시작")
    
    # 스크래퍼 생성
    scraper = EnhancedCbfScraper()
    
    # 3페이지 완전 실행을 위해 중복 체크 비활성화
    scraper.enable_duplicate_check = False
    
    # 출력 디렉토리 설정
    output_dir = "output/cbf"
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info("=== CBF 스크래퍼 테스트 시작 ===")
    
    # 스크래핑 실행
    scraper.scrape_pages(max_pages=pages, output_base=output_dir)
    
    logger.info("=== 스크래핑 완료 ===")
    return output_dir

def verify_results(output_dir):
    """결과 검증"""
    logger = logging.getLogger(__name__)
    logger.info("=== 결과 검증 시작 ===")
    
    if not os.path.exists(output_dir):
        logger.error(f"출력 디렉토리가 존재하지 않습니다: {output_dir}")
        return False
    
    # 폴더 수 확인
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
            try:
                with open(content_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if '**원본 URL**:' in content and 'cbf.or.kr' in content:
                        url_check_passed += 1
            except Exception as e:
                logger.warning(f"content.md 읽기 실패 {folder_name}: {e}")
        
        # 첨부파일 확인
        attachments_dir = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_dir):
            for filename in os.listdir(attachments_dir):
                if os.path.isfile(os.path.join(attachments_dir, filename)):
                    total_attachments += 1
                    
                    # 한글 파일명 확인
                    if any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename):
                        korean_files += 1
                    
                    # 파일 크기 확인
                    att_path = os.path.join(attachments_dir, filename)
                    try:
                        file_size = os.path.getsize(att_path)
                        file_size_total += file_size
                    except Exception as e:
                        logger.warning(f"파일 크기 확인 실패 {filename}: {e}")
    
    # 성공률 계산
    success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
    
    logger.info("=== 검증 결과 요약 ===")
    logger.info(f"총 공고 수: {total_items}")
    logger.info(f"성공적 처리: {successful_items} ({success_rate:.1f}%)")
    logger.info(f"원본 URL 포함: {url_check_passed}")
    logger.info(f"총 첨부파일: {total_attachments}")
    logger.info(f"한글 파일명: {korean_files}")
    logger.info(f"총 파일 용량: {file_size_total:,} bytes")
    
    if success_rate >= 80:
        logger.info("✓ 검증 통과: 80% 이상 성공적으로 처리됨")
        result = True
    else:
        logger.warning("✗ 검증 실패: 성공률이 80% 미만")
        result = False
    
    if total_attachments == 0:
        logger.info("ℹ 첨부파일이 없는 사이트이거나 다운로드 실패")
    
    return result

def main():
    """메인 함수"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # 3페이지 테스트 실행
        output_dir = test_cbf_scraper(pages=3)
        
        # 결과 검증
        verification_passed = verify_results(output_dir)
        
        if verification_passed:
            logger.info("테스트 성공적으로 완료됨")
        else:
            logger.warning("테스트에서 일부 문제 발견됨")
            
    except Exception as e:
        logger.error(f"테스트 실행 중 오류 발생: {e}")
        raise
    
    logger.info("테스트 완료")

if __name__ == "__main__":
    main()