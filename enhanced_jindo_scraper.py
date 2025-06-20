# -*- coding: utf-8 -*-
"""
진도군 농업기술센터 전용 스크래퍼 - 향상된 버전
"""

from enhanced_base_scraper import StandardTableScraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin, parse_qs, urlparse
import re
import logging

logger = logging.getLogger(__name__)

class EnhancedJindoScraper(StandardTableScraper):
    """진도군 농업기술센터 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://jindo.go.kr"
        self.list_url = "https://jindo.go.kr/atc/board/B0146.cs?m=43"
        
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
            return f"{self.list_url}&searchCondition=&searchKeyword=&&pageIndex={page_num}"
    
    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: 사이트 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> list:
        """진도군 사이트별 특화된 파싱 로직"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 진도군 특화: table 태그 찾기 (캡션이 "오늘의 뉴스 목록"인 테이블)
        table = soup.find('table')
        if not table:
            logger.warning("테이블을 찾을 수 없습니다")
            return announcements
        
        # tbody 찾기 (없으면 table 자체 사용)
        tbody = table.find('tbody')
        if not tbody:
            tbody = table
        
        logger.info(f"테이블에서 {len(tbody.find_all('tr'))}개 행 발견")
        
        for row in tbody.find_all('tr'):
            try:
                cells = row.find_all('td')
                if len(cells) < 5:  # 번호, 제목, 이름, 작성일, 조회수 (최소 5개)
                    continue
                
                # 제목 셀 (두 번째 셀)
                title_cell = cells[1]
                
                # 제목 링크 찾기
                link_elem = title_cell.find('a')
                if not link_elem:
                    logger.debug("링크가 없는 행 스킵")
                    continue
                
                title = link_elem.get_text(strip=True)
                if not title:
                    logger.debug("제목이 비어있는 행 스킵")
                    continue
                
                # URL 구성
                href = link_elem.get('href', '')
                if not href:
                    logger.debug("href가 없는 링크 스킵")
                    continue
                
                # 진도군 특화: 상대 경로를 완전한 URL로 변환
                detail_url = urljoin(self.list_url, href)
                
                announcement = {
                    'title': title,
                    'url': detail_url
                }
                
                # 추가 정보 추출 (있다면)
                try:
                    # 작성자 (세 번째 셀)
                    if len(cells) > 2:
                        announcement['writer'] = cells[2].get_text(strip=True)
                    
                    # 작성일 (네 번째 셀)
                    if len(cells) > 3:
                        announcement['date'] = cells[3].get_text(strip=True)
                    
                    # 조회수 (다섯 번째 셀)
                    if len(cells) > 4:
                        announcement['views'] = cells[4].get_text(strip=True)
                    
                    # 첨부파일 여부 확인 (제목에 "첨부파일" 텍스트가 있는지)
                    full_text = title_cell.get_text()
                    if "첨부파일" in full_text:
                        announcement['has_attachment'] = True
                    
                except Exception as e:
                    logger.debug(f"추가 정보 추출 실패: {e}")
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱 성공: {title[:50]}...")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> dict:
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
        content_parts = []
        
        # 진도군 특화: 제목 추출
        title_elem = soup.find('h4')
        if title_elem:
            content_parts.append(f"# {title_elem.get_text(strip=True)}")
            content_parts.append("")
        
        # 메타 정보 추출 (작성자, 작성일, 조회수)
        # li 태그들에서 메타 정보 찾기
        meta_items = soup.find_all('li')
        for item in meta_items:
            text = item.get_text(strip=True)
            if any(keyword in text for keyword in ['작성자', '작성일', '조회수']):
                content_parts.append(f"**{text}**")
        
        if content_parts:
            content_parts.append("")
            content_parts.append("---")
            content_parts.append("")
        
        # 본문 내용 추출 - 여러 방법 시도
        # 1. p 태그들 찾기
        paragraphs = soup.find_all('p')
        for p in paragraphs:
            text = p.get_text(strip=True)
            if text and len(text) > 10:  # 의미있는 길이의 텍스트만
                content_parts.append(text)
                content_parts.append("")
        
        # 2. p 태그가 없으면 div 태그에서 찾기
        if not paragraphs:
            divs = soup.find_all('div')
            for div in divs:
                # 클래스나 id가 content, body, article 등을 포함하는 div 찾기
                if div.get('class') or div.get('id'):
                    class_str = ' '.join(div.get('class', []))
                    id_str = div.get('id', '')
                    if any(keyword in (class_str + id_str).lower() 
                          for keyword in ['content', 'body', 'article', 'text']):
                        text = div.get_text(strip=True)
                        if text and len(text) > 50:
                            content_parts.append(self.h.handle(str(div)))
                            break
        
        # 3. 최종 대체 방법: 긴 텍스트가 있는 요소 찾기
        if len(content_parts) <= 5:  # 메타 정보만 있는 경우
            logger.warning("표준 본문 영역을 찾을 수 없어 대체 방법 시도")
            all_elements = soup.find_all(['div', 'section', 'article'])
            for elem in all_elements:
                text = elem.get_text(strip=True)
                if len(text) > 100:  # 100자 이상인 경우 본문으로 간주
                    logger.debug(f"긴 텍스트 영역을 본문으로 사용: {len(text)}자")
                    content_parts.append(self.h.handle(str(elem)))
                    break
        
        if not content_parts:
            logger.warning("본문 내용을 찾을 수 없습니다")
            return "본문 내용을 추출할 수 없습니다."
        
        return "\n\n".join(content_parts)
    
    def _extract_attachments(self, soup: BeautifulSoup) -> list:
        """첨부파일 추출"""
        attachments = []
        
        logger.debug("=== 첨부파일 추출 시작 ===")
        
        # 진도군 특화: "첨부파일" 헤딩 찾기
        attachment_heading = None
        for heading in soup.find_all(['h5', 'h4', 'h3']):
            if "첨부파일" in heading.get_text():
                attachment_heading = heading
                logger.debug(f"첨부파일 헤딩 발견: {heading.name}")
                break
        
        if attachment_heading:
            # 헤딩 다음의 요소들에서 파일 링크 찾기
            current = attachment_heading.next_sibling
            link_count = 0
            
            while current and link_count < 10:  # 최대 10개까지만 검색
                if hasattr(current, 'find_all'):
                    links = current.find_all('a')
                    for link in links:
                        href = link.get('href', '')
                        if '/cms/download.cs' in href:
                            filename = link.get_text(strip=True)
                            if filename:
                                file_url = urljoin(self.list_url, href)
                                attachment = {
                                    'filename': filename,
                                    'url': file_url
                                }
                                attachments.append(attachment)
                                logger.debug(f"첨부파일 발견: {filename}")
                
                current = current.next_sibling
                if current:
                    link_count += 1
        
        # 대체 방법: 전체 페이지에서 다운로드 링크 찾기
        if not attachments:
            logger.debug("헤딩 방식으로 첨부파일을 찾지 못해 전체 검색 시도")
            download_links = soup.find_all('a', href=re.compile(r'/cms/download\.cs'))
            
            for link in download_links:
                href = link.get('href', '')
                filename = link.get_text(strip=True)
                
                if filename and href:
                    file_url = urljoin(self.list_url, href)
                    attachment = {
                        'filename': filename,
                        'url': file_url
                    }
                    attachments.append(attachment)
                    logger.debug(f"전체 검색으로 첨부파일 발견: {filename}")
        
        logger.debug("=== 첨부파일 추출 완료 ===")
        logger.info(f"{len(attachments)}개 첨부파일 발견")
        return attachments

# 하위 호환성을 위한 별칭
JindoScraper = EnhancedJindoScraper