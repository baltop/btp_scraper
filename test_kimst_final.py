#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIMST 최종 3페이지 테스트 - 첨부파일 다운로드 포함
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

def test_kimst_final():
    """KIMST 최종 3페이지 테스트"""
    logger.info("=== KIMST 최종 3페이지 테스트 시작 ===")
    
    # 출력 디렉토리 설정
    output_dir = "output/kimst"
    os.makedirs(output_dir, exist_ok=True)
    
    # 스크래퍼 초기화
    scraper = EnhancedKimstScraper()
    
    try:
        # 3페이지 스크래핑 (첨부파일 다운로드 포함)
        scraper.scrape_pages(max_pages=3, output_base=output_dir)
        
        # 결과 확인
        verify_final_result(output_dir)
        
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

def verify_final_result(output_dir):
    """최종 결과 검증"""
    logger.info("=== 최종 결과 검증 ===" )
    
    folders = [d for d in os.listdir(output_dir) 
               if os.path.isdir(os.path.join(output_dir, d))]
    
    if not folders:
        logger.error("공고 폴더가 생성되지 않았습니다")
        return
    
    logger.info(f"📁 총 {len(folders)}개 공고 폴더 생성")
    
    total_files = 0
    total_size = 0
    
    for folder_name in folders:
        folder_path = os.path.join(output_dir, folder_name)
        logger.info(f"\n📂 검증 폴더: {folder_name}")
        
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
            folder_size = 0
            
            logger.info(f"📎 첨부파일 {len(files)}개")
            for filename in files:
                file_path = os.path.join(attachments_dir, filename)
                file_size = os.path.getsize(file_path)
                folder_size += file_size
                total_files += 1
                total_size += file_size
                
                # 한글 파일명 확인
                has_korean = any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename)
                korean_mark = "🇰🇷" if has_korean else ""
                
                logger.info(f"  - {filename}: {file_size:,} bytes {korean_mark}")
            
            logger.info(f"📊 폴더 총 용량: {folder_size:,} bytes ({folder_size/1024/1024:.2f} MB)")
        else:
            logger.warning("⚠️ 첨부파일 폴더 없음")
    
    # 전체 요약
    logger.info(f"\n=== 최종 요약 ===")
    logger.info(f"총 공고 수: {len(folders)}")
    logger.info(f"총 첨부파일: {total_files}개")
    logger.info(f"총 다운로드 용량: {total_size:,} bytes ({total_size/1024/1024:.2f} MB)")
    
    # 성공 여부 판단
    if total_files > 0:
        logger.info("✅ 첨부파일 다운로드 성공!")
    else:
        logger.error("❌ 첨부파일 다운로드 실패")

if __name__ == "__main__":
    test_kimst_final()