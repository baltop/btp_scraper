"""
GCAF 단일 공고 테스트 - 첨부파일 확인용
"""

import os
import sys
import logging
from enhanced_gcaf_scraper import EnhancedGCAFScraper

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,  # DEBUG 레벨로 상세 로그 확인
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_single_announcement():
    """첨부파일이 있는 특정 공고 테스트"""
    logger.info("=== GCAF 단일 공고 테스트 시작 ===")
    
    # 출력 디렉토리 설정
    output_dir = "output/gcaf_test_single"
    os.makedirs(output_dir, exist_ok=True)
    
    # 스크래퍼 초기화
    scraper = EnhancedGCAFScraper()
    
    # 첨부파일이 있는 특정 공고 URL
    test_url = "https://www.gcaf.or.kr/bbs/board.php?bo_table=sub3_7&wr_id=1884"
    
    try:
        # 상세 페이지 가져오기
        logger.info(f"테스트 URL: {test_url}")
        response = scraper.session.get(test_url, timeout=30, verify=True)
        response.raise_for_status()
        
        # 상세 페이지 파싱
        detail_data = scraper.parse_detail_page(response.text, test_url)
        
        logger.info(f"제목: {detail_data['title']}")
        logger.info(f"본문 길이: {len(detail_data['content'])} 문자")
        logger.info(f"첨부파일 수: {len(detail_data['attachments'])}")
        
        # 첨부파일 정보 출력
        for i, attachment in enumerate(detail_data['attachments'], 1):
            logger.info(f"  첨부파일 {i}: {attachment['name']}")
            logger.info(f"  URL: {attachment['url']}")
        
        if detail_data['attachments']:
            # 저장 디렉토리 생성
            safe_title = scraper.sanitize_filename(detail_data['title'])
            folder_name = f"test_{safe_title}"
            save_dir = os.path.join(output_dir, folder_name)
            os.makedirs(save_dir, exist_ok=True)
            
            # 본문 저장
            content_path = os.path.join(save_dir, 'content.md')
            with open(content_path, 'w', encoding='utf-8') as f:
                f.write(f"# {detail_data['title']}\n\n")
                f.write(f"**원본 URL**: {detail_data['url']}\n\n")
                f.write(detail_data['content'])
            
            # 첨부파일 다운로드
            attachments_dir = os.path.join(save_dir, 'attachments')
            os.makedirs(attachments_dir, exist_ok=True)
            
            success_count = 0
            for att_idx, attachment in enumerate(detail_data['attachments'], 1):
                att_name = attachment['name'] or f"attachment_{att_idx}"
                safe_att_name = scraper.sanitize_filename(att_name)
                att_path = os.path.join(attachments_dir, safe_att_name)
                
                logger.info(f"첨부파일 {att_idx} 다운로드 시도: {safe_att_name}")
                if scraper.download_file(attachment['url'], att_path):
                    success_count += 1
                    file_size = os.path.getsize(att_path)
                    logger.info(f"✓ 다운로드 성공: {safe_att_name} ({file_size:,} bytes)")
                else:
                    logger.error(f"✗ 다운로드 실패: {safe_att_name}")
            
            logger.info(f"=== 결과 요약 ===")
            logger.info(f"총 첨부파일: {len(detail_data['attachments'])}개")
            logger.info(f"다운로드 성공: {success_count}개")
            logger.info(f"성공률: {success_count/len(detail_data['attachments'])*100:.1f}%")
            logger.info(f"저장 위치: {save_dir}")
            
            return success_count > 0
        else:
            logger.warning("첨부파일이 없습니다")
            return False
            
    except Exception as e:
        logger.error(f"테스트 실패: {e}")
        return False

if __name__ == "__main__":
    success = test_single_announcement()
    
    if success:
        logger.info("첨부파일 테스트 성공!")
        sys.exit(0)
    else:
        logger.error("첨부파일 테스트 실패!")
        sys.exit(1)