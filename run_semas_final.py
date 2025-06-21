#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEMAS 최종 테스트 (3페이지)
"""

import sys
import os
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_semas_scraper import EnhancedSEMASScraper

def run_semas_final():
    """SEMAS 최종 테스트"""
    
    print("SEMAS 3페이지 스크래핑 시작")
    
    try:
        scraper = EnhancedSEMASScraper()
        
        # 출력 디렉토리 설정
        output_dir = "output/semas"
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"출력 디렉토리: {output_dir}")
        
        # 3페이지 스크래핑
        success = scraper.scrape_pages(max_pages=3, output_base=output_dir)
        
        if success:
            print("✅ 3페이지 스크래핑 성공!")
            
            # 결과 확인
            for root, dirs, files in os.walk(output_dir):
                level = root.replace(output_dir, '').count(os.sep)
                indent = ' ' * 2 * level
                print(f"{indent}{os.path.basename(root)}/")
                subindent = ' ' * 2 * (level + 1)
                for file in files:
                    file_path = os.path.join(root, file)
                    file_size = os.path.getsize(file_path)
                    print(f"{subindent}{file} ({file_size:,} bytes)")
            
            return True
        else:
            print("❌ 3페이지 스크래핑 실패")
            return False
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_semas_final()
    if success:
        print("\n🎉 SEMAS 최종 테스트 성공!")
    else:
        print("\n💥 SEMAS 최종 테스트 실패!")