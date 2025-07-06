#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEHUB (서울특별시 사회적경제지원센터) 스크래퍼 테스트
"""

import os
import sys
import logging
import argparse
from enhanced_sehub_scraper import EnhancedSehubScraper

def setup_logging():
    """로깅 설정"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def test_sehub_scraper(pages=3):
    """SEHUB 스크래퍼 테스트"""
    print(f"=== SEHUB 스크래퍼 테스트 시작 (최대 {pages}페이지) ===")
    
    # 스크래퍼 인스턴스 생성
    scraper = EnhancedSehubScraper()
    
    # 출력 디렉토리 설정
    output_dir = "output/sehub"
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # 스크래핑 실행
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        
        print(f"\n=== 테스트 완료 ===")
        
    except Exception as e:
        print(f"오류 발생: {e}")
        return False
    
    return True

def verify_results(output_dir="output/sehub"):
    """결과 검증"""
    if not os.path.exists(output_dir):
        print("출력 디렉토리를 찾을 수 없습니다.")
        return
    
    print(f"\n=== 결과 검증: {output_dir} ===")
    
    # 공고 디렉토리 수 계산
    announcement_dirs = [d for d in os.listdir(output_dir) 
                        if os.path.isdir(os.path.join(output_dir, d)) and not d.startswith('.')]
    
    print(f"수집된 공고 수: {len(announcement_dirs)}개")
    
    # 첨부파일 통계
    total_files = 0
    file_types = {}
    total_size = 0
    
    for ann_dir in announcement_dirs:
        ann_path = os.path.join(output_dir, ann_dir)
        attachments_path = os.path.join(ann_path, "attachments")
        
        if os.path.exists(attachments_path):
            files = os.listdir(attachments_path)
            for file in files:
                if not file.startswith('.'):
                    total_files += 1
                    file_path = os.path.join(attachments_path, file)
                    
                    # 파일 크기
                    if os.path.isfile(file_path):
                        size = os.path.getsize(file_path)
                        total_size += size
                    
                    # 파일 확장자 통계
                    ext = os.path.splitext(file)[1].lower()
                    file_types[ext] = file_types.get(ext, 0) + 1
    
    print(f"첨부파일 총 개수: {total_files}개")
    print(f"첨부파일 총 크기: {total_size / 1024 / 1024:.2f} MB")
    
    if file_types:
        print("파일 형식별 통계:")
        for ext, count in sorted(file_types.items()):
            print(f"  {ext}: {count}개")
    
    # 한글 파일명 검사
    korean_files = []
    for ann_dir in announcement_dirs:
        ann_path = os.path.join(output_dir, ann_dir)
        attachments_path = os.path.join(ann_path, "attachments")
        
        if os.path.exists(attachments_path):
            files = os.listdir(attachments_path)
            for file in files:
                if not file.startswith('.'):
                    # 한글 문자 포함 검사
                    if any('\uac00' <= c <= '\ud7a3' for c in file):
                        korean_files.append(file)
    
    if korean_files:
        print(f"\n한글 파일명 {len(korean_files)}개 발견:")
        for file in korean_files[:5]:  # 처음 5개만 표시
            print(f"  - {file}")
        if len(korean_files) > 5:
            print(f"  ... 외 {len(korean_files)-5}개")
    
    # 성공률 계산
    content_files = 0
    for ann_dir in announcement_dirs:
        content_path = os.path.join(output_dir, ann_dir, "content.md")
        if os.path.exists(content_path):
            content_files += 1
    
    success_rate = (content_files / len(announcement_dirs) * 100) if announcement_dirs else 0
    print(f"\n성공률: {success_rate:.1f}% ({content_files}/{len(announcement_dirs)})")

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='SEHUB 스크래퍼 테스트')
    parser.add_argument('--pages', type=int, default=3, help='테스트할 페이지 수 (기본값: 3)')
    parser.add_argument('--single', action='store_true', help='1페이지만 테스트')
    
    args = parser.parse_args()
    
    setup_logging()
    
    pages = 1 if args.single else args.pages
    
    # 테스트 실행
    success = test_sehub_scraper(pages)
    
    if success:
        # 결과 검증
        verify_results()
    else:
        print("테스트 실패")
        sys.exit(1)

if __name__ == "__main__":
    main()