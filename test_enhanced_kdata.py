#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced KDATA 스크래퍼 테스트
"""

import sys
import os
import logging
from datetime import datetime

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_kdata_scraper import EnhancedKdataScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_kdata_scraper():
    """KDATA 스크래퍼 테스트"""
    print("🚀 Enhanced KDATA 스크래퍼 테스트 시작")
    print("="*60)
    
    try:
        # 스크래퍼 인스턴스 생성
        scraper = EnhancedKdataScraper()
        logger.info("KDATA 스크래퍼 인스턴스 생성 완료")
        
        # 출력 디렉토리 설정
        output_dir = "./output/kdata_test"
        
        print(f"📂 출력 디렉토리: {output_dir}")
        print(f"🌐 베이스 URL: {scraper.base_url}")
        print(f"📋 목록 URL: {scraper.list_url}")
        print()
        
        # 1페이지만 테스트
        print("📄 1페이지 테스트 실행 중...")
        scraper.scrape_pages(max_pages=1, output_base=output_dir)
        
        # 결과 검증
        print("\n📊 결과 검증 중...")
        verify_results(output_dir)
        
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}")
        print(f"❌ 테스트 실패: {e}")
        return False
    
    print("✅ Enhanced KDATA 스크래퍼 테스트 완료")
    return True

def verify_results(output_dir):
    """결과 검증"""
    if not os.path.exists(output_dir):
        print("❌ 출력 디렉토리가 존재하지 않습니다")
        return
    
    # 공고 폴더들 찾기
    folders = [
        item for item in os.listdir(output_dir)
        if os.path.isdir(os.path.join(output_dir, item)) and item.startswith(('001_', '002_', '003_'))
    ]
    
    print(f"📁 생성된 공고 폴더: {len(folders)}개")
    
    total_files = 0
    total_size = 0
    announcements_with_attachments = 0
    url_check_passed = 0
    korean_filename_count = 0
    
    for folder in folders:
        folder_path = os.path.join(output_dir, folder)
        
        # content.md 파일 확인
        content_file = os.path.join(folder_path, 'content.md')
        if os.path.exists(content_file):
            with open(content_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 원본 URL 포함 여부 확인
            if '**원본 URL**:' in content and 'kdata.or.kr' in content:
                url_check_passed += 1
        
        # 첨부파일 확인
        attachments_dir = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_dir):
            announcements_with_attachments += 1
            
            for filename in os.listdir(attachments_dir):
                att_path = os.path.join(attachments_dir, filename)
                if os.path.isfile(att_path):
                    total_files += 1
                    file_size = os.path.getsize(att_path)
                    total_size += file_size
                    
                    # 한글 파일명 확인
                    has_korean = any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename)
                    if has_korean:
                        korean_filename_count += 1
                    
                    print(f"  📎 {filename} ({format_size(file_size)})")
    
    print(f"\n📈 상세 통계:")
    print(f"  • 총 공고 수: {len(folders)}개")
    print(f"  • 첨부파일이 있는 공고: {announcements_with_attachments}개")
    print(f"  • 총 다운로드 파일: {total_files}개")
    print(f"  • 한글 파일명: {korean_filename_count}개")
    print(f"  • 총 파일 크기: {format_size(total_size)}")
    print(f"  • 원본 URL 포함 공고: {url_check_passed}개")
    
    # 성공률 계산
    if len(folders) > 0:
        success_rate = (url_check_passed / len(folders)) * 100
        print(f"  • 성공률: {success_rate:.1f}%")

def format_size(size_bytes):
    """바이트를 읽기 쉬운 형태로 변환"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

if __name__ == "__main__":
    try:
        start_time = datetime.now()
        success = test_kdata_scraper()
        end_time = datetime.now()
        
        duration = (end_time - start_time).total_seconds()
        print(f"\n⏰ 실행 시간: {duration:.1f}초")
        
        if success:
            print("🎉 모든 테스트가 성공적으로 완료되었습니다!")
        else:
            print("⚠️  일부 테스트에서 문제가 발생했습니다.")
            
    except KeyboardInterrupt:
        print("\n⚠️  사용자에 의해 테스트가 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 테스트 실행 중 오류: {e}")
        logger.error(f"테스트 실행 중 오류: {e}")