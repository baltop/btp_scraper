#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DGDP 스크래퍼 디버깅 - 첨부파일 확인
"""

import requests
import json
import os
from bs4 import BeautifulSoup
from enhanced_dgdp_scraper import EnhancedDGDPScraper

def debug_dgdp_api():
    """DGDP API 직접 호출 테스트"""
    print("=== DGDP API 직접 호출 테스트 ===")
    
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
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {response.headers}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"API Response Keys: {data.keys()}")
            
            if 'data' in data:
                data_info = data['data']
                print(f"Data Keys: {data_info.keys()}")
                
                if 'dataList' in data_info:
                    items = data_info['dataList']
                    print(f"Found {len(items)} items")
                    
                    for i, item in enumerate(items[:3]):  # 처음 3개만
                        print(f"\n=== Item {i+1} ===")
                        print(f"ID: {item.get('id')}")
                        print(f"Title: {item.get('title')}")
                        print(f"Link YN: {item.get('linkYn')}")
                        print(f"Keys: {item.keys()}")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"API 호출 실패: {e}")

def debug_specific_announcement():
    """특정 공고 상세 페이지 직접 테스트"""
    print("\n=== 특정 공고 상세 페이지 테스트 ===")
    
    # 브라우저에서 확인한 첨부파일이 있는 공고들
    test_urls = [
        "https://dgdp.or.kr/notice/public/2482",  # 2024 디자인산업통계 보고서
        "https://dgdp.or.kr/notice/public/2353"   # 채용 공고
    ]
    
    scraper = EnhancedDGDPScraper()
    
    for url in test_urls:
        print(f"\n--- Testing URL: {url} ---")
        
        try:
            response = scraper.session.get(url, verify=False, timeout=30)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                # HTML 파싱
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 제목 찾기
                title_elem = soup.find('h1') or soup.find('h2') or soup.find('.title')
                if title_elem:
                    print(f"Title: {title_elem.get_text(strip=True)}")
                
                # 첨부파일 섹션 찾기
                print("\n첨부파일 관련 요소들:")
                
                # "첨부파일" 텍스트가 있는 요소들
                for elem in soup.find_all(text=lambda text: text and '첨부파일' in text):
                    parent = elem.parent
                    print(f"Found '첨부파일' text in: {parent.name} - {parent.get('class')}")
                    
                    # 상위 요소에서 링크 찾기
                    for _ in range(3):
                        if parent:
                            links = parent.find_all('a', href=True)
                            for link in links:
                                href = link.get('href')
                                text = link.get_text(strip=True)
                                print(f"  Link: {text} -> {href}")
                            parent = parent.parent
                
                # download 관련 링크들
                download_links = soup.find_all('a', href=lambda x: x and 'download' in x.lower())
                for link in download_links:
                    href = link.get('href')
                    text = link.get_text(strip=True)
                    print(f"Download link: {text} -> {href}")
                
                # 파일 확장자가 있는 링크들
                file_links = soup.find_all('a', href=lambda x: x and any(ext in x.lower() for ext in ['.pdf', '.hwp', '.doc', '.zip']))
                for link in file_links:
                    href = link.get('href')
                    text = link.get_text(strip=True)
                    print(f"File link: {text} -> {href}")
                
                # JavaScript에서 파일 정보 찾기
                print("\nJavaScript 데이터 확인:")
                js_content = response.text
                if 'attachFiles' in js_content:
                    print("Found 'attachFiles' in JavaScript")
                    # attachFiles 패턴 찾기
                    import re
                    pattern = r'attachFiles\s*:\s*(\[.*?\])'
                    match = re.search(pattern, js_content, re.DOTALL)
                    if match:
                        try:
                            files_data = match.group(1)
                            print(f"Attach files data: {files_data}")
                        except Exception as e:
                            print(f"Failed to parse attachFiles: {e}")
                
        except Exception as e:
            print(f"Error testing {url}: {e}")

def check_downloads_folder():
    """브라우저에서 다운로드된 파일들 확인"""
    print("\n=== 브라우저 다운로드 파일 확인 ===")
    
    download_paths = [
        "/tmp/playwright-mcp-output/2025-06-13T01-21-23.163Z/"
    ]
    
    for path in download_paths:
        if os.path.exists(path):
            print(f"Path: {path}")
            files = os.listdir(path)
            for file in files:
                file_path = os.path.join(path, file)
                if os.path.isfile(file_path):
                    size = os.path.getsize(file_path)
                    print(f"  - {file} ({size:,} bytes)")
        else:
            print(f"Path not found: {path}")

if __name__ == "__main__":
    debug_dgdp_api()
    debug_specific_announcement()
    check_downloads_folder()