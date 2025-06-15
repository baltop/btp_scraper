#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test specific DJBEA announcement attachment detection
"""

import os
import sys
import requests
from urllib3.exceptions import InsecureRequestWarning
import logging

# SSL 경고 비활성화
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 현재 디렉토리를 Python path에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_djbea_scraper import EnhancedDJBEAScraper

def test_specific_announcement():
    """특정 공고 테스트"""
    scraper = EnhancedDJBEAScraper()
    
    # 테스트할 공고들
    test_announcements = [
        {
            'title': '001_판로수출2025년 로컬상품 개발을 위한 캐릭터 IP라이센스 지원사업',
            'url': 'https://www.djbea.or.kr/pms/st/st_0205/view_new?BBSCTT_SEQ=7952&BBSCTT_TY_CD=ST_0205'
        },
        {
            'title': '002_기술개발「2025년 공공연구성과 확산 및 실용화 사업」',
            'url': 'https://www.djbea.or.kr/pms/st/st_0205/view_new?BBSCTT_SEQ=7940&BBSCTT_TY_CD=ST_0205'
        },
        {
            'title': '003_인력/교육2025년 해외조달시장 전문인력',
            'url': 'https://www.djbea.or.kr/pms/st/st_0205/view_new?BBSCTT_SEQ=7938&BBSCTT_TY_CD=ST_0205'
        }
    ]
    
    for i, announcement in enumerate(test_announcements):
        print(f"\n{'='*80}")
        print(f"Testing announcement {i+1}: {announcement['title']}")
        print(f"URL: {announcement['url']}")
        print("-" * 80)
        
        try:
            # 페이지 가져오기
            response = scraper.get_page(announcement['url'])
            if not response:
                print("Failed to get page")
                continue
                
            print(f"Page fetched successfully (status: {response.status_code})")
            
            # 상세 페이지 파싱 (URL 전달)
            detail = scraper.parse_detail_page(response.text, announcement['url'])
            
            print(f"Content length: {len(detail['content'])} characters")
            print(f"Found {len(detail['attachments'])} attachment(s)")
            
            if detail['attachments']:
                print("\nAttachments found:")
                for j, attachment in enumerate(detail['attachments']):
                    print(f"  {j+1}. {attachment['name']}")
                    print(f"     URL: {attachment['url']}")
                    if 'size' in attachment:
                        print(f"     Size: {attachment['size']}")
                    if attachment.get('verified'):
                        print(f"     Status: Verified")
                    elif attachment.get('estimated'):
                        print(f"     Status: Estimated")
                    print()
            else:
                print("\nNo attachments found")
            
        except Exception as e:
            print(f"Error during test: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_specific_announcement()