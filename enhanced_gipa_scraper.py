# -*- coding: utf-8 -*-
"""
고양산업진흥원(GIPA) Enhanced 스크래퍼 - 표준 HTML 테이블 기반
"""

import requests
from bs4 import BeautifulSoup
import re
import logging
import os
from urllib.parse import urljoin, parse_qs, urlparse, unquote
from enhanced_base_scraper import StandardTableScraper
import time
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class EnhancedGIPAScraper(StandardTableScraper):
    """고양산업진흥원(GIPA) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        
        # 향상된 헤더 설정 (차단 방지)
        self.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.session.headers.update(self.headers)
        
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://www.gipa.or.kr"
        self.list_url = "https://www.gipa.or.kr/apply/01.php?cate=1"
        
        # 사이트 특화 설정
        self.verify_ssl = True  # HTTPS 사이트
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - GET 파라미터 방식"""
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&page={page_num}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - GIPA 사이트 특화"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # GIPA 사이트 테이블 구조 분석
        # 공고 목록이 board-list 클래스 테이블 형태로 되어 있음
        table = soup.find('table', class_='board-list')
        if not table:
            logger.warning("board-list 클래스를 가진 테이블을 찾을 수 없습니다")
            # 대체 방법으로 일반 테이블 찾기
            table = soup.find('table')
            if not table:
                logger.error("테이블을 찾을 수 없습니다")
                return announcements
        
        tbody = table.find('tbody')
        if not tbody:
            # tbody가 없는 경우 table에서 직접 tr 찾기
            tbody = table
        
        rows = tbody.find_all('tr')
        logger.info(f"GIPA 테이블에서 {len(rows)}개 행 발견")
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 3:  # 유형, 사업명, 접수일정, 버튼
                    continue
                
                # 사업명 셀에서 링크 찾기 (두 번째 셀)
                title_cell = cells[1]
                link_elem = title_cell.find('a')
                
                if not link_elem:
                    continue
                
                # 제목 추출 - strong 태그에서 추출
                strong_elem = link_elem.find('strong', class_='txt_t')
                if strong_elem:
                    title = strong_elem.get_text(strip=True)
                    # D-XX 부분 제거
                    title = re.sub(r'D-\d+\s*', '', title).strip()
                else:
                    title = link_elem.get_text(strip=True)
                
                if not title:
                    continue
                
                # URL 구성 - GIPA 특화: 상대 경로를 절대 경로로 변환
                href = link_elem.get('href', '')
                if href.startswith('01_view.php'):
                    detail_url = urljoin(self.base_url + '/apply/', href)
                else:
                    detail_url = urljoin(self.base_url, href)
                
                logger.debug(f"링크 생성: {href} -> {detail_url}")
                
                announcement = {
                    'title': title,
                    'url': detail_url
                }
                
                # 추가 메타 정보 추출
                self._extract_meta_info(cells, announcement)
                
                announcements.append(announcement)
                logger.debug(f"공고 추가: {title[:50]}...")
                
            except Exception as e:
                logger.error(f"GIPA 행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"GIPA에서 {len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def _extract_meta_info(self, cells: List, announcement: Dict[str, Any]) -> None:
        """메타 정보 추출 - GIPA 특화"""
        try:
            # 유형 정보 (첫 번째 셀)
            if len(cells) >= 1:
                type_info = cells[0].get_text(strip=True)
                announcement['type'] = type_info
            
            # 접수일정 정보 (세 번째 셀)  
            if len(cells) >= 3:
                schedule = cells[2].get_text(strip=True)
                announcement['schedule'] = schedule
            
            # 담당부서, 담당자, 전화번호 정보 추출 (두 번째 셀의 ul.info에서)
            title_cell = cells[1]
            info_ul = title_cell.find('ul', class_='info')
            if info_ul:
                info_items = info_ul.find_all('li')
                for item in info_items:
                    text = item.get_text(strip=True)
                    if '담당부서' in text:
                        announcement['department'] = text.replace('담당부서', '').strip()
                    elif '담당자' in text:
                        announcement['manager'] = text.replace('담당자', '').strip()
                    elif '전화번호' in text:
                        announcement['phone'] = text.replace('전화번호', '').strip()
            
        except Exception as e:
            logger.debug(f"GIPA 메타 정보 추출 중 오류: {e}")
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱 - GIPA 특화"""
        soup = BeautifulSoup(html_content, 'html.parser')
        result = {
            'content': '',
            'attachments': []
        }
        
        try:
            # 본문 추출 - board_content 클래스에서 본문 찾기
            content_area = soup.select_one('.board_content')
            if not content_area:
                # 대체 선택자들 시도
                content_area = soup.select_one('.view_content') or soup.select_one('.content')
            
            if content_area:
                # 본문을 markdown으로 변환
                content_text = self.h.handle(str(content_area))
                result['content'] = content_text
                logger.debug(f"본문을 .board_content 선택자로 찾음")
            else:
                logger.warning("본문 영역을 찾을 수 없습니다")
                result['content'] = "본문을 찾을 수 없습니다."
            
            # 첨부파일 추출
            result['attachments'] = self._extract_attachments(soup)
            
        except Exception as e:
            logger.error(f"GIPA 상세 페이지 파싱 중 오류: {e}")
            result['content'] = f"파싱 오류: {str(e)}"
        
        return result
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """첨부파일 추출 - GIPA 특화"""
        attachments = []
        
        try:
            # GIPA 사이트의 첨부파일 패턴: ../lib/download.php?file_name=...&save_file=...
            file_links = soup.find_all('a', class_='down_file')
            
            for link in file_links:
                href = link.get('href', '')
                if 'download.php' in href:
                    # 파일명 추출
                    span_elem = link.find('span')
                    if span_elem:
                        filename = span_elem.get_text(strip=True)
                    else:
                        filename = link.get_text(strip=True)
                    
                    # 상대 URL을 절대 URL로 변환
                    download_url = urljoin(self.base_url, href)
                    
                    attachments.append({
                        'name': filename,
                        'url': download_url
                    })
                    logger.debug(f"첨부파일 발견: {filename}")
            
            if attachments:
                logger.info(f"GIPA에서 {len(attachments)}개 첨부파일 발견")
            else:
                logger.debug("첨부파일이 없습니다")
            
        except Exception as e:
            logger.error(f"GIPA 첨부파일 추출 중 오류: {e}")
        
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment_info: Dict[str, Any] = None) -> bool:
        """파일 다운로드 - GIPA 특화"""
        try:
            response = self.session.get(url, stream=True, verify=self.verify_ssl)
            response.raise_for_status()
            
            # 디렉토리 생성
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # 파일 다운로드
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(save_path)
            logger.info(f"다운로드 완료: {save_path} ({file_size:,} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"GIPA 파일 다운로드 실패 {url}: {e}")
            return False

# 하위 호환성을 위한 별칭
GIPAScraper = EnhancedGIPAScraper