#!/usr/bin/env python3
"""
KDATA Enhanced 스크래퍼 테스트
한국데이터산업진흥원 스크래퍼 테스트 실행
"""

import os
import logging
import time
from enhanced_kdata_scraper import EnhancedKdataScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_kdata_scraper(pages=3):
    """KDATA 스크래퍼 테스트 - 3페이지"""
    logger.info("=== Enhanced KDATA 스크래퍼 테스트 시작 ===")
    
    try:
        # 스크래퍼 초기화
        scraper = EnhancedKdataScraper()
        
        # 출력 디렉토리 설정
        output_dir = "output/kdata"
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"출력 디렉토리: {output_dir}")
        logger.info(f"최대 페이지: {pages}")
        
        total_processed = 0
        total_files_downloaded = 0
        
        for page_num in range(1, pages + 1):
            logger.info(f"\n=== {page_num}페이지 처리 시작 ===")
            
            # 목록 페이지 URL 가져오기
            list_url = scraper.get_list_url(page_num)
            logger.info(f"목록 URL: {list_url}")
            
            # 페이지 내용 가져오기
            try:
                response = scraper.session.get(list_url, timeout=30, verify=scraper.verify_ssl)
                response.encoding = scraper.default_encoding
                html_content = response.text
            except Exception as e:
                logger.error(f"{page_num}페이지 로드 실패: {e}")
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
                    
                    # 상세 페이지 URL
                    detail_url = announcement.get('url', '')
                    if not detail_url:
                        logger.error(f"상세 페이지 URL이 없습니다: {title}")
                        continue
                    
                    # 상세 페이지 가져오기
                    try:
                        detail_response = scraper.session.get(detail_url, timeout=30, verify=scraper.verify_ssl)
                        detail_response.encoding = scraper.default_encoding
                        detail_html = detail_response.text
                    except Exception as e:
                        logger.error(f"상세 페이지 로드 실패: {title} - {e}")
                        continue
                        
                    # 상세 내용 파싱
                    detail_data = scraper.parse_detail_page(detail_html)
                    
                    # 폴더 생성
                    safe_title = scraper.sanitize_filename(title)
                    folder_name = f"{total_processed + 1:03d}_{safe_title}"
                    announcement_dir = os.path.join(output_dir, folder_name)
                    os.makedirs(announcement_dir, exist_ok=True)
                    
                    # content.md 파일 생성
                    content_md = f"# {title}\n\n"
                    content_md += f"**번호**: {announcement.get('num', '')}\n"
                    content_md += f"**작성일**: {announcement.get('date', '')}\n"
                    content_md += f"**조회수**: {announcement.get('views', '')}\n"
                    content_md += f"**원본 URL**: {detail_url}\n\n"
                    content_md += "---\n\n"
                    content_md += detail_data.get('content', '')
                    
                    content_file = os.path.join(announcement_dir, 'content.md')
                    with open(content_file, 'w', encoding='utf-8') as f:
                        f.write(content_md)
                    
                    # 첨부파일 다운로드
                    attachments = detail_data.get('attachments', [])
                    if attachments:
                        attachments_dir = os.path.join(announcement_dir, 'attachments')
                        os.makedirs(attachments_dir, exist_ok=True)
                        
                        for attachment in attachments:
                            file_name = attachment.get('name', 'unknown_file')
                            file_url = attachment.get('url', '')
                            
                            if file_url:
                                # 파일명 정리
                                safe_filename = scraper.sanitize_filename(file_name)
                                if not safe_filename.strip():
                                    safe_filename = f"attachment_{len(os.listdir(attachments_dir)) + 1}"
                                    
                                save_path = os.path.join(attachments_dir, safe_filename)
                                
                                # 파일 다운로드
                                try:
                                    file_response = scraper.session.get(file_url, timeout=120, verify=scraper.verify_ssl, stream=True)
                                    if file_response.status_code == 200:
                                        with open(save_path, 'wb') as f:
                                            for chunk in file_response.iter_content(chunk_size=8192):
                                                if chunk:
                                                    f.write(chunk)
                                        
                                        # 파일 크기 확인
                                        if os.path.exists(save_path):
                                            file_size = os.path.getsize(save_path)
                                            logger.info(f"다운로드 완료: {safe_filename} ({file_size:,} bytes)")
                                            total_files_downloaded += 1
                                        else:
                                            logger.error(f"다운로드 파일이 저장되지 않음: {save_path}")
                                    else:
                                        logger.error(f"파일 다운로드 실패: {file_response.status_code}")
                                except Exception as e:
                                    logger.error(f"파일 다운로드 중 오류: {e}")
                                
                                time.sleep(1)  # 다운로드 간격
                    
                    total_processed += 1
                    logger.info(f"처리 완료: {title} (첨부파일: {len(attachments)}개)")
                    
                    time.sleep(2)  # 요청 간격
                    
                except Exception as e:
                    logger.error(f"공고 처리 중 오류: {e}")
                    continue
            
            logger.info(f"{page_num}페이지 처리 완료")
            time.sleep(3)  # 페이지 간격
        
        # 결과 요약
        logger.info(f"\n=== 테스트 완료 ===")
        logger.info(f"총 처리된 공고: {total_processed}개")
        logger.info(f"총 다운로드된 파일: {total_files_downloaded}개")
        logger.info(f"출력 디렉토리: {output_dir}")
        
        # 파일 크기 통계
        verify_results(output_dir)
        
        return True
        
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}")
        return False

def verify_results(output_dir):
    """결과 검증"""
    logger.info("\n=== 결과 검증 ===")
    
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
            for file in os.listdir(attachments_dir):
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
    
    logger.info(f"총 파일 수: {total_files}개")
    logger.info(f"총 파일 크기: {total_size:,} bytes ({total_size/1024/1024:.2f} MB)")
    logger.info(f"파일 형식별 통계: {file_types}")

if __name__ == "__main__":
    success = test_kdata_scraper(pages=3)
    
    if success:
        logger.info("테스트가 성공적으로 완료되었습니다!")
    else:
        logger.error("테스트가 실패했습니다!")