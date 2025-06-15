#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DJBEA 목록 페이지에서 첨부파일 표시 확인
"""

import os
import sys
import requests
from urllib3.exceptions import InsecureRequestWarning
import logging
from bs4 import BeautifulSoup
import re

# SSL 경고 비활성화
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 현재 디렉토리를 Python path에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_djbea_scraper import EnhancedDJBEAScraper

def check_djbea_list():
    """DJBEA 목록 페이지 첨부파일 표시 확인"""
    scraper = EnhancedDJBEAScraper()
    
    # 목록 페이지 가져오기
    list_url = "https://www.djbea.or.kr/pms/st/st_0205/list"
    
    print(f"DJBEA 목록 페이지 분석: {list_url}")
    print("="*80)
    
    try:
        response = scraper.get_page(list_url)
        if not response:
            print("Failed to get list page")
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 테이블 기반 목록 찾기
        table = soup.find('table', class_=re.compile('list|board|bbs'))
        if not table:
            print("목록 테이블을 찾을 수 없습니다")
            return
        
        tbody = table.find('tbody')
        if not tbody:
            print("tbody를 찾을 수 없습니다")
            return
        
        rows = tbody.find_all('tr')
        print(f"총 {len(rows)}개 행 발견")
        
        announcements_with_attachments = []
        
        for i, row in enumerate(rows):
            try:
                # 헤더 행 스킵
                if row.find('th'):
                    continue
                    
                cells = row.find_all('td')
                if len(cells) < 3:
                    continue
                
                # 번호 추출
                num = cells[0].get_text(strip=True)
                
                # 제목 및 링크 찾기
                title_cell = cells[1]
                title_link = title_cell.find('a')
                if not title_link:
                    continue
                    
                title = title_link.get_text(strip=True)
                
                # URL 추출
                href = title_link.get('href', '')
                onclick = title_link.get('onclick', '')
                
                detail_url = None
                if onclick and (not href or href == '#' or 'javascript:' in href):
                    # JavaScript 함수에서 URL 추출
                    match = re.search(r"doViewNew\s*\(\s*['\"]?(\d+)['\"]?\s*,\s*['\"]?([^'\"]+)['\"]?\s*\)", onclick)
                    if match:
                        seq = match.group(1)
                        board_type = match.group(2)
                        detail_url = f"{scraper.base_url}/pms/st/st_0205/view_new?BBSCTT_SEQ={seq}&BBSCTT_TY_CD={board_type}"
                
                # 첨부파일 아이콘 확인
                has_attachment_icon = bool(row.find('img', src=re.compile('file|attach|clip')))
                
                # 첨부파일 표시 확인 (다양한 방법)
                has_attachment_text = '첨부' in row.get_text() or 'file' in row.get_text().lower()
                
                # 파일 개수 표시 확인
                file_count_match = re.search(r'\[(\d+)\]', row.get_text())
                file_count = file_count_match.group(1) if file_count_match else None
                
                print(f"\n{i+1}. 번호: {num}")
                print(f"   제목: {title}")
                print(f"   URL: {detail_url}")
                print(f"   첨부파일 아이콘: {has_attachment_icon}")
                print(f"   첨부파일 텍스트: {has_attachment_text}")
                print(f"   파일 개수: {file_count}")
                
                if has_attachment_icon or has_attachment_text or file_count:
                    announcements_with_attachments.append({
                        'num': num,
                        'title': title,
                        'url': detail_url,
                        'has_icon': has_attachment_icon,
                        'has_text': has_attachment_text,
                        'file_count': file_count
                    })
                
            except Exception as e:
                print(f"Error parsing row {i}: {e}")
                continue
        
        print(f"\n{'='*80}")
        print(f"첨부파일이 있는 것으로 표시된 공고 {len(announcements_with_attachments)}개:")
        
        for ann in announcements_with_attachments:
            print(f"\n- 번호: {ann['num']}")
            print(f"  제목: {ann['title']}")
            print(f"  URL: {ann['url']}")
            print(f"  아이콘: {ann['has_icon']}, 텍스트: {ann['has_text']}, 개수: {ann['file_count']}")
        
        return announcements_with_attachments
        
    except Exception as e:
        print(f"Error analyzing list page: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_djbea_list()