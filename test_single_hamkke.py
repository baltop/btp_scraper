#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
함께일하는재단(hamkke.org) 단일 공고 테스트
"""

import os
import sys
import logging
from enhanced_hamkke_scraper import EnhancedHamkkeScraper

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def test_single_announcement():
    """단일 공고 상세 테스트"""
    print("=== 함께일하는재단 단일 공고 테스트 ===")
    
    scraper = EnhancedHamkkeScraper()
    
    # 첫 번째 공고 URL
    test_url = "https://hamkke.org/archives/business/51064"
    
    try:
        with scraper:  # Playwright context manager
            print(f"테스트 URL: {test_url}")
            
            # 페이지 콘텐츠 가져오기
            html_content = scraper.fetch_page_with_playwright(test_url)
            print(f"HTML 길이: {len(html_content)} 문자")
            
            # JavaScript 데이터 확인
            business_view = scraper.extract_business_view_from_js(html_content)
            print(f"\n=== JavaScript businessView 데이터 ===")
            if business_view:
                print(f"businessView 키들: {list(business_view.keys())}")
                for key, value in business_view.items():
                    if isinstance(value, str) and len(value) > 50:
                        print(f"{key}: {value[:100]}...")
                    else:
                        print(f"{key}: {value}")
            else:
                print("businessView를 찾을 수 없음")
            
            # DOM 구조 확인
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            print(f"\n=== DOM 구조 분석 ===")
            
            # 주요 컨테이너들 찾기
            selectors_to_check = [
                'article', 'main', '.entry-content', '.post-content', 
                '.wp-block-group', '.single-content', '#post-content'
            ]
            
            for selector in selectors_to_check:
                elements = soup.select(selector)
                if elements:
                    element = elements[0]
                    text_length = len(element.get_text(strip=True))
                    print(f"{selector}: {len(elements)}개 요소, 첫 번째 텍스트 길이: {text_length}")
            
            # 상세 페이지 파싱
            result = scraper.parse_detail_page(html_content)
            
            print(f"\n=== 파싱 결과 ===")
            print(f"콘텐츠 길이: {len(result['content'])} 문자")
            print(f"첨부파일 수: {len(result['attachments'])}")
            
            print(f"\n=== 콘텐츠 미리보기 ===")
            print(result['content'][:500])
            
            if result['attachments']:
                print(f"\n=== 첨부파일 목록 ===")
                for i, att in enumerate(result['attachments'], 1):
                    print(f"{i}. {att['filename']} - {att['url']}")
            
    except Exception as e:
        logger.error(f"테스트 중 오류: {e}")
        raise

if __name__ == "__main__":
    test_single_announcement()