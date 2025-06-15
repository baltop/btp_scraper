#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DJBEA SEQ=7949 공고 상세 분석 (첨부파일이 있는 것으로 보이는 공고)
"""

import os
import sys
import requests
from urllib3.exceptions import InsecureRequestWarning
import logging
from bs4 import BeautifulSoup
import re
import json

# SSL 경고 비활성화
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 현재 디렉토리를 Python path에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_djbea_scraper import EnhancedDJBEAScraper

def analyze_seq7949():
    """SEQ=7949 공고 상세 분석"""
    scraper = EnhancedDJBEAScraper()
    
    url = "https://www.djbea.or.kr/pms/st/st_0205/view_new?BBSCTT_SEQ=7949&BBSCTT_TY_CD=ST_0205"
    
    print(f"SEQ=7949 공고 상세 분석: {url}")
    print("="*80)
    
    try:
        # 페이지 가져오기
        response = scraper.get_page(url)
        if not response:
            print("Failed to get page")
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. A2mUpload 스크립트 상세 분석
        print("1. A2mUpload 스크립트 상세 분석:")
        scripts = soup.find_all('script')
        for i, script in enumerate(scripts):
            script_text = script.string if script.string else ""
            if 'A2mUpload' in script_text:
                print(f"   Script {i+1} (A2mUpload 포함):")
                print(f"   {script_text}")
                print()
                
                # targetAtchFileId 추출 시도
                patterns = [
                    r'targetAtchFileId\s*:\s*[\'"]([^\'"]+)[\'"]',
                    r'targetAtchFileId\s*=\s*[\'"]([^\'"]+)[\'"]',
                    r'targetAtchFileId[^=]*[\'"]([^\'"]+)[\'"]'
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, script_text)
                    if match:
                        file_group_id = match.group(1)
                        print(f"   -> targetAtchFileId 발견: {file_group_id}")
                        break
                else:
                    print("   -> targetAtchFileId를 찾을 수 없음")
        
        # 2. dext5-multi-container 내용 상세 분석
        print("2. dext5-multi-container 내용 상세 분석:")
        dext_container = soup.find('div', id='dext5-multi-container')
        if dext_container:
            print(f"   Container HTML: {str(dext_container)}")
            print()
        
        # 3. 페이지 전체 텍스트에서 첨부파일 관련 정보 검색
        print("3. 페이지 텍스트에서 첨부파일 정보 검색:")
        page_text = soup.get_text()
        
        # 첨부파일 관련 라인 찾기
        lines = page_text.split('\n')
        attachment_lines = []
        for line in lines:
            line = line.strip()
            if any(keyword in line for keyword in ['첨부', '붙임', '파일', 'file']):
                attachment_lines.append(line)
        
        if attachment_lines:
            print("   첨부파일 관련 라인들:")
            for line in attachment_lines:
                print(f"   -> {line}")
        else:
            print("   첨부파일 관련 라인 없음")
        
        # 4. 모든 링크 분석
        print("4. 모든 링크 분석:")
        all_links = soup.find_all('a')
        for i, link in enumerate(all_links):
            href = link.get('href', '')
            onclick = link.get('onclick', '')
            text = link.get_text(strip=True)
            
            # 파일 관련 링크만 출력
            if any(keyword in text.lower() for keyword in ['file', '파일', '첨부', '다운로드', 'download']) or \
               any(ext in href.lower() for ext in ['.pdf', '.hwp', '.doc', '.xls']) or \
               any(keyword in onclick.lower() for keyword in ['download', 'file']):
                print(f"   Link {i+1}: {text}")
                print(f"   -> href: {href}")
                print(f"   -> onclick: {onclick}")
                print()
        
        # 5. 폼과 입력 필드 분석
        print("5. 폼과 입력 필드 분석:")
        forms = soup.find_all('form')
        for i, form in enumerate(forms):
            print(f"   Form {i+1}: action={form.get('action')}, method={form.get('method')}")
            inputs = form.find_all('input')
            for j, inp in enumerate(inputs):
                inp_type = inp.get('type', '')
                inp_name = inp.get('name', '')
                inp_value = inp.get('value', '')
                if 'file' in inp_name.lower() or inp_type == 'file':
                    print(f"     Input {j+1}: type={inp_type}, name={inp_name}, value={inp_value}")
        
        # 6. Enhanced 스크래퍼로 단계별 첨부파일 추출 테스트
        print("6. Enhanced 스크래퍼 단계별 테스트:")
        
        # A2mUpload 테스트
        a2m_files = scraper._extract_djbea_a2m_files(soup)
        print(f"   A2mUpload 추출: {len(a2m_files)}개")
        
        # dext5 컨테이너 테스트
        dext5_containers = soup.find_all('div', class_='dext5-multi-container')
        total_dext5_files = 0
        for container in dext5_containers:
            dext5_files = scraper._extract_from_dext5_container(container)
            total_dext5_files += len(dext5_files)
        print(f"   dext5 컨테이너 추출: {total_dext5_files}개")
        
        # 파일 섹션 테스트
        file_sections = soup.find_all('div', class_=re.compile('file|attach'))
        total_section_files = 0
        for section in file_sections:
            section_files = scraper._extract_from_file_section(section)
            total_section_files += len(section_files)
        print(f"   파일 섹션 추출: {total_section_files}개")
        
        # 텍스트 패턴 테스트
        text_files = scraper._extract_from_text_patterns(soup)
        print(f"   텍스트 패턴 추출: {len(text_files)}개")
        
        # 하드코딩 테스트
        hardcoded_files = scraper._extract_hardcoded_djbea_files(url)
        print(f"   하드코딩 추출: {len(hardcoded_files)}개")
        
    except Exception as e:
        print(f"Error analyzing SEQ=7949: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_seq7949()