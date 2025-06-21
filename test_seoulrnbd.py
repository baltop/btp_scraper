#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEOUL RNBD Enhanced 스크래퍼 테스트
서울시 R&BD 스크래퍼 테스트 실행
"""

import os
import logging
import time
from enhanced_seoulrnbd_scraper import EnhancedSeoulRnbdScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_seoulrnbd_scraper(pages=3):
    """SEOUL RNBD 스크래퍼 테스트 - 3페이지"""
    logger.info("=== Enhanced SEOUL RNBD 스크래퍼 테스트 시작 ===")
    
    try:
        # 스크래퍼 초기화
        scraper = EnhancedSeoulRnbdScraper()
        
        # 출력 디렉토리 설정
        output_dir = "output/seoulrnbd"
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"출력 디렉토리: {output_dir}")
        logger.info(f"최대 페이지: {pages}")
        
        total_processed = 0
        total_downloaded = 0
        
        for page_num in range(1, pages + 1):
            logger.info(f"\n=== SEOUL RNBD {page_num}페이지 처리 시작 ===")
            
            # 페이지 URL 생성
            list_url = scraper.get_list_url(page_num)
            logger.info(f"목록 URL: {list_url}")
            
            # 페이지 내용 가져오기
            html_content = scraper.fetch_page_content(list_url)
            if not html_content:
                logger.error(f"{page_num}페이지 내용 가져오기 실패")
                break
            
            # 목록 파싱
            announcements = scraper.parse_list_page(html_content)
            if not announcements:
                logger.warning(f"{page_num}페이지에 공고가 없습니다")
                break
            
            logger.info(f"{len(announcements)}개 공고 발견")
            
            # 각 공고 처리
            for i, announcement in enumerate(announcements):
                try:
                    title = announcement.get('title', f'공고_{page_num}_{i+1}')
                    logger.info(f"처리 중: {title}")
                    
                    # 상세 내용 가져오기
                    detail_data = scraper.get_detail_content(announcement)
                    
                    # 폴더 생성 및 저장
                    safe_title = scraper.sanitize_filename(title)
                    folder_name = f"{total_processed + 1:03d}_{safe_title}"
                    announcement_dir = os.path.join(output_dir, folder_name)
                    os.makedirs(announcement_dir, exist_ok=True)
                    
                    # content.md 파일 생성
                    content_md = f"# {title}\n\n"
                    content_md += f"**공고 번호**: {announcement.get('seq_no', '')}\n"
                    content_md += f"**모집기간**: {announcement.get('period', '')}\n"
                    content_md += f"**상태**: {announcement.get('status', '')}\n"
                    content_md += f"**조회수**: {announcement.get('views', '')}\n"
                    content_md += f"**원본 URL**: {announcement.get('url', '')}\n\n"
                    content_md += "---\n\n"
                    content_md += detail_data.get('content', '')
                    
                    content_file = os.path.join(announcement_dir, 'content.md')
                    with open(content_file, 'w', encoding='utf-8') as f:
                        f.write(content_md)
                    
                    # 첨부파일 다운로드
                    attachments = detail_data.get('attachments', [])
                    downloaded_files = 0
                    if attachments:
                        attachments_dir = os.path.join(announcement_dir, 'attachments')
                        os.makedirs(attachments_dir, exist_ok=True)
                        
                        for j, attachment in enumerate(attachments):
                            file_name = attachment.get('name', f'attachment_{j+1}')
                            safe_file_name = scraper.sanitize_filename(file_name)
                            file_path = os.path.join(attachments_dir, safe_file_name)
                            
                            # 파일 다운로드 시도
                            download_success = scraper.download_file(
                                attachment.get('url', ''),
                                file_path,
                                attachment
                            )
                            
                            if download_success:
                                downloaded_files += 1
                                total_downloaded += 1
                                
                                # 파일 크기 확인
                                if os.path.exists(file_path):
                                    file_size = os.path.getsize(file_path)
                                    logger.info(f"파일 다운로드 완료: {safe_file_name} ({file_size:,} bytes)")
                        
                        logger.info(f"첨부파일 다운로드: {downloaded_files}/{len(attachments)}개 성공")
                    
                    total_processed += 1
                    logger.info(f"처리 완료: {title} (첨부파일: {len(attachments)}개)")
                    
                    time.sleep(scraper.delay_between_requests)
                    
                except Exception as e:
                    logger.error(f"공고 처리 중 오류: {e}")
                    continue
            
            logger.info(f"{page_num}페이지 처리 완료")
            time.sleep(2)
        
        logger.info(f"\n=== SEOUL RNBD 스크래핑 완료: 총 {total_processed}개 공고, {total_downloaded}개 파일 다운로드 ===")
        
        # 결과 검증
        logger.info("\n=== 결과 검증 ===")
        verify_results(output_dir)
        
        return True
        
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}")
        return False

def verify_results(output_dir):
    """결과 검증"""
    logger.info("=== 결과 검증 시작 ===")
    
    if not os.path.exists(output_dir):
        logger.error("출력 디렉토리가 존재하지 않습니다")
        return
    
    # 폴더 수 확인
    folders = [d for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d))]
    logger.info(f"생성된 공고 폴더: {len(folders)}개")
    
    # 파일 통계
    total_files = 0
    total_size = 0
    file_types = {}
    announcements_with_attachments = 0
    
    for folder in folders:
        folder_path = os.path.join(output_dir, folder)
        
        # content.md 확인
        content_file = os.path.join(folder_path, 'content.md')
        if os.path.exists(content_file):
            size = os.path.getsize(content_file)
            total_files += 1
            total_size += size
            file_types['md'] = file_types.get('md', 0) + 1
        
        # 첨부파일 확인
        attachments_dir = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_dir):
            attachments = os.listdir(attachments_dir)
            if attachments:
                announcements_with_attachments += 1
                
                for file in attachments:
                    file_path = os.path.join(attachments_dir, file)
                    if os.path.isfile(file_path):
                        size = os.path.getsize(file_path)
                        total_files += 1
                        total_size += size
                        
                        # 파일 확장자별 통계
                        ext = os.path.splitext(file)[1].lower()
                        if ext:
                            ext = ext[1:]  # . 제거
                            file_types[ext] = file_types.get(ext, 0) + 1
                        
                        logger.info(f"첨부파일: {file} ({size:,} bytes)")
    
    logger.info(f"총 공고 수: {len(folders)}개")
    logger.info(f"첨부파일이 있는 공고: {announcements_with_attachments}개")
    logger.info(f"총 파일 수: {total_files}개")
    logger.info(f"총 파일 크기: {total_size:,} bytes ({total_size/1024/1024:.2f} MB)")
    logger.info(f"파일 형식별 통계: {file_types}")
    
    # 성공률 계산
    if len(folders) > 0:
        success_rate = (len(folders) / (len(folders))) * 100  # 모든 폴더가 처리됨
        logger.info(f"처리 성공률: {success_rate:.1f}%")

if __name__ == "__main__":
    success = test_seoulrnbd_scraper(pages=3)
    
    if success:
        logger.info("테스트가 성공적으로 완료되었습니다!")
    else:
        logger.error("테스트가 실패했습니다!")