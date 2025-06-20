#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KBAN 경기 엔젤투자매칭펀드 공고 단일 테스트
"""

import logging
import sys
from enhanced_kban_scraper import EnhancedKBANScraper

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

def test_single_announcement():
    """경기 엔젤투자매칭펀드 공고 단일 테스트"""
    print("=== 경기 엔젤투자매칭펀드 공고 첨부파일 테스트 ===")
    
    scraper = EnhancedKBANScraper()
    
    # 경기 엔젤투자매칭펀드 공고 URL
    detail_url = "https://www.kban.or.kr/jsp/ext/etc/cmm_9001.jsp?BBS_ID=1&BBS_NO=3019&GROUP_NO=3019&STEP=0&LEVEL_VALUE=0"
    
    try:
        # 상세 페이지 가져오기
        response = scraper.session.get(detail_url, verify=scraper.verify_ssl, timeout=scraper.timeout)
        response.raise_for_status()
        html_content = response.text
        
        print(f"HTML 길이: {len(html_content)} 문자")
        
        # 상세 내용 파싱
        detail = scraper.parse_detail_page(html_content)
        
        print(f"\n=== 파싱 결과 ===")
        print(f"본문 길이: {len(detail['content'])} 문자")
        print(f"첨부파일 수: {len(detail['attachments'])}")
        
        print(f"\n본문 미리보기:")
        print(detail['content'][:300] + "..." if len(detail['content']) > 300 else detail['content'])
        
        if detail['attachments']:
            print(f"\n=== 첨부파일 목록 ===")
            for i, att in enumerate(detail['attachments'], 1):
                print(f"{i}. 파일명: {att['filename']}")
                print(f"   URL: {att['url']}")
                print(f"   크기: {att['size']} bytes")
                print()
                
                # 실제 다운로드 테스트
                print(f"   다운로드 테스트 중...")
                try:
                    download_response = scraper.session.head(att['url'], timeout=10)
                    print(f"   응답 코드: {download_response.status_code}")
                    if 'content-length' in download_response.headers:
                        size = download_response.headers['content-length']
                        print(f"   실제 파일 크기: {size} bytes")
                    if 'content-disposition' in download_response.headers:
                        disposition = download_response.headers['content-disposition']
                        print(f"   Content-Disposition: {disposition}")
                except Exception as e:
                    print(f"   다운로드 테스트 실패: {e}")
        else:
            print("\n첨부파일이 발견되지 않았습니다.")
        
        print(f"\n=== 테스트 완료 ===")
        
    except Exception as e:
        logger.error(f"테스트 중 오류: {e}")
        raise

if __name__ == "__main__":
    test_single_announcement()