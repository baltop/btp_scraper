#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KBAN 첨부파일 구조 분석 디버깅 스크립트 v2
"""

import logging
import sys
from enhanced_kban_scraper import EnhancedKBANScraper
from bs4 import BeautifulSoup
import re
import json

# 디버그 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

def debug_kban_table_structure():
    """KBAN 메인 페이지의 테이블 구조 자세히 분석"""
    print("=== KBAN 메인 페이지 테이블 구조 분석 ===")
    
    scraper = EnhancedKBANScraper()
    
    # 경기 엔젤투자매칭펀드 공고 URL (메인 페이지)
    detail_url = "https://www.kban.or.kr/jsp/ext/etc/cmm_9001.jsp?BBS_ID=1&BBS_NO=3019&GROUP_NO=3019&STEP=0&LEVEL_VALUE=0"
    print(f"테스트 URL: {detail_url}")
    
    try:
        # 상세 페이지 가져오기
        response = scraper.session.get(detail_url, verify=scraper.verify_ssl, timeout=scraper.timeout)
        response.raise_for_status()
        html_content = response.text
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        print("\n=== 모든 테이블 구조 상세 분석 ===")
        tables = soup.find_all('table')
        print(f"총 테이블 개수: {len(tables)}")
        
        for table_idx, table in enumerate(tables):
            print(f"\n테이블 {table_idx + 1}:")
            print(f"  class: {table.get('class', 'None')}")
            print(f"  id: {table.get('id', 'None')}")
            
            rows = table.find_all('tr')
            print(f"  행 개수: {len(rows)}")
            
            for row_idx, row in enumerate(rows):
                cells = row.find_all(['td', 'th'])
                print(f"    행 {row_idx + 1}: {len(cells)}개 셀")
                
                for cell_idx, cell in enumerate(cells):
                    cell_text = cell.get_text(strip=True)
                    cell_class = cell.get('class', [])
                    
                    # 첨부파일 관련 키워드 확인
                    if any(keyword in cell_text for keyword in ['첨부', '파일', 'hwp', 'pdf', 'download']):
                        print(f"      셀 {cell_idx + 1} (첨부파일 관련): '{cell_text[:50]}...'")
                        print(f"        class: {cell_class}")
                        
                        # 셀 내부의 모든 링크 확인
                        links = cell.find_all('a')
                        for link_idx, link in enumerate(links):
                            href = link.get('href', '')
                            onclick = link.get('onclick', '')
                            text = link.get_text(strip=True)
                            print(f"          링크 {link_idx + 1}: href='{href}', onclick='{onclick}', text='{text}'")
                    elif cell_text and len(cell_text) < 100:  # 짧은 텍스트만 출력
                        print(f"      셀 {cell_idx + 1}: '{cell_text}'")
        
        print("\n=== JavaScript 함수 분석 ===")
        scripts = soup.find_all('script')
        for script_idx, script in enumerate(scripts):
            script_text = script.get_text()
            if script_text and ('download' in script_text.lower() or 'file' in script_text.lower()):
                print(f"\nJavaScript {script_idx + 1}에서 파일 관련 함수 발견:")
                # 함수 정의 찾기
                function_matches = re.findall(r'function\s+(\w+)\s*\([^)]*\)\s*{[^}]*}', script_text, re.MULTILINE | re.DOTALL)
                for func in function_matches:
                    if 'download' in func.lower() or 'file' in func.lower():
                        print(f"  함수: {func}")
        
        print("\n=== 폼(Form) 분석 ===")
        forms = soup.find_all('form')
        for form_idx, form in enumerate(forms):
            print(f"폼 {form_idx + 1}:")
            print(f"  action: {form.get('action', 'None')}")
            print(f"  method: {form.get('method', 'None')}")
            print(f"  name: {form.get('name', 'None')}")
            
            # 폼 내부의 모든 input 확인
            inputs = form.find_all('input')
            for input_elem in inputs:
                input_name = input_elem.get('name', '')
                input_type = input_elem.get('type', '')
                input_value = input_elem.get('value', '')
                if 'file' in input_name.lower() or input_type == 'file':
                    print(f"    파일 관련 input: name='{input_name}', type='{input_type}', value='{input_value}'")
        
        print("\n=== 숨겨진 요소 분석 ===")
        # display:none 또는 visibility:hidden 요소들 확인
        hidden_elements = soup.find_all(attrs={'style': re.compile(r'display\s*:\s*none|visibility\s*:\s*hidden')})
        for elem in hidden_elements:
            elem_text = elem.get_text(strip=True)
            if elem_text and ('첨부' in elem_text or '파일' in elem_text or 'hwp' in elem_text.lower()):
                print(f"숨겨진 요소에서 첨부파일 관련 내용 발견: '{elem_text[:100]}...'")
        
        print("\n=== 분석 완료 ===")
        
    except Exception as e:
        logger.error(f"디버깅 중 오류: {e}")
        raise

if __name__ == "__main__":
    debug_kban_table_structure()