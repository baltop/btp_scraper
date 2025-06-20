#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
경남행복내일센터(gnlife5064.kr) Enhanced 스크래퍼 테스트
"""

import os
import sys
import logging
from enhanced_gnlife_scraper import EnhancedGnlifeScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gnlife_scraper.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def test_gnlife_scraper(pages=3):
    """경남행복내일센터 스크래퍼 테스트 - 기본 3페이지"""
    print(f"=== 경남행복내일센터 스크래퍼 테스트 시작 (최대 {pages}페이지) ===")
    
    scraper = EnhancedGnlifeScraper()
    output_dir = "output/gnlife"
    
    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # 스크래핑 실행
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        
        # 결과 검증
        verify_results(output_dir)
        
    except Exception as e:
        logger.error(f"스크래핑 중 오류 발생: {e}")
        raise

def verify_results(output_dir):
    """결과 검증 - 첨부파일 검증 필수"""
    print(f"\n=== 결과 검증 시작 ===")
    
    if not os.path.exists(output_dir):
        print(f"출력 디렉토리가 존재하지 않습니다: {output_dir}")
        return
    
    # 공고 폴더들 찾기
    announcement_folders = [d for d in os.listdir(output_dir) 
                          if os.path.isdir(os.path.join(output_dir, d)) and not d.startswith('.')]
    
    total_items = len(announcement_folders)
    successful_items = 0
    total_attachments = 0
    korean_files = 0
    file_size_total = 0
    url_check_passed = 0
    
    print(f"총 공고 폴더 수: {total_items}")
    
    for folder_name in announcement_folders:
        folder_path = os.path.join(output_dir, folder_name)
        
        # content.md 파일 확인
        content_file = os.path.join(folder_path, 'content.md')
        if os.path.exists(content_file):
            successful_items += 1
            
            # 원본 URL 포함 확인
            try:
                with open(content_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if '**원본 URL**:' in content and 'gnlife5064.kr' in content:
                        url_check_passed += 1
            except Exception as e:
                print(f"파일 읽기 오류 {content_file}: {e}")
        
        # 첨부파일 검증
        attachments_dir = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_dir):
            attachment_files = os.listdir(attachments_dir)
            folder_attachment_count = len(attachment_files)
            total_attachments += folder_attachment_count
            
            print(f"  {folder_name}: {folder_attachment_count}개 첨부파일")
            
            for filename in attachment_files:
                # 한글 파일명 검증
                has_korean = any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename)
                if has_korean:
                    korean_files += 1
                
                # 파일 크기 검증
                att_path = os.path.join(attachments_dir, filename)
                try:
                    file_size = os.path.getsize(att_path)
                    file_size_total += file_size
                    
                    print(f"    - {filename}: {file_size:,} bytes {'(한글)' if has_korean else ''}")
                    
                    if file_size == 0:
                        print(f"      ⚠️  빈 파일 발견: {filename}")
                except Exception as e:
                    print(f"      ❌ 파일 크기 확인 실패: {filename} - {e}")
        else:
            print(f"  {folder_name}: 첨부파일 없음")
    
    # 성공률 계산
    success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
    url_rate = (url_check_passed / total_items) * 100 if total_items > 0 else 0
    
    print(f"\n=== 검증 결과 요약 ===")
    print(f"총 공고 수: {total_items}")
    print(f"성공적 처리: {successful_items} ({success_rate:.1f}%)")
    print(f"원본 URL 포함: {url_check_passed} ({url_rate:.1f}%)")
    print(f"총 첨부파일: {total_attachments}")
    print(f"한글 파일명: {korean_files}")
    print(f"총 파일 용량: {file_size_total:,} bytes ({file_size_total/1024/1024:.2f} MB)")
    
    # 첨부파일 상세 분석
    if total_attachments > 0:
        avg_file_size = file_size_total / total_attachments
        print(f"평균 파일 크기: {avg_file_size:,.0f} bytes")
        
        # 파일 형식 분석
        file_extensions = {}
        for folder_name in announcement_folders:
            attachments_dir = os.path.join(output_dir, folder_name, 'attachments')
            if os.path.exists(attachments_dir):
                for filename in os.listdir(attachments_dir):
                    ext = os.path.splitext(filename)[1].lower()
                    if ext:
                        file_extensions[ext] = file_extensions.get(ext, 0) + 1
        
        print(f"파일 형식 분포: {dict(sorted(file_extensions.items()))}")
    
    # 성공 기준 확인
    if success_rate >= 80:
        print(f"✅ 테스트 성공: 성공률 {success_rate:.1f}% (기준: 80% 이상)")
    else:
        print(f"❌ 테스트 실패: 성공률 {success_rate:.1f}% (기준: 80% 이상)")
    
    return success_rate >= 80

def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='경남행복내일센터 스크래퍼 테스트')
    parser.add_argument('--pages', type=int, default=3, help='스크래핑할 페이지 수 (기본값: 3)')
    parser.add_argument('--single', action='store_true', help='단일 페이지만 테스트')
    
    args = parser.parse_args()
    
    if args.single:
        pages = 1
    else:
        pages = args.pages
    
    try:
        success = test_gnlife_scraper(pages)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"테스트 실행 중 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()