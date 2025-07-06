#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
from enhanced_win_scraper import EnhancedWinScraper

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_win_scraper():
    """WIN 스크래퍼 간단 테스트 - 1페이지만"""
    
    print("🚀 WIN 스크래퍼 테스트 시작")
    
    scraper = EnhancedWinScraper()
    output_dir = "output/win_test"
    os.makedirs(output_dir, exist_ok=True)
    
    # 1페이지만 테스트
    print("📋 1페이지 스크래핑 테스트")
    scraper.scrape_pages(max_pages=1, output_base=output_dir)
    
    # 결과 확인
    if os.path.exists(output_dir):
        folders = [f for f in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, f))]
        print(f"✅ 수집된 공고: {len(folders)}개")
        
        # 첨부파일 확인
        total_files = 0
        for folder in folders:
            attachments_dir = os.path.join(output_dir, folder, "attachments")
            if os.path.exists(attachments_dir):
                files = [f for f in os.listdir(attachments_dir) if os.path.isfile(os.path.join(attachments_dir, f))]
                total_files += len(files)
                if files:
                    print(f"  📎 {folder}: {len(files)}개 파일")
        
        print(f"📊 총 첨부파일: {total_files}개")
    else:
        print("❌ 출력 폴더를 찾을 수 없습니다")

if __name__ == "__main__":
    test_win_scraper()