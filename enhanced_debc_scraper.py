#!/usr/bin/env python3
"""
DEBC (장애인기업종합지원센터) 전용 스크래퍼 - 향상된 버전

사이트: https://www.debc.or.kr/bbs/board.php?bo_table=s2_2
특징: 그누보드 5 기반, 표준 HTML 테이블 구조
"""

import os
import re
import time
import logging
from typing import List, Dict, Any
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import requests

from enhanced_base_scraper import StandardTableScraper

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedDEBCScraper(StandardTableScraper):
    """DEBC 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 기본 설정
        self.base_url = "https://www.debc.or.kr"
        self.list_url = "https://www.debc.or.kr/bbs/board.php?bo_table=s2_2"
        
        # 사이트별 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        
        # 헤더 설정
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # 세션 설정
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - 설정 주입과 Fallback 패턴"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: 그누보드 표준 페이지네이션
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&page={page_num}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: 그누보드 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """그누보드 특화된 목록 페이지 파싱"""
        announcements = []
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 그누보드 표준 테이블 구조
        table = soup.find('table')
        if not table:
            logger.warning("테이블을 찾을 수 없습니다")
            return announcements
        
        tbody = table.find('tbody')
        if not tbody:
            tbody = table
        
        logger.info(f"테이블에서 {len(tbody.find_all('tr'))}개 행 발견")
        
        for row in tbody.find_all('tr'):
            try:
                cells = row.find_all('td')
                if len(cells) < 5:  # 최소 5개 컬럼 필요
                    continue
                
                # 제목 링크 추출 (두 번째 컬럼)
                title_cell = cells[1]
                link_elem = title_cell.find('a')
                
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                href = link_elem.get('href', '')
                
                if not title or not href:
                    continue
                
                # 이미 절대 URL이므로 urljoin 불필요
                detail_url = href
                
                # 첨부파일 여부 확인 (세 번째 컬럼)
                attachment_cell = cells[2]
                has_attachment = bool(attachment_cell.find('img'))
                
                # 작성일 (네 번째 컬럼)
                date_text = cells[3].get_text(strip=True)
                
                # 조회수 (다섯 번째 컬럼)
                views_text = cells[4].get_text(strip=True)
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'date': date_text,
                    'views': views_text,
                    'has_attachment': has_attachment
                }
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱 완료: {title}")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str, url: str = None) -> Dict[str, Any]:
        """상세 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_detail_page(html_content, url)
        
        # Fallback: 그누보드 특화 로직
        return self._parse_detail_fallback(html_content, url)
    
    def _parse_detail_fallback(self, html_content: str, announcement_url: str = None) -> Dict[str, Any]:
        """그누보드 특화된 상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 제목 추출
        title = ""
        title_selectors = [
            '.ann_title',  # 공고 제목
            '.bd_tit',     # 게시판 제목
            '#bo_v_title', # 기본 제목
            'h1', 'h2'     # 일반 헤더
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = title_elem.get_text(strip=True)
                logger.debug(f"제목을 {selector} 선택자로 찾음")
                break
        
        # 본문 추출
        content = ""
        content_selectors = [
            '#bo_v_con',        # 그누보드 기본 본문
            '.bd_ann_wrap',     # 공고 래퍼
            '.ann_txt',         # 공고 텍스트
            '.bo_v_cont',       # 게시물 내용
            '#bo_v_cont'        # 게시물 내용 (ID)
        ]
        
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                content = content_area.get_text(strip=True)
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup)
        
        # 메타데이터 추출
        metadata = self._extract_metadata(soup)
        
        return {
            'title': title,
            'content': content,
            'attachments': attachments,
            'metadata': metadata,
            'url': announcement_url
        }
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """첨부파일 정보 추출"""
        attachments = []
        
        # 그누보드 첨부파일 영역
        file_area = soup.select_one('.bo_v_file')
        if not file_area:
            return attachments
        
        # 첨부파일 링크들
        for link in file_area.select('ul li a'):
            href = link.get('href', '')
            if not href:
                continue
            
            # 파일명 추출 (링크 텍스트에서)
            link_text = link.get_text(strip=True)
            
            # 파일명 정규식으로 추출 (파일 크기 정보 제거)
            filename_match = re.search(r'([^()]+?)(?:\s*\([^)]+\))?(?:\s*\d+회\s*다운로드)?(?:\s*DATE\s*:.*)?$', link_text)
            if filename_match:
                filename = filename_match.group(1).strip()
            else:
                filename = link_text
            
            # 파일 URL (이미 절대 URL)
            file_url = href
            
            attachments.append({
                'name': filename,
                'url': file_url
            })
            
            logger.debug(f"첨부파일 발견: {filename}")
        
        logger.info(f"{len(attachments)}개 첨부파일 발견")
        return attachments
    
    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, str]:
        """메타데이터 추출"""
        metadata = {}
        
        # 공고 번호
        ann_num = soup.select_one('.ann_num')
        if ann_num:
            metadata['announcement_number'] = ann_num.get_text(strip=True)
        
        # 작성일, 조회수 등 기타 정보
        info_area = soup.select_one('.bo_v_info')
        if info_area:
            metadata['board_info'] = info_area.get_text(strip=True)
        
        return metadata
    
    def download_file(self, url: str, save_path: str, attachment: Dict[str, Any] = None) -> bool:
        """파일 다운로드"""
        try:
            logger.info(f"파일 다운로드 시작: {url}")
            
            response = self.session.get(url, stream=True, verify=self.verify_ssl, timeout=self.timeout)
            response.raise_for_status()
            
            # 파일 크기 확인
            total_size = int(response.headers.get('content-length', 0))
            
            # 파일 저장
            with open(save_path, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
            
            file_size = os.path.getsize(save_path)
            logger.info(f"다운로드 완료: {save_path} ({file_size:,} bytes)")
            
            return True
            
        except Exception as e:
            logger.error(f"파일 다운로드 실패 {url}: {e}")
            return False

# 하위 호환성을 위한 별칭
DEBCScraper = EnhancedDEBCScraper

if __name__ == "__main__":
    # 간단한 테스트
    scraper = EnhancedDEBCScraper()
    output_dir = "output/debc"
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info("DEBC 스크래퍼 테스트 시작")
    scraper.scrape_pages(max_pages=1, output_base=output_dir)
    logger.info("DEBC 스크래퍼 테스트 완료")