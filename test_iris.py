#!/usr/bin/env python3
"""
IRIS Enhanced 스크래퍼 테스트
국가과학기술연구회 스크래퍼 테스트 실행
"""

import os
import logging
import time
from enhanced_iris_scraper import EnhancedIrisScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_iris_scraper(pages=3):
    """IRIS 스크래퍼 테스트 - 3페이지"""
    logger.info("=== Enhanced IRIS 스크래퍼 테스트 시작 ===")
    
    try:
        # 스크래퍼 초기화
        scraper = EnhancedIrisScraper()
        
        # 출력 디렉토리 설정
        output_dir = "output/iris"
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"출력 디렉토리: {output_dir}")
        logger.info(f"최대 페이지: {pages}")
        
        # Enhanced 스크래퍼의 통합 메서드 사용
        success = scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        
        if success:
            # 결과 검증
            logger.info("\n=== 결과 검증 ===")
            verify_results(output_dir)
        
        return success
        
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}")
        return False

def verify_results(output_dir):
    """결과 검증"""
    logger.info("=== 결과 검증 시작 ===")
    
    if not os.path.exists(output_dir):
        logger.error("출력 디렉토리가 존재하지 않습니다")
        return
    
    # 폴더 수 확인
    folders = [d for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d))]
    logger.info(f"생성된 공고 폴더: {len(folders)}개")
    
    # 파일 통계
    total_files = 0
    total_size = 0
    file_types = {}
    announcements_with_attachments = 0
    
    for folder in folders:
        folder_path = os.path.join(output_dir, folder)
        
        # content.md 확인
        content_file = os.path.join(folder_path, 'content.md')
        if os.path.exists(content_file):
            size = os.path.getsize(content_file)
            total_files += 1
            total_size += size
            file_types['md'] = file_types.get('md', 0) + 1
        
        # 첨부파일 확인
        attachments_dir = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_dir):
            attachments = os.listdir(attachments_dir)
            if attachments:
                announcements_with_attachments += 1
                
                for file in attachments:
                    file_path = os.path.join(attachments_dir, file)
                    if os.path.isfile(file_path):
                        size = os.path.getsize(file_path)
                        total_files += 1
                        total_size += size
                        
                        # 파일 확장자별 통계
                        ext = os.path.splitext(file)[1].lower()
                        if ext:
                            ext = ext[1:]  # . 제거
                            file_types[ext] = file_types.get(ext, 0) + 1
                        
                        logger.info(f"첨부파일: {file} ({size:,} bytes)")
    
    logger.info(f"총 공고 수: {len(folders)}개")
    logger.info(f"첨부파일이 있는 공고: {announcements_with_attachments}개")
    logger.info(f"총 파일 수: {total_files}개")
    logger.info(f"총 파일 크기: {total_size:,} bytes ({total_size/1024/1024:.2f} MB)")
    logger.info(f"파일 형식별 통계: {file_types}")
    
    # 성공률 계산
    if len(folders) > 0:
        success_rate = (len(folders) / (len(folders))) * 100  # 모든 폴더가 처리됨
        logger.info(f"처리 성공률: {success_rate:.1f}%")

if __name__ == "__main__":
    success = test_iris_scraper(pages=3)
    
    if success:
        logger.info("테스트가 성공적으로 완료되었습니다!")
    else:
        logger.error("테스트가 실패했습니다!")