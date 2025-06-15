#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DGDP API 안전한 분석
"""

import requests
import json
import pprint
from enhanced_dgdp_scraper import EnhancedDGDPScraper

def safe_analyze_api():
    """API 응답 안전한 분석"""
    print("=== DGDP API 안전한 분석 ===")
    
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
            
            # 전체 응답 구조 출력
            print("=== 전체 API 응답 구조 ===")
            print(f"Response keys: {data.keys()}")
            
            if 'data' in data:
                data_info = data['data']
                print(f"Data keys: {data_info.keys()}")
                
                if 'dataList' in data_info:
                    items = data_info['dataList']
                    print(f"Found {len(items)} items")
                    
                    for i, item in enumerate(items[:3]):  # 처음 3개만
                        print(f"\n=== 공고 {i+1}: {item.get('title', 'Unknown')} ===")
                        print(f"ID: {item.get('id')}")
                        
                        # 모든 키 출력
                        print("모든 키들:")
                        for key in item.keys():
                            value = item.get(key)
                            if isinstance(value, (list, dict)):
                                print(f"  {key}: {type(value)} (길이: {len(value) if hasattr(value, '__len__') else 'N/A'})")
                                if isinstance(value, list) and len(value) > 0:
                                    print(f"    첫 번째 항목: {type(value[0])}")
                                    if isinstance(value[0], dict):
                                        print(f"    첫 번째 항목 키들: {value[0].keys()}")
                            else:
                                value_str = str(value)[:100]  # 처음 100자만
                                print(f"  {key}: {value_str}")
                        
                        # attachFileList 특별 처리
                        attach_files = item.get('attachFileList')
                        print(f"\nattachFileList 상세:")
                        print(f"  Type: {type(attach_files)}")
                        print(f"  Value: {attach_files}")
                        
                        if attach_files is not None:
                            if isinstance(attach_files, list):
                                print(f"  List length: {len(attach_files)}")
                                for j, file_info in enumerate(attach_files):
                                    print(f"    파일 {j+1}: {file_info}")
                            else:
                                print(f"  Not a list: {attach_files}")
                        else:
                            print("  attachFileList is None")
                            
    except Exception as e:
        print(f"API 분석 실패: {e}")
        import traceback
        traceback.print_exc()

def check_specific_announcement_api():
    """특정 공고 ID로 상세 API 호출 시도"""
    print("\n=== 특정 공고 상세 API 호출 시도 ===")
    
    scraper = EnhancedDGDPScraper()
    
    # 브라우저에서 확인한 공고 ID들
    test_ids = [2482, 2353]
    
    for announcement_id in test_ids:
        print(f"\n--- 공고 ID {announcement_id} 테스트 ---")
        
        # 다양한 API 엔드포인트 시도
        api_endpoints = [
            f"https://dgdp.or.kr/notice/public/{announcement_id}",
            f"https://dgdp.or.kr/api/notice/public/{announcement_id}",
            f"https://dgdp.or.kr/notice/public/api/{announcement_id}",
            f"https://dgdp.or.kr/api/board/public/{announcement_id}"
        ]
        
        for endpoint in api_endpoints:
            try:
                print(f"Testing endpoint: {endpoint}")
                
                # GET 요청
                response = scraper.session.get(
                    endpoint,
                    headers={
                        **scraper.headers,
                        'Accept': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    verify=False,
                    timeout=10
                )
                
                print(f"  Status: {response.status_code}")
                print(f"  Content-Type: {response.headers.get('content-type', '')}")
                
                if response.status_code == 200:
                    try:
                        json_data = response.json()
                        print(f"  JSON Keys: {json_data.keys()}")
                        
                        # 첨부파일 정보 찾기
                        def find_attachments(obj, path=""):
                            results = []
                            if isinstance(obj, dict):
                                for key, value in obj.items():
                                    current_path = f"{path}.{key}" if path else key
                                    if 'attach' in key.lower() or 'file' in key.lower():
                                        results.append((current_path, value))
                                    results.extend(find_attachments(value, current_path))
                            elif isinstance(obj, list):
                                for i, item in enumerate(obj):
                                    results.extend(find_attachments(item, f"{path}[{i}]"))
                            return results
                        
                        attachment_fields = find_attachments(json_data)
                        if attachment_fields:
                            print("  첨부파일 관련 필드들:")
                            for path, value in attachment_fields:
                                print(f"    {path}: {value}")
                        else:
                            print("  첨부파일 관련 필드 없음")
                            
                        # 성공한 경우 상세 정보 출력
                        print("  ✓ 성공한 API 엔드포인트 발견!")
                        break
                        
                    except json.JSONDecodeError:
                        print("  JSON 파싱 실패 (HTML 응답일 가능성)")
                        
            except Exception as e:
                print(f"  Error: {e}")

if __name__ == "__main__":
    safe_analyze_api()
    check_specific_announcement_api()