#!/usr/bin/env python3
"""
BIZBC (중소기업진흥공단) 스크래퍼 - 향상된 버전

사이트: https://bizbc.or.kr/kor/contents/BC0101010000.do
특징: JavaScript 기반 네비게이션, 카드 형태 리스트, GET 파라미터 페이지네이션
"""

import re
import logging
from typing import List, Dict, Any
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from enhanced_base_scraper import StandardTableScraper

logger = logging.getLogger(__name__)

class EnhancedBIZBCScraper(StandardTableScraper):
    """BIZBC 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 기본 설정
        self.base_url = "https://bizbc.or.kr"
        self.list_url = "https://bizbc.or.kr/kor/contents/BC0101010000.do"
        
        # 사이트별 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        
        # BIZBC 특화 설정
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        logger.info("BIZBC 스크래퍼 초기화 완료")
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: BIZBC 특화 로직
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}?schOpt2=R&schFld=0&page={page_num}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: BIZBC 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """BIZBC 카드 형태 리스트 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        try:
            # ul li.tr 구조에서 공고 목록 파싱
            items = soup.select('ul li.tr')
            logger.info(f"카드 형태 리스트에서 {len(items)}개 항목 발견")
            
            for i, item in enumerate(items):
                try:
                    # 제목 링크 찾기
                    title_link = item.select_one('.board_tit a[onclick*="fn_goView"]')
                    if not title_link:
                        logger.debug(f"항목 {i+1}: 제목 링크를 찾을 수 없음")
                        continue
                    
                    title = title_link.get_text(strip=True)
                    if not title:
                        logger.debug(f"항목 {i+1}: 제목이 비어있음")
                        continue
                    
                    # onclick에서 ID 추출: fn_goView('11098')
                    onclick = title_link.get('onclick', '')
                    match = re.search(r"fn_goView\('([^']+)'\)", onclick)
                    if not match:
                        logger.debug(f"항목 {i+1}: onclick에서 ID 추출 실패: {onclick}")
                        continue
                    
                    biz_id = match.group(1)
                    detail_url = f"{self.base_url}/kor/contents/BC0101010000.do?schM=view&bizPbancSn={biz_id}"
                    
                    # 추가 메타 정보 추출
                    meta_info = {}
                    
                    # 마감일 정보
                    deadline_elem = item.select_one('.board_deadline')
                    if deadline_elem:
                        meta_info['deadline'] = deadline_elem.get_text(strip=True)
                    
                    # 지원분야 태그
                    tag_elem = item.select_one('.biz_tag')
                    if tag_elem:
                        meta_info['category'] = tag_elem.get_text(strip=True)
                    
                    # 메타 정보 (기관명, 모집기간 등)
                    date_elem = item.select_one('.date_txt')
                    if date_elem:
                        meta_info['meta'] = date_elem.get_text(strip=True)
                    
                    announcement = {
                        'title': title,
                        'url': detail_url,
                        'id': biz_id,
                        'meta': meta_info
                    }
                    
                    announcements.append(announcement)
                    logger.debug(f"공고 파싱 완료: {title[:50]}...")
                    
                except Exception as e:
                    logger.warning(f"항목 {i+1} 파싱 중 오류: {e}")
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
        
        # Fallback: BIZBC 특화 로직
        return self._parse_detail_fallback(html_content)
    
    def _parse_detail_fallback(self, html_content: str) -> Dict[str, Any]:
        """BIZBC 상세 페이지 특화 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 추출을 위한 다양한 선택자 시도
        content_selectors = [
            '.view_content',
            '.board_view',
            '.content_area',
            '.detail_content',
            '.view_wrap',
            'article',
            '.article_content'
        ]
        
        content = ""
        content_elem = None
        
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        if content_elem:
            # HTML을 마크다운 형태로 변환
            content = self._html_to_markdown(content_elem)
        else:
            # 전체 body에서 텍스트 추출 (마지막 수단)
            body = soup.find('body')
            if body:
                content = body.get_text(separator='\n', strip=True)
                logger.warning("본문 영역을 찾지 못해 전체 페이지 텍스트 사용")
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup)
        
        return {
            'content': content,
            'attachments': attachments
        }
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """첨부파일 링크 추출 - BIZBC 사이트 구조에 맞게 수정"""
        attachments = []
        
        try:
            # BIZBC 사이트의 첨부파일 구조: .detail_file .file_wrap .file
            file_items = soup.select('.detail_file .file_wrap .file')
            logger.debug(f"첨부파일 영역에서 {len(file_items)}개 파일 발견")
            
            for i, file_item in enumerate(file_items):
                try:
                    # 파일명 추출: .file_name 클래스의 span 태그
                    filename_elem = file_item.select_one('.file_name')
                    if not filename_elem:
                        logger.debug(f"파일 {i+1}: 파일명 요소를 찾을 수 없음")
                        continue
                    
                    filename = filename_elem.get_text(strip=True)
                    if not filename:
                        logger.debug(f"파일 {i+1}: 파일명이 비어있음")
                        continue
                    
                    # 다운로드 링크 추출: /afile/fileDownload/ 패턴
                    download_link = file_item.select_one('a[href*="/afile/fileDownload/"]')
                    if not download_link:
                        logger.debug(f"파일 {i+1}: 다운로드 링크를 찾을 수 없음")
                        continue
                    
                    href = download_link.get('href', '')
                    if not href:
                        logger.debug(f"파일 {i+1}: href 속성이 비어있음")
                        continue
                    
                    # 절대 URL로 변환
                    if href.startswith('/'):
                        file_url = urljoin(self.base_url, href)
                    else:
                        file_url = href
                    
                    attachment = {
                        'name': filename,  # 'filename' 대신 'name' 키 사용
                        'url': file_url
                    }
                    
                    attachments.append(attachment)
                    logger.debug(f"첨부파일 발견: {filename}")
                    
                except Exception as e:
                    logger.warning(f"파일 {i+1} 처리 중 오류: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"첨부파일 추출 중 오류: {e}")
        
        logger.info(f"{len(attachments)}개 첨부파일 발견")
        return attachments
    
    def _extract_filename_from_link(self, link, soup) -> str:
        """링크에서 파일명 추출"""
        # 1. 링크 텍스트에서 파일명 추출
        filename = link.get_text(strip=True)
        if filename and len(filename) > 1 and '다운로드' not in filename:
            return filename
        
        # 2. 주변 텍스트에서 파일명 찾기
        parent = link.parent
        if parent:
            # 같은 부모 요소 내의 텍스트 확인
            siblings = parent.find_all(text=True)
            for text in siblings:
                text = text.strip()
                if text and len(text) > 3 and any(ext in text.lower() for ext in ['.pdf', '.hwp', '.doc', '.xls', '.zip']):
                    return text
        
        # 3. title 속성 확인
        title = link.get('title', '')
        if title:
            return title
        
        # 4. 기본값
        return "attachment"

# 하위 호환성을 위한 별칭
BIZBCScraper = EnhancedBIZBCScraper

if __name__ == "__main__":
    # 간단한 테스트
    scraper = EnhancedBIZBCScraper()
    print(f"BIZBC 스크래퍼 초기화 완료")
    print(f"기본 URL: {scraper.list_url}")
    print(f"1페이지 URL: {scraper.get_list_url(1)}")
    print(f"2페이지 URL: {scraper.get_list_url(2)}")