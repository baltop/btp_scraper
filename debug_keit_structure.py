#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KEIT 사이트 구조 분석용 스크립트
"""

from enhanced_keit_scraper import EnhancedKEITScraper
from bs4 import BeautifulSoup
import re

def analyze_keit_structure():
    scraper = EnhancedKEITScraper()
    response = scraper.get_page(scraper.list_url)
    
    if not response:
        print("페이지 가져오기 실패")
        return
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print("=== KEIT 사이트 구조 분석 ===\n")
    
    # 1. 공고 제목이 포함된 요소들 찾기
    title_elements = soup.find_all(string=re.compile('2025년.*공고'))
    print(f"1. 공고 제목 요소 수: {len(title_elements)}\n")
    
    for i, title_elem in enumerate(title_elements):
        parent = title_elem.parent
        if parent:
            print(f"{i+1}. 제목: {title_elem.strip()}")
            print(f"   부모 태그: {parent.name} - 클래스: {parent.get('class', [])}")
            
            # 부모에서 onclick 찾기
            onclick = parent.get('onclick', '')
            if onclick:
                print(f"   onClick: {onclick}")
            
            # 부모의 부모에서 onclick 찾기
            grandparent = parent.parent
            if grandparent:
                onclick = grandparent.get('onclick', '')
                if onclick:
                    print(f"   조부모 onClick: {onclick}")
            
            # href 속성이 있는 조상 찾기
            current = parent
            depth = 0
            while current and current != soup and depth < 10:
                if current.name == 'a' and current.get('href'):
                    print(f"   링크 발견: {current.get('href')}")
                    break
                try:
                    current = current.parent
                    depth += 1
                except:
                    break
            print()
    
    # 2. onclick 이벤트가 있는 모든 요소 검사
    print("2. onClick 이벤트 분석")
    onclick_elements = soup.find_all(attrs={'onclick': True})
    
    for elem in onclick_elements:
        onclick = elem.get('onclick', '')
        text = elem.get_text(strip=True)
        
        # 공고 관련 onclick만 필터링
        if '공고' in text or 'ancm' in onclick.lower() or 'view' in onclick.lower():
            print(f"   텍스트: {text[:50]}...")
            print(f"   onClick: {onclick}")
            print()
    
    # 3. JavaScript 코드에서 URL 패턴 찾기
    print("3. JavaScript 코드 분석")
    scripts = soup.find_all('script')
    
    for script in scripts:
        if script.string:
            script_content = script.string
            
            # 함수 정의 찾기
            if 'function' in script_content and ('view' in script_content.lower() or 'detail' in script_content.lower()):
                lines = script_content.split('\n')
                for line in lines:
                    if 'function' in line and ('view' in line.lower() or 'detail' in line.lower()):
                        print(f"   함수: {line.strip()}")
            
            # URL 패턴 찾기
            url_matches = re.findall(r'[\'\"](.*retrieveTaskAnncmInfoView\.do[^\'\"]*)[\'\"]', script_content)
            for url in url_matches:
                print(f"   URL 패턴: {url}")
    
    # 4. ancmId나 다른 식별자 찾기
    print("\n4. 공고 식별자 분석")
    
    # ancmId 패턴
    ancm_matches = re.findall(r'ancmId[=:]\s*[\'\"]*([^\'\",\s;)]+)', response.text)
    if ancm_matches:
        print(f"   ancmId 발견: {ancm_matches}")
    
    # 숫자 ID 패턴
    id_matches = re.findall(r'[\'\"](I\d+)[\'\"]*', response.text)
    if id_matches:
        print(f"   ID 패턴 발견: {id_matches}")
    
    # bsnsYy 패턴
    year_matches = re.findall(r'bsnsYy[=:]\s*[\'\"]*(\d{4})', response.text)
    if year_matches:
        print(f"   연도 패턴 발견: {year_matches}")

if __name__ == "__main__":
    analyze_keit_structure()