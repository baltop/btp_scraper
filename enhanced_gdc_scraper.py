# -*- coding: utf-8 -*-
"""
광주디자인진흥원(GDC) 스크래퍼 - 향상된 버전
URL: https://www.gdc.or.kr/board.do?S=S01&M=0401000000&b_code=0001
"""

from enhanced_base_scraper import StandardTableScraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin, parse_qs, urlparse
import requests
import re
import os
import time
import logging

logger = logging.getLogger(__name__)

class EnhancedGdcScraper(StandardTableScraper):
    """광주디자인진흥원 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 기본 설정
        self.base_url = "https://www.gdc.or.kr"
        self.list_url = "https://www.gdc.or.kr/board.do?S=S01&M=0401000000&b_code=0001"
        
        # 사이트별 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 2
        
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성"""
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: GDC 특화 URL 패턴
        return f"{self.list_url}&nPage={page_num}"
    
    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱"""
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: GDC 특화 파싱
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> list:
        """GDC 특화된 목록 파싱 로직"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # bo_table 클래스를 가진 테이블 찾기
        table = soup.find('table', class_='bo_table')
        if not table:
            logger.warning("bo_table 클래스를 가진 테이블을 찾을 수 없습니다")
            return []
        
        tbody = table.find('tbody')
        if not tbody:
            tbody = table
        
        logger.info(f"테이블에서 {len(tbody.find_all('tr'))}개 행 발견")
        
        for row in tbody.find_all('tr'):
            try:
                cells = row.find_all('td')
                if len(cells) < 6:  # 번호, 카테고리, 제목, 첨부, 등록일, 조회수
                    continue
                
                # 제목과 링크 추출 (3번째 셀)
                title_cell = cells[2]
                link_elem = title_cell.find('a')
                
                if link_elem:
                    title = link_elem.get_text(strip=True)
                    href = link_elem.get('href', '')
                    
                    if href:
                        detail_url = urljoin(self.base_url, href)
                        
                        # 카테고리 (2번째 셀)
                        category = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                        
                        # 첨부파일 여부 (4번째 셀)
                        file_cell = cells[3]
                        has_attachment = bool(file_cell.find('img'))
                        
                        # 등록일 (5번째 셀)
                        date = cells[4].get_text(strip=True) if len(cells) > 4 else ""
                        
                        announcement = {
                            'title': title,
                            'url': detail_url,
                            'category': category,
                            'date': date,
                            'has_attachment': has_attachment
                        }
                        announcements.append(announcement)
                        logger.debug(f"공고 파싱됨: {title}")
                        
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str, url: str = None) -> dict:
        """상세 페이지 파싱"""
        if self.config and self.config.selectors:
            return super().parse_detail_page(html_content)
        
        # Fallback: GDC 특화 파싱
        return self._parse_detail_fallback(html_content, url)
    
    def _parse_detail_fallback(self, html_content: str, detail_url: str = None) -> dict:
        """GDC 특화된 상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 제목 추출
        title_elem = soup.find('h3', class_='h4')
        title = title_elem.get_text(strip=True) if title_elem else "제목 없음"
        
        # 본문 내용 추출 (bo_v_body 클래스)
        content_elem = soup.find('div', class_='bo_v_body')
        content = ""
        
        if content_elem:
            # HTML을 마크다운으로 변환
            content = self.h.handle(str(content_elem))
            logger.debug("본문을 bo_v_body 선택자로 찾음")
        else:
            # 대체 선택자들 시도
            for selector in ['.board_view', '.view_content', '.bo_v_con']:
                content_elem = soup.select_one(selector)
                if content_elem:
                    content = self.h.handle(str(content_elem))
                    logger.debug(f"본문을 {selector} 선택자로 찾음")
                    break
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup)
        
        return {
            'title': title,
            'content': content,
            'attachments': attachments,
            'url': detail_url or ""
        }
    
    def _extract_attachments(self, soup: BeautifulSoup) -> list:
        """첨부파일 정보 추출"""
        attachments = []
        
        # filelist 클래스에서 첨부파일 링크 찾기
        filelist = soup.find('div', class_='filelist')
        if not filelist:
            return []
        
        # 다운로드 링크들 찾기
        for link in filelist.find_all('a', href=re.compile(r'/fileDownload\.do')):
            href = link.get('href', '')
            if href:
                # 파일명 추출 (링크 텍스트에서)
                text_content = link.get_text(strip=True)
                # 파일명만 추출 (용량 정보 제외)
                filename_match = re.search(r'([^\s]+\.(pdf|hwp|doc|docx|xls|xlsx|ppt|pptx|jpg|jpeg|png|gif|zip|rar))', text_content, re.IGNORECASE)
                filename = filename_match.group(1) if filename_match else "첨부파일"
                
                # 전체 URL 생성
                download_url = urljoin(self.base_url, href)
                
                attachments.append({
                    'name': filename,  # 베이스 스크래퍼에서 'name' 키를 사용
                    'filename': filename,
                    'url': download_url
                })
                logger.debug(f"첨부파일 발견: {filename}")
        
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment_info: dict = None) -> bool:
        """파일 다운로드"""
        try:
            logger.info(f"파일 다운로드 시작: {url}")
            
            response = self.session.get(url, timeout=self.timeout, verify=self.verify_ssl)
            response.raise_for_status()
            
            # 디렉토리 생성
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # 파일 저장
            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            file_size = len(response.content)
            logger.info(f"다운로드 완료: {save_path} ({file_size:,} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"파일 다운로드 실패 {url}: {e}")
            return False

# 하위 호환성을 위한 별칭
GdcScraper = EnhancedGdcScraper