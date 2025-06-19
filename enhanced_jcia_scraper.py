# -*- coding: utf-8 -*-
"""
Enhanced JCIA Scraper - 전남정보문화산업진흥원
URL: https://jcia.or.kr/cf/information/notice/business.do
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import logging
import os
from urllib.parse import urljoin, unquote, parse_qs, urlparse
from typing import List, Dict, Any
from playwright.sync_api import sync_playwright
from enhanced_base_scraper import StandardTableScraper

logger = logging.getLogger(__name__)

class EnhancedJciaScraper(StandardTableScraper):
    """JCIA 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        
        # 기본 설정
        self.base_url = "https://jcia.or.kr"
        self.list_url = "https://jcia.or.kr/cf/information/notice/business.do"
        
        # 사이트별 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 0.5  # 요청 간격 단축
        self.use_playwright = True  # JavaScript 렌더링 필요
        
        logger.info("Enhanced JCIA 스크래퍼 초기화 완료")
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - pageIndex 파라미터 방식"""
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: pageIndex 파라미터 방식
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}?pageIndex={page_num}"
    
    def get_page_with_playwright(self, url: str) -> str:
        """Playwright를 사용한 페이지 가져오기"""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # User-Agent 설정
                page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                
                page.goto(url, timeout=30000)  # 30초 timeout
                page.wait_for_timeout(1000)  # 동적 콘텐츠 로딩 대기 (1초로 단축)
                
                # 목록 페이지인 경우에만 테이블 대기
                if 'business.do' in url:
                    # 테이블이 로드될 때까지 대기
                    page.wait_for_selector('table.tbl_Board_01', timeout=15000)
                
                content = page.content()
                browser.close()
                
                return content
                
        except Exception as e:
            logger.error(f"Playwright 페이지 가져오기 실패 {url}: {e}")
            return None
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱"""
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: 사이트 특화 파싱
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """JCIA 사이트 특화 목록 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 테이블 찾기
        table = soup.find('table', class_='tbl_Board_01')
        if not table:
            logger.warning("tbl_Board_01 클래스를 가진 테이블을 찾을 수 없습니다")
            return announcements
        
        tbody = table.find('tbody')
        if not tbody:
            logger.warning("tbody를 찾을 수 없습니다")
            return announcements
        
        # 행들 찾기
        rows = tbody.find_all('tr')
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 6:  # 최소 6개 열 필요 (No, 공고번호, 제목, 진행상태, 담당자, 등록일, 조회수)
                    continue
                
                # 제목 링크 찾기 - 세 번째 열 (제목)
                title_cell = cells[2]
                link_elem = title_cell.find('a')
                
                if not link_elem:
                    continue
                
                # 제목 추출
                title = link_elem.get_text(strip=True)
                if not title or title.isspace():
                    continue
                
                # JavaScript onclick에서 ID 추출
                onclick = link_elem.get('onclick', '')
                board_id = None
                
                # pf_DetailMove('8875') 패턴 분석
                if 'pf_DetailMove' in onclick:
                    match = re.search(r"pf_DetailMove\(['\"]?([^'\"]+)['\"]?\)", onclick)
                    if match:
                        board_id = match.group(1)
                        # 상세 페이지 URL 구성
                        detail_url = f"{self.base_url}/cf/Board/{board_id}/detailView.do"
                        logger.debug(f"JavaScript 링크 분석: board_id={board_id}")
                    else:
                        logger.warning(f"pf_DetailMove 함수에서 board_id를 찾을 수 없습니다: {onclick}")
                        continue
                else:
                    logger.warning(f"pf_DetailMove 함수를 찾을 수 없습니다: {onclick}")
                    continue
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'board_id': board_id
                }
                
                # 추가 정보 추출
                # 공고번호 (두 번째 열)
                if len(cells) >= 2:
                    notice_num = cells[1].get_text(strip=True)
                    if notice_num:
                        announcement['notice_number'] = notice_num
                
                # 진행상태 (네 번째 열)
                if len(cells) >= 4:
                    status_text = cells[3].get_text(strip=True)
                    if status_text:
                        announcement['status'] = status_text
                
                # 담당자 (다섯 번째 열)
                if len(cells) >= 5:
                    manager_text = cells[4].get_text(strip=True)
                    if manager_text:
                        announcement['manager'] = manager_text
                
                # 등록일 (여섯 번째 열)
                if len(cells) >= 6:
                    date_text = cells[5].get_text(strip=True)
                    if date_text and re.match(r'\d{4}-\d{2}-\d{2}', date_text):
                        announcement['date'] = date_text
                
                # 조회수 (일곱 번째 열)
                if len(cells) >= 7:
                    view_text = cells[6].get_text(strip=True)
                    if view_text and view_text.isdigit():
                        announcement['views'] = view_text
                
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
            '.board_view_contents',
            '.view_contents',
            '.board_content',
            '.detail_content',
            '.content_area',
            '.view_area'
        ]
        
        content_area = None
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        if not content_area:
            # 클래스 없는 div나 테이블에서 본문 찾기
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
            return content_area.get_text(separator='\\n', strip=True)
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """첨부파일 추출 - JCIA 사이트 특화"""
        attachments = []
        
        # JCIA 사이트는 cf_download('FS_0000013725') 형태의 JavaScript 함수 사용
        download_links = soup.find_all('a', onclick=re.compile(r'cf_download', re.I))
        
        logger.debug(f"cf_download 패턴 링크 {len(download_links)}개 발견")
        
        for link in download_links:
            try:
                onclick = link.get('onclick', '')
                link_text = link.get_text(strip=True)
                
                # cf_download('FS_0000013725') 패턴에서 파일 ID 추출
                if 'cf_download' in onclick:
                    match = re.search(r"cf_download\(['\"]([^'\"]+)['\"]?\)", onclick)
                    if match:
                        file_id = match.group(1)
                        
                        # 링크 텍스트에서 파일명 추출
                        # 예: "[붙임1] 제안서 평가위원회 후보자 모집공고.hwp (123KB)"
                        file_name = link_text
                        
                        # 파일 크기 정보 제거
                        if '(' in file_name and ')' in file_name:
                            # 마지막 괄호 제거 (파일 크기)
                            file_name = file_name.rsplit('(', 1)[0].strip()
                        
                        # 파일명이 비어있으면 기본값 사용
                        if not file_name or len(file_name) < 3:
                            file_name = f"attachment_{file_id}"
                        
                        # JCIA 실제 다운로드 URL 구성
                        file_url = f"{self.base_url}/async/MultiFile/download.do?FS_KEYNO={file_id}"
                        
                        attachment = {
                            'name': file_name,
                            'url': file_url,
                            'file_id': file_id
                        }
                        
                        attachments.append(attachment)
                        logger.debug(f"JCIA 첨부파일 발견: {file_name} -> {file_url}")
                    else:
                        logger.warning(f"cf_download 함수에서 파일 ID를 찾을 수 없습니다: {onclick}")
                
            except Exception as e:
                logger.error(f"첨부파일 링크 처리 오류: {e}")
                continue
        
        # 추가로 일반적인 다운로드 패턴도 확인
        general_download_links = soup.find_all('a', onclick=re.compile(r'download|fileDown', re.I))
        
        for link in general_download_links:
            try:
                onclick = link.get('onclick', '')
                link_text = link.get_text(strip=True)
                
                # 이미 처리된 cf_download 제외
                if 'cf_download' in onclick:
                    continue
                
                # 다른 다운로드 패턴 처리
                if 'download' in onclick.lower() or 'filedown' in onclick.lower():
                    # 다양한 패턴 시도
                    patterns = [
                        r"download\(['\"]([^'\"]+)['\"]?\)",
                        r"fileDown\(['\"]([^'\"]+)['\"]?\)",
                        r"downloadFile\(['\"]([^'\"]+)['\"]?\)"
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, onclick)
                        if match:
                            file_id = match.group(1)
                            file_name = link_text or f"attachment_{file_id}"
                            
                            # 파일 크기 정보 제거
                            if '(' in file_name and ')' in file_name:
                                file_name = file_name.rsplit('(', 1)[0].strip()
                            
                            file_url = f"{self.base_url}/common/fileDown.do?file_idx={file_id}"
                            
                            attachment = {
                                'name': file_name,
                                'url': file_url,
                                'file_id': file_id
                            }
                            
                            attachments.append(attachment)
                            logger.debug(f"일반 다운로드 첨부파일 발견: {file_name} -> {file_url}")
                            break
                
            except Exception as e:
                logger.error(f"일반 다운로드 링크 처리 오류: {e}")
                continue
        
        # 중복 제거
        unique_attachments = []
        seen_urls = set()
        seen_file_ids = set()
        
        for att in attachments:
            file_id = att.get('file_id', '')
            if att['url'] not in seen_urls and file_id not in seen_file_ids:
                unique_attachments.append(att)
                seen_urls.add(att['url'])
                if file_id:
                    seen_file_ids.add(file_id)
        
        logger.info(f"{len(unique_attachments)}개 첨부파일 발견")
        return unique_attachments
    
    def get_page(self, url: str):
        """페이지 가져오기 - Playwright 사용"""
        if self.use_playwright:
            html_content = self.get_page_with_playwright(url)
            if html_content:
                # Response 객체처럼 동작하는 간단한 클래스 생성
                class MockResponse:
                    def __init__(self, text):
                        self.text = text
                        self.status_code = 200
                
                return MockResponse(html_content)
        
        # Fallback to requests
        return super().get_page(url)
    
    def process_announcement(self, announcement, index: int, output_base: str = 'output'):
        """JCIA 사이트 특화 공고 처리"""
        logger.info(f"공고 처리 중 {index}: {announcement['title']}")
        
        # 폴더 생성
        folder_title = self.sanitize_filename(announcement['title'])[:200]
        folder_name = f"{index:03d}_{folder_title}"
        folder_path = os.path.join(output_base, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        # 상세 페이지 가져오기
        url = announcement['url']
        response = self.get_page(url)
        
        if response and hasattr(response, 'text'):
            logger.info(f"상세 페이지 가져오기 성공: {url}")
        else:
            logger.error(f"상세 페이지 가져오기 실패: {url}")
        
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
JciaScraper = EnhancedJciaScraper