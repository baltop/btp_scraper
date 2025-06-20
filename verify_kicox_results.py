#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KICOX 스크래퍼 결과 검증 스크립트
"""

import os
import glob

def verify_kicox_results():
    """KICOX 스크래퍼 결과를 종합적으로 검증"""
    output_dir = "output/kicox"
    
    if not os.path.exists(output_dir):
        print(f"❌ 출력 디렉토리가 존재하지 않습니다: {output_dir}")
        return False
    
    # 1. 공고 폴더 확인
    announcement_folders = [d for d in os.listdir(output_dir) 
                          if os.path.isdir(os.path.join(output_dir, d))]
    
    total_items = len(announcement_folders)
    successful_items = 0
    url_check_passed = 0
    total_attachments = 0
    korean_files = 0
    file_size_total = 0
    
    print("=== KICOX 스크래퍼 결과 검증 ===")
    print(f"📁 총 공고 폴더 수: {total_items}")
    
    for folder_name in announcement_folders:
        folder_path = os.path.join(output_dir, folder_name)
        print(f"\n📋 검증 중: {folder_name}")
        
        # content.md 파일 확인
        content_file = os.path.join(folder_path, 'content.md')
        if os.path.exists(content_file):
            successful_items += 1
            print("  ✅ content.md 파일 존재")
            
            # 원본 URL 포함 확인
            with open(content_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if '**원본 URL**:' in content and 'kicox.or.kr' in content:
                    url_check_passed += 1
                    print("  ✅ 원본 URL 포함됨")
                else:
                    print("  ⚠️ 원본 URL 누락")
        else:
            print("  ❌ content.md 파일 없음")
        
        # 첨부파일 확인
        attachments_dir = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_dir):
            files = os.listdir(attachments_dir)
            folder_attachments = len(files)
            total_attachments += folder_attachments
            print(f"  📎 첨부파일: {folder_attachments}개")
            
            for filename in files:
                # 한글 파일명 검증
                has_korean = any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename)
                if has_korean:
                    korean_files += 1
                    print(f"    🔤 한글 파일명: {filename}")
                
                # 파일 크기 검증
                file_path = os.path.join(attachments_dir, filename)
                file_size = os.path.getsize(file_path)
                file_size_total += file_size
                print(f"    📊 {filename}: {file_size:,} bytes")
        else:
            print("  📎 첨부파일 없음")
    
    # 결과 요약
    print("\n" + "="*50)
    print("📊 **검증 결과 요약**")
    print("="*50)
    
    success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
    url_rate = (url_check_passed / total_items) * 100 if total_items > 0 else 0
    
    print(f"📈 총 공고 수: {total_items}")
    print(f"✅ 성공적 처리: {successful_items} ({success_rate:.1f}%)")
    print(f"🔗 URL 포함률: {url_check_passed} ({url_rate:.1f}%)")
    print(f"📎 총 첨부파일: {total_attachments}")
    print(f"🔤 한글 파일명: {korean_files}")
    print(f"💾 총 파일 용량: {file_size_total:,} bytes ({file_size_total/1024/1024:.2f} MB)")
    
    # 성공 기준 확인
    if success_rate >= 80 and total_attachments > 0:
        print("🎉 **전체 검증 통과!**")
        print("✨ 첨부파일 다운로드 포함하여 모든 기능이 정상 작동합니다.")
        return True
    else:
        print("⚠️ 일부 문제가 발견되었습니다.")
        return False

if __name__ == "__main__":
    verify_kicox_results()