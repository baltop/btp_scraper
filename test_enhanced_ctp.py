#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
충남테크노파크(CTP) Enhanced 스크래퍼 테스트 스크립트
"""

import os
import sys
import logging
from enhanced_ctp_scraper import EnhancedCTPScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('ctp_scraper.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def test_ctp_scraper(pages=3):
    """CTP 스크래퍼 테스트"""
    logger.info("=== CTP Enhanced 스크래퍼 테스트 시작 ===")
    
    # 스크래퍼 초기화
    scraper = EnhancedCTPScraper()
    
    # 출력 디렉토리 설정 (표준 패턴)
    output_dir = "output/ctp"
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # 스크래핑 실행
        logger.info(f"CTP 스크래핑 시작 - 최대 {pages}페이지")
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        
        logger.info("=== CTP 스크래핑 완료 ===")
        
        # 결과 검증
        verify_results(output_dir)
        
    except Exception as e:
        logger.error(f"스크래핑 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

def verify_results(output_dir):
    """결과 검증 - 표준 패턴"""
    logger.info("=== 결과 검증 시작 ===")
    
    if not os.path.exists(output_dir):
        logger.error(f"출력 디렉토리가 존재하지 않습니다: {output_dir}")
        return
    
    # 공고 폴더 목록
    announcement_folders = [d for d in os.listdir(output_dir) 
                          if os.path.isdir(os.path.join(output_dir, d))]
    
    total_items = len(announcement_folders)
    successful_items = 0
    url_check_passed = 0
    category_check_passed = 0
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
            
            # 파일 내용 확인
            try:
                with open(content_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # 원본 URL 포함 확인
                    if '**원본 URL**:' in content and 'ctp.or.kr' in content:
                        url_check_passed += 1
                    
                    # 카테고리 정보 확인 (CTP는 카테고리가 없을 수 있음)
                    if '**카테고리**:' in content:
                        category_check_passed += 1
                        
            except Exception as e:
                logger.warning(f"content.md 읽기 실패 {folder_name}: {e}")
        
        # 첨부파일 확인
        attachments_dir = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_dir):
            attachment_files = os.listdir(attachments_dir)
            total_attachments += len(attachment_files)
            
            for filename in attachment_files:
                # 한글 파일명 확인
                has_korean = any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename)
                if has_korean:
                    korean_files += 1
                
                # 파일 크기 확인
                att_path = os.path.join(attachments_dir, filename)
                try:
                    file_size = os.path.getsize(att_path)
                    file_size_total += file_size
                    
                    if file_size == 0:
                        logger.warning(f"빈 파일 발견: {filename}")
                        
                except Exception as e:
                    logger.warning(f"파일 크기 확인 실패 {filename}: {e}")
    
    # 성공률 계산
    success_rate = (successful_items / total_items * 100) if total_items > 0 else 0
    url_rate = (url_check_passed / total_items * 100) if total_items > 0 else 0
    category_rate = (category_check_passed / total_items * 100) if total_items > 0 else 0
    korean_rate = (korean_files / total_attachments * 100) if total_attachments > 0 else 0
    
    # 결과 출력
    logger.info("=== 검증 결과 요약 ===")
    logger.info(f"총 공고 수: {total_items}")
    logger.info(f"성공적 처리: {successful_items} ({success_rate:.1f}%)")
    logger.info(f"원본 URL 포함: {url_check_passed} ({url_rate:.1f}%)")
    logger.info(f"카테고리 정보 포함: {category_check_passed} ({category_rate:.1f}%)")
    logger.info(f"총 첨부파일: {total_attachments}")
    logger.info(f"한글 파일명: {korean_files} ({korean_rate:.1f}%)")
    logger.info(f"총 파일 용량: {file_size_total:,} bytes")
    
    # 성공 여부 판단
    if success_rate >= 80:
        logger.info("✅ 테스트 통과! (성공률 80% 이상)")
        
        if total_attachments > 0:
            logger.info("✅ 첨부파일 다운로드 기능 정상 작동")
        else:
            logger.warning("⚠️  첨부파일이 없거나 다운로드되지 않았습니다")
            
        return True
    else:
        logger.error("❌ 테스트 실패! (성공률 80% 미만)")
        return False

def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='CTP Enhanced 스크래퍼 테스트')
    parser.add_argument('--pages', type=int, default=3, help='테스트할 페이지 수 (기본: 3)')
    parser.add_argument('--single', action='store_true', help='단일 페이지만 테스트')
    
    args = parser.parse_args()
    
    pages = 1 if args.single else args.pages
    test_ctp_scraper(pages)

if __name__ == "__main__":
    main()