#!/usr/bin/env python3
"""
SMTECH 사이트 구조 분석 스크립트
HTML 소스를 직접 분석하여 파일 다운로드 링크 패턴을 파악
"""

import requests
from bs4 import BeautifulSoup
import re
import json

def analyze_smtech_page():
    """SMTECH 상세 페이지 HTML 구조 분석"""
    
    # 세션 설정
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }
    session.headers.update(headers)
    
    # 상세 페이지 URL
    detail_url = "https://www.smtech.go.kr/front/ifg/no/notice02_detail.do"
    detail_params = {
        'buclYy': '',
        'ancmId': 'S02808',
        'buclCd': 'S9111',
        'dtlAncmSn': '1',
        'schdSe': 'MO5005',
        'aplySn': '1',
        'searchCondition': '',
        'searchKeyword': '',
        'pageIndex': '1'
    }
    
    print("=== SMTECH 페이지 구조 분석 ===")
    
    try:
        # 페이지 요청
        response = session.get(detail_url, params=detail_params, verify=False)
        response.encoding = 'utf-8'
        
        print(f"응답 코드: {response.status_code}")
        
        # BeautifulSoup으로 파싱
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. cfn_AtchFileDownload 함수 호출 찾기
        print("\n=== cfn_AtchFileDownload 함수 호출 분석 ===")
        file_download_links = []
        
        # JavaScript 호출 패턴 찾기
        script_pattern = r"cfn_AtchFileDownload\(['\"]([^'\"]+)['\"],\s*['\"]([^'\"]*)['\"],\s*['\"]([^'\"]*)['\"]"
        for script_tag in soup.find_all('script'):
            if script_tag.string:
                matches = re.findall(script_pattern, script_tag.string)
                for match in matches:
                    file_id, context, target = match
                    file_download_links.append({
                        'type': 'script_tag',
                        'file_id': file_id,
                        'context': context,
                        'target': target
                    })
        
        # href 속성에서 JavaScript 호출 찾기
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if 'cfn_AtchFileDownload' in href:
                # JavaScript 함수 호출에서 파라미터 추출
                match = re.search(r"cfn_AtchFileDownload\(['\"]([^'\"]+)['\"],\s*['\"]([^'\"]*)['\"],\s*['\"]([^'\"]*)['\"]", href)
                if match:
                    file_id, context, target = match.groups()
                    file_download_links.append({
                        'type': 'href_javascript',
                        'file_id': file_id,
                        'context': context,
                        'target': target,
                        'link_text': link.get_text().strip(),
                        'link_element': str(link)[:200] + "..." if len(str(link)) > 200 else str(link)
                    })
        
        print(f"발견된 파일 다운로드 링크: {len(file_download_links)}개")
        for i, link in enumerate(file_download_links, 1):
            print(f"\n{i}. 파일 ID: {link['file_id']}")
            print(f"   컨텍스트: {link['context']}")
            print(f"   타겟: {link['target']}")
            if 'link_text' in link:
                print(f"   링크 텍스트: {link['link_text']}")
            print(f"   타입: {link['type']}")
        
        # 2. 테이블 구조 분석
        print("\n=== 테이블 구조 분석 ===")
        tables = soup.find_all('table')
        print(f"발견된 테이블: {len(tables)}개")
        
        for i, table in enumerate(tables, 1):
            print(f"\n테이블 {i}:")
            if table.get('summary'):
                print(f"  Summary: {table.get('summary')}")
            
            rows = table.find_all('tr')
            print(f"  행 수: {len(rows)}")
            
            for j, row in enumerate(rows[:5]):  # 처음 5개 행만 분석
                cells = row.find_all(['td', 'th'])
                if cells:
                    cell_texts = [cell.get_text().strip()[:50] for cell in cells]
                    print(f"    행 {j+1}: {cell_texts}")
        
        # 3. 첨부파일 관련 요소 분석
        print("\n=== 첨부파일 관련 요소 분석 ===")
        
        # "첨부파일" 텍스트가 포함된 요소 찾기
        attachment_elements = soup.find_all(string=re.compile(r'첨부파일'))
        print(f"'첨부파일' 텍스트 발견: {len(attachment_elements)}개")
        
        for element in attachment_elements:
            parent = element.parent if element.parent else None
            if parent:
                print(f"  부모 태그: {parent.name}")
                # 주변 링크 찾기
                nearby_links = parent.find_all('a', href=True) if parent else []
                for link in nearby_links:
                    href = link.get('href', '')
                    text = link.get_text().strip()
                    print(f"    링크: {text[:50]} -> {href[:100]}")
        
        # 4. HWP 파일 관련 요소 분석
        print("\n=== HWP 파일 관련 요소 분석 ===")
        hwp_links = soup.find_all('a', string=re.compile(r'\.hwp'))
        print(f"HWP 파일 링크 발견: {len(hwp_links)}개")
        
        for link in hwp_links:
            href = link.get('href', '')
            text = link.get_text().strip()
            print(f"  {text} -> {href}")
        
        # 5. 제출서류 섹션 분석
        print("\n=== 제출서류 섹션 분석 ===")
        submission_texts = soup.find_all(string=re.compile(r'제출서류'))
        for element in submission_texts:
            parent = element.parent
            if parent:
                # 해당 행의 모든 링크 찾기
                row = parent
                while row and row.name != 'tr':
                    row = row.parent
                
                if row:
                    links = row.find_all('a', href=True)
                    print(f"\n제출서류 행에서 발견된 링크: {len(links)}개")
                    for link in links:
                        href = link.get('href', '')
                        text = link.get_text().strip()
                        print(f"  {text} -> {href}")
        
        # 6. 전체 링크 패턴 분석
        print("\n=== 전체 링크 패턴 분석 ===")
        all_links = soup.find_all('a', href=True)
        
        pattern_counts = {}
        for link in all_links:
            href = link.get('href', '')
            
            # 패턴 분류
            if href.startswith('javascript:'):
                pattern = 'javascript'
            elif href.startswith('http'):
                pattern = 'external_url'
            elif href.startswith('/'):
                pattern = 'absolute_path'
            elif href.startswith('#'):
                pattern = 'anchor'
            else:
                pattern = 'relative_path'
            
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        
        print("링크 패턴 분포:")
        for pattern, count in pattern_counts.items():
            print(f"  {pattern}: {count}개")
        
        # JavaScript 링크 상세 분석
        js_links = [link for link in all_links if link.get('href', '').startswith('javascript:')]
        print(f"\nJavaScript 링크 상세 ({len(js_links)}개):")
        js_functions = {}
        for link in js_links:
            href = link.get('href', '')
            text = link.get_text().strip()
            
            # 함수명 추출
            func_match = re.search(r'javascript:(\w+)', href)
            if func_match:
                func_name = func_match.group(1)
                if func_name not in js_functions:
                    js_functions[func_name] = []
                js_functions[func_name].append({
                    'text': text[:50],
                    'href': href[:100]
                })
        
        for func_name, calls in js_functions.items():
            print(f"  {func_name}: {len(calls)}회 호출")
            for call in calls[:3]:  # 처음 3개만 표시
                print(f"    '{call['text']}' -> {call['href']}")
    
    except Exception as e:
        print(f"분석 중 오류 발생: {e}")

