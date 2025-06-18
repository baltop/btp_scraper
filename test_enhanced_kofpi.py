#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced KOFPI 스크래퍼 테스트 스크립트
"""

import os
import sys
import logging
import time
from enhanced_kofpi_scraper import EnhancedKofpiScraper

def setup_logging():
    """로깅 설정"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('kofpi_test.log', encoding='utf-8')
        ]
    )

def test_kofpi_scraper(pages=3):
    """KOFPI 스크래퍼 테스트 함수"""
    print("=" * 60)
    print("Enhanced KOFPI 스크래퍼 테스트 시작")
    print("=" * 60)
    
    # 출력 디렉토리 설정
    output_dir = "output/kofpi"
    
    # 기존 출력 디렉토리 정리 (선택적)
    if os.path.exists(output_dir):
        print(f"기존 출력 디렉토리 존재: {output_dir}")
    else:
        print(f"새 출력 디렉토리 생성: {output_dir}")
    
    # 스크래퍼 초기화
    scraper = EnhancedKofpiScraper()
    
    print(f"기본 URL: {scraper.base_url}")
    print(f"목록 URL: {scraper.list_url}")
    print(f"처리할 페이지 수: {pages}")
    print()
    
    # 스크래핑 실행
    start_time = time.time()
    
    try:
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        success = True
    except Exception as e:
        print(f"스크래핑 중 오류 발생: {e}")
        logging.error(f"스크래핑 실패: {e}")
        success = False
    
    end_time = time.time()
    duration = end_time - start_time
    
    print()
    print("=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    print(f"실행 시간: {duration:.2f}초")
    print(f"결과 상태: {'성공' if success else '실패'}")
    
    if success:
        verify_results(output_dir)
    
    return success

def verify_results(output_dir):
    """결과 검증"""
    print("\n" + "=" * 40)
    print("결과 검증")
    print("=" * 40)
    
    if not os.path.exists(output_dir):
        print("❌ 출력 디렉토리가 생성되지 않았습니다.")
        return
    
    # 폴더 개수 확인
    folders = [d for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d))]
    print(f"📁 생성된 공고 폴더: {len(folders)}개")
    
    if not folders:
        print("❌ 공고 폴더가 생성되지 않았습니다.")
        return
    
    # 각 폴더 내용 확인
    total_files = 0
    successful_items = 0
    attachment_items = 0
    url_check_passed = 0
    korean_filename_count = 0
    
    for folder in sorted(folders)[:5]:  # 처음 5개만 상세 확인
        folder_path = os.path.join(output_dir, folder)
        print(f"\n📂 {folder}")
        
        # content.md 파일 확인
        content_file = os.path.join(folder_path, 'content.md')
        if os.path.exists(content_file):
            print(f"  ✅ content.md 있음")
            successful_items += 1
            total_files += 1
            
            # 내용 확인
            try:
                with open(content_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # 원본 URL 포함 확인
                if '**원본 URL**:' in content and 'kofpi.or.kr' in content:
                    url_check_passed += 1
                    print(f"  ✅ 원본 URL 포함됨")
                else:
                    print(f"  ⚠️ 원본 URL 누락")
                
                print(f"  📄 내용 길이: {len(content)} 글자")
                
            except Exception as e:
                print(f"  ❌ content.md 읽기 실패: {e}")
        else:
            print(f"  ❌ content.md 없음")
        
        # 첨부파일 폴더 확인
        attachments_path = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_path):
            attachment_files = os.listdir(attachments_path)
            if attachment_files:
                attachment_items += 1
                total_files += len(attachment_files)
                print(f"  📎 첨부파일: {len(attachment_files)}개")
                
                # 한글 파일명 확인
                for filename in attachment_files[:3]:  # 처음 3개만 확인
                    has_korean = any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename)
                    if has_korean:
                        korean_filename_count += 1
                    
                    att_path = os.path.join(attachments_path, filename)
                    file_size = os.path.getsize(att_path)
                    
                    status = "✅" if file_size > 0 else "❌"
                    korean_marker = "🇰🇷" if has_korean else ""
                    print(f"    {status} {filename} ({file_size:,} bytes) {korean_marker}")
            else:
                print(f"  📎 첨부파일 폴더 있지만 비어있음")
        else:
            print(f"  📎 첨부파일 없음")
    
    # 전체 결과 요약
    print(f"\n" + "=" * 40)
    print("📊 전체 결과 요약")
    print("=" * 40)
    print(f"전체 공고 폴더: {len(folders)}개")
    print(f"성공한 공고: {successful_items}개")
    print(f"첨부파일 있는 공고: {attachment_items}개")
    print(f"전체 파일 수: {total_files}개")
    print(f"원본 URL 포함: {url_check_passed}개")
    print(f"한글 파일명: {korean_filename_count}개")
    
    # 성공률 계산
    if folders:
        success_rate = (successful_items / len(folders)) * 100
        print(f"성공률: {success_rate:.1f}%")
        
        if success_rate >= 90:
            print("🎉 테스트 성공!")
        elif success_rate >= 70:
            print("⚠️ 부분 성공 - 일부 개선 필요")
        else:
            print("❌ 테스트 실패 - 문제 확인 필요")

def main():
    """메인 함수"""
    setup_logging()
    
    print("KOFPI Enhanced 스크래퍼 테스트")
    print("사이트: https://www.kofpi.or.kr/notice/notice_01.do")
    print()
    
    # 기본값으로 3페이지 테스트
    success = test_kofpi_scraper(pages=3)
    
    if success:
        print("\n✅ 모든 테스트가 완료되었습니다!")
    else:
        print("\n❌ 테스트 중 오류가 발생했습니다.")
        sys.exit(1)

if __name__ == "__main__":
    main()