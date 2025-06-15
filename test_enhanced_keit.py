#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced KEIT 스크래퍼 테스트
"""

import os
import sys
import logging
import time
from enhanced_keit_scraper import EnhancedKEITScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('keit_scraper.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def test_keit_scraper(pages=2):
    """KEIT 스크래퍼 테스트"""
    logger.info("=== Enhanced KEIT 스크래퍼 테스트 시작 ===")
    
    try:
        # 스크래퍼 인스턴스 생성
        scraper = EnhancedKEITScraper()
        
        # 출력 디렉토리 설정
        output_dir = "output_keit"
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"출력 디렉토리: {output_dir}")
        logger.info(f"대상 URL: {scraper.list_url}")
        logger.info(f"스크래핑 페이지 수: {pages}")
        
        # 단계별 테스트
        
        # 1. 첫 페이지 접근 테스트
        logger.info("1. 첫 페이지 접근 테스트")
        first_page_url = scraper.get_list_url(1)
        response = scraper.get_page(first_page_url)
        
        if not response:
            logger.error("첫 페이지 접근 실패")
            return False
        
        logger.info(f"첫 페이지 응답 상태: {response.status_code}")
        logger.info(f"응답 크기: {len(response.text)} bytes")
        
        # 2. 목록 파싱 테스트
        logger.info("2. 목록 파싱 테스트")
        announcements = scraper.parse_list_page(response.text)
        
        if not announcements:
            logger.error("목록 파싱 실패 - 공고를 찾을 수 없습니다")
            logger.debug(f"HTML 내용 일부: {response.text[:1000]}")
            return False
        
        logger.info(f"파싱된 공고 수: {len(announcements)}")
        
        # 첫 번째 공고 정보 출력
        if announcements:
            first_ann = announcements[0]
            logger.info("첫 번째 공고 정보:")
            for key, value in first_ann.items():
                logger.info(f"  {key}: {value}")
        
        # 3. 상세 페이지 테스트 (첫 번째 공고만)
        logger.info("3. 상세 페이지 접근 및 파싱 테스트")
        if announcements:
            test_ann = announcements[0]
            logger.info(f"테스트 대상: {test_ann['title']}")
            
            detail_response = scraper.get_page(test_ann['url'])
            if detail_response:
                logger.info(f"상세 페이지 응답 상태: {detail_response.status_code}")
                
                detail_info = scraper.parse_detail_page(detail_response.text)
                logger.info(f"본문 길이: {len(detail_info['content'])} chars")
                logger.info(f"첨부파일 수: {len(detail_info['attachments'])}")
                
                if detail_info['attachments']:
                    logger.info("첨부파일 목록:")
                    for i, att in enumerate(detail_info['attachments'], 1):
                        logger.info(f"  {i}. {att['name']} - {att['url']}")
                
                # 테스트용 파일 저장
                test_output_dir = os.path.join(output_dir, "test_single")
                os.makedirs(test_output_dir, exist_ok=True)
                
                # 본문 저장
                content_path = os.path.join(test_output_dir, "test_content.md")
                with open(content_path, 'w', encoding='utf-8') as f:
                    f.write(f"# {test_ann['title']}\n\n")
                    f.write(f"**URL**: {test_ann['url']}\n\n")
                    f.write("---\n\n")
                    f.write(detail_info['content'])
                
                logger.info(f"테스트 본문 저장: {content_path}")
                
                # 첫 번째 첨부파일만 테스트 다운로드
                if detail_info['attachments']:
                    test_attachment = detail_info['attachments'][0]
                    att_name = scraper.sanitize_filename(test_attachment['name'])
                    att_path = os.path.join(test_output_dir, att_name)
                    
                    logger.info(f"테스트 첨부파일 다운로드: {test_attachment['name']}")
                    success = scraper.download_file(test_attachment['url'], att_path)
                    
                    if success and os.path.exists(att_path):
                        file_size = os.path.getsize(att_path)
                        logger.info(f"다운로드 성공: {att_path} ({file_size:,} bytes)")
                    else:
                        logger.warning("테스트 다운로드 실패")
            else:
                logger.error("상세 페이지 접근 실패")
                return False
        
        # 4. 전체 스크래핑 테스트 (적은 페이지만)
        logger.info(f"4. 전체 스크래핑 테스트 ({pages}페이지)")
        start_time = time.time()
        
        scraper.scrape_pages(max_pages=pages, output_base=output_dir)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        logger.info(f"스크래핑 완료. 소요시간: {elapsed:.2f}초")
        
        # 5. 결과 검증
        logger.info("5. 결과 검증")
        result_folders = [d for d in os.listdir(output_dir) 
                         if os.path.isdir(os.path.join(output_dir, d)) and d.startswith(('001_', '002_', '003_'))]
        
        logger.info(f"생성된 폴더 수: {len(result_folders)}")
        
        successful_items = 0
        total_items = len(result_folders)
        
        for folder in result_folders:
            folder_path = os.path.join(output_dir, folder)
            
            # content.md 파일 확인
            content_file = os.path.join(folder_path, 'content.md')
            if os.path.exists(content_file):
                with open(content_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # 한국산업기술기획평가원 관련 내용이 있는지 확인
                if 'keit.re.kr' in content or '한국산업기술기획평가원' in content or 'KEIT' in content or '산업기술' in content:
                    successful_items += 1
                    logger.info(f"✓ {folder}: 내용 검증 성공")
                else:
                    logger.warning(f"✗ {folder}: 내용 검증 실패")
            else:
                logger.warning(f"✗ {folder}: content.md 파일 없음")
        
        # 첨부파일 확인
        total_attachments = 0
        downloaded_attachments = 0
        
        for folder in result_folders:
            att_folder = os.path.join(output_dir, folder, 'attachments')
            if os.path.exists(att_folder):
                att_files = os.listdir(att_folder)
                total_attachments += len(att_files)
                
                for att_file in att_files:
                    att_path = os.path.join(att_folder, att_file)
                    if os.path.getsize(att_path) > 0:
                        downloaded_attachments += 1
        
        logger.info(f"첨부파일: 총 {total_attachments}개, 다운로드 성공 {downloaded_attachments}개")
        
        # 성공률 계산
        if total_items > 0:
            success_rate = (successful_items / total_items) * 100
            logger.info(f"전체 성공률: {success_rate:.1f}% ({successful_items}/{total_items})")
            
            if success_rate >= 80:
                logger.info("✓ 테스트 성공: 스크래퍼가 정상적으로 작동합니다")
                return True
            else:
                logger.warning(f"✗ 테스트 부분 성공: 성공률이 {success_rate:.1f}%입니다")
                return False
        else:
            logger.error("✗ 테스트 실패: 처리된 항목이 없습니다")
            return False
            
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}", exc_info=True)
        return False

def verify_results(output_dir="output_keit"):
    """결과 검증"""
    logger.info("=== 결과 검증 ===")
    
    if not os.path.exists(output_dir):
        logger.error(f"출력 디렉토리가 없습니다: {output_dir}")
        return False
    
    folders = [d for d in os.listdir(output_dir) 
              if os.path.isdir(os.path.join(output_dir, d)) and d[0].isdigit()]
    
    logger.info(f"확인할 폴더 수: {len(folders)}")
    
    url_check_passed = 0
    korean_files = 0
    total_size = 0
    
    for folder in folders:
        folder_path = os.path.join(output_dir, folder)
        
        # content.md 확인
        content_file = os.path.join(folder_path, 'content.md')
        if os.path.exists(content_file):
            with open(content_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 원본 URL 포함 확인
            if '**원본 URL**:' in content and 'keit.re.kr' in content:
                url_check_passed += 1
        
        # 첨부파일 확인
        att_folder = os.path.join(folder_path, 'attachments')
        if os.path.exists(att_folder):
            for filename in os.listdir(att_folder):
                att_path = os.path.join(att_folder, filename)
                if os.path.isfile(att_path):
                    file_size = os.path.getsize(att_path)
                    total_size += file_size
                    
                    # 한글 파일명 확인
                    has_korean = any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename)
                    if has_korean:
                        korean_files += 1
    
    logger.info(f"URL 확인 통과: {url_check_passed}/{len(folders)}")
    logger.info(f"한글 파일명 첨부파일: {korean_files}개")
    logger.info(f"총 다운로드 크기: {total_size:,} bytes")
    
    if len(folders) > 0:
        success_rate = (url_check_passed / len(folders)) * 100
        logger.info(f"검증 성공률: {success_rate:.1f}%")
        return success_rate >= 70
    
    return False

if __name__ == "__main__":
    # 테스트 실행
    pages = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    
    success = test_keit_scraper(pages)
    
    if success:
        print("\n✓ Enhanced KEIT 스크래퍼 테스트 성공!")
        verify_results()
    else:
        print("\n✗ Enhanced KEIT 스크래퍼 테스트 실패!")
        sys.exit(1)