# -*- coding: utf-8 -*-
"""
전북테크노파크(JBTP) 전용 스크래퍼 - 향상된 버전
"""

import re
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
from enhanced_base_scraper import StandardTableScraper
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class EnhancedJbtpScraper(StandardTableScraper):
    """전북테크노파크(JBTP) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://www.jbtp.or.kr"
        self.list_url = "https://www.jbtp.or.kr/board/list.jbtp?boardId=BBS_0000006&menuCd=DOM_000000102001000000&contentsSid=9&cpath="
        
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
            # JBTP 특화 페이지네이션 파라미터 추가
            base_params = "boardId=BBS_0000006&menuCd=DOM_000000102001000000&paging=ok&gubun=&searchType=&keyword="
            return f"{self.base_url}/board/list.jbtp?{base_params}&pageNo={page_num}"
    
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
        for selector in ['.bbs_list_t', 'table.bbs_list_t', 'table']:
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
                
                # 제목 링크 찾기
                title_cell = None
                link_elem = None
                
                # txt_left 클래스를 가진 셀에서 링크 찾기
                for cell in cells:
                    if 'txt_left' in cell.get('class', []):
                        link = cell.find('a', href=True)
                        if link:
                            title_cell = cell
                            link_elem = link
                            break
                
                # txt_left가 없으면 일반적으로 링크 찾기
                if not link_elem:
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
                
                # URL 처리
                if href.startswith('http'):
                    detail_url = href
                else:
                    detail_url = urljoin(self.base_url, href)
                
                announcement = {
                    'title': title,
                    'url': detail_url
                }
                
                # 추가 정보 추출 시도 (JBTP 특화)
                # 일반적인 테이블 구조: No, 제목, 마감일, 첨부, 작성자, 작성일, 조회
                
                # 마감일 (3번째 칼럼)
                if len(cells) > 2:
                    deadline_text = cells[2].get_text(strip=True)
                    if deadline_text and deadline_text != '':
                        announcement['deadline'] = deadline_text
                
                # 첨부파일 여부 (4번째 칼럼)
                if len(cells) > 3:
                    attach_cell = cells[3]
                    if attach_cell.get_text(strip=True) or attach_cell.find('img'):
                        announcement['has_attachment'] = True
                
                # 작성자 (5번째 칼럼)
                if len(cells) > 4:
                    writer_text = cells[4].get_text(strip=True)
                    if writer_text:
                        announcement['writer'] = writer_text
                
                # 작성일 (6번째 칼럼)
                if len(cells) > 5:
                    date_text = cells[5].get_text(strip=True)
                    if date_text:
                        announcement['date'] = date_text
                
                # 조회수 (7번째 칼럼)
                if len(cells) > 6:
                    views_text = cells[6].get_text(strip=True)
                    if views_text and views_text.isdigit():
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
        for selector in ['.bbs_view', '.view_content', '.board_view', '.content_area', '.cont_area']:
            content_area = soup.select_one(selector)
            if content_area:
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        # 본문을 찾지 못한 경우 ID로 시도
        if not content_area:
            for id_name in ['content', 'view', 'board_content']:
                content_area = soup.find(id=id_name)
                if content_area:
                    logger.debug(f"본문을 #{id_name} ID로 찾음")
                    break
        
        # 여전히 찾지 못한 경우 전체 페이지에서 추출
        if not content_area:
            logger.warning("본문 영역을 찾을 수 없어 전체 페이지에서 추출")
            # 불필요한 요소들 제거
            for tag in soup(['script', 'style', 'nav', 'header', 'footer', '.navigation', '.sidebar', '.gnb']):
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
        """첨부파일 추출 - JBTP 실제 구조 기반"""
        attachments = []
        
        # JBTP 특화: .bbs_filedown 클래스 내의 첨부파일 구조
        filedown_div = soup.find('div', class_='bbs_filedown')
        
        if filedown_div:
            logger.debug("bbs_filedown 영역 발견")
            
            # dd 태그들에서 파일 정보 추출
            for dd in filedown_div.find_all('dd'):
                try:
                    # 파일명 추출 (dd 태그의 첫 번째 텍스트 노드)
                    dd_text = dd.get_text(strip=True)
                    if not dd_text:
                        continue
                    
                    # 첫 번째 줄이 파일명 (줄바꿈으로 분리)
                    lines = dd_text.split('\n')
                    file_name = lines[0].strip()
                    
                    if not file_name:
                        continue
                    
                    # 다운로드 링크 추출 (.sbtn_down 클래스)
                    download_link = dd.find('a', class_='sbtn_down')
                    if download_link and download_link.get('href'):
                        href = download_link.get('href')
                        file_url = urljoin(self.base_url, href) if not href.startswith('http') else href
                        
                        attachment = {
                            'name': file_name,
                            'url': file_url
                        }
                        
                        attachments.append(attachment)
                        logger.debug(f"첨부파일 발견: {file_name}")
                        
                except Exception as e:
                    logger.error(f"첨부파일 추출 중 오류: {e}")
                    continue
        
        # Fallback: 기존 패턴들도 시도
        if not attachments:
            logger.debug("bbs_filedown에서 파일을 찾지 못해 fallback 패턴 시도")
            
            # 일반적인 다운로드 링크 패턴들
            attachment_patterns = [
                'a[href*="/board/download.jbtp"]',  # JBTP 특화 다운로드 URL
                'a[href*="download"]',
                'a[href*="file"]',
                '.sbtn_down',  # JBTP의 다운로드 버튼 클래스
                '.file_down a',
                '.attach a'
            ]
            
            for pattern in attachment_patterns:
                links = soup.select(pattern)
                for link in links:
                    href = link.get('href', '')
                    if not href:
                        continue
                    
                    # JBTP 다운로드 URL 패턴 확인
                    if '/board/download.jbtp' in href or 'fileSid=' in href:
                        file_name = link.get_text(strip=True)
                        if not file_name or file_name in ['다운로드', 'download']:
                            # 링크 텍스트가 없거나 일반적인 단어인 경우 부모에서 파일명 찾기
                            parent = link.parent
                            if parent:
                                parent_text = parent.get_text(strip=True)
                                # 다운로드 텍스트 제거하고 파일명 추출
                                file_name = parent_text.replace('다운로드', '').replace('미리보기', '').strip()
                        
                        if not file_name:
                            file_name = f"attachment_{len(attachments)+1}"
                        
                        file_url = urljoin(self.base_url, href) if not href.startswith('http') else href
                        
                        attachment = {
                            'name': file_name,
                            'url': file_url
                        }
                        
                        attachments.append(attachment)
                        logger.debug(f"Fallback 첨부파일 발견: {file_name}")
        
        logger.info(f"총 {len(attachments)}개 첨부파일 발견")
        return attachments


# 하위 호환성을 위한 별칭
JbtpScraper = EnhancedJbtpScraper