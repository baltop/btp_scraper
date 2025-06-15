#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced JBF 스크래퍼 테스트 스크립트
"""

import sys
import os
import logging

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_jbf_scraper import EnhancedJBFScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_enhanced_jbf_scraper():
    """Enhanced JBF 스크래퍼 테스트"""
    print("=== Enhanced JBF 스크래퍼 테스트 시작 ===")
    
    # 스크래퍼 인스턴스 생성
    scraper = EnhancedJBFScraper()
    
    # 기본 정보 출력
    print(f"Base URL: {scraper.base_url}")
    print(f"List URL: {scraper.list_url}")
    print(f"SSL 검증: {scraper.verify_ssl}")
    
    try:
        # 1페이지만 테스트
        print("\n=== 1페이지 테스트 ===")
        
        # 목록 페이지 URL 생성 테스트
        page1_url = scraper.get_list_url(1)
        page2_url = scraper.get_list_url(2)
        
        print(f"Page 1 URL: {page1_url}")
        print(f"Page 2 URL: {page2_url}")
        
        # 목록 페이지 가져오기
        print("\n목록 페이지 가져오는 중...")
        response = scraper.get_page(page1_url)
        
        if not response:
            print("ERROR: 목록 페이지를 가져올 수 없습니다.")
            return False
        
        print(f"응답 상태: {response.status_code}")
        print(f"응답 크기: {len(response.text)} bytes")
        
        # 목록 파싱
        print("\n목록 파싱 중...")
        announcements = scraper.parse_list_page(response.text)
        
        print(f"발견된 공고 수: {len(announcements)}")
        
        if announcements:
            print("\n첫 번째 공고:")
            first = announcements[0]
            for key, value in first.items():
                print(f"  {key}: {value}")
            
            # 첫 번째 공고 상세 페이지 테스트
            print(f"\n=== 상세 페이지 테스트 ({first['title']}) ===")
            detail_response = scraper.get_page(first['url'])
            
            if detail_response:
                print(f"상세 페이지 상태: {detail_response.status_code}")
                
                # 상세 페이지 파싱
                detail = scraper.parse_detail_page(detail_response.text)
                
                print(f"본문 길이: {len(detail['content'])} 문자")
                print(f"첨부파일 수: {len(detail['attachments'])}")
                
                if detail['attachments']:
                    print("첨부파일 목록:")
                    for i, att in enumerate(detail['attachments'], 1):
                        print(f"  {i}. {att['name']} - {att['url']}")
                
                # 본문 일부 출력 (처음 200자)
                if detail['content']:
                    print(f"\n본문 미리보기:")
                    preview = detail['content'][:200]
                    print(f"  {preview}...")
            else:
                print("ERROR: 상세 페이지를 가져올 수 없습니다.")
        
        print("\n=== 테스트 완료 ===")
        return True
        
    except Exception as e:
        print(f"ERROR: 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_enhanced_jbf_scraper()
    sys.exit(0 if success else 1)