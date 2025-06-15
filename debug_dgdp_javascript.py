#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DGDP HTML에서 JavaScript 데이터 추출 분석
"""

import requests
import json
import re
from bs4 import BeautifulSoup
from enhanced_dgdp_scraper import EnhancedDGDPScraper

def extract_javascript_data(html_content):
    """HTML에서 JavaScript 데이터 추출"""
    print("=== JavaScript 데이터 추출 ===")
    
    # 다양한 패턴으로 JavaScript 변수 찾기
    patterns = [
        # Vue.js 또는 React 데이터
        r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
        r'window\.__NUXT__\s*=\s*({.*?});',
        r'window\.props\s*=\s*({.*?});',
        
        # 일반적인 변수들
        r'const\s+publicDetail\s*=\s*({.*?});',
        r'var\s+publicDetail\s*=\s*({.*?});',
        r'let\s+publicDetail\s*=\s*({.*?});',
        r'publicDetail\s*=\s*({.*?});',
        
        r'const\s+noticeDetail\s*=\s*({.*?});',
        r'var\s+noticeDetail\s*=\s*({.*?});',
        r'let\s+noticeDetail\s*=\s*({.*?});',
        r'noticeDetail\s*=\s*({.*?});',
        
        r'const\s+detail\s*=\s*({.*?});',
        r'var\s+detail\s*=\s*({.*?});',
        r'let\s+detail\s*=\s*({.*?});',
        r'detail\s*=\s*({.*?});',
        
        r'const\s+data\s*=\s*({.*?});',
        r'var\s+data\s*=\s*({.*?});',
        
        # 첨부파일 관련
        r'attachFiles\s*:\s*(\[.*?\])',
        r'attachFileList\s*:\s*(\[.*?\])',
        r'files\s*:\s*(\[.*?\])',
        
        # JSON 형태의 큰 객체들
        r'({[^{}]*"attachFiles"[^{}]*})',
        r'({[^{}]*"attachFileList"[^{}]*})',
        r'({[^{}]*"fileName"[^{}]*})',
        r'({[^{}]*"fileUuid"[^{}]*})',
    ]
    
    found_data = []
    
    for pattern in patterns:
        matches = re.finditer(pattern, html_content, re.DOTALL | re.IGNORECASE)
        for match in matches:
            try:
                json_str = match.group(1)
                # 간단한 JSON 유효성 검사
                if json_str.strip().startswith(('{', '[')):
                    found_data.append({
                        'pattern': pattern,
                        'data': json_str,
                        'length': len(json_str)
                    })
                    print(f"패턴 매치: {pattern}")
                    print(f"데이터 길이: {len(json_str)}")
                    print(f"데이터 미리보기: {json_str[:200]}...")
                    
                    # JSON 파싱 시도
                    try:
                        parsed = json.loads(json_str)
                        print(f"JSON 파싱 성공! 타입: {type(parsed)}")
                        if isinstance(parsed, dict):
                            print(f"키들: {list(parsed.keys())}")
                        elif isinstance(parsed, list):
                            print(f"리스트 길이: {len(parsed)}")
                            if len(parsed) > 0:
                                print(f"첫 번째 요소 타입: {type(parsed[0])}")
                    except json.JSONDecodeError as e:
                        print(f"JSON 파싱 실패: {e}")
                    
                    print("-" * 50)
                    
            except Exception as e:
                print(f"패턴 처리 중 오류: {e}")
    
    return found_data

def analyze_html_structure(html_content):
    """HTML 구조 분석"""
    print("\n=== HTML 구조 분석 ===")
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # script 태그들 분석
    scripts = soup.find_all('script')
    print(f"Script 태그 수: {len(scripts)}")
    
    for i, script in enumerate(scripts):
        if script.string:
            content = script.string.strip()
            if len(content) > 100:  # 충분히 긴 스크립트만
                print(f"\nScript {i+1} (길이: {len(content)}):")
                print(f"미리보기: {content[:200]}...")
                
                # 첨부파일 관련 키워드 찾기
                keywords = ['attach', 'file', 'download', 'uuid', 'fileName']
                found_keywords = [kw for kw in keywords if kw.lower() in content.lower()]
                if found_keywords:
                    print(f"발견된 키워드: {found_keywords}")
                    
                    # 해당 스크립트에서 더 자세히 분석
                    lines = content.split('\n')
                    for line_num, line in enumerate(lines, 1):
                        if any(kw.lower() in line.lower() for kw in found_keywords):
                            print(f"  Line {line_num}: {line.strip()}")
                            if line_num <= len(lines) - 1:  # 다음 줄도 출력
                                print(f"  Line {line_num+1}: {lines[line_num].strip()}")

def test_specific_pages():
    """특정 페이지들에서 JavaScript 데이터 추출 테스트"""
    print("\n=== 특정 페이지 JavaScript 데이터 추출 테스트 ===")
    
    test_urls = [
        "https://dgdp.or.kr/notice/public/2482",  # 2024 디자인산업통계 보고서
        "https://dgdp.or.kr/notice/public/2353"   # 채용 공고
    ]
    
    scraper = EnhancedDGDPScraper()
    
    for url in test_urls:
        print(f"\n--- URL: {url} ---")
        
        try:
            response = scraper.session.get(url, verify=False, timeout=30)
            
            if response.status_code == 200:
                print(f"페이지 로드 성공 (크기: {len(response.text)} 문자)")
                
                # JavaScript 데이터 추출
                js_data = extract_javascript_data(response.text)
                
                if not js_data:
                    print("JavaScript 데이터를 찾을 수 없음 - HTML 구조 분석 실행")
                    analyze_html_structure(response.text)
                else:
                    print(f"총 {len(js_data)}개의 JavaScript 데이터 발견")
                    
            else:
                print(f"페이지 로드 실패: {response.status_code}")
                
        except Exception as e:
            print(f"페이지 테스트 실패: {e}")

if __name__ == "__main__":
    test_specific_pages()