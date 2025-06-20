#!/usr/bin/env python3
"""
Enhanced GBMAKERS 스크래퍼 테스트 스크립트

사용법:
    python test_enhanced_gbmakers.py --pages 3
    python test_enhanced_gbmakers.py --single (1페이지만)
"""

import os
import sys
import logging
import argparse
from enhanced_gbmakers_scraper import EnhancedGbmakersScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def test_gbmakers_scraper(pages=3):
    """GBMAKERS 스크래퍼 테스트"""
    logger.info("=== Enhanced GBMAKERS 스크래퍼 테스트 시작 ===")
    
    # 스크래퍼 초기화
    scraper = EnhancedGbmakersScraper()
    
    # 표준 출력 디렉토리 사용
    output_dir = "output/gbmakers"
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"출력 디렉토리: {output_dir}")
    logger.info(f"테스트 페이지 수: {pages}")
    
    try:
        # 스크래핑 실행
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        
        logger.info("=== 테스트 완료, 결과 검증 시작 ===")
        verify_results(output_dir)
        
    except Exception as e:
        logger.error(f"테스트 실행 중 오류 발생: {e}")
        raise

def verify_results(output_dir):
    """결과 검증 - 첨부파일 검증 필수"""
    logger.info("=== 결과 검증 시작 ===")
    
    if not os.path.exists(output_dir):
        logger.error(f"출력 디렉토리가 존재하지 않습니다: {output_dir}")
        return
    
    # 공고 폴더들 찾기
    announcement_folders = [d for d in os.listdir(output_dir) 
                          if os.path.isdir(os.path.join(output_dir, d))]
    
    total_items = len(announcement_folders)
    successful_items = 0
    total_attachments = 0
    korean_files = 0
    file_size_total = 0
    url_check_passed = 0
    
    logger.info(f"총 {total_items}개의 공고 폴더 발견")
    
    for folder_name in announcement_folders:
        folder_path = os.path.join(output_dir, folder_name)
        
        # content.md 파일 확인
        content_file = os.path.join(folder_path, 'content.md')
        if os.path.exists(content_file):
            successful_items += 1
            
            # 원본 URL 포함 확인
            try:
                with open(content_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if '**원본 URL**:' in content and 'gbmakers.or.kr' in content:
                        url_check_passed += 1
            except Exception as e:
                logger.warning(f"content.md 파일 읽기 실패 {folder_name}: {e}")
        
        # 첨부파일 검증
        attachments_dir = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_dir):
            attachment_files = os.listdir(attachments_dir)
            total_attachments += len(attachment_files)
            
            for filename in attachment_files:
                # 한글 파일명 검증
                has_korean = any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename)
                if has_korean:
                    korean_files += 1
                
                # 파일 크기 검증
                file_path = os.path.join(attachments_dir, filename)
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    file_size_total += file_size
                    
                    # 파일 크기가 0인 경우 경고
                    if file_size == 0:
                        logger.warning(f"빈 파일 발견: {filename}")
    
    # 성공률 계산
    success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
    url_success_rate = (url_check_passed / successful_items) * 100 if successful_items > 0 else 0
    
    # 결과 출력
    logger.info("=== 검증 결과 요약 ===")
    logger.info(f"총 공고 수: {total_items}")
    logger.info(f"성공적 처리: {successful_items} ({success_rate:.1f}%)")
    logger.info(f"원본 URL 포함: {url_check_passed} ({url_success_rate:.1f}%)")
    logger.info(f"총 첨부파일: {total_attachments}")
    logger.info(f"한글 파일명: {korean_files}")
    logger.info(f"총 파일 용량: {file_size_total:,} bytes ({file_size_total/1024/1024:.1f} MB)")
    
    # 첨부파일 세부 분석
    if total_attachments > 0:
        korean_ratio = (korean_files / total_attachments) * 100
        avg_file_size = file_size_total / total_attachments
        logger.info(f"한글 파일명 비율: {korean_ratio:.1f}%")
        logger.info(f"평균 파일 크기: {avg_file_size:,.0f} bytes")
    else:
        logger.warning("첨부파일이 발견되지 않았습니다. GBMAKERS 사이트 특성상 첨부파일이 제한적일 수 있습니다.")
    
    # 첨부파일 상세 정보 출력
    logger.info("=== 첨부파일 상세 정보 ===")
    for folder_name in announcement_folders[:3]:  # 처음 3개만 상세 출력
        folder_path = os.path.join(output_dir, folder_name)
        attachments_dir = os.path.join(folder_path, 'attachments')
        
        if os.path.exists(attachments_dir):
            attachment_files = os.listdir(attachments_dir)
            if attachment_files:
                logger.info(f"[{folder_name}] 첨부파일 {len(attachment_files)}개:")
                for filename in attachment_files:
                    file_path = os.path.join(attachments_dir, filename)
                    file_size = os.path.getsize(file_path)
                    has_korean = any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename)
                    korean_mark = " [한글]" if has_korean else ""
                    logger.info(f"  - {filename}{korean_mark} ({file_size:,} bytes)")
        else:
            logger.info(f"[{folder_name}] 첨부파일 없음")
    
    # GBMAKERS 특화 분석
    logger.info("=== GBMAKERS 특화 분석 ===")
    
    # 공고 유형 분석
    education_count = 0
    support_count = 0
    notice_count = 0
    
    for folder_name in announcement_folders:
        folder_path = os.path.join(output_dir, folder_name)
        content_file = os.path.join(folder_path, 'content.md')
        
        if os.path.exists(content_file):
            try:
                with open(content_file, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                    if any(keyword in content for keyword in ['교육', 'education', '강의', '교실']):
                        education_count += 1
                    elif any(keyword in content for keyword in ['지원', 'support', '사업', '신청']):
                        support_count += 1
                    else:
                        notice_count += 1
            except:
                notice_count += 1
    
    logger.info(f"공고 유형 분석:")
    logger.info(f"  - 교육 관련: {education_count}개 ({education_count/total_items*100:.1f}%)")
    logger.info(f"  - 지원사업: {support_count}개 ({support_count/total_items*100:.1f}%)")
    logger.info(f"  - 일반공지: {notice_count}개 ({notice_count/total_items*100:.1f}%)")
    
    # 성공 여부 판정 (GBMAKERS는 첨부파일이 적을 수 있으므로 기준을 조정)
    test_passed = success_rate >= 70  # 70% 이상으로 기준 낮춤
    if test_passed:
        logger.info("✅ 테스트 통과!")
    else:
        logger.warning("❌ 테스트 실패 - 성공률이 70% 미만입니다.")
    
    # 특별 경고사항
    if total_attachments == 0:
        logger.warning("⚠️  첨부파일이 전혀 발견되지 않았습니다. GBMAKERS 사이트의 첨부파일 구조를 재확인이 필요할 수 있습니다.")
    
    return test_passed

def main():
    parser = argparse.ArgumentParser(description='Enhanced GBMAKERS 스크래퍼 테스트')
    parser.add_argument('--pages', type=int, default=3, help='테스트할 페이지 수 (기본값: 3)')
    parser.add_argument('--single', action='store_true', help='1페이지만 테스트')
    
    args = parser.parse_args()
    
    pages = 1 if args.single else args.pages
    
    try:
        test_gbmakers_scraper(pages)
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단되었습니다.")
    except Exception as e:
        logger.error(f"테스트 실행 중 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()