def test_file_download_variations():
    """다양한 파일 다운로드 방식 테스트"""
    print("\n=== 파일 다운로드 방식 테스트 ===")
    
    session = requests.Session()
    base_url = "https://www.smtech.go.kr"
    
    # 알려진 파일 ID
    file_id = "DF2CA1CDD4664BCD3C7294CD7CB7D562"
    
    # 다양한 엔드포인트 패턴 테스트
    endpoints = [
        "/front/comn/AtchFileDownload.do",
        "/front/comn/fileDownload.do", 
        "/comn/AtchFileDownload.do",
        "/comn/fileDownload.do",
        "/front/comn/download.do",
        "/front/comn/atchFileDownload.do",
    ]
    
    for endpoint in endpoints:
        full_url = base_url + endpoint
        
        # GET 방식
        print(f"\nGET {full_url}?atchFileId={file_id}")
        try:
            response = session.get(f"{full_url}?atchFileId={file_id}", verify=False)
            content_type = response.headers.get('Content-Type', '')
            content_length = response.headers.get('Content-Length', 'Unknown')
            print(f"  응답: {response.status_code}, Content-Type: {content_type}, Length: {content_length}")
            
            if response.status_code == 200 and 'application' in content_type:
                print(f"  ✓ 파일 다운로드 가능!")
        except Exception as e:
            print(f"  오류: {e}")
        
        # POST 방식
        print(f"POST {full_url}")
        try:
            response = session.post(full_url, data={'atchFileId': file_id}, verify=False)
            content_type = response.headers.get('Content-Type', '')
            content_length = response.headers.get('Content-Length', 'Unknown')
            print(f"  응답: {response.status_code}, Content-Type: {content_type}, Length: {content_length}")
            
            if response.status_code == 200 and 'application' in content_type:
                print(f"  ✓ 파일 다운로드 가능!")
        except Exception as e:
            print(f"  오류: {e}")

if __name__ == "__main__":
    # SSL 경고 무시
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    analyze_smtech_page()
    test_file_download_variations()