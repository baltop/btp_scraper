#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KEAD Enhanced 스크래퍼 테스트
"""

import logging
import sys
import os
import time
from enhanced_kead_scraper import EnhancedKEADScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('kead_test.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def test_kead_scraper(pages=3):
    """KEAD 스크래퍼 테스트 (기본 3페이지)"""
    print("=== KEAD(한국농업기술진흥원) Enhanced 스크래퍼 테스트 ===")
    
    # 출력 디렉토리 설정
    output_dir = "output/kead"
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # 스크래퍼 초기화
        scraper = EnhancedKEADScraper()
        
        print(f"대상 사이트: {scraper.list_url}")
        print(f"테스트 페이지: {pages}페이지")
        print(f"출력 디렉토리: {output_dir}")
        print("-" * 60)
        
        # 스크래핑 실행
        results = scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        
        # 결과 출력
        print("\n" + "=" * 60)
        print("테스트 결과 요약")
        print("=" * 60)
        print(f"처리된 페이지: {results['pages_scraped']}")
        print(f"총 공고 수: {results['total_announcements']}")
        print(f"성공 처리: {results['successful_items']}")
        print(f"첨부파일 다운로드: {results['attachments_downloaded']}개")
        
        if results['errors']:
            print(f"오류 발생: {len(results['errors'])}개")
            for error in results['errors'][:5]:  # 최대 5개만 표시
                print(f"  - {error}")
        
        # 성공률 계산
        if results['total_announcements'] > 0:
            success_rate = (results['successful_items'] / results['total_announcements']) * 100
            print(f"성공률: {success_rate:.1f}%")
        
        # 파일 검증
        verify_results(output_dir)
        
        return results
        
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}")
        raise

def verify_results(output_dir):
    """결과 검증 - 표준 패턴"""
    print("\n" + "=" * 60)
    print("결과 검증")
    print("=" * 60)
    
    if not os.path.exists(output_dir):
        print(f"출력 디렉토리가 존재하지 않습니다: {output_dir}")
        return
    
    announcement_folders = [d for d in os.listdir(output_dir) 
                          if os.path.isdir(os.path.join(output_dir, d))]
    
    total_items = len(announcement_folders)
    successful_items = 0
    total_attachments = 0
    korean_files = 0
    file_size_total = 0
    url_check_passed = 0
    
    print(f"총 공고 폴더: {total_items}개")
    
    for folder_name in announcement_folders:
        folder_path = os.path.join(output_dir, folder_name)
        
        # content.md 파일 확인
        content_file = os.path.join(folder_path, 'content.md')
        if os.path.exists(content_file):
            successful_items += 1
            
            # 원본 URL 포함 확인
            with open(content_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if '**원본 URL**:' in content and 'kead.or.kr' in content:
                    url_check_passed += 1
        
        # 첨부파일 검증
        attachments_dir = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_dir):
            for filename in os.listdir(attachments_dir):
                total_attachments += 1
                
                # 한글 파일명 검증
                if any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename):
                    korean_files += 1
                
                # 파일 크기 검증
                file_path = os.path.join(attachments_dir, filename)
                if os.path.isfile(file_path):
                    file_size = os.path.getsize(file_path)
                    file_size_total += file_size
                    
                    # 파일 크기 상세 정보
                    if file_size > 1024 * 1024:  # 1MB 이상
                        print(f"  대용량 파일: {filename} ({file_size:,} bytes)")
                    elif file_size == 0:
                        print(f"  빈 파일 경고: {filename}")
    
    # 성공률 계산 및 리포트
    success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
    url_success_rate = (url_check_passed / total_items) * 100 if total_items > 0 else 0
    
    print(f"성공적 처리: {successful_items}/{total_items} ({success_rate:.1f}%)")
    print(f"URL 포함 확인: {url_check_passed}/{total_items} ({url_success_rate:.1f}%)")
    print(f"총 첨부파일: {total_attachments}개")
    print(f"한글 파일명: {korean_files}개")
    print(f"총 파일 용량: {file_size_total:,} bytes ({file_size_total/1024/1024:.1f} MB)")
    
    # 파일 크기별 분석
    if total_attachments > 0:
        avg_file_size = file_size_total / total_attachments
        print(f"평균 파일 크기: {avg_file_size:,.0f} bytes")
    
    # 검증 통과 기준
    if success_rate >= 80:
        print("✅ 검증 통과 (80% 이상 성공)")
    else:
        print("❌ 검증 실패 (80% 미만 성공)")
    
    return {
        'total_items': total_items,
        'successful_items': successful_items,
        'success_rate': success_rate,
        'total_attachments': total_attachments,
        'korean_files': korean_files,
        'file_size_total': file_size_total
    }

def main():
    """메인 함수"""
    try:
        # 기본 3페이지 테스트
        test_kead_scraper(pages=3)
        
        print("\n🎉 KEAD 스크래퍼 테스트 완료!")
        
    except KeyboardInterrupt:
        print("\n사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()