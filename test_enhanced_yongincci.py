#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
용인상공회의소(Yongincci) Enhanced 스크래퍼 테스트 스크립트
"""

import os
import sys
import logging
import argparse
from enhanced_yongincci_scraper import EnhancedYongincciScraper

def setup_logging():
    """로깅 설정"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('yongincci_test.log', encoding='utf-8')
        ]
    )

def test_yongincci_scraper(pages=3, output_dir="output/yongincci"):
    """용인상공회의소 스크래퍼 테스트"""
    logger = logging.getLogger(__name__)
    
    try:
        # 출력 디렉토리 생성
        os.makedirs(output_dir, exist_ok=True)
        
        # 스크래퍼 인스턴스 생성
        scraper = EnhancedYongincciScraper()
        
        logger.info(f"=== 용인상공회의소 스크래퍼 테스트 시작 ===")
        logger.info(f"대상 URL: {scraper.list_url}")
        logger.info(f"테스트 페이지 수: {pages}")
        logger.info(f"출력 디렉토리: {output_dir}")
        logger.info(f"타임아웃 설정: {scraper.timeout}초")
        logger.info(f"요청 간 대기시간: {scraper.delay_between_requests}초")
        
        # 스크래핑 실행
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        
        logger.info(f"=== 용인상공회의소 스크래퍼 테스트 완료 ===")
        
        # 결과 검증
        verify_results(output_dir)
        
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}")
        raise

def verify_results(output_dir):
    """결과 검증"""
    logger = logging.getLogger(__name__)
    
    if not os.path.exists(output_dir):
        logger.error(f"출력 디렉토리가 존재하지 않습니다: {output_dir}")
        return
    
    # 생성된 폴더 확인
    folders = [d for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d))]
    logger.info(f"생성된 공고 폴더 수: {len(folders)}")
    
    total_files = 0
    total_attachments = 0
    total_size = 0
    
    for folder in sorted(folders):
        folder_path = os.path.join(output_dir, folder)
        files = os.listdir(folder_path)
        
        # content.md 파일 확인
        content_file = os.path.join(folder_path, 'content.md')
        if os.path.exists(content_file):
            with open(content_file, 'r', encoding='utf-8') as f:
                content = f.read()
                logger.info(f"[{folder}] content.md: {len(content)} 글자")
        
        # 첨부파일 확인
        attachments = [f for f in files if f != 'content.md']
        if attachments:
            logger.info(f"[{folder}] 첨부파일: {len(attachments)}개")
            
            # attachments 폴더 내부 파일들 확인
            att_dir = os.path.join(folder_path, 'attachments')
            if os.path.exists(att_dir):
                att_files = os.listdir(att_dir)
                for att in att_files:
                    att_path = os.path.join(att_dir, att)
                    if os.path.isfile(att_path):
                        size = os.path.getsize(att_path)
                        total_size += size
                        logger.info(f"  - {att}: {size:,} bytes")
                        total_attachments += 1
        else:
            logger.info(f"[{folder}] 첨부파일: 없음")
        
        total_files += len(files)
    
    logger.info(f"\n=== 검증 결과 요약 ===")
    logger.info(f"공고 폴더 수: {len(folders)}")
    logger.info(f"총 파일 수: {total_files}")
    logger.info(f"첨부파일 수: {total_attachments}")
    logger.info(f"총 다운로드 크기: {total_size:,} bytes ({total_size/1024/1024:.2f} MB)")
    
    if total_attachments == 0:
        logger.warning("⚠️ 다운로드된 첨부파일이 없습니다!")
    else:
        logger.info(f"✅ 첨부파일 다운로드 성공: {total_attachments}개")

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='용인상공회의소 스크래퍼 테스트')
    parser.add_argument('--pages', type=int, default=3, help='테스트할 페이지 수 (기본값: 3)')
    parser.add_argument('--output', type=str, default='output/yongincci', help='출력 디렉토리')
    parser.add_argument('--single', action='store_true', help='단일 페이지만 테스트')
    
    args = parser.parse_args()
    
    # 로깅 설정
    setup_logging()
    
    pages = 1 if args.single else args.pages
    
    try:
        test_yongincci_scraper(pages=pages, output_dir=args.output)
        print(f"\n✅ 테스트 완료! 결과는 {args.output} 디렉토리에서 확인하세요.")
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()