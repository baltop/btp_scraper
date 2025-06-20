#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DJTP Enhanced 스크래퍼 테스트 스크립트
"""

import logging
import os
import sys
from enhanced_djtp_scraper import EnhancedDJTPScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('djtp_scraper.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def test_djtp_scraper(pages=3):
    """DJTP 스크래퍼 테스트 - 기본값 3페이지"""
    logger.info("=== DJTP Enhanced 스크래퍼 테스트 시작 ===")
    
    try:
        # 스크래퍼 초기화
        scraper = EnhancedDJTPScraper()
        
        # 출력 디렉토리 설정 - output/djtp (표준 형식)
        output_dir = "output/djtp"
        os.makedirs(output_dir, exist_ok=True)
        
        # 스크래핑 실행
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        
        logger.info("=== DJTP 스크래퍼 테스트 완료 ===")
        
        # 결과 검증
        verify_results(output_dir)
        
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}")
        raise

def verify_results(output_dir):
    """결과 검증 - 첨부파일 검증 필수"""
    logger.info("=== 결과 검증 시작 ===")
    
    # 공고 폴더들 확인
    announcement_folders = [d for d in os.listdir(output_dir) 
                          if os.path.isdir(os.path.join(output_dir, d)) and d.startswith(('001_', '002_', '003_'))]
    
    logger.info(f"총 {len(announcement_folders)}개 공고 폴더 생성됨")
    
    total_items = len(announcement_folders)
    successful_items = 0
    total_attachments = 0
    korean_files = 0
    url_check_passed = 0
    file_size_total = 0
    pdf_files = 0
    
    for folder_name in announcement_folders[:20]:  # 상위 20개만 검증
        folder_path = os.path.join(output_dir, folder_name)
        
        # content.md 파일 확인
        content_file = os.path.join(folder_path, 'content.md')
        if os.path.exists(content_file):
            successful_items += 1
            
            # 원본 URL 포함 확인
            with open(content_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if '**원본 URL**:' in content and 'djtp.or.kr' in content:
                    url_check_passed += 1
        
        # 첨부파일 확인 (PDF 파일 중심)
        attachments_dir = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_dir):
            attachment_files = os.listdir(attachments_dir)
            total_attachments += len(attachment_files)
            
            # 첨부파일 상세 분석
            for filename in attachment_files:
                # 한글 파일명 확인
                if any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename):
                    korean_files += 1
                
                # PDF 파일 확인
                if filename.lower().endswith('.pdf'):
                    pdf_files += 1
                
                # 파일 크기 확인
                att_path = os.path.join(attachments_dir, filename)
                if os.path.exists(att_path):
                    file_size = os.path.getsize(att_path)
                    file_size_total += file_size
                    logger.info(f"  - {filename}: {file_size:,} bytes")
                    
                    # PDF 파일 내용 검증 (첫 몇 바이트로 PDF 여부 확인)
                    if filename.lower().endswith('.pdf'):
                        with open(att_path, 'rb') as f:
                            header = f.read(4)
                            if header.startswith(b'%PDF'):
                                logger.debug(f"    유효한 PDF 파일: {filename}")
                            else:
                                logger.warning(f"    의심스러운 PDF 파일: {filename}")
    
    # 결과 요약
    success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
    avg_file_size = file_size_total / total_attachments if total_attachments > 0 else 0
    pdf_rate = (pdf_files / total_attachments) * 100 if total_attachments > 0 else 0
    
    logger.info("=== 검증 결과 요약 ===")
    logger.info(f"총 공고 수: {total_items}")
    logger.info(f"성공적 처리: {successful_items} ({success_rate:.1f}%)")
    logger.info(f"원본 URL 포함: {url_check_passed}")
    logger.info(f"총 첨부파일: {total_attachments}")
    logger.info(f"PDF 파일: {pdf_files} ({pdf_rate:.1f}%)")
    logger.info(f"한글 파일명: {korean_files}")
    logger.info(f"총 파일 용량: {file_size_total:,} bytes")
    logger.info(f"평균 파일 크기: {avg_file_size:,.0f} bytes")
    
    # 첨부파일 타입 분석
    if total_attachments > 0:
        logger.info("=== 첨부파일 분석 ===")
        file_types = {}
        for folder_name in announcement_folders[:20]:
            attachments_dir = os.path.join(output_dir, folder_name, 'attachments')
            if os.path.exists(attachments_dir):
                for filename in os.listdir(attachments_dir):
                    ext = filename.lower().split('.')[-1] if '.' in filename else 'unknown'
                    file_types[ext] = file_types.get(ext, 0) + 1
        
        for ext, count in sorted(file_types.items()):
            logger.info(f"  {ext.upper()}: {count}개")
    
    # DJTP 특화 검증
    logger.info("=== DJTP 특화 검증 ===")
    
    # 사업 정보 확인
    business_info = {}
    department_count = {}
    
    for folder_name in announcement_folders[:15]:
        content_file = os.path.join(output_dir, folder_name, 'content.md')
        if os.path.exists(content_file):
            with open(content_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 사업 유형 확인
                for biz_type in ['사업화', '기술', '지식재산권', '사업화패키지', '인프라', '기타']:
                    if biz_type in content:
                        business_info[biz_type] = business_info.get(biz_type, 0) + 1
                
                # 담당 부서 확인
                for dept in ['로봇·방위산업센터', '기술사업화실', '지역산업육성실', '우주·ICT산업센터', '바이오센터']:
                    if dept in content:
                        department_count[dept] = department_count.get(dept, 0) + 1
    
    if business_info:
        logger.info("사업 유형 분포:")
        for biz_type, count in sorted(business_info.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {biz_type}: {count}개")
    
    if department_count:
        logger.info("담당 부서 분포:")
        for dept, count in sorted(department_count.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {dept}: {count}개")
    
    # PDF 다운로드 성공률 검증
    pdf_success_rate = (pdf_files / total_items) * 100 if total_items > 0 else 0
    logger.info(f"PDF 다운로드 성공률: {pdf_success_rate:.1f}%")
    
    if success_rate >= 80 and pdf_success_rate >= 70:
        logger.info("✅ 테스트 성공! PDF 다운로드도 정상 작동")
    elif success_rate >= 80:
        logger.warning(f"⚠️ 기본 테스트는 성공했으나 PDF 다운로드 성공률이 낮습니다: {pdf_success_rate:.1f}%")
    else:
        logger.warning(f"⚠️ 성공률이 낮습니다: {success_rate:.1f}%")

def test_single_page():
    """단일 페이지 테스트"""
    logger.info("=== 단일 페이지 테스트 ===")
    test_djtp_scraper(pages=1)

def test_three_pages():
    """3페이지 테스트"""
    logger.info("=== 3페이지 테스트 ===")
    test_djtp_scraper(pages=3)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='DJTP Enhanced 스크래퍼 테스트')
    parser.add_argument('--pages', type=int, default=3, help='테스트할 페이지 수 (기본값: 3)')
    parser.add_argument('--single', action='store_true', help='단일 페이지 테스트')
    
    args = parser.parse_args()
    
    if args.single:
        test_single_page()
    else:
        test_djtp_scraper(pages=args.pages)