# -*- coding: utf-8 -*-
"""
한국방송통신전파진흥원(KCA) Enhanced 스크래퍼
사이트: https://www.kca.kr/boardList.do?boardId=NOTICE&pageId=www47
"""

import requests
from bs4 import BeautifulSoup
import os
import time
import html2text
from urllib.parse import urljoin, parse_qs, urlparse
import re
import json
import logging
from enhanced_base_scraper import StandardTableScraper
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class EnhancedKCAScraper(StandardTableScraper):
    """한국방송통신전파진흥원(KCA) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://www.kca.kr"
        self.list_url = "https://www.kca.kr/boardList.do?boardId=NOTICE&pageId=www47"
        
        # 사이트 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        
        # 헤더 설정
        self.headers.update({
            'Referer': self.base_url,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        self.session.headers.update(self.headers)
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - 설정 주입과 Fallback 패턴"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: KCA 특화 로직
        if page_num == 1:
            return self.list_url
        else:
            # movePage 파라미터로 페이지네이션
            return f"{self.list_url}&movePage={page_num}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: KCA 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """KCA 사이트 특화된 파싱 로직"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        logger.info("KCA 목록 페이지 파싱 시작")
        
        # KCA의 게시판 구조는 일반적인 테이블 형태
        # boardView.do 링크를 찾아서 공고 목록 추출
        
        # 먼저 전체 게시글 수 확인
        total_info = soup.find(string=re.compile(r'전체게시글\s*:\s*\d+'))
        if total_info:
            logger.info(f"페이지 정보: {total_info.strip()}")
        
        # 테이블 행들 찾기 - 실제 공고 데이터가 있는 행들
        rows = soup.find_all('div', class_=lambda x: x and 'boardListItem' in str(x)) or \
               soup.find_all('li', class_=lambda x: x and 'item' in str(x)) or \
               soup.select('div[class*="row"], tr')
        
        # boardView.do 링크가 있는 요소들을 직접 찾기
        board_links = soup.find_all('a', href=lambda x: x and 'boardView.do' in x)
        
        if board_links:
            for link in board_links:
                try:
                    # 제목 추출
                    title = link.get_text(strip=True)
                    if not title or len(title) < 5:
                        continue
                    
                    # URL 구성
                    href = link.get('href')
                    detail_url = urljoin(self.base_url, href)
                    
                    # URL에서 seq 파라미터 추출 (게시글 번호)
                    parsed_url = urlparse(href)
                    query_params = parse_qs(parsed_url.query)
                    seq = query_params.get('seq', [''])[0]
                    move_page = query_params.get('movePage', ['1'])[0]
                    
                    # 부모 요소들에서 추가 정보 추출
                    parent = link.parent
                    root_parent = self._find_list_item_root(link)
                    
                    # 분류, 작성자, 작성일, 조회수 등 메타 정보 추출
                    category = self._extract_category(root_parent)
                    writer = self._extract_writer(root_parent)
                    date = self._extract_date(root_parent)
                    views = self._extract_views(root_parent)
                    number = self._extract_number(root_parent)
                    has_file = self._extract_file_info(root_parent)
                    
                    announcement = {
                        'title': title,
                        'url': detail_url,
                        'category': category,
                        'writer': writer,
                        'date': date,
                        'views': views,
                        'number': number,
                        'has_file': has_file,
                        'seq': seq,
                        'move_page': move_page
                    }
                    
                    announcements.append(announcement)
                    logger.debug(f"공고 파싱: {title[:50]}... - 번호: {number}")
                    
                except Exception as e:
                    logger.error(f"공고 링크 파싱 중 오류: {e}")
                    continue
        
        logger.info(f"KCA 목록에서 {len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def _find_list_item_root(self, element) -> BeautifulSoup:
        """링크 요소에서 목록 아이템의 루트 요소 찾기"""
        current = element
        depth = 0
        
        while current and current.parent and depth < 10:
            # div나 li 태그이면서 형제가 여러 개 있는 경우 (목록 아이템일 가능성)
            if current.name in ['div', 'li', 'tr']:
                siblings = current.find_next_siblings() + current.find_previous_siblings()
                if len(siblings) > 0:
                    return current
            
            current = current.parent
            depth += 1
        
        return element.parent if element.parent else element
    
    def _extract_category(self, root_element) -> str:
        """분류 정보 추출"""
        if not root_element:
            return ""
        
        # 일반적인 분류 패턴들
        category_patterns = [
            '방송통신진흥', '빛마루방송지원센터', '전파진흥', '전파검사', 
            '기술자격', 'ICT기금관리', '공통'
        ]
        
        text = root_element.get_text()
        for pattern in category_patterns:
            if pattern in text:
                return pattern
        
        return ""
    
    def _extract_writer(self, root_element) -> str:
        """작성자 정보 추출"""
        if not root_element:
            return ""
        
        text = root_element.get_text()
        
        # 팀명이 포함된 패턴 찾기
        writer_patterns = [
            r'([가-힣]+팀)', r'([가-힣]+센터)', r'([가-힣]+부서)', r'([가-힣]+과)'
        ]
        
        for pattern in writer_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return ""
    
    def _extract_date(self, root_element) -> str:
        """작성일 추출"""
        if not root_element:
            return ""
        
        text = root_element.get_text()
        
        # 날짜 패턴 찾기 (YYYY-MM-DD 형식)
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
        if date_match:
            return date_match.group(1)
        
        return ""
    
    def _extract_views(self, root_element) -> str:
        """조회수 추출"""
        if not root_element:
            return ""
        
        text = root_element.get_text()
        
        # 숫자만 있는 패턴 (조회수일 가능성)
        numbers = re.findall(r'\b(\d{1,6})\b', text)
        
        # 가장 마지막 숫자가 조회수일 가능성이 높음
        if numbers:
            # 4자리 이하의 숫자 중 가장 마지막 것
            for num in reversed(numbers):
                if len(num) <= 6 and int(num) > 0:
                    return num
        
        return ""
    
    def _extract_number(self, root_element) -> str:
        """게시글 번호 추출"""
        if not root_element:
            return ""
        
        text = root_element.get_text()
        
        # 게시글 번호 패턴 (보통 4자리 숫자)
        number_match = re.search(r'\b(\d{4})\b', text)
        if number_match:
            return number_match.group(1)
        
        return ""
    
    def _extract_file_info(self, root_element) -> bool:
        """첨부파일 존재 여부 확인"""
        if not root_element:
            return False
        
        # 파일 아이콘이나 첨부파일 관련 요소 찾기
        file_elements = root_element.find_all(['img', 'span'], class_=lambda x: x and 'file' in str(x).lower())
        
        # fileDownload.do 링크가 있는지 확인
        file_links = root_element.find_all('a', href=lambda x: x and 'fileDownload.do' in x)
        
        return len(file_elements) > 0 or len(file_links) > 0
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 내용 추출 - 여러 선택자 시도
        content = ""
        content_selectors = [
            'div[class*="boardContent"]',
            'div[class*="content"]',
            'div[class*="view"]',
            '.board_view',
            '.view_content',
            'div.text'
        ]
        
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                # 네비게이션, 버튼 등 제거
                for unwanted in content_area.find_all(['script', 'style', 'button', 'nav']):
                    unwanted.decompose()
                
                # HTML을 마크다운으로 변환
                content = self.h.handle(str(content_area))
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        # 기본 추출에 실패한 경우 본문이 있을만한 div 찾기
        if not content or len(content.strip()) < 100:
            logger.warning("본문 추출에 실패했습니다. 대체 방법을 시도합니다.")
            
            # 텍스트가 많은 div 찾기
            all_divs = soup.find_all('div')
            best_div = None
            max_text_length = 0
            
            for div in all_divs:
                div_text = div.get_text(strip=True)
                if len(div_text) > max_text_length and len(div_text) > 100:
                    # 네비게이션이나 메뉴가 아닌지 확인
                    if not any(keyword in div_text.lower() for keyword in ['menu', 'nav', 'footer', 'header', 'login']):
                        max_text_length = len(div_text)
                        best_div = div
            
            if best_div:
                content = self.h.handle(str(best_div))
                logger.info(f"대체 방법으로 본문 추출 완료 (길이: {len(content)})")
        
        # 첨부파일 정보 추출
        attachments = self._extract_attachments(soup)
        
        logger.info(f"상세 페이지 파싱 완료 - 내용길이: {len(content)}, 첨부파일: {len(attachments)}개")
        
        return {
            'content': content,
            'attachments': attachments
        }
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """첨부파일 정보 추출"""
        attachments = []
        
        # KCA의 첨부파일 다운로드 링크 패턴: /fileDownload.do?action=fileDown&...
        file_links = soup.find_all('a', href=lambda x: x and 'fileDownload.do' in x)
        
        for link in file_links:
            try:
                href = link.get('href', '')
                if not href:
                    continue
                
                # 파일명 추출
                name = link.get_text(strip=True)
                
                # 압축 다운로드 링크 제외 (개별 파일만)
                if 'zipFileDown' in href:
                    continue
                
                # 파일명이 없으면 스킵
                if not name or len(name) < 3:
                    continue
                
                # 파일 URL 구성
                file_url = urljoin(self.base_url, href)
                
                # 파일 크기 정보 추출 (있는 경우)
                size_info = ""
                download_count = ""
                
                # 부모 요소에서 파일 정보 찾기
                parent = link.parent
                if parent:
                    parent_text = parent.get_text()
                    
                    # 크기 정보 추출
                    size_match = re.search(r'\[size:\s*([^,\]]+)', parent_text)
                    if size_match:
                        size_info = size_match.group(1)
                    
                    # 다운로드 카운트 추출
                    download_match = re.search(r'Download:\s*(\d+)', parent_text)
                    if download_match:
                        download_count = download_match.group(1)
                
                # next_sibling에서도 시도
                try:
                    next_sibling = link.next_sibling
                    if next_sibling:
                        # BeautifulSoup 요소나 문자열 모두 처리
                        if hasattr(next_sibling, 'get_text'):
                            sibling_text = next_sibling.get_text()
                        else:
                            sibling_text = str(next_sibling)
                        
                        if not size_info:
                            size_match = re.search(r'\[size:\s*([^,\]]+)', sibling_text)
                            if size_match:
                                size_info = size_match.group(1)
                        
                        if not download_count:
                            download_match = re.search(r'Download:\s*(\d+)', sibling_text)
                            if download_match:
                                download_count = download_match.group(1)
                except Exception as e:
                    logger.debug(f"sibling 텍스트 처리 중 오류: {e}")
                    pass
                
                attachment = {
                    'name': name,
                    'url': file_url,
                    'size': size_info,
                    'download_count': download_count
                }
                
                attachments.append(attachment)
                logger.debug(f"KCA 첨부파일 발견: {name}")
                
            except Exception as e:
                logger.error(f"첨부파일 추출 중 오류: {e}")
                continue
        
        # 중복 제거
        unique_attachments = []
        seen_names = set()
        for att in attachments:
            if att['name'] not in seen_names:
                unique_attachments.append(att)
                seen_names.add(att['name'])
        
        logger.info(f"총 {len(unique_attachments)}개 첨부파일 발견")
        return unique_attachments


# 하위 호환성을 위한 별칭
KCAScraper = EnhancedKCAScraper