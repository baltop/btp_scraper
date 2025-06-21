#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEMAS scrape_pages 메서드 테스트
"""

import sys
import os
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_semas_scraper import EnhancedSEMASScraper

def test_scrape_pages():
    """scrape_pages 메서드 테스트"""
    
    try:
        print("스크래퍼 초기화 중...")
        scraper = EnhancedSEMASScraper()
        
        # 출력 디렉토리 설정
        output_dir = "output/semas_test"
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"출력 디렉토리: {output_dir}")
        
        # 1페이지만 테스트
        print("1페이지 스크래핑 시작...")
        success = scraper.scrape_pages(max_pages=1, output_base=output_dir)
        
        if success:
            print("✅ scrape_pages 성공!")
            
            # 결과 확인
            for root, dirs, files in os.walk(output_dir):
                for dir_name in dirs:
                    print(f"생성된 디렉토리: {dir_name}")
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    file_size = os.path.getsize(file_path)
                    print(f"생성된 파일: {file_path} ({file_size} bytes)")
                    
        else:
            print("❌ scrape_pages 실패")
            
        return success
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_scrape_pages()
    if success:
        print("\n🎉 scrape_pages 테스트 성공!")
    else:
        print("\n💥 scrape_pages 테스트 실패!")