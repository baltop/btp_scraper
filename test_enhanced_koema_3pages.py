#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced KOEMA 스크래퍼 3페이지 전체 테스트
output/koema_enhanced 디렉토리에 저장
"""

import sys
import os
import logging

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_koema_scraper import EnhancedKOEMAScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_koema_3pages():
    """KOEMA 스크래퍼 3페이지 테스트"""
    print("=== Enhanced KOEMA 스크래퍼 3페이지 테스트 ===")
    
    # 스크래퍼 인스턴스 생성
    scraper = EnhancedKOEMAScraper()
    
    # 출력 디렉토리 설정
    output_dir = "output/koema_enhanced"
    
    try:
        print(f"출력 디렉토리: {output_dir}")
        print("3페이지 스크래핑 시작...")
        
        # 3페이지 스크래핑
        scraper.scrape_pages(max_pages=3, output_base=output_dir)
        
        print("\n=== 스크래핑 완료 ===")
        
        # 결과 확인 및 검증
        return verify_results(output_dir)
        
    except Exception as e:
        print(f"ERROR: 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_results(output_dir):
    """결과 검증"""
    print(f"\n=== 결과 검증 ===")
    
    if not os.path.exists(output_dir):
        print("ERROR: 출력 디렉토리가 존재하지 않습니다.")
        return False
    
    # 생성된 폴더들 확인
    folders = [item for item in os.listdir(output_dir) 
              if os.path.isdir(os.path.join(output_dir, item)) and item.startswith(('001_', '002_', '003_'))]
    folders.sort()
    
    print(f"생성된 공고 폴더 수: {len(folders)}")
    
    total_content_files = 0
    total_attachment_files = 0
    url_check_passed = 0
    korean_filename_count = 0
    
    for folder in folders:
        folder_path = os.path.join(output_dir, folder)
        print(f"\n📁 {folder}")
        
        # content.md 파일 확인
        content_path = os.path.join(folder_path, 'content.md')
        if os.path.exists(content_path):
            total_content_files += 1
            
            # 원본 URL 확인
            with open(content_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if '**원본 URL**:' in content and 'koema.or.kr' in content:
                    url_check_passed += 1
                    print(f"  ✓ content.md - 원본 URL 포함 ({os.path.getsize(content_path):,} bytes)")
                else:
                    print(f"  ✗ content.md - 원본 URL 누락 ({os.path.getsize(content_path):,} bytes)")
        else:
            print(f"  ✗ content.md 파일이 없습니다")
        
        # 첨부파일 폴더 확인
        attachments_path = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_path):
            attachment_files = os.listdir(attachments_path)
            total_attachment_files += len(attachment_files)
            
            print(f"  📎 첨부파일 {len(attachment_files)}개:")
            for att_file in attachment_files:
                att_path = os.path.join(attachments_path, att_file)
                file_size = os.path.getsize(att_path)
                
                # 한글 파일명 확인
                has_korean = any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in att_file)
                if has_korean:
                    korean_filename_count += 1
                    print(f"    🇰🇷 {att_file} ({file_size:,} bytes)")
                else:
                    print(f"    📄 {att_file} ({file_size:,} bytes)")
        else:
            print(f"  📎 첨부파일 없음")
    
    # 종합 결과
    print(f"\n=== 검증 결과 ===")
    print(f"총 공고 폴더: {len(folders)}개")
    print(f"content.md 파일: {total_content_files}개")
    print(f"원본 URL 포함: {url_check_passed}개")
    print(f"총 첨부파일: {total_attachment_files}개")
    print(f"한글 파일명: {korean_filename_count}개")
    
    # 성공 조건 체크
    success = True
    if total_content_files != len(folders):
        print("✗ content.md 파일이 누락된 폴더가 있습니다.")
        success = False
    
    if url_check_passed != len(folders):
        print("✗ 원본 URL이 누락된 content.md가 있습니다.")
        success = False
    
    if total_attachment_files == 0:
        print("✗ 첨부파일이 하나도 다운로드되지 않았습니다.")
        success = False
    
    if korean_filename_count == 0:
        print("⚠ 한글 파일명을 가진 첨부파일이 없습니다. (정상일 수 있음)")
    
    if success:
        print("✓ 모든 검증 조건을 통과했습니다!")
    else:
        print("✗ 일부 검증 조건을 통과하지 못했습니다.")
    
    return success

if __name__ == "__main__":
    success = test_koema_3pages()
    sys.exit(0 if success else 1)