#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KBAN 경기 엔젤투자매칭펀드 공고 첨부파일 정밀 분석
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

def debug_gyeonggi_announcement():
    """경기 엔젤투자매칭펀드 공고 첨부파일 정밀 분석"""
    print("=== 경기 엔젤투자매칭펀드 공고 첨부파일 분석 ===")
    
    scraper = EnhancedKBANScraper()
    
    # 경기 엔젤투자매칭펀드 공고 URL (output/kban/004에서 확인한 URL)
    detail_url = "https://www.kban.or.kr/jsp/ext/etc/cmm_9001.jsp?BBS_ID=1&BBS_NO=3019&GROUP_NO=3019&STEP=0&LEVEL_VALUE=0"
    print(f"분석 URL: {detail_url}")
    
    try:
        # 상세 페이지 가져오기
        response = scraper.session.get(detail_url, verify=scraper.verify_ssl, timeout=scraper.timeout)
        response.raise_for_status()
        html_content = response.text
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # HTML 전체를 파일로 저장
        with open('gyeonggi_detail.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        print("HTML 저장: gyeonggi_detail.html")
        
        # 1. 모든 테이블 행 상세 분석
        print("\n=== 모든 테이블 행 상세 분석 ===")
        tables = soup.find_all('table')
        for table_idx, table in enumerate(tables):
            print(f"\n테이블 {table_idx + 1}:")
            rows = table.find_all('tr')
            
            for row_idx, row in enumerate(rows):
                cells = row.find_all(['td', 'th'])
                print(f"  행 {row_idx + 1}: {len(cells)}개 셀")
                
                for cell_idx, cell in enumerate(cells):
                    cell_text = cell.get_text(strip=True)
                    cell_html = str(cell)
                    
                    print(f"    셀 {cell_idx + 1}: '{cell_text}'")
                    
                    # 첨부파일 관련 키워드가 있는 셀 상세 분석
                    if '첨부' in cell_text or 'hwp' in cell_text.lower() or 'pdf' in cell_text.lower():
                        print(f"      ★ 첨부파일 관련 셀 발견!")
                        print(f"      HTML: {cell_html[:200]}...")
                        
                        # 셀 내부 모든 요소 분석
                        links = cell.find_all('a')
                        spans = cell.find_all('span')
                        divs = cell.find_all('div')
                        
                        print(f"      링크 수: {len(links)}")
                        for link in links:
                            href = link.get('href', '')
                            onclick = link.get('onclick', '')
                            link_text = link.get_text(strip=True)
                            print(f"        링크: href='{href}', onclick='{onclick}', text='{link_text}'")
                        
                        print(f"      span 수: {len(spans)}")
                        for span in spans:
                            span_text = span.get_text(strip=True)
                            span_class = span.get('class', [])
                            span_style = span.get('style', '')
                            print(f"        span: text='{span_text}', class={span_class}, style='{span_style}'")
                        
                        print(f"      div 수: {len(divs)}")
                        for div in divs:
                            div_text = div.get_text(strip=True)
                            div_class = div.get('class', [])
                            print(f"        div: text='{div_text}', class={div_class}")
        
        # 2. iframe 내부 상세 분석
        print("\n=== iframe 내부 상세 분석 ===")
        iframes = soup.find_all('iframe')
        for iframe_idx, iframe in enumerate(iframes):
            iframe_src = iframe.get('src', '')
            print(f"iframe {iframe_idx + 1}: {iframe_src}")
            
            if iframe_src:
                iframe_url = scraper.base_url + iframe_src if iframe_src.startswith('/') else iframe_src
                print(f"완전한 iframe URL: {iframe_url}")
                
                try:
                    iframe_response = scraper.session.get(iframe_url, timeout=30)
                    iframe_html = iframe_response.text
                    iframe_soup = BeautifulSoup(iframe_html, 'html.parser')
                    
                    # iframe HTML 저장
                    iframe_filename = f'gyeonggi_iframe_{iframe_idx + 1}.html'
                    with open(iframe_filename, 'w', encoding='utf-8') as f:
                        f.write(iframe_html)
                    print(f"iframe HTML 저장: {iframe_filename}")
                    
                    # iframe 내부에서 파일 관련 텍스트 찾기
                    iframe_text = iframe_soup.get_text()
                    
                    # hwp, pdf 등 파일 확장자 찾기
                    file_patterns = re.findall(r'[^\s<>]+\.(hwp|pdf|docx?|xlsx?|pptx?)', iframe_text, re.I)
                    if file_patterns:
                        print(f"  iframe에서 파일 패턴 발견: {file_patterns}")
                    
                    # 파일명 패턴 더 넓게 찾기
                    broader_patterns = re.findall(r'([가-힣a-zA-Z0-9_\-\.()]+\.(hwp|pdf|docx?|xlsx?|pptx?))', iframe_text, re.I)
                    if broader_patterns:
                        print(f"  iframe에서 파일명 패턴 발견: {broader_patterns}")
                    
                    # 특정 키워드 주변 텍스트 확인
                    if '입찰서' in iframe_text or '양식' in iframe_text:
                        lines = iframe_text.split('\n')
                        for i, line in enumerate(lines):
                            if '입찰서' in line or '양식' in line or '.hwp' in line or '.pdf' in line:
                                print(f"  관련 라인 {i}: {line.strip()}")
                    
                except Exception as e:
                    print(f"iframe 접근 오류: {e}")
        
        # 3. JavaScript 분석
        print("\n=== JavaScript 함수 상세 분석 ===")
        scripts = soup.find_all('script')
        for script_idx, script in enumerate(scripts):
            script_text = script.get_text()
            if script_text and ('download' in script_text.lower() or 'file' in script_text.lower() or 'hwp' in script_text.lower()):
                print(f"\nJavaScript {script_idx + 1}:")
                print(script_text[:500] + "..." if len(script_text) > 500 else script_text)
        
        # 4. 모든 텍스트에서 파일 패턴 찾기
        print("\n=== 전체 텍스트에서 파일 패턴 검색 ===")
        all_text = soup.get_text()
        
        # 다양한 파일명 패턴 시도
        patterns = [
            r'([가-힣a-zA-Z0-9_\-\.()[\]]+\.hwp)',
            r'([가-힣a-zA-Z0-9_\-\.()[\]]+\.pdf)',
            r'([가-힣a-zA-Z0-9_\-\.()[\]]+\.docx?)',
            r'([가-힣a-zA-Z0-9_\-\.()[\]]+\.xlsx?)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, all_text, re.I)
            if matches:
                print(f"패턴 '{pattern}'에서 발견: {matches}")
        
        # 5. 숨겨진 form이나 input 찾기
        print("\n=== 숨겨진 form/input 분석 ===")
        forms = soup.find_all('form')
        for form in forms:
            inputs = form.find_all('input')
            for inp in inputs:
                inp_name = inp.get('name', '')
                inp_value = inp.get('value', '')
                inp_type = inp.get('type', '')
                if 'file' in inp_name.lower() or inp_type == 'file' or 'attach' in inp_name.lower():
                    print(f"파일 관련 input: name='{inp_name}', value='{inp_value}', type='{inp_type}'")
        
        print("\n=== 분석 완료 ===")
        
    except Exception as e:
        logger.error(f"디버깅 중 오류: {e}")
        raise

if __name__ == "__main__":
    debug_gyeonggi_announcement()