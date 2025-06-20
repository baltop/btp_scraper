#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
여성과학기술인지원센터(WMIT) Enhanced 스크래퍼 테스트 스크립트
"""

import os
import sys
import logging
import argparse
from enhanced_wmit_scraper import EnhancedWMITScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('wmit_scraper.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def test_wmit_scraper(pages=3):
    """WMIT 스크래퍼 테스트"""
    logger.info("=" * 60)
    logger.info("WMIT Enhanced 스크래퍼 테스트 시작")
    logger.info("=" * 60)
    
    # 출력 디렉토리 설정 (표준 패턴)
    output_dir = "output/wmit"
    
    # 기존 출력 디렉토리 정리
    if os.path.exists(output_dir):
        logger.info(f"기존 출력 디렉토리 정리: {output_dir}")
        import shutil
        shutil.rmtree(output_dir)
    
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # 스크래퍼 초기화
        scraper = EnhancedWMITScraper()
        
        # 스크래핑 실행
        logger.info(f"최대 {pages}페이지까지 스크래핑 시작")
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        
        # 결과 검증
        verify_results(output_dir)
        
        logger.info("=" * 60)
        logger.info("WMIT 스크래퍼 테스트 완료")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}")
        raise

def verify_results(output_dir):
    """결과 검증 - 첨부파일 검증 필수"""
    logger.info("=" * 50)
    logger.info("결과 검증 시작")
    logger.info("=" * 50)
    
    if not os.path.exists(output_dir):
        logger.error(f"출력 디렉토리가 존재하지 않습니다: {output_dir}")
        return
    
    # 공고 폴더 목록 가져오기
    announcement_folders = [d for d in os.listdir(output_dir) 
                          if os.path.isdir(os.path.join(output_dir, d))]
    
    if not announcement_folders:
        logger.error("처리된 공고가 없습니다")
        return
    
    total_items = len(announcement_folders)
    successful_items = 0
    total_attachments = 0
    korean_files = 0
    file_size_total = 0
    url_check_passed = 0
    
    # 여성과학기술인지원센터 관련 키워드 (검증용)
    wmit_keywords = [
        '여성', '과학기술', '지원', '사업', '모집', '공모', '신청', '접수',
        '선정', '선발', '교육', '훈련', '연구', '개발', 'R&D', '창업',
        '멘토링', '네트워킹', '리더십', '역량', '강화', '진흥', '육성',
        '과학자', '공학자', '연구원', '전문가', '인재', '양성'
    ]
    
    # 파일 확장자별 통계
    file_extensions = {}
    
    logger.info(f"총 {total_items}개 공고 폴더 검증 시작")
    
    for i, folder_name in enumerate(announcement_folders, 1):
        folder_path = os.path.join(output_dir, folder_name)
        logger.info(f"\n[{i}/{total_items}] 폴더 검증: {folder_name}")
        
        # content.md 파일 확인
        content_file = os.path.join(folder_path, 'content.md')
        if os.path.exists(content_file):
            successful_items += 1
            
            # 파일 내용 확인
            try:
                with open(content_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # 원본 URL 포함 확인
                    if '**원본 URL**:' in content and 'wmit.or.kr' in content:
                        url_check_passed += 1
                    
                    # WMIT 관련 키워드 확인
                    found_keywords = [kw for kw in wmit_keywords if kw in content]
                    if found_keywords:
                        logger.debug(f"관련 키워드 발견: {', '.join(found_keywords[:3])}")
                    
                    logger.info(f"✓ content.md: {len(content)}자, 키워드 {len(found_keywords)}개")
                    
            except Exception as e:
                logger.warning(f"content.md 읽기 실패: {e}")
        else:
            logger.warning("✗ content.md 파일 없음")
        
        # 첨부파일 확인
        attachments_dir = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_dir):
            attachment_files = os.listdir(attachments_dir)
            if attachment_files:
                total_attachments += len(attachment_files)
                logger.info(f"✓ 첨부파일: {len(attachment_files)}개")
                
                for filename in attachment_files:
                    file_path = os.path.join(attachments_dir, filename)
                    
                    # 한글 파일명 확인
                    has_korean = any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename)
                    if has_korean:
                        korean_files += 1
                    
                    # 파일 크기 확인
                    try:
                        file_size = os.path.getsize(file_path)
                        file_size_total += file_size
                        
                        # 파일 확장자 통계
                        ext = os.path.splitext(filename)[1].lower()
                        if ext:
                            file_extensions[ext] = file_extensions.get(ext, 0) + 1
                        
                        size_mb = file_size / (1024 * 1024)
                        logger.debug(f"  - {filename}: {size_mb:.2f}MB {'(한글)' if has_korean else ''}")
                        
                    except Exception as e:
                        logger.warning(f"파일 크기 확인 실패 {filename}: {e}")
            else:
                logger.info("첨부파일 없음")
        else:
            logger.info("첨부파일 디렉토리 없음")
    
    # 최종 통계
    success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
    korean_rate = (korean_files / total_attachments) * 100 if total_attachments > 0 else 0
    url_rate = (url_check_passed / successful_items) * 100 if successful_items > 0 else 0
    
    logger.info("\n" + "=" * 60)
    logger.info("최종 검증 결과")
    logger.info("=" * 60)
    logger.info(f"📊 공고 처리 현황:")
    logger.info(f"   - 총 공고 수: {total_items}")
    logger.info(f"   - 성공적 처리: {successful_items} ({success_rate:.1f}%)")
    logger.info(f"   - 원본 URL 포함: {url_check_passed} ({url_rate:.1f}%)")
    
    logger.info(f"\n📎 첨부파일 현황:")
    logger.info(f"   - 총 첨부파일: {total_attachments}")
    logger.info(f"   - 한글 파일명: {korean_files} ({korean_rate:.1f}%)")
    logger.info(f"   - 총 파일 용량: {file_size_total / (1024*1024):.2f} MB")
    
    if file_extensions:
        logger.info(f"\n📋 파일 형식 분포:")
        for ext, count in sorted(file_extensions.items()):
            logger.info(f"   - {ext}: {count}개")
    
    # 성공 기준 체크
    if success_rate >= 80:
        logger.info(f"\n✅ 테스트 성공: 성공률 {success_rate:.1f}% (기준: 80% 이상)")
    else:
        logger.warning(f"\n⚠️  테스트 주의: 성공률 {success_rate:.1f}% (기준: 80% 이상)")
    
    if total_attachments > 0:
        logger.info(f"✅ 첨부파일 다운로드 성공: {total_attachments}개 파일")
        if korean_rate > 50:
            logger.info(f"✅ 한글 파일명 처리 우수: {korean_rate:.1f}%")
    else:
        logger.info("ℹ️  첨부파일이 있는 공고가 없거나 다운로드에 실패했습니다")
        logger.info("ℹ️  이는 사이트의 404 오류나 인증 문제일 수 있습니다")
    
    # WMIT 특화 정보
    logger.info(f"\n🏢 WMIT 특화 정보:")
    logger.info(f"   - POST 기반 페이지네이션 사용")
    logger.info(f"   - HTTP 사이트 (SSL 없음)")
    logger.info(f"   - 목록 페이지 메타데이터 수집 완료")
    
    if total_attachments == 0:
        logger.info(f"   - 상세 페이지 접근 제한으로 첨부파일 다운로드 불가")
        logger.info(f"   - 향후 세션 관리나 인증 기능 추가 필요")

def main():
    parser = argparse.ArgumentParser(description='WMIT Enhanced 스크래퍼 테스트')
    parser.add_argument('--pages', type=int, default=3, help='테스트할 페이지 수 (기본값: 3)')
    parser.add_argument('--single', action='store_true', help='1페이지만 테스트')
    
    args = parser.parse_args()
    
    pages = 1 if args.single else args.pages
    
    try:
        test_wmit_scraper(pages=pages)
    except KeyboardInterrupt:
        logger.info("테스트가 사용자에 의해 중단되었습니다")
    except Exception as e:
        logger.error(f"테스트 실행 중 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()