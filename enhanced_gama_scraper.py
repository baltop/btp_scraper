# -*- coding: utf-8 -*-
"""
GAMA(광주미래차모빌리티진흥원) 스크래퍼 - Enhanced 버전
"""

import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from enhanced_base_scraper import StandardTableScraper
import logging

logger = logging.getLogger(__name__)

class EnhancedGAMAScraper(StandardTableScraper):
    """GAMA 공지사항 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://gama.or.kr"
        self.list_url = "https://gama.or.kr/bbs/?b_id=green_notice&site=basic&mn=1136"
        
        # GAMA 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 2
        
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 (offset 기반 페이지네이션)"""
        if page_num == 1:
            return self.list_url
        else:
            # 15개씩 노출되므로 offset = (page_num - 1) * 15
            offset = (page_num - 1) * 15
            return f"{self.list_url}&offset={offset}"
    
    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 테이블 찾기
        table = soup.find('table')
        if not table:
            logger.warning("공지사항 테이블을 찾을 수 없습니다")
            return announcements
        
        # tbody 찾기
        tbody = table.find('tbody')
        if not tbody:
            logger.warning("테이블 본문(tbody)을 찾을 수 없습니다")
            return announcements
        
        # 각 행 처리
        rows = tbody.find_all('tr')
        logger.info(f"총 {len(rows)}개 행 발견")
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 6:
                    continue
                
                # 제목 셀 (두 번째 셀)
                title_cell = cells[1]
                link_elem = title_cell.find('a')
                
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                if not title:
                    continue
                
                # URL 구성
                href = link_elem.get('href', '')
                if href.startswith('?'):
                    detail_url = self.base_url + '/bbs/' + href
                else:
                    detail_url = urljoin(self.base_url, href)
                
                # 작성자 (세 번째 셀)
                writer = cells[2].get_text(strip=True)
                
                # 등록일 (네 번째 셀)
                date = cells[3].get_text(strip=True)
                
                # 조회수 (여섯 번째 셀)
                views = cells[5].get_text(strip=True)
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'writer': writer,
                    'date': date,
                    'views': views
                }
                
                announcements.append(announcement)
                logger.debug(f"공고 추가: {title}")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"총 {len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> dict:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 내용 찾기 - 테이블에서 이미지 부분
        content = ""
        
        # 테이블 내 이미지 영역 찾기
        content_table = soup.find('table')
        if content_table:
            # 마지막 행에서 이미지 찾기
            rows = content_table.find_all('tr')
            for row in reversed(rows):
                img_cell = row.find('td')
                if img_cell and img_cell.find('img'):
                    img = img_cell.find('img')
                    if img and img.get('src'):
                        img_src = urljoin(self.base_url, img.get('src'))
                        content = f"![공고 이미지]({img_src})\n\n"
                        logger.info(f"이미지 발견: {img_src}")
                    break
        
        # 첨부파일 찾기
        attachments = []
        
        # 첨부파일 행 찾기
        attach_row = None
        if content_table:
            rows = content_table.find_all('tr')
            for row in rows:
                header = row.find('th')
                if header and '첨부' in header.get_text():
                    attach_row = row
                    break
        
        if attach_row:
            attach_cell = attach_row.find('td')
            if attach_cell:
                # 첨부파일 링크 찾기
                attach_link = attach_cell.find('a')
                if attach_link:
                    filename = attach_link.get_text(strip=True)
                    href = attach_link.get('href', '')
                    
                    if href.startswith('?'):
                        file_url = self.base_url + '/bbs/' + href
                    else:
                        file_url = urljoin(self.base_url, href)
                    
                    # 파일 크기 정보 추출
                    size_info = ""
                    size_text = attach_cell.get_text()
                    size_match = re.search(r'\(([^)]+MB)\)', size_text)
                    if size_match:
                        size_info = size_match.group(1)
                    
                    attachment = {
                        'filename': filename,
                        'url': file_url,
                        'size': size_info
                    }
                    attachments.append(attachment)
                    logger.info(f"첨부파일 발견: {filename} ({size_info})")
        
        # 본문이 비어있으면 기본 텍스트 추가
        if not content.strip():
            content = "## 공고 내용\n\n공고 내용을 확인하려면 첨부파일을 다운로드하여 확인하세요.\n\n"
        
        result = {
            'content': content,
            'attachments': attachments
        }
        
        logger.info(f"상세 페이지 파싱 완료 - 내용: {len(content)}자, 첨부파일: {len(attachments)}개")
        return result

# 테스트용 함수
def test_gama_scraper(pages=3):
    """GAMA 스크래퍼 테스트"""
    import os
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    scraper = EnhancedGAMAScraper()
    output_dir = "output/gama"
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"GAMA 스크래퍼 테스트 시작 - {pages}페이지")
    scraper.scrape_pages(max_pages=pages, output_base=output_dir)
    logger.info("GAMA 스크래퍼 테스트 완료")

if __name__ == "__main__":
    test_gama_scraper(3)