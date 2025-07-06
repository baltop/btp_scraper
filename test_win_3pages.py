#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
from enhanced_win_scraper import EnhancedWinScraper

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_win_3pages():
    """WIN 스크래퍼 3페이지 전체 테스트"""
    
    print("🚀 WIN 스크래퍼 3페이지 테스트 시작")
    
    scraper = EnhancedWinScraper()
    output_dir = "output/win_final"
    os.makedirs(output_dir, exist_ok=True)
    
    # 3페이지 테스트
    print("📋 3페이지 스크래핑 테스트")
    scraper.scrape_pages(max_pages=3, output_base=output_dir)
    
    # 결과 확인
    if os.path.exists(output_dir):
        folders = [f for f in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, f))]
        print(f"✅ 총 수집된 공고: {len(folders)}개")
        
        # 첨부파일 확인
        total_files = 0
        total_size = 0
        file_types = {}
        
        for folder in folders:
            attachments_dir = os.path.join(output_dir, folder, "attachments")
            if os.path.exists(attachments_dir):
                files = [f for f in os.listdir(attachments_dir) if os.path.isfile(os.path.join(attachments_dir, f))]
                for file in files:
                    file_path = os.path.join(attachments_dir, file)
                    file_size = os.path.getsize(file_path)
                    total_files += 1
                    total_size += file_size
                    
                    # 파일 타입별 통계
                    ext = file.split('.')[-1].lower()
                    file_types[ext] = file_types.get(ext, 0) + 1
                
                if files:
                    print(f"  📎 {folder}: {len(files)}개 파일")
        
        print(f"\n📊 첨부파일 통계:")
        print(f"  • 총 파일 수: {total_files}개")
        print(f"  • 총 파일 크기: {total_size/1024/1024:.1f} MB")
        
        if file_types:
            print(f"  • 파일 타입별:")
            for ext, count in sorted(file_types.items()):
                print(f"    - {ext.upper()}: {count}개")
        
        # 샘플 파일 확인
        sample_files = []
        for folder in folders[:3]:  # 처음 3개 폴더만
            attachments_dir = os.path.join(output_dir, folder, "attachments")
            if os.path.exists(attachments_dir):
                files = [f for f in os.listdir(attachments_dir) if os.path.isfile(os.path.join(attachments_dir, f))]
                for file in files[:2]:  # 각 폴더에서 2개까지만
                    file_path = os.path.join(attachments_dir, file)
                    file_size = os.path.getsize(file_path)
                    sample_files.append(f"    {file} ({file_size} bytes)")
        
        if sample_files:
            print(f"\n📋 샘플 파일들:")
            for sample in sample_files[:10]:  # 최대 10개만 표시
                print(sample)
    else:
        print("❌ 출력 폴더를 찾을 수 없습니다")

if __name__ == "__main__":
    test_win_3pages()