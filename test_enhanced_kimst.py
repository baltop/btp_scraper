#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIMST Enhanced 스크래퍼 테스트 스크립트
"""

import os
import sys
import logging
from enhanced_kimst_scraper import EnhancedKimstScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('kimst_test.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def test_kimst_scraper(pages=3):
    """KIMST 스크래퍼 테스트"""
    logger.info("=== KIMST Enhanced 스크래퍼 테스트 시작 ===")
    
    # 출력 디렉토리 설정
    output_dir = "output/kimst"
    os.makedirs(output_dir, exist_ok=True)
    
    # 스크래퍼 초기화
    scraper = EnhancedKimstScraper()
    
    try:
        # 스크래핑 실행
        logger.info(f"{pages}페이지까지 스크래핑 시작")
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        
        logger.info("=== 스크래핑 완료 ===")
        
        # 결과 검증
        verify_results(output_dir)
        
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

def verify_results(output_dir):
    """결과 검증 - 첨부파일 검증 포함"""
    logger.info("=== 결과 검증 시작 ===")
    
    if not os.path.exists(output_dir):
        logger.error(f"출력 디렉토리가 존재하지 않습니다: {output_dir}")
        return
    
    # 공고 폴더 목록
    announcement_folders = [d for d in os.listdir(output_dir) 
                          if os.path.isdir(os.path.join(output_dir, d))]
    
    total_items = len(announcement_folders)
    successful_items = 0
    total_attachments = 0
    korean_files = 0
    file_size_total = 0
    url_check_passed = 0
    iris_urls = 0
    
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
                if '**원본 URL**:' in content:
                    url_check_passed += 1
                    
                # IRIS URL 확인
                if 'iris.go.kr' in content:
                    iris_urls += 1
                    
                logger.debug(f"공고 처리 성공: {folder_name}")
                    
            except Exception as e:
                logger.error(f"content.md 읽기 실패 {folder_name}: {e}")
        
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
                att_path = os.path.join(attachments_dir, filename)
                try:
                    file_size = os.path.getsize(att_path)
                    file_size_total += file_size
                    
                    if file_size > 0:
                        logger.debug(f"첨부파일: {filename} ({file_size:,} bytes)")
                    else:
                        logger.warning(f"빈 파일: {filename}")
                        
                except Exception as e:
                    logger.error(f"파일 크기 확인 실패 {filename}: {e}")
    
    # 성공률 계산
    success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
    url_success_rate = (url_check_passed / successful_items) * 100 if successful_items > 0 else 0
    iris_rate = (iris_urls / successful_items) * 100 if successful_items > 0 else 0
    
    # 결과 리포트
    logger.info("=== 검증 결과 요약 ===")
    logger.info(f"총 공고 수: {total_items}")
    logger.info(f"성공적 처리: {successful_items} ({success_rate:.1f}%)")
    logger.info(f"원본 URL 포함: {url_check_passed} ({url_success_rate:.1f}%)")
    logger.info(f"IRIS 연동 확인: {iris_urls} ({iris_rate:.1f}%)")
    logger.info(f"총 첨부파일: {total_attachments}")
    logger.info(f"한글 파일명: {korean_files}")
    logger.info(f"총 파일 용량: {file_size_total:,} bytes")
    
    if total_attachments > 0:
        avg_file_size = file_size_total / total_attachments
        logger.info(f"평균 파일 크기: {avg_file_size:,.0f} bytes")
        korean_ratio = (korean_files / total_attachments) * 100
        logger.info(f"한글 파일명 비율: {korean_ratio:.1f}%")
    
    # KIMST 특화 검증
    logger.info(f"\n=== KIMST 특화 검증 ===")
    logger.info(f"이중 시스템 처리: {'✅' if iris_rate > 0 else '❌'}")
    logger.info(f"IRIS 연동 성공률: {iris_rate:.1f}%")
    
    # 성공 기준 확인
    if success_rate >= 80:
        logger.info("✅ 테스트 통과 (성공률 80% 이상)")
    else:
        logger.warning("⚠️  테스트 부분 통과 (성공률 80% 미만)")
    
    # 샘플 파일 확인
    if announcement_folders:
        sample_folder = announcement_folders[0]
        sample_path = os.path.join(output_dir, sample_folder)
        logger.info(f"\n=== 샘플 확인: {sample_folder} ===")
        
        content_file = os.path.join(sample_path, 'content.md')
        if os.path.exists(content_file):
            try:
                with open(content_file, 'r', encoding='utf-8') as f:
                    preview = f.read()[:500]
                    logger.info(f"내용 미리보기:\n{preview}...")
            except Exception as e:
                logger.error(f"샘플 파일 읽기 실패: {e}")
        
        # 첨부파일 확인
        att_dir = os.path.join(sample_path, 'attachments')
        if os.path.exists(att_dir):
            att_files = os.listdir(att_dir)
            if att_files:
                logger.info(f"첨부파일 예시: {att_files[:3]}")
    
    return success_rate >= 80

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='KIMST 스크래퍼 테스트')
    parser.add_argument('--pages', type=int, default=3, help='테스트할 페이지 수 (기본값: 3)')
    parser.add_argument('--single', action='store_true', help='단일 페이지만 테스트')
    
    args = parser.parse_args()
    
    if args.single:
        test_pages = 1
    else:
        test_pages = args.pages
    
    test_kimst_scraper(pages=test_pages)