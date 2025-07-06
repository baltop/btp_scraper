#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GSIC 스크래퍼 테스트 스크립트
"""

import os
import sys
import logging
from enhanced_gsic_scraper import EnhancedGsicScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('gsic_test.log', encoding='utf-8')
    ]
)

def test_gsic_scraper(pages=3):
    """GSIC 스크래퍼 테스트"""
    print(f"=== GSIC 스크래퍼 테스트 시작 (최대 {pages}페이지) ===")
    
    # 출력 디렉토리 생성
    output_dir = "output/gsic"
    os.makedirs(output_dir, exist_ok=True)
    
    # 스크래퍼 생성 및 실행
    scraper = EnhancedGsicScraper()
    
    try:
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        print(f"✅ 스크래핑 완료!")
        
        # 결과 검증
        verify_results(output_dir)
        
    except Exception as e:
        print(f"❌ 스크래핑 실패: {e}")
        raise

def verify_results(output_dir):
    """결과 검증"""
    print(f"\n=== 결과 검증 ===")
    
    if not os.path.exists(output_dir):
        print("❌ 출력 디렉토리가 존재하지 않습니다")
        return
    
    # 공고 디렉토리 개수 확인
    announcement_dirs = [d for d in os.listdir(output_dir) 
                        if os.path.isdir(os.path.join(output_dir, d))]
    print(f"📁 총 공고 디렉토리: {len(announcement_dirs)}개")
    
    # 각 공고별 파일 확인
    total_files = 0
    total_attachments = 0
    
    for dir_name in announcement_dirs[:5]:  # 처음 5개만 상세 확인
        dir_path = os.path.join(output_dir, dir_name)
        files = os.listdir(dir_path)
        
        # content.md 파일 확인
        content_file = os.path.join(dir_path, 'content.md')
        if os.path.exists(content_file):
            with open(content_file, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"📄 {dir_name}: content.md ({len(content)} chars)")
        
        # 첨부파일 확인
        attachments = [f for f in files if f != 'content.md']
        if attachments:
            total_attachments += len(attachments)
            print(f"📎 {dir_name}: {len(attachments)}개 첨부파일")
            for att in attachments:
                att_path = os.path.join(dir_path, att)
                size = os.path.getsize(att_path)
                print(f"   - {att} ({size:,} bytes)")
        
        total_files += len(files)
    
    print(f"\n📊 요약:")
    print(f"   총 공고: {len(announcement_dirs)}개")
    print(f"   총 파일: {total_files}개")
    print(f"   총 첨부파일: {total_attachments}개")
    
    # 한글 파일명 확인
    korean_files = []
    for dir_name in announcement_dirs:
        dir_path = os.path.join(output_dir, dir_name)
        for file in os.listdir(dir_path):
            if any(ord(c) >= 0xAC00 and ord(c) <= 0xD7A3 for c in file):
                korean_files.append(file)
    
    if korean_files:
        print(f"🇰🇷 한글 파일명: {len(korean_files)}개")
        for kf in korean_files[:3]:  # 처음 3개만 표시
            print(f"   - {kf}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='GSIC 스크래퍼 테스트')
    parser.add_argument('--pages', type=int, default=3, help='테스트할 페이지 수 (기본값: 3)')
    parser.add_argument('--single', action='store_true', help='1페이지만 테스트')
    
    args = parser.parse_args()
    
    pages = 1 if args.single else args.pages
    test_gsic_scraper(pages)