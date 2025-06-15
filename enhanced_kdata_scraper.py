# -*- coding: utf-8 -*-
"""
KDATA (한국데이터산업진흥원) Enhanced 스크래퍼
URL: https://www.kdata.or.kr/kr/board/notice_01/boardList.do
"""

import requests
from bs4 import BeautifulSoup
import os
import time
import re
import json
import logging
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin, parse_qs, urlparse
from enhanced_base_scraper import StandardTableScraper

logger = logging.getLogger(__name__)

class EnhancedKdataScraper(StandardTableScraper):
    """KDATA 한국데이터산업진흥원 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://www.kdata.or.kr"
        self.list_url = "https://www.kdata.or.kr/kr/board/notice_01/boardList.do"
        
        # KDATA 특화 설정
        self.verify_ssl = False  # SSL 인증서 문제
        self.default_encoding = 'utf-8'
        
        # 헤더 업데이트
        self.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        self.session.headers.update(self.headers)
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - 설정 주입과 Fallback 패턴"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: KDATA 특화 로직
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}?pageIndex={page_num}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: KDATA 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """KDATA 특화된 목록 파싱 로직"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # KDATA의 목록 구조: ul.bbs_list > li
        list_container = soup.find('ul', class_='bbs_list')
        if not list_container:
            logger.warning("ul.bbs_list 컨테이너를 찾을 수 없습니다")
            return announcements
        
        # 헤더 li 제외하고 실제 공고 li들만 가져오기
        items = list_container.find_all('li')
        logger.info(f"리스트에서 {len(items)}개 항목 발견")
        
        for item in items:
            try:
                # 헤더 항목 스킵 (class="cate" 포함)
                if 'cate' in item.get('class', []):
                    continue
                
                # onclick 속성에서 공고 ID 추출
                onclick = item.get('onclick', '')
                if not onclick:
                    continue
                
                # fnLinkView('38690') 형태에서 ID 추출
                id_match = re.search(r"fnLinkView\('(\d+)'\)", onclick)
                if not id_match:
                    continue
                
                notice_id = id_match.group(1)
                
                # 제목 추출
                title_elem = item.find('p', class_='tit')
                if not title_elem:
                    continue
                
                title_link = title_elem.find('a')
                if not title_link:
                    continue
                
                title = title_link.get_text(strip=True)
                if not title:
                    continue
                
                # 상세 페이지 URL 구성
                detail_url = f"{self.base_url}/kr/board/notice_01/boardView.do?bbsIdx={notice_id}"
                
                # 등록일자 추출
                date_elem = item.find('p', class_='date')
                date = ""
                if date_elem:
                    date_span = date_elem.find('span')
                    if date_span:
                        date = date_span.get_text(strip=True)
                
                # 조회수 추출
                view_elem = item.find('p', class_='view')
                views = ""
                if view_elem:
                    views = view_elem.get_text(strip=True)
                
                # 첨부파일 여부 확인
                file_elem = item.find('p', class_='file')
                has_attachment = False
                if file_elem:
                    file_text = file_elem.get_text(strip=True)
                    has_attachment = "첨부파일 있음" in file_text
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'date': date,
                    'views': views,
                    'has_attachment': has_attachment,
                    'notice_id': notice_id
                }
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱: {title}")
                
            except Exception as e:
                logger.error(f"공고 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 기본 결과 구조
        result = {
            'content': '',
            'attachments': []
        }
        
        try:
            # 내용 추출 - 여러 선택자 시도
            content_selectors = [
                '.cont',  # KDATA 메인 컨텐츠
                '.view_content',
                '.board_view',
                '.content_area'
            ]
            
            content_area = None
            for selector in content_selectors:
                content_area = soup.select_one(selector)
                if content_area:
                    logger.debug(f"본문을 {selector} 선택자로 찾음")
                    break
            
            if content_area:
                # HTML을 마크다운으로 변환
                content_html = str(content_area)
                markdown_content = self.h.handle(content_html)
                result['content'] = markdown_content.strip()
                logger.info(f"본문 추출 완료 - 길이: {len(result['content'])}")
            else:
                logger.warning("본문 영역을 찾을 수 없습니다")
                result['content'] = "본문을 찾을 수 없습니다."
            
            # 첨부파일 추출
            result['attachments'] = self._extract_attachments(soup)
            
        except Exception as e:
            logger.error(f"상세 페이지 파싱 중 오류: {e}")
            result['content'] = f"파싱 오류: {e}"
        
        return result
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """첨부파일 링크 추출"""
        attachments = []
        
        try:
            # KDATA의 첨부파일 구조 탐색
            # 1. 일반적인 다운로드 링크 찾기
            download_links = soup.find_all('a', href=re.compile(r'(download|file)', re.I))
            
            for link in download_links:
                href = link.get('href', '')
                if not href:
                    continue
                
                # 상대 URL을 절대 URL로 변환
                file_url = urljoin(self.base_url, href)
                
                # 파일명 추출 시도
                file_name = link.get_text(strip=True)
                if not file_name:
                    # href에서 파일명 추출 시도
                    url_parts = href.split('/')
                    file_name = url_parts[-1] if url_parts else f"attachment_{len(attachments)+1}"
                
                attachment = {
                    'name': file_name,
                    'url': file_url
                }
                
                attachments.append(attachment)
                logger.debug(f"첨부파일 발견: {file_name}")
            
            # 2. JavaScript 기반 다운로드 함수 찾기
            script_tags = soup.find_all('script')
            for script in script_tags:
                script_content = script.get_text() if script.string else ""
                
                # JavaScript 다운로드 함수 패턴 찾기
                js_patterns = [
                    r'fileDown\([\'"]([^\'"]+)[\'"]',  # fileDown('filename')
                    r'downloadFile\([\'"]([^\'"]+)[\'"]',  # downloadFile('filename')
                ]
                
                for pattern in js_patterns:
                    matches = re.findall(pattern, script_content)
                    for match in matches:
                        # 파일 다운로드 URL 구성
                        file_url = f"{self.base_url}/kr/board/notice_01/fileDown.do?fileName={match}"
                        
                        attachment = {
                            'name': match,
                            'url': file_url
                        }
                        
                        attachments.append(attachment)
                        logger.debug(f"JavaScript 첨부파일 발견: {match}")
            
            logger.info(f"{len(attachments)}개 첨부파일 발견")
            
        except Exception as e:
            logger.error(f"첨부파일 추출 중 오류: {e}")
        
        return attachments

# 하위 호환성을 위한 별칭
KdataScraper = EnhancedKdataScraper