#!/usr/bin/env python3
"""
GICON (전라북도 경제통상진흥원) 스크래퍼 - 향상된 버전

사이트: https://www.gicon.or.kr/board.es?mid=a10204000000&bid=0003
특징: 표준 HTML 테이블, 직접 링크 방식, 다중 첨부파일, PDF 뷰어
"""

import re
import os
import logging
from typing import List, Dict, Any
from urllib.parse import urljoin, parse_qs, urlparse
from bs4 import BeautifulSoup

from enhanced_base_scraper import StandardTableScraper

logger = logging.getLogger(__name__)

class EnhancedGICONScraper(StandardTableScraper):
    """GICON 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 기본 설정
        self.base_url = "https://www.gicon.or.kr"
        self.list_url = "https://www.gicon.or.kr/board.es?mid=a10204000000&bid=0003"
        
        # 사이트별 특화 설정
        self.verify_ssl = True  # 표준 SSL 인증서 지원
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        
        # GICON 특화 설정
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        logger.info("GICON 스크래퍼 초기화 완료")
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: GICON 특화 로직
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&nPage={page_num}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: GICON 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """GICON 공고 목록 파싱 (표준 테이블 구조)"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        try:
            # 표준 HTML 테이블 구조에서 공고 목록 파싱
            table = soup.find('table')
            if not table:
                logger.warning("테이블을 찾을 수 없습니다")
                return announcements
            
            tbody = table.find('tbody')
            if not tbody:
                tbody = table  # tbody가 없는 경우 table 직접 사용
            
            rows = tbody.find_all('tr')
            logger.info(f"테이블에서 {len(rows)}개 행 발견")
            
            for i, row in enumerate(rows):
                try:
                    cells = row.find_all('td')
                    if len(cells) < 4:  # 최소 4개 컬럼 필요 (번호, 제목, 접수기간, 상태)
                        logger.debug(f"행 {i+1}: 컬럼 수 부족 ({len(cells)}개)")
                        continue
                    
                    # 번호 셀 (첫 번째)
                    number_cell = cells[0]
                    number_text = number_cell.get_text(strip=True)
                    
                    # 제목 셀 (두 번째)
                    title_cell = cells[1]
                    link_elem = title_cell.find('a')
                    
                    if not link_elem:
                        logger.debug(f"행 {i+1}: 제목 링크를 찾을 수 없음")
                        continue
                    
                    title = link_elem.get_text(strip=True)
                    if not title:
                        logger.debug(f"행 {i+1}: 제목이 비어있음")
                        continue
                    
                    href = link_elem.get('href', '')
                    if not href:
                        logger.debug(f"행 {i+1}: href가 비어있음")
                        continue
                    
                    # 절대 URL로 변환
                    if href.startswith('/'):
                        detail_url = urljoin(self.base_url, href)
                    else:
                        detail_url = href
                    
                    # URL에서 list_no 추출
                    parsed_url = urlparse(detail_url)
                    query_params = parse_qs(parsed_url.query)
                    list_no = query_params.get('list_no', [''])[0]
                    
                    # 접수기간 (세 번째)
                    period = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                    
                    # 상태 (네 번째)
                    status = cells[3].get_text(strip=True) if len(cells) > 3 else ""
                    
                    announcement = {
                        'title': title,
                        'url': detail_url,
                        'number': number_text,
                        'list_no': list_no,
                        'period': period,
                        'status': status
                    }
                    
                    announcements.append(announcement)
                    logger.debug(f"공고 파싱 완료: {title[:50]}...")
                    
                except Exception as e:
                    logger.warning(f"행 {i+1} 파싱 중 오류: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"목록 페이지 파싱 중 오류: {e}")
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_detail_page(html_content)
        
        # Fallback: GICON 특화 로직
        return self._parse_detail_fallback(html_content)
    
    def _parse_detail_fallback(self, html_content: str) -> Dict[str, Any]:
        """GICON 상세 페이지 특화 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 추출을 위한 다양한 선택자 시도
        content_selectors = [
            '.board_view_content',
            '.view_content',
            '.content_area',
            '.board_content',
            'div[class*="content"]',
            'div[class*="view"]'
        ]
        
        content_parts = []
        
        # 메타 정보 추출 (리스트 형태로 제공됨)
        meta_info = []
        
        # 정보 리스트 찾기 (dl, dt, dd 구조 또는 테이블)
        info_lists = soup.find_all(['dl', 'table'])
        for info_list in info_lists:
            if info_list.name == 'dl':
                # dl/dt/dd 구조
                terms = info_list.find_all('dt')
                definitions = info_list.find_all('dd')
                for term, definition in zip(terms, definitions):
                    term_text = term.get_text(strip=True)
                    def_text = definition.get_text(strip=True)
                    if term_text and def_text:
                        meta_info.append(f"**{term_text}**: {def_text}")
            elif info_list.name == 'table':
                # 테이블 구조에서 정보 추출
                rows = info_list.find_all('tr')
                for row in rows:
                    cells = row.find_all(['th', 'td'])
                    if len(cells) >= 2:
                        label = cells[0].get_text(strip=True)
                        value = cells[1].get_text(strip=True)
                        if label and value and len(label) < 20:  # 제목이 너무 길지 않은 경우만
                            meta_info.append(f"**{label}**: {value}")
        
        if meta_info:
            content_parts.extend(meta_info)
            content_parts.append("---")
        
        # 본문 내용 추출
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                text = content_elem.get_text(separator='\n', strip=True)
                if text and len(text) > 100:  # 충분한 내용이 있는 경우
                    content_parts.append(text)
                    logger.debug(f"본문을 {selector} 선택자로 찾음")
                    break
        
        # 본문을 찾지 못한 경우 전체 body에서 추출
        if len(content_parts) <= len(meta_info) + 1:  # 메타정보와 구분선만 있는 경우
            body = soup.find('body')
            if body:
                # 스크립트, 스타일, 네비게이션 태그 제거
                for unwanted in body(["script", "style", "nav", "header", "footer"]):
                    unwanted.decompose()
                
                text = body.get_text(separator='\n', strip=True)
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                
                # 중복 제거 및 필터링
                filtered_lines = []
                for line in lines:
                    if len(line) > 10 and line not in filtered_lines[-5:]:  # 최근 5줄과 중복 체크
                        filtered_lines.append(line)
                
                content_parts.extend(filtered_lines[:50])  # 최대 50줄까지
                logger.warning("본문 영역을 찾지 못해 전체 페이지 텍스트 사용")
        
        content = '\n\n'.join(content_parts)
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup)
        
        return {
            'content': content,
            'attachments': attachments
        }
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """첨부파일 링크 추출"""
        attachments = []
        
        try:
            # GICON 첨부파일 패턴: /boardDownload.es?bid=0003&list_no=XXXXX&seq=Y
            download_patterns = [
                'a[href*="boardDownload.es"]',
                'a[href*="download"]',
                'a[href*="file"]'
            ]
            
            for pattern in download_patterns:
                links = soup.select(pattern)
                for link in links:
                    href = link.get('href', '')
                    filename = link.get_text(strip=True)
                    
                    if not href or not filename:
                        continue
                    
                    # boardDownload.es 패턴 우선 처리
                    if 'boardDownload.es' in href:
                        # URL에서 파라미터 추출
                        parsed_url = urlparse(href)
                        query_params = parse_qs(parsed_url.query)
                        
                        list_no = query_params.get('list_no', [''])[0]
                        seq = query_params.get('seq', [''])[0]
                        
                        if list_no and seq:
                            # 절대 URL로 변환
                            if href.startswith('/'):
                                file_url = urljoin(self.base_url, href)
                            else:
                                file_url = href
                            
                            # 파일 정보 추출 (주변 텍스트에서)
                            parent = link.parent
                            file_info = ""
                            if parent:
                                parent_text = parent.get_text()
                                # 파일 크기 패턴 찾기
                                size_match = re.search(r'[\(\[]([0-9,.]+\s*[KMG]?B)[\)\]]', parent_text)
                                if size_match:
                                    file_info = size_match.group(1)
                            
                            attachment = {
                                'name': filename,
                                'url': file_url,
                                'size': file_info,
                                'seq': seq
                            }
                            
                            # 중복 제거
                            if attachment not in attachments:
                                attachments.append(attachment)
                                logger.debug(f"첨부파일 발견: {filename}")
                    
                    else:
                        # 일반적인 다운로드 링크 처리
                        if any(ext in filename.lower() for ext in ['.pdf', '.hwp', '.doc', '.xls', '.zip']):
                            if href.startswith('/'):
                                file_url = urljoin(self.base_url, href)
                            else:
                                file_url = href
                            
                            attachment = {
                                'name': filename,
                                'url': file_url,
                                'size': "",
                                'seq': ""
                            }
                            
                            if attachment not in attachments:
                                attachments.append(attachment)
                                logger.debug(f"첨부파일 발견: {filename}")
                
                # 첫 번째 패턴에서 파일을 찾았으면 다른 패턴은 시도하지 않음
                if attachments:
                    break
            
        except Exception as e:
            logger.error(f"첨부파일 추출 중 오류: {e}")
        
        logger.info(f"{len(attachments)}개 첨부파일 발견")
        return attachments

# 하위 호환성을 위한 별칭
GICONScraper = EnhancedGICONScraper

if __name__ == "__main__":
    # 간단한 테스트
    scraper = EnhancedGICONScraper()
    print(f"GICON 스크래퍼 초기화 완료")
    print(f"기본 URL: {scraper.list_url}")
    print(f"1페이지 URL: {scraper.get_list_url(1)}")
    print(f"2페이지 URL: {scraper.get_list_url(2)}")
    print(f"SSL 검증: {scraper.verify_ssl}")  # True여야 함