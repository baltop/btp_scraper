#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DJBEA Enhanced 첨부파일 추출 테스트
"""

import os
import sys
import requests
from urllib3.exceptions import InsecureRequestWarning
import logging
from bs4 import BeautifulSoup

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

def test_enhanced_extraction():
    """Enhanced 첨부파일 추출 테스트"""
    scraper = EnhancedDJBEAScraper()
    
    # 테스트할 공고들
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
        }
    ]
    
    print("Enhanced DJBEA 첨부파일 추출 테스트")
    print("="*80)
    
    for i, announcement in enumerate(test_announcements):
        print(f"\n{i+1}. {announcement['title']} (SEQ: {announcement['seq']})")
        print("-" * 60)
        
        try:
            # 페이지 가져오기
            response = scraper.get_page(announcement['url'])
            if not response:
                print("페이지 가져오기 실패")
                continue
            
            # 상세 페이지 파싱
            detail = scraper.parse_detail_page(response.text, announcement['url'])
            attachments = detail['attachments']
            
            print(f"발견된 첨부파일: {len(attachments)}개")
            
            # 중복 제거 후 결과 출력
            unique_attachments = []
            seen_urls = set()
            
            for attachment in attachments:
                url = attachment['url']
                if url not in seen_urls:
                    seen_urls.add(url)
                    unique_attachments.append(attachment)
            
            print(f"중복 제거 후: {len(unique_attachments)}개")
            print()
            
            for j, attachment in enumerate(unique_attachments):
                print(f"  {j+1}. {attachment['name']}")
                print(f"     URL: {attachment['url']}")
                print(f"     크기: {attachment.get('size', 'Unknown')}")
                print(f"     타입: {attachment.get('content_type', 'Unknown')}")
                
                # 실제 다운로드 테스트
                test_download = scraper._try_download_url(attachment['url'], f"/tmp/test_{j+1}")
                if test_download:
                    print(f"     다운로드: ✅ 성공")
                    # 테스트 파일 삭제
                    try:
                        os.remove(f"/tmp/test_{j+1}")
                    except:
                        pass
                else:
                    print(f"     다운로드: ❌ 실패")
                print()
            
            # PDF와 HWP 파일 개수 확인
            pdf_count = len([a for a in unique_attachments if a['name'].endswith('.pdf')])
            hwp_count = len([a for a in unique_attachments if a['name'].endswith('.hwp')])
            
            print(f"PDF 파일: {pdf_count}개, HWP 파일: {hwp_count}개")
            
            if pdf_count >= 1 and hwp_count >= 1:
                print("✅ PDF와 HWP 파일 모두 발견됨")
            elif pdf_count >= 1:
                print("⚠️  PDF 파일만 발견됨 (HWP 파일 없음)")
            elif hwp_count >= 1:
                print("⚠️  HWP 파일만 발견됨 (PDF 파일 없음)")
            else:
                print("❌ PDF/HWP 파일 없음")
            
        except Exception as e:
            print(f"오류 발생: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_enhanced_extraction()