#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Fintech 스크래퍼 테스트 스크립트
"""

import os
import sys
import logging

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_fintech_scraper import EnhancedFintechScraper

def setup_logging():
    """로깅 설정"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
        ]
    )

def test_fintech_scraper(pages=3):
    """Fintech 스크래퍼 테스트"""
    print(f"=== 금융보안원 Fintech 스크래퍼 테스트 시작 ({pages}페이지) ===")
    
    # 출력 디렉토리 설정
    output_dir = "output/fintech"
    print(f"출력 디렉토리: {output_dir}")
    
    # 스크래퍼 초기화
    scraper = EnhancedFintechScraper()
    
    try:
        # 스크래핑 실행
        os.makedirs(output_dir, exist_ok=True)
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        
        # 결과 검증
        verify_results(output_dir)
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

def verify_results(output_dir):
    """결과 검증"""
    print("=== 결과 검증 시작 ===")
    
    if not os.path.exists(output_dir):
        print("❌ 출력 디렉토리가 존재하지 않습니다")
        return
    
    # 공고 폴더 목록
    announcement_folders = [d for d in os.listdir(output_dir) 
                          if os.path.isdir(os.path.join(output_dir, d))]
    
    total_items = len(announcement_folders)
    successful_items = 0
    url_check_passed = 0
    total_attachments = 0
    pdf_files = 0
    hwp_files = 0
    image_files = 0
    korean_files = 0
    file_size_total = 0
    
    for folder_name in announcement_folders:
        folder_path = os.path.join(output_dir, folder_name)
        
        # content.md 파일 확인
        content_file = os.path.join(folder_path, 'content.md')
        if os.path.exists(content_file):
            successful_items += 1
            
            # 원본 URL 포함 확인
            with open(content_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if '**원본 URL**:' in content and 'fintech.or.kr' in content:
                    url_check_passed += 1
        
        # 첨부파일 검증
        attachments_dir = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_dir):
            for filename in os.listdir(attachments_dir):
                att_path = os.path.join(attachments_dir, filename)
                if os.path.isfile(att_path):
                    total_attachments += 1
                    
                    # 파일 유형 분류
                    if filename.lower().endswith('.pdf'):
                        pdf_files += 1
                    elif filename.lower().endswith(('.hwp', '.hwpx')):
                        hwp_files += 1
                    elif filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                        image_files += 1
                    
                    # 한글 파일명 검증
                    if any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename):
                        korean_files += 1
                    
                    # 파일 크기 검증
                    file_size = os.path.getsize(att_path)
                    file_size_total += file_size
                    
                    print(f"  - 첨부파일: {filename} ({file_size:,} bytes)")
    
    # 성공률 계산
    success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
    url_success_rate = (url_check_passed / total_items) * 100 if total_items > 0 else 0
    
    print("=== 검증 결과 요약 ===")
    print(f"총 공고 수: {total_items}")
    print(f"성공적 처리: {successful_items} ({success_rate:.1f}%)")
    print(f"원본 URL 포함: {url_check_passed} ({url_success_rate:.1f}%)")
    print(f"총 첨부파일: {total_attachments}")
    print(f"PDF 파일: {pdf_files}")
    print(f"HWP 파일: {hwp_files}")
    print(f"이미지 파일: {image_files}")
    print(f"한글 파일명: {korean_files}")
    print(f"총 파일 용량: {file_size_total:,} bytes ({file_size_total/1024/1024:.2f} MB)")
    
    # 첨부파일 분석
    attachments_with_files = sum(1 for folder in announcement_folders 
                               if os.path.exists(os.path.join(output_dir, folder, 'attachments')))
    attachments_without_files = total_items - attachments_with_files
    
    print(f"첨부파일 있는 공고: {attachments_with_files}")
    print(f"첨부파일 없는 공고: {attachments_without_files}")
    
    # Fintech 특성 분석
    if pdf_files > 0:
        print(f"✅ PDF 파일 {pdf_files}개 발견 - 공문서 특성 확인")
    if hwp_files > 0:
        print(f"✅ HWP 파일 {hwp_files}개 발견 - 한국 공공기관 특성 확인")
    if image_files > 0:
        print(f"✅ 이미지 파일 {image_files}개 발견 - 포스터/안내문 특성 확인")
    
    # 테스트 성공 여부 판단
    if success_rate >= 80:
        print("✅ 테스트 성공: 80% 이상 성공적으로 처리됨")
        return True
    else:
        print("❌ 테스트 실패: 성공률이 80% 미만임")
        return False

if __name__ == "__main__":
    setup_logging()
    
    # 명령행 인자 처리
    import argparse
    parser = argparse.ArgumentParser(description='Enhanced Fintech 스크래퍼 테스트')
    parser.add_argument('--pages', type=int, default=3, help='테스트할 페이지 수 (기본값: 3)')
    parser.add_argument('--single', action='store_true', help='단일 공고만 테스트')
    
    args = parser.parse_args()
    
    if args.single:
        # 단일 공고 테스트
        test_fintech_scraper(pages=1)
    else:
        # 전체 테스트
        test_fintech_scraper(pages=args.pages)