#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
사회적기업진흥원(KOSEF) Enhanced 스크래퍼 테스트
"""

import os
import sys
import logging
import argparse
from enhanced_kosef_scraper import EnhancedKosefScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('kosef_scraper.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def test_kosef_scraper(pages=3):
    """사회적기업진흥원 스크래퍼 테스트"""
    logger.info("=== 사회적기업진흥원 Enhanced 스크래퍼 테스트 시작 ===")
    
    try:
        # 스크래퍼 초기화
        scraper = EnhancedKosefScraper()
        
        # 출력 디렉토리 설정 - 표준 형식
        output_dir = "output/kosef"
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"출력 디렉토리: {output_dir}")
        logger.info(f"대상 페이지 수: {pages}")
        logger.info(f"사이트 URL: {scraper.list_url}")
        
        # 스크래핑 실행
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        
        logger.info("=== 스크래핑 완료 ===")
        
        # 결과 검증
        verify_results(output_dir)
        
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}")
        raise

def verify_results(output_dir):
    """결과 검증 - 첨부파일 검증 필수"""
    logger.info("=== 결과 검증 시작 ===")
    
    if not os.path.exists(output_dir):
        logger.error(f"출력 디렉토리가 존재하지 않습니다: {output_dir}")
        return
    
    # 공고 폴더 목록 가져오기
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
                    if '**원본 URL**:' in content and 'socialenterprise.or.kr' in content:
                        url_check_passed += 1
            except Exception as e:
                logger.warning(f"content.md 읽기 실패 {folder_name}: {e}")
        
        # 첨부파일 검증
        attachments_dir = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_dir):
            attachment_files = os.listdir(attachments_dir)
            total_attachments += len(attachment_files)
            
            for filename in attachment_files:
                # 한글 파일명 검증
                has_korean = any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename)
                if has_korean:
                    korean_files += 1
                
                # 파일 크기 검증
                file_path = os.path.join(attachments_dir, filename)
                try:
                    file_size = os.path.getsize(file_path)
                    file_size_total += file_size
                    logger.debug(f"첨부파일: {filename} ({file_size:,} bytes)")
                except Exception as e:
                    logger.warning(f"파일 크기 확인 실패 {filename}: {e}")
    
    # 성공률 계산
    success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
    url_success_rate = (url_check_passed / successful_items) * 100 if successful_items > 0 else 0
    
    logger.info("=== 검증 결과 요약 ===")
    logger.info(f"총 공고 수: {total_items}")
    logger.info(f"성공적 처리: {successful_items} ({success_rate:.1f}%)")
    logger.info(f"원본 URL 포함: {url_check_passed} ({url_success_rate:.1f}%)")
    logger.info(f"총 첨부파일: {total_attachments}")
    logger.info(f"한글 파일명: {korean_files}")
    logger.info(f"총 파일 용량: {file_size_total:,} bytes ({file_size_total/1024/1024:.1f} MB)")
    
    # 첨부파일 상세 정보
    if total_attachments > 0:
        avg_file_size = file_size_total / total_attachments
        korean_ratio = (korean_files / total_attachments) * 100
        logger.info(f"평균 파일 크기: {avg_file_size:,.0f} bytes")
        logger.info(f"한글 파일명 비율: {korean_ratio:.1f}%")
    
    # 성공 기준 체크
    test_passed = success_rate >= 80
    
    if test_passed:
        logger.info("✅ 테스트 PASSED - 80% 이상 성공적으로 처리됨")
    else:
        logger.warning("❌ 테스트 FAILED - 성공률이 80% 미만")
    
    return test_passed

def main():
    parser = argparse.ArgumentParser(description='사회적기업진흥원 Enhanced 스크래퍼 테스트')
    parser.add_argument('--pages', type=int, default=3, help='스크래핑할 페이지 수 (기본값: 3)')
    parser.add_argument('--single', action='store_true', help='단일 페이지만 테스트')
    parser.add_argument('--debug', action='store_true', help='디버그 모드')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.single:
        pages = 1
    else:
        pages = args.pages
    
    try:
        test_kosef_scraper(pages)
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"테스트 실패: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()