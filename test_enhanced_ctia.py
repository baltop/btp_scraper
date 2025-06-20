#!/usr/bin/env python3
"""
Enhanced CTIA 스크래퍼 테스트 스크립트
"""
import os
import sys
import logging
from enhanced_ctia_scraper import EnhancedCTIAScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ctia_scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def test_ctia_scraper(pages=3):
    """CTIA 스크래퍼 테스트"""
    logger.info("=== Enhanced CTIA 스크래퍼 테스트 시작 ===")
    
    scraper = EnhancedCTIAScraper()
    output_dir = "output/ctia"  # 표준 출력 디렉토리
    
    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # 스크래핑 실행
        logger.info(f"최대 {pages}페이지까지 스크래핑 시작")
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
    
    # 공고별 폴더 목록
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
        
        # 1. content.md 파일 확인
        content_file = os.path.join(folder_path, 'content.md')
        if os.path.exists(content_file):
            successful_items += 1
            
            # 원본 URL 포함 확인
            try:
                with open(content_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if '**원본 URL**:' in content and 'ctia.kr' in content:
                        url_check_passed += 1
            except Exception as e:
                logger.warning(f"content.md 읽기 실패 {folder_name}: {e}")
        
        # 2. 첨부파일 검증
        attachments_dir = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_dir):
            for filename in os.listdir(attachments_dir):
                if os.path.isfile(os.path.join(attachments_dir, filename)):
                    total_attachments += 1
                    
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
    success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
    url_success_rate = (url_check_passed / successful_items) * 100 if successful_items > 0 else 0
    
    # 결과 리포트
    logger.info("=== 검증 결과 요약 ===")
    logger.info(f"총 공고 수: {total_items}")
    logger.info(f"성공적 처리: {successful_items} ({success_rate:.1f}%)")
    logger.info(f"원본 URL 포함: {url_check_passed} ({url_success_rate:.1f}%)")
    logger.info(f"총 첨부파일: {total_attachments}개")
    logger.info(f"한글 파일명: {korean_files}개")
    logger.info(f"총 파일 용량: {file_size_total:,} bytes ({file_size_total/1024/1024:.1f} MB)")
    
    # 성과 평가
    if success_rate >= 80:
        logger.info("✅ 테스트 PASS: 80% 이상 성공")
    else:
        logger.warning("⚠️ 테스트 주의: 성공률이 80% 미만")
    
    if total_attachments > 0:
        logger.info("✅ 첨부파일 다운로드 확인됨")
    else:
        logger.warning("⚠️ 첨부파일이 다운로드되지 않음")
    
    if korean_files > 0:
        logger.info("✅ 한글 파일명 처리 확인됨")
    
    # 샘플 파일 확인
    if announcement_folders:
        sample_folder = os.path.join(output_dir, announcement_folders[0])
        logger.info(f"샘플 폴더 확인: {sample_folder}")
        if os.path.exists(sample_folder):
            for item in os.listdir(sample_folder):
                item_path = os.path.join(sample_folder, item)
                if os.path.isfile(item_path):
                    size = os.path.getsize(item_path)
                    logger.info(f"  📄 {item} ({size:,} bytes)")
                elif os.path.isdir(item_path):
                    file_count = len([f for f in os.listdir(item_path) if os.path.isfile(os.path.join(item_path, f))])
                    logger.info(f"  📁 {item}/ ({file_count}개 파일)")

def main():
    """메인 함수"""
    pages = 3  # 기본값 3페이지
    
    if len(sys.argv) > 1:
        try:
            pages = int(sys.argv[1])
        except ValueError:
            logger.error("페이지 수는 숫자여야 합니다")
            sys.exit(1)
    
    test_ctia_scraper(pages)

if __name__ == "__main__":
    main()