#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DIP 첨부파일 디버깅 스크립트
"""

import sys
import logging
from enhanced_dip_scraper import EnhancedDipScraper

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def debug_attachment_parsing():
    """첨부파일 파싱 디버깅"""
    scraper = EnhancedDipScraper()
    
    # 첨부파일이 있는 공고 URL (앞서 확인한 8568번 공고)
    test_url = "https://www.dip.or.kr/home/notice/businessbbs/boardRead.ubs?sfpsize=10&fboardcd=business&sfkind=&sfcategory=&sfstdt=&sfendt=&sfsearch=ftitle&sfkeyword=&fboardnum=8568&sfpage=1"
    
    logger.info(f"테스트 URL: {test_url}")
    
    # 페이지 가져오기
    response = scraper.get_page(test_url)
    if not response:
        logger.error("페이지를 가져올 수 없습니다")
        return
    
    logger.info(f"페이지 응답 상태: {response.status_code}")
    
    # 상세 페이지 파싱
    detail = scraper.parse_detail_page(response.text)
    
    logger.info(f"본문 길이: {len(detail['content'])}")
    logger.info(f"첨부파일 수: {len(detail['attachments'])}")
    
    if detail['attachments']:
        for i, attachment in enumerate(detail['attachments']):
            logger.info(f"첨부파일 {i+1}: {attachment}")
    else:
        logger.warning("첨부파일을 찾을 수 없습니다")
        
        # HTML에서 "첨부" 텍스트 검색
        if "첨부" in response.text:
            logger.info("HTML에 '첨부' 텍스트가 존재합니다")
            # 첨부 관련 HTML 부분 추출
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # "첨부파일" 텍스트를 포함하는 요소들 찾기
            attachment_elements = soup.find_all(text=lambda text: text and "첨부" in text)
            logger.info(f"첨부 관련 텍스트 요소 {len(attachment_elements)}개 발견")
            
            for elem in attachment_elements:
                logger.info(f"첨부 텍스트: {repr(elem)}")
                if elem.parent:
                    logger.info(f"부모 태그: {elem.parent.name}")
                    # 부모 요소의 HTML 출력
                    logger.info(f"부모 HTML: {str(elem.parent)[:200]}...")
            
            # download() 함수 호출 찾기
            import re
            download_matches = re.findall(r'download\(\d+\)', response.text)
            logger.info(f"download() 함수 호출 {len(download_matches)}개 발견: {download_matches}")
            
            # onclick 속성을 가진 모든 링크 찾기
            all_links = soup.find_all('a')
            logger.info(f"총 {len(all_links)}개 링크 발견")
            
            onclick_count = 0
            for i, link in enumerate(all_links):
                onclick = link.get('onclick', '')
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                if onclick:
                    onclick_count += 1
                    if onclick_count <= 5:  # 처음 5개만 출력
                        logger.info(f"링크 {i+1} onclick: {onclick[:100]}...")
                    if 'download(' in onclick:
                        logger.info(f"  -> 다운로드 링크 발견!")
                        logger.info(f"  -> 링크 텍스트: {text}")
                        logger.info(f"  -> 전체 HTML: {str(link)}")
                elif 'download' in href.lower() or 'download' in text.lower():
                    logger.info(f"링크 {i+1} href에 download 포함: {href}")
                    logger.info(f"  -> 링크 텍스트: {text}")
            
            logger.info(f"onclick 속성을 가진 링크 총 {onclick_count}개")
            
            # 첨부파일 영역 HTML 구조 분석
            attachment_text_elem = soup.find(text="첨부파일")
            if attachment_text_elem:
                logger.info("첨부파일 텍스트 요소의 상위 구조 분석:")
                current = attachment_text_elem.parent
                level = 0
                while current and level < 5:
                    logger.info(f"  레벨 {level}: {current.name} - {current.get('class', 'no-class')}")
                    # 이 레벨에서 링크 찾기
                    links_in_level = current.find_all('a')
                    for link in links_in_level:
                        onclick = link.get('onclick', '')
                        if onclick and 'download(' in onclick:
                            logger.info(f"    -> 레벨 {level}에서 다운로드 링크 발견: {onclick}")
                    current = current.parent
                    level += 1
        else:
            logger.warning("HTML에 '첨부' 텍스트가 없습니다")

if __name__ == "__main__":
    debug_attachment_parsing()