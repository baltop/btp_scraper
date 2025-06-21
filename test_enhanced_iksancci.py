#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Iksancci(익산상공회의소) 스크래퍼 테스트 스크립트
"""

import os
import sys
import time
import logging
from enhanced_iksancci_scraper import EnhancedIksancciScraper

def setup_logging():
    """로깅 설정"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('iksancci_test.log', encoding='utf-8')
        ]
    )

def test_iksancci_scraper(pages=3):
    """Iksancci 스크래퍼 테스트"""
    print(f"=== Enhanced Iksancci 스크래퍼 테스트 시작 ===")
    print(f"테스트 페이지: {pages}페이지")
    print(f"시작 시간: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 출력 디렉토리 생성
    output_dir = "output/iksancci"
    os.makedirs(output_dir, exist_ok=True)
    
    # 스크래퍼 생성 및 실행
    scraper = EnhancedIksancciScraper()
    
    try:
        # 스크래핑 실행
        start_time = time.time()
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        end_time = time.time()
        
        # 결과 검증
        print(f"\n=== 스크래핑 완료 ===")
        print(f"소요 시간: {end_time - start_time:.2f}초")
        
        # 결과 검증
        verify_results(output_dir)
        
    except Exception as e:
        print(f"테스트 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

def verify_results(output_dir):
    """결과 검증"""
    print(f"\n=== 결과 검증 ===")
    
    if not os.path.exists(output_dir):
        print(f"❌ 출력 디렉토리가 존재하지 않습니다: {output_dir}")
        return
    
    # 공고 폴더 수 확인
    folders = [f for f in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, f))]
    print(f"📁 생성된 공고 폴더 수: {len(folders)}개")
    
    # 각 폴더 검증
    total_attachments = 0
    successful_downloads = 0
    failed_downloads = 0
    
    for folder in folders[:5]:  # 처음 5개만 검증
        folder_path = os.path.join(output_dir, folder)
        
        # content.md 파일 확인
        content_file = os.path.join(folder_path, 'content.md')
        if os.path.exists(content_file):
            with open(content_file, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"✅ {folder}: content.md ({len(content)}자)")
        else:
            print(f"❌ {folder}: content.md 없음")
        
        # 첨부파일 확인
        files = [f for f in os.listdir(folder_path) if f != 'content.md']
        if files:
            print(f"📎 {folder}: 첨부파일 {len(files)}개")
            for file in files:
                file_path = os.path.join(folder_path, file)
                file_size = os.path.getsize(file_path)
                if file_size > 0:
                    print(f"   ✅ {file} ({file_size:,} bytes)")
                    successful_downloads += 1
                else:
                    print(f"   ❌ {file} (0 bytes)")
                    failed_downloads += 1
                total_attachments += 1
        else:
            print(f"📎 {folder}: 첨부파일 없음")
    
    # 전체 통계
    print(f"\n=== 전체 통계 ===")
    print(f"📊 총 공고 수: {len(folders)}개")
    print(f"📊 총 첨부파일 수: {total_attachments}개")
    print(f"📊 다운로드 성공: {successful_downloads}개")
    print(f"📊 다운로드 실패: {failed_downloads}개")
    
    if total_attachments > 0:
        success_rate = (successful_downloads / total_attachments) * 100
        print(f"📊 성공률: {success_rate:.1f}%")

def main():
    """메인 함수"""
    setup_logging()
    
    # 인자 처리
    pages = 3
    if len(sys.argv) > 1:
        try:
            pages = int(sys.argv[1])
        except ValueError:
            print("페이지 수는 숫자여야 합니다.")
            return
    
    test_iksancci_scraper(pages)

if __name__ == "__main__":
    main()