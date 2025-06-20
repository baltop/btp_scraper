#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KBAN 스크래퍼 디버깅 스크립트
"""

import logging
import sys
from enhanced_kban_scraper import EnhancedKBANScraper

# 디버그 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

def debug_single_page():
    """단일 페이지 디버깅"""
    print("=== KBAN 단일 페이지 디버깅 ===")
    
    scraper = EnhancedKBANScraper()
    
    # 첫 페이지 가져오기
    url = scraper.get_list_url(1)
    print(f"테스트 URL: {url}")
    
    try:
        response = scraper.session.get(url, verify=scraper.verify_ssl, timeout=scraper.timeout)
        response.raise_for_status()
        html_content = response.text
        
        print(f"HTML 길이: {len(html_content)} 문자")
        
        # 목록 파싱
        announcements = scraper.parse_list_page(html_content)
        
        print(f"\n=== 파싱 결과 ===")
        print(f"추출된 공고 수: {len(announcements)}")
        
        if announcements:
            print("\n첫 5개 공고:")
            for i, ann in enumerate(announcements[:5], 1):
                print(f"{i}. {ann['title'][:50]}...")
                print(f"   URL: {ann['url']}")
                print(f"   번호: {ann['number']}")
        
        # 첫 번째 공고 상세 테스트
        if announcements:
            first_ann = announcements[0]
            print(f"\n=== 첫 번째 공고 상세 테스트 ===")
            print(f"제목: {first_ann['title']}")
            print(f"URL: {first_ann['url']}")
            
            try:
                detail_response = scraper.session.get(first_ann['url'], verify=scraper.verify_ssl, timeout=scraper.timeout)
                detail_response.raise_for_status()
                detail_html = detail_response.text
                
                result = scraper.parse_detail_page(detail_html)
                print(f"본문 길이: {len(result['content'])} 문자")
                print(f"첨부파일 수: {len(result['attachments'])}")
                print(f"본문 미리보기: {result['content'][:200]}...")
                
                if result['attachments']:
                    print(f"첨부파일 목록:")
                    for att in result['attachments']:
                        print(f"  - {att['filename']}: {att['url']}")
                
            except Exception as e:
                print(f"상세 페이지 접근 오류: {e}")
        
    except Exception as e:
        logger.error(f"디버깅 중 오류: {e}")
        raise

if __name__ == "__main__":
    debug_single_page()