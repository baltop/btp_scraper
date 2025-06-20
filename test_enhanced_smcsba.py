#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SMCSBA 스크래퍼 테스트 스크립트
"""

import os
import sys
import logging
from enhanced_smcsba_scraper import EnhancedSmcsbaScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('smcsba_scraper.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def test_smcsba_scraper(pages=3):
    """SMCSBA 스크래퍼 테스트 - 기본값 3페이지"""
    logger.info("=== SMCSBA 스크래퍼 테스트 시작 ===")
    
    # 출력 디렉토리 설정 (표준 규칙)
    output_dir = "output/smcsba"
    os.makedirs(output_dir, exist_ok=True)
    
    # 스크래퍼 생성 및 실행
    scraper = EnhancedSmcsbaScraper()
    
    try:
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        logger.info("=== 스크래핑 완료 ===")
        
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
    
    if not announcement_folders:
        logger.error("처리된 공고가 없습니다")
        return
    
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
                    if '**원본 URL**:' in content and 'smc.sba.kr' in content:
                        url_check_passed += 1
            except Exception as e:
                logger.warning(f"content.md 읽기 실패 {folder_name}: {e}")
        
        # 첨부파일 검증
        attachments_dir = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_dir):
            try:
                attachment_files = os.listdir(attachments_dir)
                total_attachments += len(attachment_files)
                
                for filename in attachment_files:
                    # 한글 파일명 검증
                    has_korean = any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename)
                    if has_korean:
                        korean_files += 1
                    
                    # 파일 크기 검증
                    att_path = os.path.join(attachments_dir, filename)
                    if os.path.exists(att_path):
                        file_size = os.path.getsize(att_path)
                        file_size_total += file_size
                        
                        if file_size == 0:
                            logger.warning(f"빈 파일 발견: {filename}")
                        else:
                            logger.debug(f"첨부파일: {filename} ({file_size:,} bytes)")
                            
            except Exception as e:
                logger.warning(f"첨부파일 검증 실패 {folder_name}: {e}")
    
    # 성공률 계산
    success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
    
    # 결과 출력
    logger.info("=== 검증 결과 요약 ===")
    logger.info(f"총 공고 수: {total_items}")
    logger.info(f"성공적 처리: {successful_items} ({success_rate:.1f}%)")
    logger.info(f"원본 URL 포함: {url_check_passed}")
    logger.info(f"총 첨부파일: {total_attachments}")
    logger.info(f"한글 파일명: {korean_files}")
    logger.info(f"총 파일 용량: {file_size_total:,} bytes")
    
    # 첨부파일 상세 정보
    if total_attachments > 0:
        avg_file_size = file_size_total / total_attachments
        korean_ratio = (korean_files / total_attachments) * 100 if total_attachments > 0 else 0
        logger.info(f"평균 파일 크기: {avg_file_size:,.0f} bytes")
        logger.info(f"한글 파일명 비율: {korean_ratio:.1f}%")
    
    # 성공 기준 확인
    if success_rate >= 80:
        logger.info("✓ 검증 통과: 80% 이상 성공적으로 처리됨")
    else:
        logger.warning("✗ 검증 실패: 성공률이 80% 미만임")
    
    if total_attachments > 0:
        logger.info("✓ 첨부파일 다운로드 확인됨")
    else:
        logger.info("ℹ 첨부파일이 없는 사이트이거나 다운로드 실패")
    
    return success_rate >= 80

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SMCSBA 스크래퍼 테스트')
    parser.add_argument('--pages', type=int, default=3, help='테스트할 페이지 수 (기본: 3)')
    parser.add_argument('--single', action='store_true', help='단일 페이지 테스트')
    
    args = parser.parse_args()
    
    if args.single:
        pages = 1
    else:
        pages = args.pages
    
    logger.info(f"{pages}페이지 테스트 시작")
    
    try:
        test_smcsba_scraper(pages)
        logger.info("테스트 완료")
    except Exception as e:
        logger.error(f"테스트 실패: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()