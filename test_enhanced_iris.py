#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IRIS (국가과학기술연구회) Enhanced 스크래퍼 테스트
"""

import os
import sys
import logging
import argparse
from enhanced_iris_scraper import EnhancedIrisScraper

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_iris_scraper(pages=3):
    """IRIS 스크래퍼 테스트"""
    logger.info("=== IRIS Enhanced 스크래퍼 테스트 시작 ===")
    
    scraper = EnhancedIrisScraper()
    output_dir = "output/iris"
    os.makedirs(output_dir, exist_ok=True)
    
    # 스크래핑 실행
    success = scraper.scrape_pages(max_pages=pages, output_base=output_dir)
    
    if success:
        logger.info("=== IRIS 스크래핑 테스트 완료 ===")
        verify_results(output_dir)
    else:
        logger.error("=== IRIS 스크래핑 테스트 실패 ===")

def verify_results(output_dir):
    """결과 검증"""
    logger.info("=== 결과 검증 시작 ===")
    
    if not os.path.exists(output_dir):
        logger.error(f"출력 디렉토리가 없습니다: {output_dir}")
        return
    
    folders = [f for f in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, f))]
    logger.info(f"총 {len(folders)}개 공고 폴더 생성됨")
    
    total_files = 0
    total_attachments = 0
    
    for folder in sorted(folders):
        folder_path = os.path.join(output_dir, folder)
        
        # content.md 파일 확인
        content_file = os.path.join(folder_path, 'content.md')
        if os.path.exists(content_file):
            file_size = os.path.getsize(content_file)
            logger.info(f"{folder}: content.md ({file_size:,} bytes)")
            total_files += 1
        else:
            logger.warning(f"{folder}: content.md 파일 없음")
        
        # 첨부파일 확인
        attachments_dir = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_dir):
            attachment_files = os.listdir(attachments_dir)
            if attachment_files:
                logger.info(f"{folder}: {len(attachment_files)}개 첨부파일")
                total_attachments += len(attachment_files)
                
                # 첨부파일 상세 정보
                for file_name in attachment_files:
                    file_path = os.path.join(attachments_dir, file_name)
                    file_size = os.path.getsize(file_path)
                    logger.info(f"  - {file_name} ({file_size:,} bytes)")
    
    logger.info(f"=== 검증 완료: 총 {total_files}개 content.md, {total_attachments}개 첨부파일 ===")

def test_api_response():
    """API 응답 테스트"""
    logger.info("=== IRIS API 응답 테스트 ===")
    
    scraper = EnhancedIrisScraper()
    
    # 1페이지 데이터 가져오기
    page_data = scraper.get_page_data(1)
    if page_data:
        logger.info(f"API 응답 상태: {page_data['status_code']}")
        logger.info(f"응답 내용 길이: {len(page_data['content'])} 문자")
        logger.info(f"응답 인코딩: {page_data['encoding']}")
        
        # JSON 파싱 테스트
        announcements = scraper.parse_list_page(page_data['content'])
        logger.info(f"파싱된 공고 수: {len(announcements)}")
        
        if announcements:
            logger.info("첫 번째 공고 정보:")
            first = announcements[0]
            for key, value in first.items():
                logger.info(f"  {key}: {value}")
    else:
        logger.error("API 응답 가져오기 실패")

def main():
    parser = argparse.ArgumentParser(description='IRIS Enhanced 스크래퍼 테스트')
    parser.add_argument('--pages', type=int, default=3, help='테스트할 페이지 수 (기본값: 3)')
    parser.add_argument('--api-only', action='store_true', help='API 응답만 테스트')
    parser.add_argument('--single', action='store_true', help='1페이지만 테스트')
    
    args = parser.parse_args()
    
    if args.api_only:
        test_api_response()
    elif args.single:
        test_iris_scraper(pages=1)
    else:
        test_iris_scraper(pages=args.pages)

if __name__ == "__main__":
    main()