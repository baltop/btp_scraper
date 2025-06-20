#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KOAT Enhanced 스크래퍼 테스트 스크립트
"""

import logging
import os
import sys
from enhanced_koat_scraper import EnhancedKOATScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('koat_scraper.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def test_koat_scraper(pages=3):
    """KOAT 스크래퍼 테스트 - 기본값 3페이지"""
    logger.info("=== KOAT Enhanced 스크래퍼 테스트 시작 ===")
    
    try:
        # 스크래퍼 초기화
        scraper = EnhancedKOATScraper()
        
        # 출력 디렉토리 설정 - output/koat (표준 형식)
        output_dir = "output/koat"
        os.makedirs(output_dir, exist_ok=True)
        
        # 스크래핑 실행
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        
        logger.info("=== KOAT 스크래퍼 테스트 완료 ===")
        
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
    
    for folder_name in announcement_folders[:20]:  # 상위 20개만 검증
        folder_path = os.path.join(output_dir, folder_name)
        
        # content.md 파일 확인
        content_file = os.path.join(folder_path, 'content.md')
        if os.path.exists(content_file):
            successful_items += 1
            
            # 원본 URL 포함 확인
            with open(content_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if '**원본 URL**:' in content and 'koat.or.kr' in content:
                    url_check_passed += 1
        
        # 첨부파일 확인
        attachments_dir = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_dir):
            attachment_files = os.listdir(attachments_dir)
            total_attachments += len(attachment_files)
            
            # 첨부파일 상세 분석
            for filename in attachment_files:
                # 한글 파일명 확인
                if any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename):
                    korean_files += 1
                
                # 파일 크기 확인
                att_path = os.path.join(attachments_dir, filename)
                if os.path.exists(att_path):
                    file_size = os.path.getsize(att_path)
                    file_size_total += file_size
                    logger.info(f"  - {filename}: {file_size:,} bytes")
                    
                    # 파일 타입별 검증
                    if filename.lower().endswith('.pdf'):
                        # PDF 파일 검증
                        with open(att_path, 'rb') as f:
                            header = f.read(4)
                            if header.startswith(b'%PDF'):
                                logger.debug(f"    유효한 PDF 파일: {filename}")
                            else:
                                logger.warning(f"    의심스러운 PDF 파일: {filename}")
                    elif filename.lower().endswith(('.hwp', '.doc', '.docx')):
                        # 문서 파일 검증
                        logger.debug(f"    문서 파일: {filename}")
                    elif filename.lower().endswith(('.jpg', '.png', '.gif')):
                        # 이미지 파일 검증
                        logger.debug(f"    이미지 파일: {filename}")
    
    # 결과 요약
    success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
    avg_file_size = file_size_total / total_attachments if total_attachments > 0 else 0
    attachment_rate = (len([f for f in announcement_folders[:20] 
                          if os.path.exists(os.path.join(output_dir, f, 'attachments'))]) / min(20, total_items)) * 100 if total_items > 0 else 0
    
    logger.info("=== 검증 결과 요약 ===")
    logger.info(f"총 공고 수: {total_items}")
    logger.info(f"성공적 처리: {successful_items} ({success_rate:.1f}%)")
    logger.info(f"원본 URL 포함: {url_check_passed}")
    logger.info(f"총 첨부파일: {total_attachments}")
    logger.info(f"한글 파일명: {korean_files}")
    logger.info(f"총 파일 용량: {file_size_total:,} bytes")
    logger.info(f"평균 파일 크기: {avg_file_size:,.0f} bytes")
    logger.info(f"첨부파일 보유율: {attachment_rate:.1f}%")
    
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
    
    # KOAT 특화 검증
    logger.info("=== KOAT 특화 검증 ===")
    
    # 농업 관련 키워드 확인
    agriculture_keywords = ['농업', '농촌', '농산물', '농기계', '농업기술', '스마트팜', '농업혁신', '귀농', '농가']
    keyword_count = {}
    
    # 제목 길이 분석
    title_lengths = []
    
    for folder_name in announcement_folders[:15]:
        content_file = os.path.join(output_dir, folder_name, 'content.md')
        if os.path.exists(content_file):
            with open(content_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 제목 추출
                lines = content.split('\n')
                if lines:
                    title = lines[0].replace('# ', '').strip()
                    title_lengths.append(len(title))
                
                # 농업 키워드 확인
                for keyword in agriculture_keywords:
                    if keyword in content:
                        keyword_count[keyword] = keyword_count.get(keyword, 0) + 1
    
    if keyword_count:
        logger.info("농업 관련 키워드 분포:")
        for keyword, count in sorted(keyword_count.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {keyword}: {count}개")
    
    if title_lengths:
        avg_title_length = sum(title_lengths) / len(title_lengths)
        logger.info(f"평균 제목 길이: {avg_title_length:.1f}자")
        logger.info(f"제목 길이 범위: {min(title_lengths)}~{max(title_lengths)}자")
    
    # 첨부파일 다운로드 성공률 검증
    attachment_success_rate = (total_attachments / total_items) if total_items > 0 else 0
    logger.info(f"첨부파일 평균 개수: {attachment_success_rate:.1f}개/공고")
    
    # 본문 내용 품질 확인
    content_quality_count = 0
    for folder_name in announcement_folders[:10]:
        content_file = os.path.join(output_dir, folder_name, 'content.md')
        if os.path.exists(content_file):
            with open(content_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # "본문 내용을 추출할 수 없습니다" 가 아닌 경우
                if "본문 내용을 추출할 수 없습니다" not in content and len(content) > 200:
                    content_quality_count += 1
    
    content_quality_rate = (content_quality_count / min(10, total_items)) * 100 if total_items > 0 else 0
    logger.info(f"본문 추출 성공률: {content_quality_rate:.1f}%")
    
    if success_rate >= 80 and content_quality_rate >= 60:
        logger.info("✅ 테스트 성공! 본문 추출과 첨부파일 다운로드 정상 작동")
    elif success_rate >= 80:
        logger.warning(f"⚠️ 기본 테스트는 성공했으나 본문 추출 성공률이 낮습니다: {content_quality_rate:.1f}%")
    else:
        logger.warning(f"⚠️ 성공률이 낮습니다: {success_rate:.1f}%")

def test_single_page():
    """단일 페이지 테스트"""
    logger.info("=== 단일 페이지 테스트 ===")
    test_koat_scraper(pages=1)

def test_three_pages():
    """3페이지 테스트"""
    logger.info("=== 3페이지 테스트 ===")
    test_koat_scraper(pages=3)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='KOAT Enhanced 스크래퍼 테스트')
    parser.add_argument('--pages', type=int, default=3, help='테스트할 페이지 수 (기본값: 3)')
    parser.add_argument('--single', action='store_true', help='단일 페이지 테스트')
    
    args = parser.parse_args()
    
    if args.single:
        test_single_page()
    else:
        test_koat_scraper(pages=args.pages)