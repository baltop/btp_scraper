# -*- coding: utf-8 -*-
"""
성남산업진흥원(SNIP) 전용 스크래퍼 - 향상된 버전
"""

import re
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from enhanced_base_scraper import StandardTableScraper
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class EnhancedSnipScraper(StandardTableScraper):
    """성남산업진흥원(SNIP) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://www.snip.or.kr"
        self.list_url = "https://www.snip.or.kr/SNIP/contents/Business1.do"
        
        # 사이트 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        self.delay_between_pages = 2
        
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - 설정 주입과 Fallback 패턴"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: 사이트 특화 로직
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}?page={page_num}&viewCount=10"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: 사이트 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """사이트별 특화된 파싱 로직"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 테이블 찾기 - 여러 선택자를 순차적으로 시도
        table = None
        for selector in ['.board-list', 'table.board-list', 'table', '.board_table', '.basic_table']:
            table = soup.select_one(selector)
            if table:
                logger.debug(f"테이블을 {selector} 선택자로 찾음")
                break
        
        if not table:
            logger.warning("테이블을 찾을 수 없습니다")
            return announcements
        
        # tbody 찾기
        tbody = table.find('tbody')
        if not tbody:
            tbody = table
        
        rows = tbody.find_all('tr')
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 3:  # 최소 필드 확인
                    continue
                
                # 제목 셀 찾기 (일반적으로 두 번째나 세 번째 셀)
                title_cell = None
                link_elem = None
                
                # 링크가 있는 셀 찾기
                for cell in cells:
                    link = cell.find('a', href=True)
                    if link:
                        title_cell = cell
                        link_elem = link
                        break
                
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                if not title:
                    continue
                
                href = link_elem.get('href', '')
                if not href:
                    continue
                
                # URL 처리 - SNIP는 절대 URL을 사용하는 것으로 보임
                if href.startswith('http'):
                    detail_url = href
                else:
                    detail_url = urljoin(self.base_url, href)
                
                announcement = {
                    'title': title,
                    'url': detail_url
                }
                
                # 추가 정보 추출 시도
                if len(cells) >= 4:
                    # 상태 (두 번째 셀)
                    if len(cells) > 1:
                        status_text = cells[1].get_text(strip=True)
                        if status_text:
                            announcement['status'] = status_text
                    
                    # 접수기간 (네 번째 셀)
                    if len(cells) > 3:
                        period_text = cells[3].get_text(strip=True)
                        if period_text and '~' in period_text:
                            announcement['period'] = period_text
                    
                    # 담당자 (다섯 번째 셀)
                    if len(cells) > 4:
                        writer_text = cells[4].get_text(strip=True)
                        if writer_text:
                            announcement['writer'] = writer_text
                    
                    # 작성일 (여섯 번째 셀)
                    if len(cells) > 5:
                        date_text = cells[5].get_text(strip=True)
                        if date_text:
                            announcement['date'] = date_text
                    
                    # 조회수 (일곱 번째 셀)
                    if len(cells) > 6:
                        views_text = cells[6].get_text(strip=True)
                        if views_text:
                            announcement['views'] = views_text
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱 완료: {title[:50]}...")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        result = {
            'content': '',
            'attachments': []
        }
        
        # 본문 영역 찾기 - 다단계 시도
        content_area = None
        for selector in ['.content_area', '.view_content', '.board_view', '.table_con']:
            content_area = soup.select_one(selector)
            if content_area:
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        # 본문을 찾지 못한 경우 전체 body에서 추출
        if not content_area:
            logger.warning("본문 영역을 찾을 수 없어 전체 페이지에서 추출")
            # 불필요한 요소들 제거
            for tag in soup(['script', 'style', 'nav', 'header', 'footer', '.navigation', '.sidebar']):
                tag.decompose()
            content_area = soup.find('body') or soup
        
        # HTML을 마크다운으로 변환
        if content_area:
            content_html = str(content_area)
            try:
                result['content'] = self.h.handle(content_html)
            except Exception as e:
                logger.error(f"HTML to Markdown 변환 실패: {e}")
                result['content'] = content_area.get_text(separator='\n', strip=True)
        
        # 첨부파일 찾기
        result['attachments'] = self._extract_attachments(soup)
        
        logger.info(f"상세 페이지 파싱 완료 - 내용길이: {len(result['content'])}, 첨부파일: {len(result['attachments'])}")
        return result
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """첨부파일 추출"""
        attachments = []
        
        # 일반적인 첨부파일 링크 패턴들
        attachment_patterns = [
            'a[href*="download"]',
            'a[href*="file"]',
            'a[href*="attach"]',
            '.attach a',
            '.file_list a',
            '.attachment a'
        ]
        
        for pattern in attachment_patterns:
            links = soup.select(pattern)
            for link in links:
                href = link.get('href', '')
                if not href:
                    continue
                
                # 파일 확장자가 있는 링크만 처리
                if not re.search(r'\.(pdf|hwp|doc|docx|xls|xlsx|ppt|pptx|zip|rar|7z|jpg|jpeg|png|gif)($|\?)', href, re.I):
                    continue
                
                file_name = link.get_text(strip=True)
                if not file_name:
                    # 파일명을 URL에서 추출 시도
                    parsed_url = urlparse(href)
                    file_name = parsed_url.path.split('/')[-1]
                    if not file_name:
                        file_name = f"attachment_{len(attachments)+1}"
                
                file_url = urljoin(self.base_url, href) if not href.startswith('http') else href
                
                attachment = {
                    'name': file_name,
                    'url': file_url
                }
                
                attachments.append(attachment)
                logger.debug(f"첨부파일 발견: {file_name}")
        
        logger.info(f"총 {len(attachments)}개 첨부파일 발견")
        return attachments


# 하위 호환성을 위한 별칭
SnipScraper = EnhancedSnipScraper