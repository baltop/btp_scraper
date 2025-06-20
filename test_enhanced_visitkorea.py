#!/usr/bin/env python3
"""
Visit Korea Enhanced 스크래퍼 테스트

한국관광품질인증제 사이트 스크래퍼의 테스트 및 검증을 수행합니다.
JavaScript 기반 동적 사이트의 Playwright 처리를 검증합니다.
"""

import os
import sys
import logging
import time
from enhanced_visitkorea_scraper import EnhancedVisitKoreaScraper

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_visitkorea_scraper(pages=3):
    """Visit Korea 스크래퍼 테스트
    
    Args:
        pages (int): 테스트할 페이지 수 (기본값: 3)
    """
    logger.info("=== Visit Korea Enhanced 스크래퍼 테스트 시작 ===")
    logger.info(f"테스트 페이지 수: {pages}")
    
    # 출력 디렉토리 설정
    output_dir = "output/visitkorea"
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # 스크래퍼 실행
        scraper = EnhancedVisitKoreaScraper()
        success = scraper.scrape_pages(max_pages=pages, output_base="output")
        
        if success:
            logger.info("스크래핑 완료. 결과 검증을 시작합니다.")
            verify_results(output_dir)
        else:
            logger.error("스크래핑 실패")
            return False
                
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}")
        return False
    
    return True


def verify_results(output_dir):
    """결과 검증 - JavaScript 기반 사이트 특화 검증"""
    logger.info("=== 결과 검증 시작 ===")
    
    if not os.path.exists(output_dir):
        logger.error(f"출력 디렉토리가 존재하지 않습니다: {output_dir}")
        return
    
    # 공고 폴더 목록 가져오기
    announcement_folders = [d for d in os.listdir(output_dir) 
                          if os.path.isdir(os.path.join(output_dir, d))]
    
    if not announcement_folders:
        logger.warning("처리된 공고가 없습니다")
        return
    
    # 정렬 (번호순)
    announcement_folders.sort()
    
    total_items = len(announcement_folders)
    successful_items = 0
    url_check_passed = 0
    total_attachments = 0
    korean_files = 0
    playwright_files = 0
    file_size_total = 0
    
    logger.info(f"총 {total_items}개 공고 폴더 발견")
    
    for folder_name in announcement_folders:
        folder_path = os.path.join(output_dir, folder_name)
        
        # content.md 파일 확인
        content_file = os.path.join(folder_path, 'content.md')
        if os.path.exists(content_file):
            successful_items += 1
            
            # content.md 내용 검증
            try:
                with open(content_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # 원본 URL 포함 확인
                    if '**원본 URL**:' in content and 'koreaquality.visitkorea.or.kr' in content:
                        url_check_passed += 1
                        
            except Exception as e:
                logger.warning(f"content.md 읽기 실패 ({folder_name}): {e}")
        
        # 첨부파일 검증
        attachments_dir = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_dir):
            attachment_files = os.listdir(attachments_dir)
            folder_attachment_count = len(attachment_files)
            total_attachments += folder_attachment_count
            
            for filename in attachment_files:
                file_path = os.path.join(attachments_dir, filename)
                
                if os.path.isfile(file_path):
                    # 파일 크기 확인
                    file_size = os.path.getsize(file_path)
                    file_size_total += file_size
                    
                    # 한글 파일명 확인
                    has_korean = any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename)
                    if has_korean:
                        korean_files += 1
                    
                    # Playwright 다운로드 파일 확인 (PDF, HWP 등)
                    if filename.lower().endswith(('.pdf', '.hwp', '.doc', '.docx', '.xls', '.xlsx')):
                        playwright_files += 1
                    
                    logger.debug(f"첨부파일: {filename} ({file_size:,} bytes, 한글: {has_korean})")
            
            if folder_attachment_count > 0:
                logger.info(f"{folder_name}: {folder_attachment_count}개 첨부파일")
    
    # 성공률 계산
    success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
    url_success_rate = (url_check_passed / successful_items) * 100 if successful_items > 0 else 0
    korean_file_rate = (korean_files / total_attachments) * 100 if total_attachments > 0 else 0
    playwright_ratio = (playwright_files / total_attachments) * 100 if total_attachments > 0 else 0
    
    # 결과 출력
    logger.info("=== 검증 결과 요약 ===")
    logger.info(f"총 공고 수: {total_items}")
    logger.info(f"성공적 처리: {successful_items} ({success_rate:.1f}%)")
    logger.info(f"원본 URL 포함: {url_check_passed} ({url_success_rate:.1f}%)")
    logger.info(f"총 첨부파일: {total_attachments}")
    logger.info(f"한글 파일명: {korean_files}")
    logger.info(f"Playwright 다운로드 파일: {playwright_files}")
    logger.info(f"총 파일 용량: {file_size_total:,} bytes ({file_size_total/1024/1024:.2f} MB)")
    
    # 성과 평가
    if success_rate >= 90:
        logger.info("✅ 우수한 성과: 90% 이상 성공")
    elif success_rate >= 70:
        logger.info("✅ 양호한 성과: 70% 이상 성공")
    else:
        logger.warning("⚠️ 개선 필요: 70% 미만 성공")
    
    # JavaScript/Playwright 특화 검증
    if korean_file_rate >= 80:
        logger.info("✅ 한글 파일명 처리 양호")
    else:
        logger.warning("⚠️ 한글 파일명 처리 개선 필요")
    
    if total_attachments > 0:
        logger.info("✅ 파일 다운로드 정상적")
    else:
        logger.warning("⚠️ 첨부파일 다운로드 확인 필요")
    
    if playwright_files > 0:
        logger.info("✅ Playwright 파일 다운로드 성공")
    else:
        logger.warning("⚠️ Playwright 파일 다운로드 확인 필요")
    
    # JavaScript 기반 사이트 특화 검증
    if url_check_passed > 0:
        logger.info("✅ JavaScript 상세 페이지 접근 정상")
    else:
        logger.warning("⚠️ JavaScript 상세 페이지 접근 확인 필요")
    
    return success_rate >= 70


def test_single_page():
    """단일 페이지 테스트"""
    logger.info("=== 단일 페이지 테스트 ===")
    return test_visitkorea_scraper(pages=1)


def test_three_pages():
    """3페이지 테스트"""
    logger.info("=== 3페이지 테스트 ===")
    return test_visitkorea_scraper(pages=3)


def main():
    """메인 함수"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--single":
            test_single_page()
        elif sys.argv[1] == "--pages":
            pages = int(sys.argv[2]) if len(sys.argv) > 2 else 3
            test_visitkorea_scraper(pages)
        else:
            print("사용법: python test_enhanced_visitkorea.py [--single|--pages 숫자]")
    else:
        # 기본값: 3페이지 테스트
        test_three_pages()


if __name__ == "__main__":
    main()