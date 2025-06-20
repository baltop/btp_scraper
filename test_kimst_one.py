#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIMST 첫 번째 공고만 테스트 (첨부파일 다운로드 포함)
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

def test_one_announcement():
    """하나의 공고만 처리 테스트"""
    logger.info("=== KIMST 첫 번째 공고만 테스트 ===")
    
    # 출력 디렉토리 설정
    output_dir = "output/kimst"
    os.makedirs(output_dir, exist_ok=True)
    
    # 스크래퍼 초기화
    scraper = EnhancedKimstScraper()
    
    try:
        # 1페이지 스크래핑 (1개 공고만)
        scraper.scrape_pages(max_pages=1, output_base=output_dir, max_announcements=1)
        
        # 결과 확인
        folders = [d for d in os.listdir(output_dir) 
                   if os.path.isdir(os.path.join(output_dir, d))]
        
        if folders:
            folder_path = os.path.join(output_dir, folders[0])
            logger.info(f"처리된 폴더: {folders[0]}")
            
            # 첨부파일 확인
            attachments_dir = os.path.join(folder_path, 'attachments')
            if os.path.exists(attachments_dir):
                files = os.listdir(attachments_dir)
                total_size = 0
                for filename in files:
                    file_path = os.path.join(attachments_dir, filename)
                    file_size = os.path.getsize(file_path)
                    total_size += file_size
                    logger.info(f"✅ {filename}: {file_size:,} bytes")
                
                logger.info(f"📊 총 {len(files)}개 파일, {total_size:,} bytes ({total_size/1024/1024:.1f} MB)")
            else:
                logger.warning("❌ 첨부파일 폴더 없음")
        else:
            logger.error("❌ 처리된 폴더 없음")
        
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_one_announcement()