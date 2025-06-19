# -*- coding: utf-8 -*-
"""
Enhanced PTP Scraper - 포항테크노파크
URL: https://www.ptp.or.kr/main/board/index.do?menu_idx=113&manage_idx=2
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import logging
import os
from urllib.parse import urljoin, unquote, parse_qs, urlparse
from typing import List, Dict, Any
from enhanced_base_scraper import StandardTableScraper

logger = logging.getLogger(__name__)

class EnhancedPtpScraper(StandardTableScraper):
    """PTP 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        
        # 기본 설정
        self.base_url = "https://www.ptp.or.kr"
        self.list_url = "https://www.ptp.or.kr/main/board/index.do?menu_idx=113&manage_idx=2"
        
        # 사이트별 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        
        # 기본 파라미터
        self.base_params = {
            'menu_idx': '113',
            'manage_idx': '2'
        }
        
        logger.info("Enhanced PTP 스크래퍼 초기화 완료")
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - GET 파라미터 방식"""
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: GET 파라미터 방식
        params = self.base_params.copy()
        if page_num > 1:
            params['viewPage'] = str(page_num)
        
        param_str = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{self.base_url}/main/board/index.do?{param_str}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱"""
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: 사이트 특화 파싱
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """PTP 사이트 특화 목록 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 테이블 찾기
        table = None
        for selector in ['table.table-list', 'table', '.board-list']:
            table = soup.select_one(selector)
            if table:
                logger.debug(f"테이블을 {selector} 선택자로 찾음")
                break
        
        if not table:
            logger.warning("테이블을 찾을 수 없습니다")
            return announcements
        
        # 행들 찾기
        rows = table.find_all('tr')
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 3:  # 최소 3개 열 필요
                    continue
                
                # 제목 링크 찾기 - JavaScript onclick 패턴
                title_cell = None
                link_elem = None
                
                for cell in cells:
                    link_elem = cell.find('a')
                    if link_elem and 'onclick' in link_elem.attrs:
                        title_cell = cell
                        break
                
                if not link_elem:
                    continue
                
                # 제목 추출
                title_span = link_elem.find('span')
                title = title_span.get_text(strip=True) if title_span else link_elem.get_text(strip=True)
                if not title or title.isspace():
                    continue
                
                # JavaScript onclick에서 board_idx 추출
                onclick = link_elem.get('onclick', '')
                board_idx = None
                
                # viewBoard(7245) 패턴 분석
                if 'viewBoard' in onclick:
                    match = re.search(r'viewBoard\((\d+)\)', onclick)
                    if match:
                        board_idx = match.group(1)
                        # GET 요청을 위한 URL 형식 사용
                        detail_url = f"{self.base_url}/main/board/view.do?menu_idx=113&manage_idx=2&board_idx={board_idx}"
                        logger.debug(f"JavaScript 링크 분석: board_idx={board_idx}")
                    else:
                        logger.warning(f"viewBoard 함수에서 board_idx를 찾을 수 없습니다: {onclick}")
                        continue
                else:
                    logger.warning(f"viewBoard 함수를 찾을 수 없습니다: {onclick}")
                    continue
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'board_idx': board_idx
                }
                
                # 추가 정보 추출
                if len(cells) >= 2:
                    # 구분 (일반적으로 두 번째 열)
                    category_text = cells[1].get_text(strip=True)
                    if category_text:
                        announcement['category'] = category_text
                
                if len(cells) >= 4:
                    # 작성자 (네 번째 열)
                    writer_text = cells[3].get_text(strip=True)
                    if writer_text:
                        announcement['writer'] = writer_text
                
                if len(cells) >= 5:
                    # 작성일 (다섯 번째 열)
                    date_text = cells[4].get_text(strip=True)
                    if date_text and re.match(r'\d{4}-\d{2}-\d{2}', date_text):
                        announcement['date'] = date_text
                
                # 첨부파일 여부 확인 (파일 열)
                if len(cells) >= 4:
                    file_cell = cells[2]  # 파일 열
                    if file_cell.find('img') or '파일' in file_cell.get_text():
                        announcement['has_attachment'] = True
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱 완료: {title}")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 내용 추출
        content = self._extract_content(soup)
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup)
        
        return {
            'content': content,
            'attachments': attachments
        }
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """본문 내용 추출"""
        # 다양한 선택자 시도
        content_selectors = [
            '.board-view-content',
            '.content',
            '.view-content',
            '.board-content',
            '.detail-content',
            '#content'
        ]
        
        content_area = None
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        if not content_area:
            # 클래스 없는 테이블이나 div에서 본문 찾기
            possible_areas = soup.find_all(['div', 'td'])
            for area in possible_areas:
                text_content = area.get_text(strip=True)
                if len(text_content) > 200:  # 충분한 길이의 텍스트가 있는 경우
                    content_area = area
                    logger.debug("길이 기반으로 본문 영역 추정")
                    break
        
        if not content_area:
            logger.warning("본문 영역을 찾을 수 없습니다")
            return "본문을 추출할 수 없습니다."
        
        # HTML을 마크다운으로 변환
        try:
            content_markdown = self.h.handle(str(content_area))
            return content_markdown.strip()
        except Exception as e:
            logger.error(f"마크다운 변환 실패: {e}")
            return content_area.get_text(separator='\n', strip=True)
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """첨부파일 추출 - PTP 사이트 특화"""
        attachments = []
        
        # PTP 사이트는 .board-view-attach 클래스에 첨부파일이 있음
        attachment_area = soup.find('div', class_='board-view-attach')
        
        if attachment_area:
            logger.debug("board-view-attach 영역 발견")
            # 첨부파일 링크들 추출
            file_links = attachment_area.find_all('a')
            
            for link in file_links:
                try:
                    href = link.get('href', '')
                    link_text = link.get_text(strip=True)
                    
                    # PTP 사이트의 첨부파일 패턴: /board/boardFile/download/2/7245/12927.do
                    if href and '/board/boardFile/download/' in href:
                        file_url = urljoin(self.base_url, href)
                        
                        # 링크 텍스트에서 파일명과 크기 정보 추출
                        # 예: "[대구TP] 2025년 3차 과학기술분야RnD 대체인력 모집공고 웹포스터.png(582.0KB)"
                        if '(' in link_text and ')' in link_text:
                            # 파일 크기 정보 제거하여 순수 파일명만 추출
                            file_name = link_text.rsplit('(', 1)[0].strip()
                        else:
                            file_name = link_text
                        
                        # 파일명이 비어있거나 너무 짧으면 URL에서 추출
                        if not file_name or len(file_name) < 3:
                            file_name = href.split('/')[-1]
                        
                        attachment = {
                            'name': file_name,
                            'url': file_url
                        }
                        
                        attachments.append(attachment)
                        logger.debug(f"PTP 첨부파일 발견: {file_name} -> {file_url}")
                        
                except Exception as e:
                    logger.error(f"첨부파일 링크 처리 오류: {e}")
                    continue
        else:
            logger.debug("board-view-attach 영역을 찾을 수 없음, 일반 패턴으로 시도")
            
            # 일반적인 첨부파일 패턴도 시도
            file_links = soup.find_all('a', href=re.compile(r'/board/boardFile/download/'))
            
            for link in file_links:
                try:
                    href = link.get('href', '')
                    link_text = link.get_text(strip=True)
                    
                    if href:
                        file_url = urljoin(self.base_url, href)
                        
                        # 파일명 추출
                        if '(' in link_text and ')' in link_text:
                            file_name = link_text.rsplit('(', 1)[0].strip()
                        else:
                            file_name = link_text or href.split('/')[-1]
                        
                        attachment = {
                            'name': file_name,
                            'url': file_url
                        }
                        
                        attachments.append(attachment)
                        logger.debug(f"일반 패턴 첨부파일 발견: {file_name} -> {file_url}")
                        
                except Exception as e:
                    logger.error(f"일반 패턴 첨부파일 처리 오류: {e}")
                    continue
        
        # 중복 제거
        unique_attachments = []
        seen_urls = set()
        for att in attachments:
            if att['url'] not in seen_urls:
                unique_attachments.append(att)
                seen_urls.add(att['url'])
        
        logger.info(f"{len(unique_attachments)}개 첨부파일 발견")
        return unique_attachments
    
    def process_announcement(self, announcement, index: int, output_base: str = 'output'):
        """PTP 사이트 특화 공고 처리 - GET 요청"""
        logger.info(f"공고 처리 중 {index}: {announcement['title']}")
        
        # 폴더 생성
        folder_title = self.sanitize_filename(announcement['title'])[:200]
        folder_name = f"{index:03d}_{folder_title}"
        folder_path = os.path.join(output_base, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        # GET 요청으로 상세 페이지 가져오기
        url = announcement['url']
        response = self.get_page(url)
        
        if response:
            logger.info(f"GET 요청 성공: {url}")
        else:
            logger.error(f"GET 요청 실패: {url}")
        
        if not response:
            logger.error(f"상세 페이지 가져오기 실패: {announcement['title']}")
            return
        
        # 상세 내용 파싱
        try:
            detail = self.parse_detail_page(response.text)
            logger.info(f"상세 페이지 파싱 완료 - 내용길이: {len(detail['content'])}, 첨부파일: {len(detail['attachments'])}")
        except Exception as e:
            logger.error(f"상세 페이지 파싱 실패: {e}")
            return
        
        # 메타 정보 생성
        meta_info = self._create_meta_info(announcement)
        
        # 본문 저장
        content_path = os.path.join(folder_path, 'content.md')
        with open(content_path, 'w', encoding='utf-8') as f:
            f.write(meta_info + detail['content'])
        
        logger.info(f"내용 저장 완료: {content_path}")
        
        # 첨부파일 다운로드
        self._download_attachments(detail['attachments'], folder_path)
        
        # 처리된 제목으로 추가
        self.add_processed_title(announcement['title'])
        
        # 요청 간 대기
        if self.delay_between_requests > 0:
            time.sleep(self.delay_between_requests)


# 하위 호환성을 위한 별칭
PtpScraper = EnhancedPtpScraper