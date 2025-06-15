#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
여러 DJBEA 공고의 첨부파일 실제 확인
"""

import os
import sys
import requests
from urllib3.exceptions import InsecureRequestWarning
import logging
from bs4 import BeautifulSoup
import re

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

def test_multiple_djbea_announcements():
    """여러 DJBEA 공고의 첨부파일 실제 확인"""
    scraper = EnhancedDJBEAScraper()
    
    # 여러 공고 테스트
    test_announcements = [
        {
            'seq': '7952', 
            'title': '로컬상품 개발을 위한 캐릭터 IP라이센스 지원사업',
            'url': 'https://www.djbea.or.kr/pms/st/st_0205/view_new?BBSCTT_SEQ=7952&BBSCTT_TY_CD=ST_0205'
        },
        {
            'seq': '7951',
            'title': '2025년 공공연구성과 확산 및 실용화 사업',
            'url': 'https://www.djbea.or.kr/pms/st/st_0205/view_new?BBSCTT_SEQ=7951&BBSCTT_TY_CD=ST_0205'
        },
        {
            'seq': '7950',
            'title': '2025년 해외조달시장 전문인력 양성과정',
            'url': 'https://www.djbea.or.kr/pms/st/st_0205/view_new?BBSCTT_SEQ=7950&BBSCTT_TY_CD=ST_0205'
        },
        {
            'seq': '7949',
            'title': '대전우수상품판매장 입점 기업 상품 전시',
            'url': 'https://www.djbea.or.kr/pms/st/st_0205/view_new?BBSCTT_SEQ=7949&BBSCTT_TY_CD=ST_0205'
        },
        {
            'seq': '7948',
            'title': '2025년 특허분쟁 대응전략 지원사업',
            'url': 'https://www.djbea.or.kr/pms/st/st_0205/view_new?BBSCTT_SEQ=7948&BBSCTT_TY_CD=ST_0205'
        }
    ]
    
    for i, announcement in enumerate(test_announcements):
        print(f"\n{'='*80}")
        print(f"Testing announcement {i+1}: {announcement['title']}")
        print(f"SEQ: {announcement['seq']}, URL: {announcement['url']}")
        print("-" * 80)
        
        try:
            # 페이지 가져오기
            response = scraper.get_page(announcement['url'])
            if not response:
                print("Failed to get page")
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text()
            
            print(f"Page fetched successfully (status: {response.status_code})")
            
            # 1. 첨부파일 키워드 검색
            attachment_keywords = ['첨부', '붙임', '파일', '다운로드', '.pdf', '.hwp', '.doc', '.xls']
            found_keywords = []
            for keyword in attachment_keywords:
                if keyword in page_text:
                    found_keywords.append(keyword)
            
            print(f"첨부파일 관련 키워드: {found_keywords}")
            
            # 2. 파일 확장자 패턴 검색
            file_patterns = re.findall(r'[^\s]*\.(pdf|hwp|doc|docx|xls|xlsx|zip|rar)', page_text, re.IGNORECASE)
            if file_patterns:
                print(f"파일 확장자 패턴 발견: {file_patterns}")
            
            # 3. dext5 컨테이너 확인
            dext_container = soup.find('div', id='dext5-multi-container')
            if dext_container:
                print("dext5-multi-container 발견")
                # 내용 확인
                container_text = dext_container.get_text(strip=True)
                if container_text:
                    print(f"컨테이너 내용: {container_text[:200]}...")
            
            # 4. 스크립트에서 파일 정보 검색
            scripts = soup.find_all('script')
            for script in scripts:
                script_text = script.string if script.string else ""
                if any(keyword in script_text for keyword in ['file', 'attach', 'download']):
                    print(f"파일 관련 스크립트 발견: {script_text[:200]}...")
                    break
            
            # 5. Enhanced 스크래퍼로 첨부파일 추출 테스트
            detail = scraper.parse_detail_page(response.text, announcement['url'])
            print(f"Enhanced 스크래퍼 결과: {len(detail['attachments'])}개 첨부파일")
            
            for j, attachment in enumerate(detail['attachments']):
                print(f"  {j+1}. {attachment['name']}")
                print(f"     URL: {attachment['url']}")
                if attachment.get('verified'):
                    print(f"     Status: Verified")
                elif attachment.get('estimated'):
                    print(f"     Status: Estimated")
            
        except Exception as e:
            print(f"Error testing {announcement['url']}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_multiple_djbea_announcements()