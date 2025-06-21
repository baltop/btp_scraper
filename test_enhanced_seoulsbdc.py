#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEOULSBDC 향상된 스크래퍼 테스트 스크립트
"""

import os
import sys
import time
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_seoulsbdc_scraper import EnhancedSEOULSBDCScraper


def test_seoulsbdc_scraper(pages=3):
    """SEOULSBDC 스크래퍼 테스트"""
    print("=" * 60)
    print("SEOULSBDC 향상된 스크래퍼 테스트 시작")
    print("=" * 60)
    
    # 출력 디렉토리 설정
    output_dir = "output/seoulsbdc"
    os.makedirs(output_dir, exist_ok=True)
    
    # 스크래퍼 초기화
    scraper = EnhancedSEOULSBDCScraper()
    
    try:
        print(f"📋 목표: {pages}페이지 스크래핑")
        print(f"📁 출력 디렉토리: {output_dir}")
        print(f"🌐 대상 사이트: {scraper.base_url}")
        print()
        
        # 시작 시간 기록
        start_time = time.time()
        
        # 스크래핑 실행
        print("🚀 스크래핑 시작...")
        success = scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        
        # 완료 시간 계산
        end_time = time.time()
        duration = end_time - start_time
        
        print("\n" + "=" * 60)
        print("📊 스크래핑 결과 분석")
        print("=" * 60)
        
        if success:
            print("✅ 스크래핑 성공!")
        else:
            print("❌ 스크래핑 실패")
            return False
        
        print(f"⏱️  총 소요 시간: {duration:.1f}초")
        
        # 결과 검증
        verify_results(output_dir)
        
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류 발생: {e}")
        return False
    finally:
        # 브라우저 리소스 정리
        scraper.cleanup_browser()


def verify_results(output_dir):
    """결과 검증 및 통계 출력"""
    print("\n📈 결과 검증 중...")
    
    try:
        output_path = Path(output_dir)
        
        if not output_path.exists():
            print("❌ 출력 디렉토리가 존재하지 않습니다")
            return
        
        # 공고 디렉토리 수집
        announcement_dirs = [d for d in output_path.iterdir() if d.is_dir()]
        announcement_count = len(announcement_dirs)
        
        print(f"📄 처리된 공고 수: {announcement_count}개")
        
        if announcement_count == 0:
            print("❌ 처리된 공고가 없습니다")
            return
        
        # 각 공고별 파일 분석
        total_files = 0
        total_size = 0
        successful_downloads = 0
        content_files = 0
        attachment_files = 0
        
        print("\n📁 공고별 상세 분석:")
        print("-" * 80)
        print(f"{'번호':<4} {'공고명':<40} {'파일수':<6} {'크기(MB)':<10} {'상태':<6}")
        print("-" * 80)
        
        for i, ann_dir in enumerate(sorted(announcement_dirs), 1):
            try:
                # content.md 파일 확인
                content_file = ann_dir / "content.md"
                has_content = content_file.exists()
                if has_content:
                    content_files += 1
                
                # 첨부파일 확인
                files = list(ann_dir.glob("*"))
                file_count = len([f for f in files if f.name != "content.md"])
                
                # 파일 크기 계산
                dir_size = sum(f.stat().st_size for f in files if f.is_file())
                total_size += dir_size
                
                # 첨부파일 다운로드 성공 확인
                download_success = file_count > 0
                if download_success:
                    successful_downloads += 1
                    attachment_files += file_count
                
                total_files += len(files)
                
                # 공고명 (디렉토리명에서 번호 제거)
                title = ann_dir.name
                if title.startswith(f"{i:03d}_"):
                    title = title[4:]  # "001_" 제거
                
                # 상태 표시
                status = "✅" if has_content and (file_count > 0 or not has_content) else "⚠️"
                
                print(f"{i:<4} {title[:40]:<40} {len(files):<6} {dir_size/1024/1024:.1f}MB{'':<3} {status:<6}")
                
            except Exception as e:
                print(f"{i:<4} {'오류 발생':<40} {'N/A':<6} {'N/A':<10} {'❌':<6}")
                continue
        
        print("-" * 80)
        
        # 전체 통계
        print(f"\n📊 전체 통계:")
        print(f"  • 총 공고 수: {announcement_count}개")
        print(f"  • content.md 파일: {content_files}개")
        print(f"  • 첨부파일 총 개수: {attachment_files}개")
        print(f"  • 첨부파일 다운로드 성공: {successful_downloads}개 공고")
        print(f"  • 총 파일 크기: {total_size/1024/1024:.1f} MB")
        
        # 성공률 계산
        content_success_rate = (content_files / announcement_count * 100) if announcement_count > 0 else 0
        download_success_rate = (successful_downloads / announcement_count * 100) if announcement_count > 0 else 0
        
        print(f"\n📈 성공률:")
        print(f"  • 본문 추출 성공률: {content_success_rate:.1f}%")
        print(f"  • 첨부파일 다운로드 성공률: {download_success_rate:.1f}%")
        
        # 한글 파일명 처리 확인
        verify_korean_filenames(output_dir)
        
        # 원본 URL 포함 확인
        verify_original_urls(output_dir)
        
    except Exception as e:
        print(f"❌ 결과 검증 중 오류: {e}")


def verify_korean_filenames(output_dir):
    """한글 파일명 처리 확인"""
    print(f"\n🇰🇷 한글 파일명 처리 확인:")
    
    try:
        korean_files = []
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                if file != "content.md":
                    # 한글 포함 여부 확인
                    if any(ord(char) >= 0xAC00 and ord(char) <= 0xD7AF for char in file):
                        korean_files.append(file)
        
        if korean_files:
            print(f"  • 한글 파일명 파일 수: {len(korean_files)}개")
            print(f"  • 예시 파일명: {korean_files[0] if korean_files else 'N/A'}")
            print("  ✅ 한글 파일명 처리 정상")
        else:
            print("  • 한글 파일명 파일 없음")
        
    except Exception as e:
        print(f"  ❌ 한글 파일명 확인 실패: {e}")


def verify_original_urls(output_dir):
    """원본 URL 포함 확인"""
    print(f"\n🔗 원본 URL 포함 확인:")
    
    try:
        url_count = 0
        total_content_files = 0
        
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                if file == "content.md":
                    total_content_files += 1
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if "**원본 URL**:" in content or "원본 URL" in content:
                                url_count += 1
                    except:
                        continue
        
        if total_content_files > 0:
            url_success_rate = (url_count / total_content_files * 100)
            print(f"  • 원본 URL 포함 파일: {url_count}/{total_content_files}개")
            print(f"  • 원본 URL 포함률: {url_success_rate:.1f}%")
            
            if url_success_rate >= 90:
                print("  ✅ 원본 URL 포함 우수")
            elif url_success_rate >= 70:
                print("  ⚠️ 원본 URL 포함 양호")
            else:
                print("  ❌ 원본 URL 포함 부족")
        else:
            print("  • content.md 파일 없음")
        
    except Exception as e:
        print(f"  ❌ 원본 URL 확인 실패: {e}")


def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SEOULSBDC 스크래퍼 테스트")
    parser.add_argument("--pages", type=int, default=3, help="테스트할 페이지 수 (기본값: 3)")
    parser.add_argument("--single", action="store_true", help="1페이지만 테스트")
    
    args = parser.parse_args()
    
    if args.single:
        pages = 1
    else:
        pages = args.pages
    
    success = test_seoulsbdc_scraper(pages)
    
    if success:
        print(f"\n🎉 SEOULSBDC 스크래퍼 테스트 완료!")
        sys.exit(0)
    else:
        print(f"\n💥 SEOULSBDC 스크래퍼 테스트 실패!")
        sys.exit(1)


if __name__ == "__main__":
    main()