#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
경기테크노파크(GTP) Enhanced 스크래퍼 테스트 스크립트
"""

import sys
import os
import logging
import glob

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_gtp_scraper import EnhancedGtpScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('gtp_scraper.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def test_gtp_scraper(pages=3):
    """경기테크노파크(GTP) 스크래퍼 테스트"""
    output_dir = "output/gtp"
    
    logger.info("=" * 50)
    logger.info("경기테크노파크(GTP) Enhanced 스크래퍼 테스트 시작")
    logger.info("=" * 50)
    
    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)
    
    # 스크래퍼 초기화
    scraper = EnhancedGtpScraper()
    
    try:
        # 스크래핑 실행
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        
        # 결과 검증
        verify_results(output_dir)
        
    except Exception as e:
        logger.error(f"스크래핑 중 오류 발생: {e}")
        return False
    
    logger.info("테스트 완료")
    return True

def verify_results(output_dir):
    """결과 검증"""
    logger.info("=" * 50)
    logger.info("결과 검증 시작")
    logger.info("=" * 50)
    
    # 생성된 폴더들 확인
    folders = [d for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d))]
    folders = [f for f in folders if not f.startswith('.')]  # 숨김 폴더 제외
    
    logger.info(f"총 {len(folders)}개 공고 폴더 생성됨")
    
    if not folders:
        logger.warning("생성된 공고 폴더가 없습니다!")
        return
    
    # 처리된 제목 파일 확인
    processed_file = os.path.join(output_dir, 'processed_titles_enhancedgtp.json')
    if os.path.exists(processed_file):
        logger.info(f"처리된 제목 파일 존재: {processed_file}")
    
    # 각 폴더 내용 검증
    total_items = len(folders)
    successful_items = 0
    url_check_passed = 0
    korean_filename_count = 0
    attachment_folders = 0
    total_attachments = 0
    
    for folder in folders[:5]:  # 최대 5개만 상세 검증
        folder_path = os.path.join(output_dir, folder)
        
        # content.md 파일 확인
        content_file = os.path.join(folder_path, 'content.md')
        if os.path.exists(content_file):
            successful_items += 1
            
            # content.md 내용 확인
            try:
                with open(content_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 원본 URL 포함 확인
                if '**원본 URL**:' in content and 'pms.gtp.or.kr' in content:
                    url_check_passed += 1
                
                logger.info(f"✓ {folder}: content.md ({len(content)} chars)")
                
            except Exception as e:
                logger.error(f"✗ {folder}: content.md 읽기 실패 - {e}")
        else:
            logger.warning(f"✗ {folder}: content.md 없음")
        
        # 첨부파일 확인
        attachments_dir = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_dir):
            attachment_folders += 1
            attachment_files = os.listdir(attachments_dir)
            folder_attachment_count = len(attachment_files)
            total_attachments += folder_attachment_count
            
            logger.info(f"  - 첨부파일 {folder_attachment_count}개")
            
            # 첨부파일 상세 정보
            for att_file in attachment_files[:3]:  # 최대 3개만 표시
                att_path = os.path.join(attachments_dir, att_file)
                if os.path.isfile(att_path):
                    file_size = os.path.getsize(att_path)
                    
                    # 한글 파일명 확인
                    has_korean = any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in att_file)
                    if has_korean:
                        korean_filename_count += 1
                    
                    logger.info(f"    * {att_file} ({file_size:,} bytes) {'[한글]' if has_korean else ''}")
        else:
            logger.info(f"  - 첨부파일 없음")
    
    # 요약 정보
    logger.info("=" * 50)
    logger.info("검증 결과 요약")
    logger.info("=" * 50)
    
    success_rate = (successful_items / total_items * 100) if total_items > 0 else 0
    url_check_rate = (url_check_passed / total_items * 100) if total_items > 0 else 0
    
    logger.info(f"총 공고 수: {total_items}")
    logger.info(f"성공한 공고: {successful_items} ({success_rate:.1f}%)")
    logger.info(f"URL 포함 확인: {url_check_passed} ({url_check_rate:.1f}%)")
    logger.info(f"첨부파일 있는 공고: {attachment_folders}")
    logger.info(f"총 첨부파일 수: {total_attachments}")
    logger.info(f"한글 파일명 수: {korean_filename_count}")
    
    # 결과 판정
    if success_rate >= 80:
        logger.info("✓ 테스트 성공!")
    elif success_rate >= 60:
        logger.warning("△ 테스트 부분 성공")
    else:
        logger.error("✗ 테스트 실패")

def test_single_page():
    """단일 페이지 테스트"""
    logger.info("단일 페이지 테스트 시작")
    
    scraper = EnhancedGtpScraper()
    
    # 첫 페이지 목록 가져오기
    try:
        page_url = scraper.get_list_url(1)
        logger.info(f"테스트 URL: {page_url}")
        
        response = scraper.get_page(page_url)
        if not response:
            logger.error("페이지 가져오기 실패")
            return False
        
        announcements = scraper.parse_list_page(response.text)
        logger.info(f"파싱된 공고 수: {len(announcements)}")
        
        if announcements:
            # 첫 번째 공고 상세 정보 테스트
            first_ann = announcements[0]
            logger.info(f"첫 번째 공고: {first_ann['title']}")
            logger.info(f"URL: {first_ann['url']}")
            
            # 상세 페이지 테스트
            detail_response = scraper.get_page(first_ann['url'])
            if detail_response:
                detail = scraper.parse_detail_page(detail_response.text)
                logger.info(f"본문 길이: {len(detail['content'])}")
                logger.info(f"첨부파일 수: {len(detail['attachments'])}")
                
                if detail['attachments']:
                    for att in detail['attachments'][:3]:
                        logger.info(f"  - {att['name']}: {att['url']}")
            
        return True
        
    except Exception as e:
        logger.error(f"단일 페이지 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='경기테크노파크(GTP) Enhanced 스크래퍼 테스트')
    parser.add_argument('--pages', type=int, default=3, help='테스트할 페이지 수 (기본값: 3)')
    parser.add_argument('--single', action='store_true', help='단일 페이지 테스트만 실행')
    
    args = parser.parse_args()
    
    if args.single:
        test_single_page()
    else:
        test_gtp_scraper(args.pages)