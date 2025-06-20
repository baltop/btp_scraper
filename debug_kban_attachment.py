#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KBAN 첨부파일 구조 분석 디버깅 스크립트
"""

import logging
import sys
from enhanced_kban_scraper import EnhancedKBANScraper
from bs4 import BeautifulSoup
import re

# 디버그 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

def debug_specific_announcement():
    """특정 공고의 첨부파일 구조 분석"""
    print("=== KBAN 첨부파일 구조 분석 ===")
    
    scraper = EnhancedKBANScraper()
    
    # 경기 엔젤투자매칭펀드 공고 URL
    detail_url = "https://www.kban.or.kr/jsp/ext/etc/cmm_9001.jsp?BBS_ID=1&BBS_NO=3019&GROUP_NO=3019&STEP=0&LEVEL_VALUE=0"
    print(f"테스트 URL: {detail_url}")
    
    try:
        # 상세 페이지 가져오기
        response = scraper.session.get(detail_url, verify=scraper.verify_ssl, timeout=scraper.timeout)
        response.raise_for_status()
        html_content = response.text
        
        print(f"HTML 길이: {len(html_content)} 문자")
        
        # HTML 파일로 저장 (분석용)
        with open('kban_detail_debug.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        print("HTML 파일 저장: kban_detail_debug.html")
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 1. iframe 분석
        print("\n=== iframe 분석 ===")
        iframes = soup.find_all('iframe')
        print(f"iframe 개수: {len(iframes)}")
        
        for i, iframe in enumerate(iframes):
            iframe_src = iframe.get('src', '')
            print(f"iframe {i+1}: src='{iframe_src}'")
            
            if iframe_src:
                iframe_url = scraper.base_url + iframe_src if iframe_src.startswith('/') else iframe_src
                print(f"완전한 iframe URL: {iframe_url}")
                
                try:
                    iframe_response = scraper.session.get(iframe_url, timeout=30)
                    iframe_html = iframe_response.text
                    iframe_soup = BeautifulSoup(iframe_html, 'html.parser')
                    
                    # iframe HTML 저장
                    iframe_filename = f'kban_iframe_{i+1}_debug.html'
                    with open(iframe_filename, 'w', encoding='utf-8') as f:
                        f.write(iframe_html)
                    print(f"iframe HTML 저장: {iframe_filename}")
                    
                    # iframe 내 링크 분석
                    iframe_links = iframe_soup.find_all('a')
                    print(f"iframe {i+1} 내 링크 개수: {len(iframe_links)}")
                    
                    for j, link in enumerate(iframe_links):
                        href = link.get('href', '')
                        text = link.get_text(strip=True)
                        print(f"  링크 {j+1}: href='{href}', text='{text}'")
                        
                        # 파일 링크인지 확인
                        if href and any(ext in href.lower() for ext in ['.hwp', '.pdf', '.doc', '.xls']):
                            print(f"    -> 첨부파일 발견!")
                    
                    # iframe 내 테이블 분석
                    iframe_tables = iframe_soup.find_all('table')
                    print(f"iframe {i+1} 내 테이블 개수: {len(iframe_tables)}")
                    
                    for k, table in enumerate(iframe_tables):
                        rows = table.find_all('tr')
                        print(f"  테이블 {k+1}: {len(rows)}개 행")
                        
                        for row_idx, row in enumerate(rows):
                            cells = row.find_all('td')
                            if len(cells) >= 2:
                                first_cell = cells[0].get_text(strip=True)
                                second_cell = cells[1]
                                
                                if any(keyword in first_cell for keyword in ['첨부', '파일', '자료']):
                                    print(f"    행 {row_idx+1}: '{first_cell}' 발견!")
                                    
                                    # 두 번째 셀의 링크들 확인
                                    cell_links = second_cell.find_all('a')
                                    for link in cell_links:
                                        link_href = link.get('href', '')
                                        link_text = link.get_text(strip=True)
                                        print(f"      첨부파일 링크: href='{link_href}', text='{link_text}'")
                    
                except Exception as e:
                    print(f"iframe 접근 오류: {e}")
        
        # 2. 메인 페이지의 모든 링크 분석
        print("\n=== 메인 페이지 링크 분석 ===")
        all_links = soup.find_all('a')
        print(f"전체 링크 개수: {len(all_links)}")
        
        file_link_count = 0
        for i, link in enumerate(all_links):
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # 파일 링크 패턴 확인
            if href and (any(ext in href.lower() for ext in ['.hwp', '.pdf', '.doc', '.xls']) or 
                        any(keyword in href.lower() for keyword in ['download', 'file', 'attach'])):
                file_link_count += 1
                print(f"파일 링크 {file_link_count}: href='{href}', text='{text}'")
        
        # 3. 테이블 구조 분석
        print("\n=== 테이블 구조 분석 ===")
        tables = soup.find_all('table')
        print(f"테이블 개수: {len(tables)}")
        
        for i, table in enumerate(tables):
            rows = table.find_all('tr')
            print(f"테이블 {i+1}: {len(rows)}개 행")
            
            for j, row in enumerate(rows):
                cells = row.find_all('td')
                if len(cells) >= 1:
                    first_cell = cells[0].get_text(strip=True)
                    if '첨부' in first_cell or '파일' in first_cell:
                        print(f"  행 {j+1}: 첨부파일 관련 행 발견 - '{first_cell}'")
                        if len(cells) >= 2:
                            second_cell_text = cells[1].get_text(strip=True)
                            print(f"    내용: '{second_cell_text}'")
        
        # 4. JavaScript 분석
        print("\n=== JavaScript 분석 ===")
        scripts = soup.find_all('script')
        js_file_count = 0
        
        for script in scripts:
            script_text = script.get_text()
            if 'hwp' in script_text.lower() or 'pdf' in script_text.lower():
                js_file_count += 1
                print(f"JavaScript에서 파일 관련 코드 발견 {js_file_count}:")
                # hwp나 pdf가 포함된 줄만 출력
                lines = script_text.split('\n')
                for line_num, line in enumerate(lines):
                    if 'hwp' in line.lower() or 'pdf' in line.lower():
                        print(f"  라인 {line_num+1}: {line.strip()}")
        
        print("\n=== 분석 완료 ===")
        
    except Exception as e:
        logger.error(f"디버깅 중 오류: {e}")
        raise

if __name__ == "__main__":
    debug_specific_announcement()