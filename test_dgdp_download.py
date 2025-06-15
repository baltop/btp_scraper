#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DGDP 첨부파일 다운로드 URL 패턴 테스트
"""

import requests
import json
import re
import os
from enhanced_dgdp_scraper import EnhancedDGDPScraper

def test_download_patterns():
    """발견된 UUID로 다운로드 URL 패턴 테스트"""
    print("=== DGDP 다운로드 URL 패턴 테스트 ===")
    
    # 발견된 파일 정보들
    test_files = [
        {
            'name': '2024 디자인산업통계 카드뉴스',
            'uuid': '2b0f4116-c2c1-491e-b8ae-0446f4b2daf7',
            'ext': 'pdf',
            'size': 1154083,
            'url': 'https://dgdp.or.kr/notice/public/2482'
        },
        {
            'name': '공고문 및 붙임서류',
            'uuid': '167bd647-f2c7-471d-9592-abf11b29d7e0', 
            'ext': 'hwp',
            'size': 4320768,
            'url': 'https://dgdp.or.kr/notice/public/2353'
        }
    ]
    
    scraper = EnhancedDGDPScraper()
    
    # 다양한 다운로드 URL 패턴들
    url_patterns = [
        "https://dgdp.or.kr/download/board/{uuid}",
        "https://dgdp.or.kr/file/download/board/{uuid}",
        "https://dgdp.or.kr/api/file/download/{uuid}",
        "https://dgdp.or.kr/download/{uuid}",
        "https://dgdp.or.kr/file/download/{uuid}",
        "https://dgdp.or.kr/download/file/{uuid}",
        "https://dgdp.or.kr/attach/download/{uuid}",
        "https://dgdp.or.kr/notice/download/{uuid}",
        "https://dgdp.or.kr/api/download/{uuid}",
        "https://dgdp.or.kr/file/{uuid}",
    ]
    
    successful_urls = []
    
    for file_info in test_files:
        print(f"\n--- 파일: {file_info['name']}.{file_info['ext']} ---")
        print(f"UUID: {file_info['uuid']}")
        print(f"예상 크기: {file_info['size']:,} bytes")
        
        for pattern in url_patterns:
            download_url = pattern.format(uuid=file_info['uuid'])
            
            try:
                print(f"테스트 중: {download_url}")
                
                # HEAD 요청으로 파일 존재 확인
                response = scraper.session.head(
                    download_url,
                    verify=False,
                    timeout=10,
                    allow_redirects=True
                )
                
                print(f"  Status: {response.status_code}")
                
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    content_length = response.headers.get('content-length', '')
                    content_disposition = response.headers.get('content-disposition', '')
                    
                    print(f"  ✓ 성공!")
                    print(f"  Content-Type: {content_type}")
                    print(f"  Content-Length: {content_length}")
                    print(f"  Content-Disposition: {content_disposition}")
                    
                    successful_urls.append({
                        'file_info': file_info,
                        'download_url': download_url,
                        'headers': dict(response.headers)
                    })
                    
                    # 실제 다운로드 테스트 (작은 크기만)
                    if int(content_length or 0) < 2000000:  # 2MB 이하만
                        print(f"  실제 다운로드 테스트 중...")
                        
                        download_response = scraper.session.get(
                            download_url,
                            verify=False,
                            timeout=30,
                            stream=True
                        )
                        
                        if download_response.status_code == 200:
                            # 임시 파일로 저장
                            temp_filename = f"temp_{file_info['name']}.{file_info['ext']}"
                            temp_path = os.path.join("/tmp", temp_filename)
                            
                            with open(temp_path, 'wb') as f:
                                for chunk in download_response.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)
                            
                            actual_size = os.path.getsize(temp_path)
                            print(f"  다운로드 완료: {actual_size:,} bytes")
                            print(f"  파일 저장: {temp_path}")
                            
                            # 크기 비교
                            if actual_size == file_info['size']:
                                print(f"  ✓ 크기 일치!")
                            else:
                                print(f"  ⚠ 크기 불일치 (예상: {file_info['size']:,}, 실제: {actual_size:,})")
                        else:
                            print(f"  다운로드 실패: {download_response.status_code}")
                    else:
                        print(f"  파일이 너무 큼 - 실제 다운로드 스킵")
                    
                    break  # 성공하면 다른 패턴 테스트 안함
                    
                elif response.status_code == 404:
                    print(f"  404 Not Found")
                elif response.status_code == 403:
                    print(f"  403 Forbidden")
                else:
                    print(f"  기타 오류: {response.status_code}")
                    
            except Exception as e:
                print(f"  Error: {e}")
    
    # 결과 요약
    print(f"\n=== 테스트 결과 요약 ===")
    print(f"성공한 다운로드 URL: {len(successful_urls)}개")
    
    for success in successful_urls:
        file_info = success['file_info']
        download_url = success['download_url']
        print(f"✓ {file_info['name']}.{file_info['ext']}")
        print(f"  URL: {download_url}")
        print(f"  패턴: {download_url.replace(file_info['uuid'], '{uuid}')}")

def extract_file_info_from_page(url):
    """페이지에서 파일 정보 추출"""
    print(f"\n=== 페이지에서 파일 정보 추출: {url} ===")
    
    scraper = EnhancedDGDPScraper()
    
    try:
        response = scraper.session.get(url, verify=False, timeout=30)
        
        if response.status_code == 200:
            # fileUuid 패턴으로 파일 정보 찾기
            pattern = r'{"fileUploadId":\d+,"fileNm":"[^"]*","fileSize":\d+,"fileExt":"[^"]*","fileUuid":"[^"]*"}'
            matches = re.findall(pattern, response.text)
            
            files = []
            for match in matches:
                try:
                    file_data = json.loads(match)
                    files.append(file_data)
                    print(f"파일 발견: {file_data}")
                except json.JSONDecodeError:
                    continue
            
            return files
        else:
            print(f"페이지 로드 실패: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"페이지 분석 실패: {e}")
        return []

if __name__ == "__main__":
    test_download_patterns()
    
    # 추가 페이지들에서 파일 정보 확인
    additional_pages = [
        "https://dgdp.or.kr/notice/public/2482",
        "https://dgdp.or.kr/notice/public/2353"
    ]
    
    for page_url in additional_pages:
        files = extract_file_info_from_page(page_url)
        if files:
            print(f"페이지 {page_url}에서 {len(files)}개 파일 발견")