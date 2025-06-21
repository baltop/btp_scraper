#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEMAS 직접 테스트
"""

import sys
import os
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from enhanced_semas_scraper import EnhancedSEMASScraper
    print("✅ SEMAS 스크래퍼 import 성공")
except Exception as e:
    print(f"❌ SEMAS 스크래퍼 import 실패: {e}")
    sys.exit(1)

def test_semas_direct():
    """SEMAS 직접 테스트"""
    
    try:
        print("스크래퍼 초기화 중...")
        scraper = EnhancedSEMASScraper()
        print("✅ 스크래퍼 초기화 성공")
        
        # 첫 페이지 URL 테스트
        list_url = scraper.get_list_url(1)
        print(f"첫 페이지 URL: {list_url}")
        
        # 페이지 가져오기
        print("페이지 가져오기 중...")
        response = scraper.get_page(list_url)
        if not response:
            print("❌ 페이지 가져오기 실패")
            return False
        
        print(f"✅ 페이지 가져오기 성공: {response.status_code}")
        
        # 목록 파싱
        print("목록 파싱 중...")
        announcements = scraper.parse_list_page(response.text)
        print(f"✅ 파싱된 공고 수: {len(announcements)}")
        
        if len(announcements) > 0:
            first_ann = announcements[0]
            print(f"첫 번째 공고:")
            print(f"  제목: {first_ann['title']}")
            print(f"  URL: {first_ann['url']}")
            print(f"  날짜: {first_ann['date']}")
            print(f"  첨부파일: {first_ann['has_attachment']}")
            
            # 상세 페이지 테스트
            print("\n상세 페이지 테스트...")
            detail_response = scraper.get_page(first_ann['url'])
            if detail_response:
                detail = scraper.parse_detail_page(detail_response.text, first_ann['url'])
                print(f"✅ 상세 페이지 파싱 성공")
                print(f"  제목: {detail.get('title', 'N/A')}")
                print(f"  내용 길이: {len(detail.get('content', ''))}")
                print(f"  첨부파일 수: {len(detail.get('attachments', []))}")
                
                if detail.get('attachments'):
                    for i, att in enumerate(detail['attachments'][:3]):  # 처음 3개만
                        print(f"    첨부파일 {i+1}: {att['filename']} - {att['url']}")
            else:
                print("❌ 상세 페이지 가져오기 실패")
        
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_semas_direct()
    if success:
        print("\n🎉 직접 테스트 성공!")
    else:
        print("\n💥 직접 테스트 실패!")