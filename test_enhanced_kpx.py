#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced KPX 스크래퍼 테스트
"""

import os
import sys
import logging
import argparse
from enhanced_kpx_scraper import EnhancedKPXScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('kpx_scraper.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def test_kpx_scraper(pages=3):
    """KPX 스크래퍼 테스트 - 기본값 3페이지"""
    scraper = EnhancedKPXScraper()
    output_dir = "output/kpx"  # 표준 출력 디렉토리
    
    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"=== KPX 스크래퍼 테스트 시작 ({pages}페이지) ===")
    logger.info(f"출력 디렉토리: {output_dir}")
    
    try:
        # 스크래핑 실행
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
    
    # 공고 폴더들 확인
    announcement_folders = [d for d in os.listdir(output_dir) 
                          if os.path.isdir(os.path.join(output_dir, d)) and not d.startswith('.')]
    
    total_items = len(announcement_folders)
    successful_items = 0
    total_attachments = 0
    korean_files = 0
    file_size_total = 0
    url_check_passed = 0
    pdf_files = 0
    hwp_files = 0
    
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
                    if '**원본 URL**:' in content and 'edu.kpx.or.kr' in content:
                        url_check_passed += 1
            except Exception as e:
                logger.warning(f"content.md 읽기 실패: {folder_name} - {e}")
        
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
                    
                    # 파일 확장자별 분류
                    if filename.lower().endswith('.pdf'):
                        pdf_files += 1
                    elif filename.lower().endswith(('.hwp', '.hwpx')):
                        hwp_files += 1
                    
                    # 파일 크기 검증
                    try:
                        file_size = os.path.getsize(att_path)
                        file_size_total += file_size
                        
                        if file_size == 0:
                            logger.warning(f"빈 파일 발견: {filename}")
                        else:
                            logger.debug(f"첨부파일: {filename} ({file_size:,} bytes)")
                            
                    except Exception as e:
                        logger.warning(f"파일 크기 확인 실패: {filename} - {e}")
    
    # 성공률 계산 및 리포트
    success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
    url_success_rate = (url_check_passed / successful_items) * 100 if successful_items > 0 else 0
    
    logger.info("=== 검증 결과 요약 ===")
    logger.info(f"총 공고 수: {total_items}")
    logger.info(f"성공적 처리: {successful_items} ({success_rate:.1f}%)")
    logger.info(f"원본 URL 포함: {url_check_passed} ({url_success_rate:.1f}%)")
    logger.info(f"총 첨부파일: {total_attachments}")
    logger.info(f"PDF 파일: {pdf_files}")
    logger.info(f"HWP 파일: {hwp_files}")
    logger.info(f"한글 파일명: {korean_files}")
    logger.info(f"총 파일 용량: {file_size_total:,} bytes ({file_size_total/1024/1024:.2f} MB)")
    
    # 첨부파일이 있는 공고와 없는 공고 분류
    with_attachments = 0
    without_attachments = 0
    
    for folder_name in announcement_folders:
        folder_path = os.path.join(output_dir, folder_name)
        attachments_dir = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_dir) and os.listdir(attachments_dir):
            with_attachments += 1
        else:
            without_attachments += 1
    
    logger.info(f"첨부파일 있는 공고: {with_attachments}")
    logger.info(f"첨부파일 없는 공고: {without_attachments}")
    
    # 특별 검증: KPX 사이트 특성상 교육 관련 파일이 많을 것으로 예상
    if pdf_files > 0:
        logger.info(f"✅ PDF 파일 {pdf_files}개 발견 - KPX 교육 자료 특성 확인")
    
    # 결과 판정
    if success_rate >= 80:
        logger.info("✅ 테스트 성공: 80% 이상 성공적으로 처리됨")
        return True
    else:
        logger.warning("⚠️ 테스트 부분 성공: 성공률이 80% 미만")
        return False

def main():
    parser = argparse.ArgumentParser(description='KPX Enhanced 스크래퍼 테스트')
    parser.add_argument('--pages', type=int, default=3, help='스크래핑할 페이지 수 (기본값: 3)')
    parser.add_argument('--output', default='output/kpx', help='출력 디렉토리 (기본값: output/kpx)')
    parser.add_argument('--verify-only', action='store_true', help='스크래핑 없이 기존 결과만 검증')
    
    args = parser.parse_args()
    
    if args.verify_only:
        verify_results(args.output)
    else:
        test_kpx_scraper(args.pages)

if __name__ == "__main__":
    main()