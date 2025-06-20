#!/usr/bin/env python3
"""
KOSMES Enhanced Scraper 테스트 스크립트
"""

import os
import sys
import time
import logging

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_kosmes_scraper import EnhancedKosmesScraper

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_kosmes_scraper(pages=3):
    """KOSMES 스크래퍼 테스트"""
    logger.info(f"=== KOSMES Enhanced 스크래퍼 테스트 시작 (최대 {pages}페이지) ===")
    
    # 스크래퍼 초기화
    scraper = EnhancedKosmesScraper()
    
    # 출력 디렉토리 설정
    output_dir = "output/kosmes"
    os.makedirs(output_dir, exist_ok=True)
    
    start_time = time.time()
    
    try:
        # 스크래핑 실행
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        
        # 실행 시간 계산
        execution_time = time.time() - start_time
        logger.info(f"스크래핑 완료. 총 실행 시간: {execution_time:.2f}초")
        
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
        return False
    
    # 생성된 폴더 확인
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
                    if '**원본 URL**:' in content and 'kosmes.or.kr' in content:
                        url_check_passed += 1
            except Exception as e:
                logger.warning(f"content.md 읽기 실패 {folder_name}: {e}")
        
        # 첨부파일 검증
        attachments_dir = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_dir):
            for filename in os.listdir(attachments_dir):
                att_path = os.path.join(attachments_dir, filename)
                if os.path.isfile(att_path):
                    total_attachments += 1
                    
                    # 한글 파일명 확인
                    if any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename):
                        korean_files += 1
                    
                    # 파일 크기 확인
                    try:
                        file_size = os.path.getsize(att_path)
                        file_size_total += file_size
                        logger.debug(f"첨부파일: {filename} ({file_size:,} bytes)")
                    except:
                        pass
    
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
    logger.info(f"총 파일 용량: {file_size_total:,} bytes")
    
    # 상세 통계
    if total_attachments > 0:
        avg_file_size = file_size_total / total_attachments
        korean_ratio = (korean_files / total_attachments) * 100
        logger.info(f"평균 파일 크기: {avg_file_size:,.0f} bytes")
        logger.info(f"한글 파일명 비율: {korean_ratio:.1f}%")
    
    # 성공 기준: 80% 이상 성공적 처리
    if success_rate >= 80:
        logger.info("✅ 테스트 성공!")
        return True
    else:
        logger.warning("⚠️ 테스트 결과가 기준에 미달합니다.")
        return False

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='KOSMES Enhanced 스크래퍼 테스트')
    parser.add_argument('--pages', type=int, default=3, help='테스트할 페이지 수 (기본값: 3)')
    parser.add_argument('--output', type=str, default='output/kosmes', help='출력 디렉토리')
    
    args = parser.parse_args()
    
    # 테스트 실행
    test_kosmes_scraper(pages=args.pages)

if __name__ == "__main__":
    main()