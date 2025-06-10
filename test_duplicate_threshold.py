#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import logging

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_ccei_scraper import EnhancedCCEIScraper

def test_duplicate_threshold():
    """중복 임계값 테스트"""
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("Enhanced CCEI 스크래퍼 - 중복 임계값 테스트")
    print("=" * 50)
    
    try:
        # 스크래퍼 인스턴스 생성
        scraper = EnhancedCCEIScraper()
        
        # 중복 임계값을 3으로 설정 (기본값)
        print(f"중복 임계값: {scraper.duplicate_threshold}개")
        
        # 6페이지 스크래핑 실행 (중복 체크로 인해 조기 종료될 것)
        output_dir = 'output_duplicate_test'
        scraper.scrape_pages(max_pages=6, output_base=output_dir)
        
        print(f"\n테스트 완료! 결과는 {output_dir} 폴더에 저장되었습니다.")
        
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_duplicate_threshold()