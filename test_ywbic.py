#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YWBIC (영월군 비즈니스 인큐베이터 센터) Enhanced Scraper 테스트 스크립트
"""

import os
import sys
import logging
from datetime import datetime
from enhanced_ywbic_scraper import EnhancedYwbicScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'ywbic_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def test_ywbic_scraper(pages=3):
    """YWBIC 스크래퍼 테스트"""
    print(f"🚀 YWBIC Enhanced Scraper 테스트 시작 (최대 {pages}페이지)")
    print("=" * 60)
    
    # 출력 디렉토리 설정
    output_dir = "output/ywbic"
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # 스크래퍼 초기화
        scraper = EnhancedYwbicScraper()
        print(f"✅ 스크래퍼 초기화 완료")
        
        # 스크래핑 실행
        start_time = datetime.now()
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        end_time = datetime.now()
        
        duration = end_time - start_time
        print(f"⏱️  스크래핑 소요 시간: {duration}")
        
        # 결과 검증
        verify_results(output_dir, pages)
        
    except Exception as e:
        logger.error(f"스크래핑 중 오류 발생: {e}")
        print(f"❌ 스크래핑 실패: {e}")
        raise

def verify_results(output_dir, expected_pages):
    """결과 검증"""
    print("\n📊 결과 검증 중...")
    print("-" * 40)
    
    if not os.path.exists(output_dir):
        print("❌ 출력 디렉토리가 존재하지 않습니다")
        return
    
    # 1. 공고 디렉토리 수 확인
    announcement_dirs = [d for d in os.listdir(output_dir) 
                        if os.path.isdir(os.path.join(output_dir, d))]
    
    total_announcements = len(announcement_dirs)
    expected_announcements = expected_pages * 25  # 페이지당 약 25개 (공지 + 일반)
    
    print(f"📁 수집된 공고 수: {total_announcements}개")
    print(f"📄 예상 공고 수: 약 {expected_announcements}개")
    
    if total_announcements > 0:
        success_rate = min(100, (total_announcements / expected_announcements) * 100)
        print(f"✅ 수집 성공률: {success_rate:.1f}%")
    else:
        print("❌ 수집된 공고가 없습니다")
        return
    
    # 2. 첨부파일 다운로드 상태 확인
    total_files = 0
    total_size = 0
    korean_files = 0
    
    for announcement_dir in announcement_dirs:
        dir_path = os.path.join(output_dir, announcement_dir)
        if os.path.isdir(dir_path):
            files = [f for f in os.listdir(dir_path) 
                    if os.path.isfile(os.path.join(dir_path, f)) and f != 'content.md']
            
            total_files += len(files)
            
            for file in files:
                file_path = os.path.join(dir_path, file)
                file_size = os.path.getsize(file_path)
                total_size += file_size
                
                # 한글 파일명 확인
                if any(ord(char) > 127 for char in file):
                    korean_files += 1
    
    print(f"📎 다운로드된 첨부파일: {total_files}개")
    print(f"💾 총 파일 크기: {format_size(total_size)}")
    print(f"🇰🇷 한글 파일명: {korean_files}개")
    
    # 3. 샘플 공고 내용 확인
    print("\n📋 샘플 공고 확인:")
    print("-" * 30)
    
    sample_count = min(3, len(announcement_dirs))
    for i, announcement_dir in enumerate(announcement_dirs[:sample_count]):
        dir_path = os.path.join(output_dir, announcement_dir)
        content_file = os.path.join(dir_path, 'content.md')
        
        if os.path.exists(content_file):
            with open(content_file, 'r', encoding='utf-8') as f:
                content = f.read()
                title_line = content.split('\n')[0] if content else "제목 없음"
                print(f"{i+1}. {title_line}")
        else:
            print(f"{i+1}. {announcement_dir} - content.md 없음")
    
    # 4. 원본 URL 포함 확인
    url_included = 0
    for announcement_dir in announcement_dirs[:5]:  # 처음 5개만 확인
        dir_path = os.path.join(output_dir, announcement_dir)
        content_file = os.path.join(dir_path, 'content.md')
        
        if os.path.exists(content_file):
            with open(content_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'ywbic.kr' in content:
                    url_included += 1
    
    print(f"🔗 원본 URL 포함: {url_included}/5개 확인")
    
    print("\n✅ 검증 완료!")

def format_size(size_bytes):
    """파일 크기를 읽기 쉬운 형태로 변환"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='YWBIC Enhanced Scraper 테스트')
    parser.add_argument('--pages', type=int, default=3, help='스크래핑할 페이지 수 (기본값: 3)')
    parser.add_argument('--single', action='store_true', help='1페이지만 테스트')
    
    args = parser.parse_args()
    
    pages = 1 if args.single else args.pages
    
    try:
        test_ywbic_scraper(pages)
        print(f"\n🎉 YWBIC 스크래퍼 테스트 완료!")
    except Exception as e:
        print(f"\n💥 테스트 실패: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()