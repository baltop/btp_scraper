#!/usr/bin/env python3
"""
NIPA (한국지능정보사회진흥원) 스크래퍼 테스트 스크립트
"""

import os
import sys
import logging
import time
from enhanced_nipa_scraper import EnhancedNIPAScraper

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_nipa_scraper(pages=3):
    """NIPA 스크래퍼 테스트"""
    logger.info("=== NIPA 스크래퍼 테스트 시작 ===")
    
    # 출력 디렉토리 설정
    output_dir = "output/nipa"
    os.makedirs(output_dir, exist_ok=True)
    
    # 스크래퍼 인스턴스 생성
    scraper = EnhancedNIPAScraper()
    
    try:
        # 스크래핑 실행
        logger.info(f"{pages}페이지 스크래핑 시작")
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        
        # 결과 검증
        verify_results(output_dir)
        
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}")
        return False
    
    logger.info("=== NIPA 스크래퍼 테스트 완료 ===")
    return True

def verify_results(output_dir):
    """결과 검증"""
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
            
            # 원본 URL 포함 확인
            try:
                with open(content_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if '**원본 URL**:' in content and 'nipa.kr' in content:
                        url_check_passed += 1
            except Exception as e:
                logger.warning(f"파일 읽기 실패: {content_file}, {e}")
        
        # 첨부파일 확인
        attachments_dir = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_dir):
            for filename in os.listdir(attachments_dir):
                att_path = os.path.join(attachments_dir, filename)
                if os.path.isfile(att_path):
                    total_attachments += 1
                    
                    # 한글 파일명 확인
                    has_korean = any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename)
                    if has_korean:
                        korean_files += 1
                    
                    # 파일 크기 확인
                    try:
                        file_size = os.path.getsize(att_path)
                        file_size_total += file_size
                        logger.debug(f"첨부파일: {filename} ({file_size:,} bytes)")
                    except Exception as e:
                        logger.warning(f"파일 크기 확인 실패: {filename}, {e}")
    
    # 성공률 계산
    success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
    url_success_rate = (url_check_passed / successful_items) * 100 if successful_items > 0 else 0
    korean_file_rate = (korean_files / total_attachments) * 100 if total_attachments > 0 else 0
    
    # 결과 출력
    logger.info("=== 검증 결과 요약 ===")
    logger.info(f"총 공고 수: {total_items}")
    logger.info(f"성공적 처리: {successful_items} ({success_rate:.1f}%)")
    logger.info(f"원본 URL 포함: {url_check_passed} ({url_success_rate:.1f}%)")
    logger.info(f"총 첨부파일: {total_attachments}")
    logger.info(f"한글 파일명: {korean_files} ({korean_file_rate:.1f}%)")
    logger.info(f"총 파일 용량: {file_size_total:,} bytes ({file_size_total/1024/1024:.1f} MB)")
    
    # 테스트 통과 여부 판정
    if success_rate >= 80:
        logger.info("✅ 테스트 통과! (성공률 80% 이상)")
    else:
        logger.warning("❌ 테스트 실패 (성공률 80% 미만)")
    
    if total_attachments > 0:
        logger.info("✅ 첨부파일 다운로드 기능 정상 작동")
    else:
        logger.warning("⚠️ 첨부파일이 다운로드되지 않았습니다")
    
    # 샘플 파일 내용 확인
    if announcement_folders:
        sample_folder = announcement_folders[0]
        sample_content = os.path.join(output_dir, sample_folder, 'content.md')
        if os.path.exists(sample_content):
            logger.info(f"\n=== 샘플 파일 내용 ({sample_folder}) ===")
            try:
                with open(sample_content, 'r', encoding='utf-8') as f:
                    content_preview = f.read()[:500]  # 처음 500자만
                    logger.info(content_preview + "..." if len(content_preview) == 500 else content_preview)
            except Exception as e:
                logger.warning(f"샘플 파일 읽기 실패: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='NIPA 스크래퍼 테스트')
    parser.add_argument('--pages', type=int, default=3, help='테스트할 페이지 수 (기본: 3)')
    parser.add_argument('--single', action='store_true', help='1페이지만 테스트')
    parser.add_argument('--verify-only', action='store_true', help='검증만 실행')
    
    args = parser.parse_args()
    
    if args.single:
        pages = 1
    else:
        pages = args.pages
    
    try:
        if args.verify_only:
            verify_results("output/nipa")
        else:
            test_nipa_scraper(pages)
            
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"테스트 실행 중 오류: {e}")
        sys.exit(1)