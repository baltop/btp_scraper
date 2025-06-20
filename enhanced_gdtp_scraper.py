# -*- coding: utf-8 -*-
"""
경기도기술개발원(GDTP) Enhanced 스크래퍼 - 표준 HTML 테이블 기반
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

class EnhancedGDTPScraper(StandardTableScraper):
    """경기도기술개발원(GDTP) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        
        # 향상된 헤더 설정 (차단 방지)
        self.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1',
        })
        self.session.headers.update(self.headers)
        
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://www.gdtp.or.kr"
        self.list_url = "https://www.gdtp.or.kr/board/notice"
        
        # 사이트 특화 설정
        self.verify_ssl = False  # SSL 인증서 문제 해결
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - GET 파라미터 방식"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: GDTP는 page 파라미터 사용
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}?&page={page_num}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: 사이트 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """GDTP 특화된 목록 파싱 로직 - div 기반 구조"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # div.tbody 찾기 (GDTP는 테이블 대신 div 구조 사용)
        tbody_div = soup.find('div', class_='tbody')
        
        if not tbody_div:
            logger.warning("div.tbody를 찾을 수 없습니다")
            return announcements
        
        # colgroup div들 찾기 (각 공고가 하나의 colgroup)
        colgroups = tbody_div.find_all('div', class_='colgroup')
        
        if not colgroups:
            logger.warning("공고 목록(colgroup)을 찾을 수 없습니다")
            return announcements
        
        logger.info(f"div.tbody에서 {len(colgroups)}개 공고 발견")
        
        for i, colgroup in enumerate(colgroups):
            try:
                # 제목 추출 (btitle 클래스의 div 안에 h3 > a)
                title_div = colgroup.find('div', class_='btitle')
                if not title_div:
                    logger.debug(f"공고 {i}: btitle div를 찾을 수 없음")
                    continue
                
                h3_elem = title_div.find('h3')
                if not h3_elem:
                    logger.debug(f"공고 {i}: h3 태그를 찾을 수 없음")
                    continue
                
                link_elem = h3_elem.find('a')
                if not link_elem:
                    logger.debug(f"공고 {i}: 링크를 찾을 수 없음")
                    continue
                
                # 제목과 URL 추출
                title = link_elem.get_text(strip=True)
                href = link_elem.get('href', '')
                
                if not title or len(title) < 3:
                    logger.debug(f"공고 {i}: 제목이 너무 짧음: '{title}'")
                    continue
                
                # URL 정규화
                if href.startswith('/'):
                    detail_url = f"{self.base_url}{href}"
                elif href.startswith('http'):
                    detail_url = href
                else:
                    detail_url = urljoin(self.base_url, href)
                
                # 날짜 추출 (bdate 클래스의 div에서)
                date = ""
                date_div = colgroup.find('div', class_='bdate')
                if date_div:
                    date_text = date_div.get_text(strip=True)
                    # 날짜 패턴 매칭 (YY-MM-DD 형식)
                    date_match = re.search(r'(\d{2}-\d{1,2}-\d{1,2})', date_text)
                    if date_match:
                        date = "20" + date_match.group(1)  # YY-MM-DD를 YYYY-MM-DD로 변환
                
                # 공고 번호 추출 (bnum 클래스의 div에서)
                number = ""
                num_div = colgroup.find('div', class_='bnum')
                if num_div:
                    number_text = num_div.get_text(strip=True)
                    if number_text and "번호" not in number_text:
                        number = number_text
                
                # 첨부파일 여부 확인 (bdown 클래스의 div에서)
                has_attachment = False
                down_div = colgroup.find('div', class_='bdown')
                if down_div:
                    # 아이콘이나 텍스트가 있으면 첨부파일 있음
                    if down_div.find('i') or down_div.get_text(strip=True):
                        has_attachment = True
                
                # 조회수 추출 (bview 클래스의 div에서)
                view_count = ""
                view_div = colgroup.find('div', class_='bview')
                if view_div:
                    view_text = view_div.get_text(strip=True)
                    view_match = re.search(r'(\d+)', view_text)
                    if view_match:
                        view_count = view_match.group(1)
                
                logger.debug(f"공고 {i}: {title[:30]}... (날짜: {date}, 조회수: {view_count})")
                
                # 공고 정보 구성
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'date': date,
                    'number': number,
                    'has_attachment': has_attachment,
                    'view_count': view_count,
                    'summary': ""
                }
                
                announcements.append(announcement)
                
            except Exception as e:
                logger.error(f"공고 {i} 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str, announcement_url: str = None) -> Dict[str, Any]:
        """상세 페이지 파싱 - GDTP 실제 HTML 구조 기반"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 제목 추출
        title = ""
        # 제목 후보들 검색 (h4, h3, h2, h1 순서로)
        for tag in ['h4', 'h3', 'h2', 'h1']:
            title_elem = soup.find(tag)
            if title_elem:
                title = title_elem.get_text(strip=True)
                if title and len(title) > 5:  # 유효한 제목
                    logger.debug(f"제목을 {tag} 태그에서 찾음: {title[:50]}...")
                    break
        
        # 본문 내용 추출
        content = ""
        
        # 방법 1: article 태그 내의 본문 찾기
        article = soup.find('article')
        if article:
            # article 내의 모든 p 태그 수집
            paragraphs = article.find_all('p')
            if paragraphs:
                content_parts = []
                for p in paragraphs:
                    p_text = p.get_text(strip=True)
                    if p_text and len(p_text) > 10:  # 의미있는 텍스트만
                        content_parts.append(p_text)
                content = "\n\n".join(content_parts)
                logger.debug(f"article 태그에서 {len(paragraphs)}개 문단 추출")
        
        # 방법 2: 백업 - div 컨테이너에서 긴 텍스트 찾기
        if not content or len(content) < 100:
            for div in soup.find_all('div'):
                div_text = div.get_text(strip=True)
                if len(div_text) > 200 and ('공고' in div_text or '모집' in div_text or '지원' in div_text):
                    content = div_text
                    logger.debug(f"div 태그에서 본문 추출: {len(content)}자")
                    break
        
        # 방법 3: 최후 수단 - 전체 텍스트에서 본문 부분 추출
        if not content or len(content) < 50:
            all_text = soup.get_text()
            # 본문 시작점 찾기
            content_start_markers = ['공고', '모집', '지원사업', '신청']
            for marker in content_start_markers:
                if marker in all_text:
                    start_idx = all_text.find(marker)
                    content = all_text[start_idx:start_idx+2000]  # 적당한 길이로 제한
                    break
        
        if not content or len(content) < 30:
            logger.warning("본문 영역을 찾을 수 없거나 내용이 부족합니다")
            content = "본문 내용을 추출할 수 없습니다."
        else:
            logger.info(f"본문 추출 성공: {len(content)}자")
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup, announcement_url)
        
        return {
            'title': title,
            'content': content,
            'attachments': attachments
        }
    
    def _extract_attachments(self, soup: BeautifulSoup, page_url: str = None) -> List[Dict[str, Any]]:
        """첨부파일 추출 - GDTP JavaScript 기반 다운로드"""
        attachments = []
        
        # JavaScript file_download() 함수 호출 링크 찾기
        for link in soup.find_all('a'):
            onclick = link.get('onclick', '')
            href = link.get('href', '')
            
            # JavaScript file_download 패턴 확인 (href 또는 onclick에서)
            js_pattern = onclick if 'file_download' in onclick else href if 'file_download' in href else ''
            
            if 'file_download' in js_pattern:
                # file_download('URL') 패턴에서 URL 추출
                match = re.search(r"file_download\(['\"]([^'\"]+)['\"]", js_pattern)
                if match:
                    download_url = match.group(1)
                    
                    # 파일명 추출 (링크의 span 텍스트에서)
                    filename = ""
                    span_elem = link.find('span')
                    if span_elem:
                        filename = span_elem.get_text(strip=True)
                    else:
                        filename = link.get_text(strip=True)
                    
                    # 파일명에서 크기 정보 제거 (예: "파일명.pdf(3.5 MB)" -> "파일명.pdf")
                    filename = re.sub(r'\s*\([^)]+\)\s*$', '', filename)
                    
                    if filename and download_url:
                        attachments.append({
                            'name': filename,
                            'url': download_url
                        })
                        
                        logger.debug(f"JavaScript 첨부파일 발견: {filename} -> {download_url}")
            
            # 직접 다운로드 링크도 확인
            elif '/postact/download/' in href and 'javascript:' not in href:
                filename = link.get_text(strip=True)
                filename = re.sub(r'\s*\([^)]+\)\s*$', '', filename)  # 크기 정보 제거
                
                download_url = href if href.startswith('http') else f"{self.base_url}{href}"
                
                if filename:
                    attachments.append({
                        'name': filename,
                        'url': download_url
                    })
                    
                    logger.debug(f"직접 다운로드 링크 발견: {filename} -> {download_url}")
        
        logger.info(f"총 {len(attachments)}개 첨부파일 발견")
        return attachments
    
    def _create_meta_info(self, announcement: Dict[str, Any]) -> str:
        """GDTP 메타 정보 생성"""
        meta_lines = [f"# {announcement['title']}", ""]
        
        # GDTP 특화 메타 정보
        if 'number' in announcement and announcement['number']:
            meta_lines.append(f"**공고번호**: {announcement['number']}")
        if 'date' in announcement and announcement['date']:
            meta_lines.append(f"**등록일**: {announcement['date']}")
        if 'has_attachment' in announcement and announcement['has_attachment']:
            meta_lines.append(f"**첨부파일**: 있음")
        if 'summary' in announcement and announcement['summary']:
            meta_lines.append(f"**요약**: {announcement['summary']}")
        
        meta_lines.extend([
            f"**원본 URL**: {announcement['url']}",
            "",
            "---",
            ""
        ])
        
        return "\n".join(meta_lines)

# 하위 호환성을 위한 별칭
GDTPScraper = EnhancedGDTPScraper