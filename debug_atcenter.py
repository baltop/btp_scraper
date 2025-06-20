#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ATCENTER HTML 구조 디버깅
"""

import requests
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_atcenter_structure():
    """ATCENTER 사이트 HTML 구조 분석"""
    
    url = "https://www.at.or.kr/article/apko364000/list.action"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }
    
    try:
        logger.info(f"페이지 요청: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        logger.info(f"응답 상태 코드: {response.status_code}")
        logger.info(f"응답 크기: {len(response.text)} characters")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # HTML 저장
        with open('atcenter_debug.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        logger.info("HTML 파일 저장: atcenter_debug.html")
        
        # 테이블 찾기
        tables = soup.find_all('table')
        logger.info(f"발견된 테이블 수: {len(tables)}")
        
        for i, table in enumerate(tables):
            logger.info(f"\n=== 테이블 {i+1} ===")
            
            # caption 확인
            caption = table.find('caption')
            if caption:
                logger.info(f"Caption: {caption.get_text(strip=True)}")
            
            # 클래스 확인
            table_class = table.get('class', [])
            logger.info(f"Table class: {table_class}")
            
            # 헤더 확인
            thead = table.find('thead')
            if thead:
                headers = [th.get_text(strip=True) for th in thead.find_all('th')]
                logger.info(f"Headers: {headers}")
            
            # 행 확인
            tbody = table.find('tbody') or table
            rows = tbody.find_all('tr')
            logger.info(f"총 행 수: {len(rows)}")
            
            # 첫 번째 데이터 행 분석
            data_rows = [row for row in rows if row.find_all('td')]
            if data_rows:
                first_row = data_rows[0]
                cells = first_row.find_all('td')
                logger.info(f"첫 번째 데이터 행 셀 수: {len(cells)}")
                
                for j, cell in enumerate(cells):
                    cell_text = cell.get_text(strip=True)
                    cell_html = str(cell)[:200] + "..." if len(str(cell)) > 200 else str(cell)
                    logger.info(f"  셀 {j+1}: '{cell_text[:50]}...' if len(cell_text) > 50 else cell_text")
                    
                    # 링크 확인
                    links = cell.find_all('a')
                    for link in links:
                        href = link.get('href', '')
                        link_text = link.get_text(strip=True)
                        logger.info(f"    링크: '{link_text}' -> {href}")
        
        # body 전체 구조 확인
        logger.info("\n=== BODY 구조 확인 ===")
        body = soup.find('body')
        if body:
            # 주요 컨테이너 찾기
            main_containers = body.find_all(['main', 'article', 'section', 'div'], class_=True)
            logger.info(f"주요 컨테이너 수: {len(main_containers[:5])} (상위 5개만 표시)")
            
            for container in main_containers[:5]:
                tag_name = container.name
                classes = container.get('class', [])
                container_text = container.get_text(strip=True)[:100]
                logger.info(f"  {tag_name}.{'.'.join(classes)}: '{container_text}...'")
        
    except Exception as e:
        logger.error(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_atcenter_structure()