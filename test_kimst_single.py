#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIMST 단일 공고 첨부파일 다운로드 테스트
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
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def test_single_announcement():
    """단일 공고 첨부파일 다운로드 테스트"""
    logger.info("=== KIMST 단일 공고 테스트 시작 ===")
    
    # 출력 디렉토리 설정
    output_dir = "output/kimst_single"
    os.makedirs(output_dir, exist_ok=True)
    
    # 스크래퍼 초기화
    scraper = EnhancedKimstScraper()
    
    try:
        # 첫 번째 페이지에서 공고 목록 가져오기
        response = scraper.get_page(scraper.list_url)
        if not response:
            logger.error("목록 페이지를 가져올 수 없습니다")
            return
        
        announcements = scraper.parse_list_page(response.text)
        if not announcements:
            logger.error("공고를 찾을 수 없습니다")
            return
        
        # 첫 번째 공고만 처리
        first_announcement = announcements[0]
        logger.info(f"처리할 공고: {first_announcement['title']}")
        
        # 상세 페이지 처리
        success = scraper.scrape_announcement_detail(first_announcement, output_dir)
        
        if success:
            logger.info("✅ 단일 공고 처리 성공")
        else:
            logger.error("❌ 단일 공고 처리 실패")
        
        # 결과 확인
        verify_single_result(output_dir)
        
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

def verify_single_result(output_dir):
    """단일 결과 검증"""
    logger.info("=== 결과 검증 ===")
    
    folders = [d for d in os.listdir(output_dir) 
               if os.path.isdir(os.path.join(output_dir, d))]
    
    if not folders:
        logger.error("공고 폴더가 생성되지 않았습니다")
        return
    
    folder_path = os.path.join(output_dir, folders[0])
    logger.info(f"검증 폴더: {folders[0]}")
    
    # content.md 확인
    content_file = os.path.join(folder_path, 'content.md')
    if os.path.exists(content_file):
        logger.info("✅ content.md 파일 존재")
    else:
        logger.error("❌ content.md 파일 없음")
    
    # 첨부파일 확인
    attachments_dir = os.path.join(folder_path, 'attachments')
    if os.path.exists(attachments_dir):
        files = os.listdir(attachments_dir)
        logger.info(f"📎 첨부파일 {len(files)}개")
        
        for filename in files:
            file_path = os.path.join(attachments_dir, filename)
            file_size = os.path.getsize(file_path)
            logger.info(f"  - {filename}: {file_size:,} bytes")
    else:
        logger.warning("⚠️ 첨부파일 폴더 없음")

if __name__ == "__main__":
    test_single_announcement()