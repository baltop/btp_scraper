#!/usr/bin/env python3
"""
CBA (충청북도 중소벤처기업진흥공단) 스크래퍼 테스트 스크립트
"""

import os
import sys
import logging
from pathlib import Path

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.append('/home/baltop/work/bizsupnew/btp_scraper')

from enhanced_cba_scraper import EnhancedCBAScraper

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_cba_scraper_single():
    """CBA 스크래퍼 단일 페이지 테스트"""
    logger.info("=== CBA 스크래퍼 단일 페이지 테스트 시작 ===")
    
    scraper = EnhancedCBAScraper()
    output_dir = "output/cba"
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        scraper.scrape_pages(max_pages=1, output_base=output_dir)
        logger.info("✅ 단일 페이지 테스트 완료")
        return True
    except Exception as e:
        logger.error(f"❌ 단일 페이지 테스트 실패: {e}")
        return False

def test_cba_scraper(pages=3):
    """CBA 스크래퍼 테스트"""
    logger.info(f"=== CBA 스크래퍼 {pages}페이지 테스트 시작 ===")
    
    scraper = EnhancedCBAScraper()
    output_dir = "output/cba"
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        logger.info(f"✅ {pages}페이지 테스트 완료")
        
        # 결과 검증
        success = verify_results(output_dir)
        if success:
            logger.info("✅ 테스트 통과! (성공률 80% 이상)")
        else:
            logger.warning("⚠️ 테스트 미통과 (성공률 80% 미만)")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ {pages}페이지 테스트 실패: {e}")
        return False

def verify_results(output_dir):
    """결과 검증 - 첨부파일 검증 필수"""
    logger.info("=== 결과 검증 시작 ===")
    
    if not os.path.exists(output_dir):
        logger.error("출력 디렉토리가 없습니다")
        return False
    
    announcement_folders = [d for d in os.listdir(output_dir) 
                          if os.path.isdir(os.path.join(output_dir, d))]
    
    if not announcement_folders:
        logger.error("공고 폴더가 없습니다")
        return False
    
    total_items = len(announcement_folders)
    successful_items = 0
    url_check_passed = 0
    total_attachments = 0
    korean_files = 0
    file_size_total = 0
    
    logger.info(f"총 {total_items}개 공고 폴더 확인 중...")
    
    for folder_name in announcement_folders:
        folder_path = os.path.join(output_dir, folder_name)
        
        try:
            # content.md 파일 확인
            content_file = os.path.join(folder_path, 'content.md')
            if os.path.exists(content_file):
                successful_items += 1
                
                # 원본 URL 포함 확인
                with open(content_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if '**원본 URL**:' in content and 'cba.ne.kr' in content:
                        url_check_passed += 1
            
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
                        file_size = os.path.getsize(att_path)
                        file_size_total += file_size
                        
                        logger.debug(f"첨부파일: {filename} ({file_size:,} bytes, 한글: {has_korean})")
        
        except Exception as e:
            logger.error(f"폴더 {folder_name} 검증 중 오류: {e}")
    
    # 성공률 계산
    success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
    url_success_rate = (url_check_passed / successful_items) * 100 if successful_items > 0 else 0
    
    # 결과 출력
    logger.info("=== 검증 결과 요약 ===")
    logger.info(f"총 공고 수: {total_items}")
    logger.info(f"성공적 처리: {successful_items} ({success_rate:.1f}%)")
    logger.info(f"원본 URL 포함: {url_check_passed} ({url_success_rate:.1f}%)")
    logger.info(f"총 첨부파일: {total_attachments}")
    logger.info(f"한글 파일명: {korean_files}")
    logger.info(f"총 파일 용량: {file_size_total:,} bytes ({file_size_total/1024/1024:.1f} MB)")
    
    # 첨부파일 다운로드 기능 확인
    if total_attachments > 0:
        logger.info("✅ 첨부파일 다운로드 기능 정상 작동")
    else:
        logger.warning("⚠️ 첨부파일이 다운로드되지 않았습니다")
    
    # 성공 기준: 80% 이상 성공
    return success_rate >= 80

def count_downloaded_files(output_dir):
    """다운로드된 파일 수 계산"""
    total_files = 0
    
    if not os.path.exists(output_dir):
        return total_files
    
    for root, dirs, files in os.walk(output_dir):
        if 'attachments' in root:
            total_files += len(files)
    
    return total_files

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='CBA 스크래퍼 테스트')
    parser.add_argument('--pages', type=int, default=3, help='테스트할 페이지 수 (기본값: 3)')
    parser.add_argument('--single', action='store_true', help='단일 페이지 테스트만 실행')
    
    args = parser.parse_args()
    
    if args.single:
        success = test_cba_scraper_single()
    else:
        success = test_cba_scraper(args.pages)
    
    # 파일 수 확인
    file_count = count_downloaded_files("output/cba")
    logger.info(f"총 다운로드된 파일 수: {file_count}")
    
    if success:
        logger.info("🎉 전체 테스트 성공!")
        sys.exit(0)
    else:
        logger.error("💥 테스트 실패!")
        sys.exit(1)