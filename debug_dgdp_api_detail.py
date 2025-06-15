#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DGDP API 세부 분석 - attachFileList 확인
"""

import requests
import json
import pprint
from enhanced_dgdp_scraper import EnhancedDGDPScraper

def analyze_attachments_in_api():
    """API 응답에서 첨부파일 정보 상세 분석"""
    print("=== DGDP API attachFileList 상세 분석 ===")
    
    scraper = EnhancedDGDPScraper()
    
    # API 요청 데이터
    request_data = {
        "searchCategory": "",
        "searchCategorySub": "",
        "searchValue": "",
        "searchType": "all",
        "pageIndex": 1,
        "pageUnit": 10,
        "pageSize": 5
    }
    
    try:
        response = scraper.session.post(
            scraper.api_url,
            json=request_data,
            headers=scraper.headers,
            verify=False,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            items = data['data']['dataList']
            
            for i, item in enumerate(items):
                print(f"\n=== 공고 {i+1}: {item.get('title')} ===")
                print(f"ID: {item.get('id')}")
                
                # 첨부파일 리스트 확인
                attach_files = item.get('attachFileList', [])
                print(f"첨부파일 개수: {len(attach_files)}")
                
                if attach_files:
                    print("첨부파일 상세 정보:")
                    for j, file_info in enumerate(attach_files):
                        print(f"  파일 {j+1}:")
                        pprint.pprint(file_info, indent=4)
                        
                        # 다운로드 URL 생성 시도
                        file_uuid = file_info.get('fileUuid') or file_info.get('uuid')
                        file_name = file_info.get('fileName') or file_info.get('name')
                        
                        if file_uuid:
                            download_urls = [
                                f"https://dgdp.or.kr/download/board/{file_uuid}",
                                f"https://dgdp.or.kr/file/download/board/{file_uuid}",
                                f"https://dgdp.or.kr/api/file/download/{file_uuid}"
                            ]
                            
                            print(f"    가능한 다운로드 URLs:")
                            for url in download_urls:
                                print(f"      - {url}")
                else:
                    print("첨부파일 없음")
                
                # contents 필드도 확인 (본문 내용)
                contents = item.get('contents', '')
                if contents:
                    print(f"본문 길이: {len(contents)} 문자")
                    if len(contents) > 200:
                        print(f"본문 미리보기: {contents[:200]}...")
                    else:
                        print(f"본문 전체: {contents}")
                else:
                    print("본문 내용 없음")
                
                if i >= 4:  # 처음 5개만 분석
                    break
                    
    except Exception as e:
        print(f"API 분석 실패: {e}")

def test_download_url():
    """실제 다운로드 URL 테스트"""
    print("\n=== 다운로드 URL 테스트 ===")
    
    # 브라우저에서 확인한 파일들
    test_cases = [
        {
            'name': '2024 디자인산업통계 카드뉴스.pdf',
            'announcement_id': 2482,
            'possible_uuids': []  # API에서 확인 후 채움
        },
        {
            'name': '공고문 및 붙임서류.hwp', 
            'announcement_id': 2353,
            'possible_uuids': []  # API에서 확인 후 채움
        }
    ]
    
    scraper = EnhancedDGDPScraper()
    
    # 먼저 API에서 UUID 확인
    request_data = {
        "searchCategory": "",
        "searchCategorySub": "",
        "searchValue": "",
        "searchType": "all",
        "pageIndex": 1,
        "pageUnit": 10,
        "pageSize": 5
    }
    
    try:
        response = scraper.session.post(
            scraper.api_url,
            json=request_data,
            headers=scraper.headers,
            verify=False,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            items = data['data']['dataList']
            
            # UUID 매핑
            for item in items:
                item_id = item.get('id')
                attach_files = item.get('attachFileList', [])
                
                for test_case in test_cases:
                    if test_case['announcement_id'] == item_id:
                        for file_info in attach_files:
                            file_uuid = file_info.get('fileUuid') or file_info.get('uuid')
                            if file_uuid:
                                test_case['possible_uuids'].append(file_uuid)
            
            # 다운로드 테스트
            for test_case in test_cases:
                print(f"\n--- {test_case['name']} ---")
                print(f"공고 ID: {test_case['announcement_id']}")
                print(f"발견된 UUIDs: {test_case['possible_uuids']}")
                
                for uuid in test_case['possible_uuids']:
                    download_urls = [
                        f"https://dgdp.or.kr/download/board/{uuid}",
                        f"https://dgdp.or.kr/file/download/board/{uuid}",
                        f"https://dgdp.or.kr/api/file/download/{uuid}"
                    ]
                    
                    for url in download_urls:
                        try:
                            print(f"Testing: {url}")
                            head_response = scraper.session.head(url, verify=False, timeout=10)
                            print(f"  Status: {head_response.status_code}")
                            if head_response.status_code == 200:
                                content_type = head_response.headers.get('content-type', '')
                                content_length = head_response.headers.get('content-length', '')
                                content_disposition = head_response.headers.get('content-disposition', '')
                                print(f"  Content-Type: {content_type}")
                                print(f"  Content-Length: {content_length}")
                                print(f"  Content-Disposition: {content_disposition}")
                                print(f"  ✓ 다운로드 가능한 URL 발견!")
                                break
                        except Exception as e:
                            print(f"  Error: {e}")
                            
    except Exception as e:
        print(f"다운로드 URL 테스트 실패: {e}")

if __name__ == "__main__":
    analyze_attachments_in_api()
    test_download_url()