#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
단일 DGDP 공고 테스트 - 첨부파일 검증용
"""

import os
import sys
import logging
from enhanced_dgdp_scraper import EnhancedDGDPScraper

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def test_single_dgdp():
    """첨부파일이 있는 단일 DGDP 공고 테스트"""
    logger.info("=== 단일 DGDP 공고 테스트 시작 ===")
    
    # 출력 디렉토리
    output_dir = "output/dgdp_single"
    os.makedirs(output_dir, exist_ok=True)
    
    # 스크래퍼 초기화
    scraper = EnhancedDGDPScraper()
    
    # 첨부파일이 있는 공고 정보
    announcement = {
        'title': '2024 디자인산업통계 보고서',
        'url': 'https://dgdp.or.kr/notice/public/2482',
        'id': '2482',
        'date': '2025-06-12',
        'views': '23'
    }
    
    try:
        # 개별 공고 처리
        scraper.process_announcement(announcement, 1, output_dir)
        
        # 결과 검증
        folder_path = os.path.join(output_dir, "001_2024 디자인산업통계 보고서")
        
        logger.info("=== 결과 검증 ===")
        
        # content.md 확인
        content_file = os.path.join(folder_path, 'content.md')
        if os.path.exists(content_file):
            with open(content_file, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.info(f"Content 파일 크기: {len(content)} 문자")
            logger.info("Content 일부 미리보기:")
            logger.info(content[:200] + "..." if len(content) > 200 else content)
        
        # 첨부파일 확인
        attachments_folder = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_folder):
            files = os.listdir(attachments_folder)
            logger.info(f"첨부파일 수: {len(files)}개")
            for f in files:
                file_path = os.path.join(attachments_folder, f)
                file_size = os.path.getsize(file_path)
                logger.info(f"  - {f} ({file_size:,} bytes)")
        else:
            logger.info("첨부파일 폴더가 존재하지 않습니다")
        
    except Exception as e:
        logger.error(f"테스트 중 오류: {e}")
        raise
    
    logger.info("=== 단일 DGDP 공고 테스트 완료 ===")

if __name__ == "__main__":
    test_single_dgdp()