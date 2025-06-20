#!/usr/bin/env python3
"""
Enhanced GBFOOD 스크래퍼 테스트 스크립트

사용법:
    python test_enhanced_gbfood.py --pages 3
    python test_enhanced_gbfood.py --single (1페이지만)
"""

import os
import sys
import logging
import argparse
from enhanced_gbfood_scraper import EnhancedGbfoodScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def test_gbfood_scraper(pages=3):
    """GBFOOD 스크래퍼 테스트"""
    logger.info("=== Enhanced GBFOOD 스크래퍼 테스트 시작 ===")
    
    # 스크래퍼 초기화
    scraper = EnhancedGbfoodScraper()
    
    # 표준 출력 디렉토리 사용
    output_dir = "output/gbfood"
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"출력 디렉토리: {output_dir}")
    logger.info(f"테스트 페이지 수: {pages}")
    
    try:
        # 스크래핑 실행
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        
        logger.info("=== 테스트 완료, 결과 검증 시작 ===")
        verify_results(output_dir)
        
    except Exception as e:
        logger.error(f"테스트 실행 중 오류 발생: {e}")
        raise

def verify_results(output_dir):
    """결과 검증 - 첨부파일 검증 필수"""
    logger.info("=== 결과 검증 시작 ===")
    
    if not os.path.exists(output_dir):
        logger.error(f"출력 디렉토리가 존재하지 않습니다: {output_dir}")
        return
    
    # 공고 폴더들 찾기
    announcement_folders = [d for d in os.listdir(output_dir) 
                          if os.path.isdir(os.path.join(output_dir, d))]
    
    total_items = len(announcement_folders)
    successful_items = 0
    total_attachments = 0
    korean_files = 0
    file_size_total = 0
    url_check_passed = 0
    
    logger.info(f"총 {total_items}개의 공고 폴더 발견")
    
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
                    if '**원본 URL**:' in content and 'gbfood.or.kr' in content:
                        url_check_passed += 1
            except Exception as e:
                logger.warning(f"content.md 파일 읽기 실패 {folder_name}: {e}")
        
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
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    file_size_total += file_size
                    
                    # 파일 크기가 0인 경우 경고
                    if file_size == 0:
                        logger.warning(f"빈 파일 발견: {filename}")
    
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
    
    # 첨부파일 세부 분석
    if total_attachments > 0:
        korean_ratio = (korean_files / total_attachments) * 100
        avg_file_size = file_size_total / total_attachments
        logger.info(f"한글 파일명 비율: {korean_ratio:.1f}%")
        logger.info(f"평균 파일 크기: {avg_file_size:,.0f} bytes")
    
    # 첨부파일 상세 정보 출력
    logger.info("=== 첨부파일 상세 정보 ===")
    for folder_name in announcement_folders[:3]:  # 처음 3개만 상세 출력
        folder_path = os.path.join(output_dir, folder_name)
        attachments_dir = os.path.join(folder_path, 'attachments')
        
        if os.path.exists(attachments_dir):
            attachment_files = os.listdir(attachments_dir)
            if attachment_files:
                logger.info(f"[{folder_name}] 첨부파일 {len(attachment_files)}개:")
                for filename in attachment_files:
                    file_path = os.path.join(attachments_dir, filename)
                    file_size = os.path.getsize(file_path)
                    has_korean = any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename)
                    korean_mark = " [한글]" if has_korean else ""
                    logger.info(f"  - {filename}{korean_mark} ({file_size:,} bytes)")
        else:
            logger.info(f"[{folder_name}] 첨부파일 없음")
    
    # 성공 여부 판정
    test_passed = success_rate >= 80
    if test_passed:
        logger.info("✅ 테스트 통과!")
    else:
        logger.warning("❌ 테스트 실패 - 성공률이 80% 미만입니다.")
    
    return test_passed

def main():
    parser = argparse.ArgumentParser(description='Enhanced GBFOOD 스크래퍼 테스트')
    parser.add_argument('--pages', type=int, default=3, help='테스트할 페이지 수 (기본값: 3)')
    parser.add_argument('--single', action='store_true', help='1페이지만 테스트')
    
    args = parser.parse_args()
    
    pages = 1 if args.single else args.pages
    
    try:
        test_gbfood_scraper(pages)
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단되었습니다.")
    except Exception as e:
        logger.error(f"테스트 실행 중 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()