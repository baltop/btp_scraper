"""
Enhanced GCAF 스크래퍼 테스트 스크립트
3페이지까지 테스트하고 첨부파일 검증 포함
"""

import os
import sys
import json
import logging
from enhanced_gcaf_scraper import EnhancedGCAFScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_gcaf_scraper(pages=3):
    """GCAF 스크래퍼 테스트"""
    logger.info("=== Enhanced GCAF 스크래퍼 테스트 시작 ===")
    
    # 출력 디렉토리 설정 (표준 형식)
    output_dir = "output/gcaf"
    os.makedirs(output_dir, exist_ok=True)
    
    # 스크래퍼 실행
    scraper = EnhancedGCAFScraper()
    try:
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        logger.info(f"스크래핑 완료: {output_dir}")
        
        # 결과 검증
        verify_results(output_dir)
        
    except Exception as e:
        logger.error(f"스크래퍼 실행 중 오류: {e}")
        return False
    
    return True

def verify_results(output_dir):
    """결과 검증 - 첨부파일 검증 포함"""
    logger.info("=== 결과 검증 시작 ===")
    
    if not os.path.exists(output_dir):
        logger.error(f"출력 디렉토리가 존재하지 않습니다: {output_dir}")
        return
    
    announcement_folders = [d for d in os.listdir(output_dir) 
                          if os.path.isdir(os.path.join(output_dir, d)) and not d.startswith('.')]
    
    total_items = len(announcement_folders)
    successful_items = 0
    total_attachments = 0
    korean_files = 0
    file_size_total = 0
    url_check_passed = 0
    
    logger.info(f"총 공고 폴더 수: {total_items}")
    
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
                    if '**원본 URL**:' in content and 'gcaf.or.kr' in content:
                        url_check_passed += 1
            except Exception as e:
                logger.warning(f"content.md 읽기 오류 {folder_name}: {e}")
        
        # 첨부파일 검증
        attachments_dir = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_dir):
            attachment_files = [f for f in os.listdir(attachments_dir) 
                              if os.path.isfile(os.path.join(attachments_dir, f))]
            
            for filename in attachment_files:
                total_attachments += 1
                
                # 한글 파일명 검증
                has_korean = any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename)
                if has_korean:
                    korean_files += 1
                
                # 파일 크기 검증
                att_path = os.path.join(attachments_dir, filename)
                try:
                    file_size = os.path.getsize(att_path)
                    file_size_total += file_size
                    
                    if file_size == 0:
                        logger.warning(f"빈 파일 발견: {filename}")
                    elif file_size < 100:
                        logger.warning(f"크기가 작은 파일: {filename} ({file_size} bytes)")
                        
                except Exception as e:
                    logger.error(f"파일 크기 확인 실패 {filename}: {e}")
    
    # 성공률 계산
    success_rate = (successful_items / total_items * 100) if total_items > 0 else 0
    url_success_rate = (url_check_passed / successful_items * 100) if successful_items > 0 else 0
    
    # 결과 출력
    logger.info("=== 검증 결과 요약 ===")
    logger.info(f"총 공고 수: {total_items}")
    logger.info(f"성공적 처리: {successful_items} ({success_rate:.1f}%)")
    logger.info(f"원본 URL 포함: {url_check_passed} ({url_success_rate:.1f}%)")
    logger.info(f"총 첨부파일: {total_attachments}")
    logger.info(f"한글 파일명: {korean_files}")
    logger.info(f"총 파일 용량: {file_size_total:,} bytes")
    
    if total_attachments > 0:
        avg_file_size = file_size_total / total_attachments
        logger.info(f"평균 파일 크기: {avg_file_size:,.0f} bytes")
        
        korean_ratio = (korean_files / total_attachments * 100)
        logger.info(f"한글 파일명 비율: {korean_ratio:.1f}%")
    
    # 상세 폴더별 정보
    logger.info("=== 폴더별 상세 정보 ===")
    for folder_name in sorted(announcement_folders)[:5]:  # 처음 5개만 출력
        folder_path = os.path.join(output_dir, folder_name)
        content_file = os.path.join(folder_path, 'content.md')
        attachments_dir = os.path.join(folder_path, 'attachments')
        
        att_count = 0
        if os.path.exists(attachments_dir):
            att_count = len([f for f in os.listdir(attachments_dir) 
                           if os.path.isfile(os.path.join(attachments_dir, f))])
        
        status = "✓" if os.path.exists(content_file) else "✗"
        logger.info(f"{status} {folder_name[:60]}... (첨부파일: {att_count}개)")
    
    if len(announcement_folders) > 5:
        logger.info(f"... 및 {len(announcement_folders) - 5}개 추가 폴더")
    
    # 성공 기준 판단 (80% 이상)
    if success_rate >= 80:
        logger.info("✓ 테스트 성공: 80% 이상 성공률 달성")
        return True
    else:
        logger.warning(f"✗ 테스트 실패: 성공률 {success_rate:.1f}% (80% 미만)")
        return False

def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced GCAF 스크래퍼 테스트')
    parser.add_argument('--pages', type=int, default=3, help='테스트할 페이지 수 (기본값: 3)')
    parser.add_argument('--single', action='store_true', help='단일 페이지만 테스트')
    
    args = parser.parse_args()
    
    pages = 1 if args.single else args.pages
    
    logger.info(f"테스트 설정: {pages}페이지")
    
    success = test_gcaf_scraper(pages=pages)
    
    if success:
        logger.info("모든 테스트가 성공적으로 완료되었습니다!")
        sys.exit(0)
    else:
        logger.error("테스트 실패")
        sys.exit(1)

if __name__ == "__main__":
    main()