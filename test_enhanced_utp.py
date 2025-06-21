#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UTP (울산테크노파크) 향상된 스크래퍼 테스트
"""

import os
import sys
import logging
import argparse
from enhanced_utp_scraper import EnhancedUTPScraper


def setup_logging():
    """로깅 설정"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('utp_scraper.log', encoding='utf-8')
        ]
    )


def test_utp_scraper(pages=3, single=False):
    """UTP 스크래퍼 테스트"""
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("UTP (울산테크노파크) 스크래퍼 테스트 시작")
    logger.info("=" * 60)
    
    # 출력 디렉토리 설정
    output_dir = "output/utp"
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # 스크래퍼 인스턴스 생성
        scraper = EnhancedUTPScraper()
        
        if single:
            # 단일 페이지 테스트
            logger.info("단일 페이지 테스트 모드")
            pages = 1
        
        # 스크래핑 실행
        logger.info(f"최대 {pages}페이지까지 스크래핑 시작")
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        
        # 결과 검증
        verify_results(output_dir)
        
        logger.info("=" * 60)
        logger.info("UTP 스크래퍼 테스트 완료")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}")
        raise


def verify_results(output_dir):
    """결과 검증"""
    logger = logging.getLogger(__name__)
    
    logger.info("\n" + "=" * 40)
    logger.info("결과 검증")
    logger.info("=" * 40)
    
    if not os.path.exists(output_dir):
        logger.error(f"출력 디렉토리가 존재하지 않습니다: {output_dir}")
        return
    
    # 공고 폴더 수 확인
    announcement_dirs = [d for d in os.listdir(output_dir) 
                        if os.path.isdir(os.path.join(output_dir, d)) and d.startswith(('001_', '002_', '003_'))]
    
    logger.info(f"총 {len(announcement_dirs)}개 공고 폴더 생성됨")
    
    # 각 공고별 상세 검증
    total_files = 0
    total_size = 0
    successful_downloads = 0
    failed_downloads = 0
    
    for i, folder_name in enumerate(sorted(announcement_dirs)[:5], 1):  # 처음 5개만 상세 검증
        folder_path = os.path.join(output_dir, folder_name)
        logger.info(f"\n[{i}] {folder_name}")
        
        # content.md 파일 확인
        content_file = os.path.join(folder_path, 'content.md')
        if os.path.exists(content_file):
            size = os.path.getsize(content_file)
            logger.info(f"  ✓ 본문 파일: {size:,} bytes")
            
            # 한글 파일명 확인을 위해 일부 내용 읽기
            try:
                with open(content_file, 'r', encoding='utf-8') as f:
                    content_preview = f.read(200)
                    if '지원사업' in content_preview or '공고' in content_preview or '울산테크노파크' in content_preview:
                        logger.info(f"  ✓ 한글 내용 확인됨")
            except Exception as e:
                logger.warning(f"  ⚠ 내용 확인 실패: {e}")
        else:
            logger.warning(f"  ✗ 본문 파일 없음")
        
        # 첨부파일 확인
        attachments_dir = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_dir):
            files = os.listdir(attachments_dir)
            if files:
                logger.info(f"  ✓ 첨부파일 {len(files)}개:")
                for file_name in files:
                    file_path = os.path.join(attachments_dir, file_name)
                    file_size = os.path.getsize(file_path)
                    total_files += 1
                    total_size += file_size
                    
                    if file_size > 0:
                        successful_downloads += 1
                        logger.info(f"    - {file_name}: {file_size:,} bytes ✓")
                    else:
                        failed_downloads += 1
                        logger.warning(f"    - {file_name}: 0 bytes ✗")
            else:
                logger.info(f"  - 첨부파일 없음")
        else:
            logger.info(f"  - 첨부파일 폴더 없음")
    
    # 전체 통계
    logger.info(f"\n" + "=" * 40)
    logger.info("전체 통계")
    logger.info("=" * 40)
    logger.info(f"처리된 공고 수: {len(announcement_dirs)}개")
    logger.info(f"총 첨부파일 수: {total_files}개")
    logger.info(f"성공한 다운로드: {successful_downloads}개")
    logger.info(f"실패한 다운로드: {failed_downloads}개")
    logger.info(f"총 다운로드 크기: {total_size:,} bytes ({total_size/1024/1024:.2f} MB)")
    
    if total_files > 0:
        success_rate = (successful_downloads / total_files) * 100
        logger.info(f"다운로드 성공률: {success_rate:.1f}%")
        
        if success_rate >= 80:
            logger.info("✓ 다운로드 성공률이 양호합니다")
        else:
            logger.warning("⚠ 다운로드 성공률이 낮습니다")
    
    # 한글 파일명 처리 확인
    korean_files = 0
    for folder_name in announcement_dirs:
        attachments_dir = os.path.join(output_dir, folder_name, 'attachments')
        if os.path.exists(attachments_dir):
            for file_name in os.listdir(attachments_dir):
                if any(ord(char) > 127 for char in file_name):  # 한글 포함 확인
                    korean_files += 1
                    break
    
    if korean_files > 0:
        logger.info(f"✓ 한글 파일명 처리: {korean_files}개 폴더에서 확인됨")
    
    # 원본 URL 포함 확인
    url_included = 0
    for i, folder_name in enumerate(announcement_dirs[:3]):  # 처음 3개만 확인
        content_file = os.path.join(output_dir, folder_name, 'content.md')
        if os.path.exists(content_file):
            try:
                with open(content_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'utp.or.kr' in content and '원본 URL' in content:
                        url_included += 1
            except:
                pass
    
    if url_included > 0:
        logger.info(f"✓ 원본 URL 포함: {url_included}개 파일에서 확인됨")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='UTP 스크래퍼 테스트')
    parser.add_argument('--pages', type=int, default=3, help='테스트할 페이지 수 (기본값: 3)')
    parser.add_argument('--single', action='store_true', help='단일 페이지 테스트')
    
    args = parser.parse_args()
    
    setup_logging()
    
    try:
        test_utp_scraper(pages=args.pages, single=args.single)
    except KeyboardInterrupt:
        print("\n테스트가 사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"테스트 실행 중 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()