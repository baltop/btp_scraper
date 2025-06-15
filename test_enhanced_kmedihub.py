#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced KMEDIHUB 스크래퍼 테스트
한국의료기기안전정보원 공지사항 스크래핑 테스트
"""

import sys
import os
import logging
from enhanced_kmedihub_scraper import EnhancedKMEDIHUBScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def verify_results(output_dir):
    """결과 검증"""
    if not os.path.exists(output_dir):
        logger.error(f"출력 디렉토리가 존재하지 않습니다: {output_dir}")
        return False
    
    # 생성된 디렉토리 확인
    subdirs = [d for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d))]
    logger.info(f"생성된 공고 디렉토리 수: {len(subdirs)}")
    
    total_items = len(subdirs)
    successful_items = 0
    total_attachments = 0
    url_check_passed = 0
    korean_filename_count = 0
    
    for subdir in subdirs:
        subdir_path = os.path.join(output_dir, subdir)
        
        # content.md 파일 확인
        content_file = os.path.join(subdir_path, "content.md")
        if os.path.exists(content_file):
            successful_items += 1
            
            # 내용 확인
            with open(content_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 원본 URL 포함 여부 확인
            if '**원본 URL**:' in content and 'kmedihub.re.kr' in content:
                url_check_passed += 1
        
        # 첨부파일 확인
        attachments_dir = os.path.join(subdir_path, "attachments")
        if os.path.exists(attachments_dir):
            attachments = os.listdir(attachments_dir)
            total_attachments += len(attachments)
            
            # 한글 파일명 확인
            for filename in attachments:
                att_path = os.path.join(attachments_dir, filename)
                if os.path.isfile(att_path):
                    # 한글 포함 여부 확인
                    has_korean = any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename)
                    if has_korean:
                        korean_filename_count += 1
                    
                    # 파일 크기 확인
                    file_size = os.path.getsize(att_path)
                    logger.debug(f"첨부파일: {filename} ({file_size:,} bytes)")
    
    # 결과 출력
    success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
    
    logger.info("=" * 50)
    logger.info("📊 KMEDIHUB 스크래핑 결과 검증")
    logger.info("=" * 50)
    logger.info(f"📁 총 공고 수: {total_items}")
    logger.info(f"✅ 성공한 공고 수: {successful_items}")
    logger.info(f"📈 성공률: {success_rate:.1f}%")
    logger.info(f"📎 총 첨부파일 수: {total_attachments}")
    logger.info(f"🔗 원본 URL 포함: {url_check_passed}/{total_items}")
    logger.info(f"🇰🇷 한글 파일명: {korean_filename_count}")
    
    if success_rate >= 80:
        logger.info("✨ 테스트 성공! 스크래핑이 정상적으로 작동합니다.")
        return True
    else:
        logger.warning("⚠️ 테스트 실패. 성공률이 80% 미만입니다.")
        return False

def main():
    if len(sys.argv) < 2:
        print("사용법: python test_enhanced_kmedihub.py <페이지수>")
        print("예시: python test_enhanced_kmedihub.py 3")
        sys.exit(1)
    
    try:
        max_pages = int(sys.argv[1])
        if max_pages <= 0:
            raise ValueError("페이지 수는 1 이상이어야 합니다.")
    except ValueError as e:
        print(f"오류: {e}")
        sys.exit(1)
    
    output_dir = "output/kmedihub"
    
    logger.info("=" * 50)
    logger.info("🧪 Enhanced KMEDIHUB 스크래퍼 테스트 시작")
    logger.info("=" * 50)
    logger.info(f"출력 디렉토리: {output_dir}")
    logger.info(f"대상 URL: https://www.kmedihub.re.kr/index.do?menu_id=00000063")
    logger.info(f"스크래핑 페이지 수: {max_pages}")
    
    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)
    
    # 스크래퍼 초기화
    scraper = EnhancedKMEDIHUBScraper()
    
    try:
        # 1. 첫 페이지 접근 테스트
        logger.info("1. 첫 페이지 접근 테스트")
        first_page_url = scraper.get_list_url(1)
        response = scraper.session.get(first_page_url, verify=scraper.verify_ssl, timeout=10)
        logger.info(f"첫 페이지 응답 상태: {response.status_code}")
        logger.info(f"응답 크기: {len(response.content)} bytes")
        
        if response.status_code != 200:
            logger.error("첫 페이지 접근에 실패했습니다.")
            return False
        
        # 2. 목록 파싱 테스트
        logger.info("2. 목록 파싱 테스트")
        announcements = scraper.parse_list_page(response.text)
        logger.info(f"파싱된 공고 수: {len(announcements)}")
        
        if not announcements:
            logger.error("공고를 파싱할 수 없습니다.")
            return False
        
        # 첫 번째 공고 정보 출력
        first_announcement = announcements[0]
        logger.info("첫 번째 공고 정보:")
        logger.info(f"  title: {first_announcement.get('title', 'N/A')}")
        logger.info(f"  url: {first_announcement.get('url', 'N/A')}")
        logger.info(f"  author: {first_announcement.get('author', 'N/A')}")
        logger.info(f"  date: {first_announcement.get('date', 'N/A')}")
        logger.info(f"  views: {first_announcement.get('views', 'N/A')}")
        logger.info(f"  number: {first_announcement.get('number', 'N/A')}")
        logger.info(f"  has_attachment: {first_announcement.get('has_attachment', False)}")
        logger.info(f"  attachments: {len(first_announcement.get('attachments', []))}개")
        
        # 3. 상세 페이지 접근 및 파싱 테스트
        if first_announcement.get('url') and 'javascript:' not in first_announcement.get('onclick', ''):
            logger.info("3. 상세 페이지 접근 및 파싱 테스트")
            logger.info(f"테스트 대상: {first_announcement['title']}")
            
            try:
                detail_response = scraper.session.get(
                    first_announcement['url'], 
                    verify=scraper.verify_ssl, 
                    timeout=10
                )
                logger.info(f"상세 페이지 응답 상태: {detail_response.status_code}")
                
                if detail_response.status_code == 200:
                    detail_data = scraper.parse_detail_page(detail_response.text)
                    logger.info(f"본문 길이: {len(detail_data.get('content', ''))} chars")
                    logger.info(f"첨부파일 수: {len(detail_data.get('attachments', []))}")
                    
                    # 첨부파일 목록 출력
                    if detail_data.get('attachments'):
                        logger.info("첨부파일 목록:")
                        for i, att in enumerate(detail_data['attachments'], 1):
                            logger.info(f"  {i}. {att['name']} - {att.get('download_type', 'unknown')}")
                            logger.info(f"     파일ID: {att.get('file_id', 'N/A')}")
                            logger.info(f"     인덱스: {att.get('file_index', 'N/A')}")
                    
                    # 테스트용 단일 파일 저장
                    test_dir = os.path.join(output_dir, "test_single")
                    os.makedirs(test_dir, exist_ok=True)
                    
                    # 본문 저장
                    with open(os.path.join(test_dir, "test_content.md"), 'w', encoding='utf-8') as f:
                        f.write(detail_data.get('content', ''))
                    logger.info(f"테스트 본문 저장: {test_dir}/test_content.md")
                    
                    # 첫 번째 첨부파일 다운로드 테스트
                    if detail_data.get('attachments'):
                        first_attachment = detail_data['attachments'][0]
                        logger.info(f"테스트 첨부파일 다운로드: {first_attachment['name']}")
                        
                        safe_filename = scraper.sanitize_filename(first_attachment['name'])
                        test_file_path = os.path.join(test_dir, safe_filename)
                        
                        if first_attachment.get('original_href'):
                            success = scraper.download_file(first_attachment['original_href'], test_file_path)
                            if success and os.path.exists(test_file_path):
                                file_size = os.path.getsize(test_file_path)
                                logger.info(f"다운로드 성공: {test_file_path} ({file_size:,} bytes)")
                            else:
                                logger.warning(f"다운로드 실패: {first_attachment['name']}")
                        
            except Exception as e:
                logger.warning(f"상세 페이지 테스트 중 오류: {e}")
        else:
            logger.info("3. JavaScript 기반 상세 페이지로 인해 상세 테스트 건너뛰기")
        
        # 4. 전체 스크래핑 테스트
        logger.info(f"4. 전체 스크래핑 테스트 ({max_pages}페이지)")
        success = scraper.scrape_pages(
            max_pages=max_pages,
            output_base=output_dir
        )
        
        if success:
            logger.info("스크래핑 완료")
            
            # 5. 결과 검증
            logger.info("5. 결과 검증")
            verification_success = verify_results(output_dir)
            
            if verification_success:
                print("\n" + "="*50)
                print("✅ Enhanced KMEDIHUB 스크래퍼 테스트 성공!")
                print("="*50)
                return True
            else:
                print("\n" + "="*50)
                print("❌ 결과 검증 실패")
                print("="*50)
                return False
        else:
            logger.error("스크래핑 실패")
            return False
            
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)