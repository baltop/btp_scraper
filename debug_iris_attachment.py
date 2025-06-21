#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IRIS 첨부파일 추출 디버깅
"""

import requests
from bs4 import BeautifulSoup
import re

def test_iris_attachment():
    """IRIS 첨부파일 추출 테스트"""
    
    # 세션 생성
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    
    # 상세 페이지 POST 요청
    detail_url = "https://www.iris.go.kr/contents/retrieveBsnsAncmView.do"
    post_data = {
        'ancmId': '014116',
        'pageIndex': '1'
    }
    
    response = session.post(detail_url, data=post_data, verify=False, timeout=30)
    print(f"응답 상태: {response.status_code}")
    print(f"응답 길이: {len(response.text)}")
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # HTML에서 첨부파일 관련 텍스트 찾기
    print("\n첨부파일 관련 텍스트 검색:")
    if 'f_bsnsAncm_downloadAtchFile' in response.text:
        print("f_bsnsAncm_downloadAtchFile 함수 발견!")
    else:
        print("f_bsnsAncm_downloadAtchFile 함수를 찾을 수 없음")
    
    if 'downloadAtchFile' in response.text:
        print("downloadAtchFile 텍스트 발견!")
    else:
        print("downloadAtchFile 텍스트를 찾을 수 없음")
    
    if '.hwp' in response.text:
        print(".hwp 파일 확장자 발견!")
    else:
        print(".hwp 파일 확장자를 찾을 수 없음")
    
    # JavaScript 함수 호출 링크 찾기
    download_links = soup.find_all('a', onclick=re.compile(r'f_bsnsAncm_downloadAtchFile'))
    print(f"\nf_bsnsAncm_downloadAtchFile 링크: {len(download_links)}개")
    
    # 일반적인 onclick 속성 찾기
    all_onclick_links = soup.find_all('a', onclick=True)
    print(f"모든 onclick 링크: {len(all_onclick_links)}개")
    
    # 처음 몇 개의 onclick 속성 출력
    for i, link in enumerate(all_onclick_links[:5]):
        onclick = link.get('onclick', '')
        print(f"  {i+1}. {onclick[:100]}...")
    
    # JavaScript 함수가 포함된 모든 텍스트 찾기
    print("\nHTML에서 f_bsnsAncm_downloadAtchFile 검색:")
    html_text = response.text
    function_calls = re.findall(r'f_bsnsAncm_downloadAtchFile[^;]*', html_text)
    
    for i, call in enumerate(function_calls[:10]):
        print(f"{i+1}. {call}")
    
    # 첨부파일이 있는 섹션 찾기
    print("\n첨부파일 관련 HTML 태그 찾기:")
    
    # 파일명이 포함된 모든 링크 찾기
    all_links = soup.find_all('a')
    file_links = []
    
    for link in all_links:
        link_text = link.get_text(strip=True)
        href = link.get('href', '')
        onclick = link.get('onclick', '')
        
        # 파일 확장자가 포함된 링크 찾기
        if any(ext in link_text.lower() for ext in ['.hwp', '.pdf', '.doc', '.xls']):
            file_links.append({
                'text': link_text,
                'href': href,
                'onclick': onclick
            })
    
    print(f"파일 확장자가 포함된 링크: {len(file_links)}개")
    for i, link in enumerate(file_links):
        print(f"{i+1}. 텍스트: {link['text'][:50]}...")
        print(f"   href: {link['href']}")
        print(f"   onclick: {link['onclick'][:100]}...")
        print()
    
    for i, link in enumerate(download_links):
        onclick = link.get('onclick', '')
        print(f"\n{i+1}. onclick: {onclick}")
        
        # JavaScript 함수에서 파라미터 추출
        pattern = r"f_bsnsAncm_downloadAtchFile\('([^']+)','([^']+)','([^']+)'\s*,\s*'([^']+)'\)"
        match = re.search(pattern, onclick)
        
        if match:
            file_group_id = match.group(1)
            file_detail_id = match.group(2)
            file_name = match.group(3)
            file_size = match.group(4)
            
            print(f"   파일 그룹 ID: {file_group_id}")
            print(f"   파일 상세 ID: {file_detail_id}")
            print(f"   파일명: {file_name}")
            print(f"   파일 크기: {file_size}")
        else:
            print("   파라미터 추출 실패")
    
    # 실제 다운로드 테스트
    if download_links:
        first_link = download_links[0]
        onclick = first_link.get('onclick', '')
        match = re.search(r"f_bsnsAncm_downloadAtchFile\('([^']+)','([^']+)','([^']+)'\s*,\s*'([^']+)'\)", onclick)
        
        if match:
            file_group_id = match.group(1)
            file_detail_id = match.group(2)
            file_name = match.group(3)
            file_size = match.group(4)
            
            print(f"\n첫 번째 파일 다운로드 테스트: {file_name}")
            
            download_url = "https://www.iris.go.kr/contents/downloadBsnsAncmAtchFile.do"
            download_data = {
                'atchFileId': file_group_id,
                'fileSn': file_detail_id
            }
            
            print(f"다운로드 URL: {download_url}")
            print(f"다운로드 데이터: {download_data}")
            
            try:
                print(f"\n다운로드 시도 1: 기본 헤더")
                download_response = session.post(
                    download_url,
                    data=download_data,
                    headers={
                        'Referer': detail_url,
                        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
                    },
                    timeout=30
                )
                
                if download_response.status_code != 200:
                    print(f"다운로드 시도 2: 확장 헤더")
                    download_response = session.post(
                        download_url,
                        data=download_data,
                        headers={
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
                            'Accept-Encoding': 'gzip, deflate',
                            'Connection': 'keep-alive',
                            'Upgrade-Insecure-Requests': '1',
                            'X-Requested-With': 'XMLHttpRequest',
                            'Referer': detail_url,
                            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
                        },
                        timeout=30
                    )
                
                print(f"다운로드 응답 상태: {download_response.status_code}")
                print(f"다운로드 응답 헤더: {dict(download_response.headers)}")
                
                if download_response.status_code == 200:
                    content_type = download_response.headers.get('Content-Type', '')
                    content_length = download_response.headers.get('Content-Length', '0')
                    print(f"Content-Type: {content_type}")
                    print(f"Content-Length: {content_length}")
                    
                    if 'application' in content_type or 'hwp' in content_type:
                        print("파일 다운로드 성공!")
                    else:
                        print(f"응답 내용 (처음 500자): {download_response.text[:500]}")
                else:
                    print(f"다운로드 실패: {download_response.text[:500]}")
                    
            except Exception as e:
                print(f"다운로드 오류: {e}")

if __name__ == "__main__":
    test_iris_attachment()