#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POHANGCCI 향상된 스크래퍼 테스트
"""

import sys
import os
import logging
import asyncio

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_pohangcci_scraper import EnhancedPOHANGCCIScraper

def test_pohangcci_scraper(pages=3):
    """POHANGCCI 스크래퍼 테스트"""
    print("=" * 60)
    print("POHANGCCI 향상된 스크래퍼 테스트 시작")
    print("=" * 60)
    
    try:
        scraper = EnhancedPOHANGCCIScraper()
        
        # 출력 디렉토리 설정
        output_dir = "output/pohangcci"
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"출력 디렉토리: {output_dir}")
        print(f"테스트 페이지 수: {pages}")
        print(f"사이트 URL: {scraper.list_url}")
        print()
        
        # Playwright 설치 확인
        try:
            from playwright.async_api import async_playwright
            print("✅ Playwright 설치 확인됨")
        except ImportError:
            print("❌ Playwright가 설치되지 않았습니다")
            print("다음 명령어로 설치해주세요:")
            print("pip install playwright")
            print("playwright install chromium")
            return False
        
        # 스크래핑 실행
        print("스크래핑 시작...")
        success = scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        
        if success:
            print("\n" + "=" * 60)
            print("✅ 스크래핑 성공!")
            print("=" * 60)
            
            # 결과 분석
            analyze_results(output_dir)
            
        else:
            print("\n" + "=" * 60)
            print("❌ 스크래핑 실패")
            print("=" * 60)
            
        return success
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

def analyze_results(output_dir):
    """결과 분석 및 출력"""
    print("📊 결과 분석:")
    print("-" * 40)
    
    announcement_count = 0
    total_files = 0
    total_size = 0
    attachment_count = 0
    content_files = 0
    
    # 각 공고 폴더 분석
    if os.path.exists(output_dir):
        for item in os.listdir(output_dir):
            item_path = os.path.join(output_dir, item)
            if os.path.isdir(item_path):
                announcement_count += 1
                
                # content.md 파일 확인
                content_file = os.path.join(item_path, 'content.md')
                if os.path.exists(content_file):
                    content_files += 1
                    file_size = os.path.getsize(content_file)
                    total_files += 1
                    total_size += file_size
                    print(f"  📄 {item}/content.md ({file_size:,} bytes)")
                
                # 첨부파일 폴더 확인
                attachments_dir = os.path.join(item_path, 'attachments')
                if os.path.exists(attachments_dir):
                    for file in os.listdir(attachments_dir):
                        file_path = os.path.join(attachments_dir, file)
                        if os.path.isfile(file_path):
                            file_size = os.path.getsize(file_path)
                            total_files += 1
                            total_size += file_size
                            attachment_count += 1
                            print(f"  📎 {item}/attachments/{file} ({file_size:,} bytes)")
    
    print("-" * 40)
    print(f"📋 요약:")
    print(f"  - 처리된 공고: {announcement_count}개")
    print(f"  - 본문 파일: {content_files}개")
    print(f"  - 첨부파일: {attachment_count}개")
    print(f"  - 전체 파일: {total_files}개")
    print(f"  - 전체 크기: {total_size:,} bytes ({total_size/1024/1024:.2f} MB)")
    
    # 파일 검증
    verify_file_downloads(output_dir)

def verify_file_downloads(output_dir):
    """파일 다운로드 검증"""
    print("\n🔍 파일 다운로드 검증:")
    print("-" * 40)
    
    zero_size_files = []
    large_files = []
    korean_filename_files = []
    
    if os.path.exists(output_dir):
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                file_path = os.path.join(root, file)
                file_size = os.path.getsize(file_path)
                
                # 0바이트 파일 체크
                if file_size == 0:
                    zero_size_files.append(file_path)
                
                # 큰 파일 체크 (1MB 이상)
                if file_size > 1024 * 1024:
                    large_files.append((file_path, file_size))
                
                # 한글 파일명 체크
                if any(ord(char) > 127 for char in file):
                    korean_filename_files.append(file_path)
    
    # 검증 결과 출력
    if zero_size_files:
        print(f"⚠️  0바이트 파일: {len(zero_size_files)}개")
        for file_path in zero_size_files[:5]:  # 최대 5개만 표시
            print(f"    - {os.path.basename(file_path)}")
    else:
        print("✅ 0바이트 파일 없음")
    
    if large_files:
        print(f"📁 대용량 파일 (1MB+): {len(large_files)}개")
        for file_path, size in large_files[:3]:  # 최대 3개만 표시
            print(f"    - {os.path.basename(file_path)} ({size:,} bytes)")
    
    if korean_filename_files:
        print(f"🇰🇷 한글 파일명: {len(korean_filename_files)}개")
        for file_path in korean_filename_files[:3]:  # 최대 3개만 표시
            print(f"    - {os.path.basename(file_path)}")
    else:
        print("ℹ️  한글 파일명 없음")
    
    print("-" * 40)

def check_playwright_installation():
    """Playwright 설치 상태 확인"""
    try:
        from playwright.async_api import async_playwright
        print("✅ Playwright 모듈 설치됨")
        
        # 브라우저 바이너리 확인
        import subprocess
        result = subprocess.run(['playwright', 'list'], capture_output=True, text=True)
        if 'chromium' in result.stdout:
            print("✅ Chromium 브라우저 설치됨")
            return True
        else:
            print("❌ Chromium 브라우저 미설치")
            print("다음 명령어로 설치해주세요: playwright install chromium")
            return False
            
    except ImportError:
        print("❌ Playwright 모듈 미설치")
        print("다음 명령어로 설치해주세요:")
        print("pip install playwright")
        print("playwright install chromium")
        return False
    except FileNotFoundError:
        print("⚠️  playwright 명령어를 찾을 수 없습니다")
        print("Playwright는 설치되었지만 CLI가 PATH에 없을 수 있습니다")
        return True  # 모듈은 있으므로 시도해볼 수 있음

def single_page_test():
    """단일 페이지 테스트"""
    print("🔬 단일 페이지 테스트 실행...")
    return test_pohangcci_scraper(pages=1)

def full_test():
    """전체 3페이지 테스트"""
    print("🚀 전체 3페이지 테스트 실행...")
    return test_pohangcci_scraper(pages=3)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='POHANGCCI 스크래퍼 테스트')
    parser.add_argument('--pages', type=int, default=3, help='테스트할 페이지 수 (기본값: 3)')
    parser.add_argument('--single', action='store_true', help='단일 페이지 테스트')
    parser.add_argument('--check', action='store_true', help='Playwright 설치 상태 확인')
    
    args = parser.parse_args()
    
    if args.check:
        check_playwright_installation()
        exit(0)
    
    if args.single:
        success = single_page_test()
    else:
        success = test_pohangcci_scraper(args.pages)
    
    if success:
        print("\n🎉 테스트 성공!")
        exit(0)
    else:
        print("\n💥 테스트 실패!")
        exit(1)