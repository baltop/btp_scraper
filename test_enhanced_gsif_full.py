#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced GSIF 스크래퍼 전체 기능 테스트 (1페이지만)
"""

import sys
import os
import logging

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_gsif_scraper import EnhancedGSIFScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_full_scraping():
    """전체 스크래핑 기능 테스트 (1페이지만)"""
    print("=== Enhanced GSIF 전체 스크래핑 테스트 (1페이지) ===")
    
    # 스크래퍼 인스턴스 생성
    scraper = EnhancedGSIFScraper()
    
    # 출력 디렉토리 설정
    output_dir = "test_output_enhanced_gsif"
    
    try:
        # 1페이지만 스크래핑
        print(f"출력 디렉토리: {output_dir}")
        scraper.scrape_pages(max_pages=1, output_base=output_dir)
        
        print("\n=== 스크래핑 완료 ===")
        
        # 결과 확인
        if os.path.exists(output_dir):
            print(f"\n생성된 폴더 목록:")
            for item in sorted(os.listdir(output_dir)):
                item_path = os.path.join(output_dir, item)
                if os.path.isdir(item_path):
                    print(f"  📁 {item}")
                    # 폴더 내 파일 목록
                    for file in os.listdir(item_path):
                        file_path = os.path.join(item_path, file)
                        if os.path.isfile(file_path):
                            size = os.path.getsize(file_path)
                            print(f"    📄 {file} ({size:,} bytes)")
                        elif os.path.isdir(file_path):
                            print(f"    📁 {file}/")
                            # 첨부파일 폴더 내용
                            for att_file in os.listdir(file_path):
                                att_path = os.path.join(file_path, att_file)
                                if os.path.isfile(att_path):
                                    att_size = os.path.getsize(att_path)
                                    print(f"      📎 {att_file} ({att_size:,} bytes)")
        
        return True
        
    except Exception as e:
        print(f"ERROR: 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_full_scraping()
    sys.exit(0 if success else 1)