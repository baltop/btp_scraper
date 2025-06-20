# -*- coding: utf-8 -*-
"""
Enhanced 한국사회적기업진흥원 스크래퍼 - 향상된 버전
사이트: https://www.socialenterprise.or.kr/social/board/list.do?m_cd=D019&board_code=BO02&com_certifi_num=&selectyear=&magazine=&search_word=&search_type=&mode=list&category_id=CA92
"""

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
from enhanced_base_scraper import StandardTableScraper
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class EnhancedSocialEnterpriseScraper(StandardTableScraper):
    """한국사회적기업진흥원 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://www.socialenterprise.or.kr"
        self.list_url = "https://www.socialenterprise.or.kr/social/board/list.do?m_cd=D019&board_code=BO02&com_certifi_num=&selectyear=&magazine=&search_word=&search_type=&mode=list&category_id=CA92"
        
        # 사이트 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: 사이트 특화 로직
        if page_num == 1:
            return self.list_url
        else:
            # &pg= 파라미터 추가
            return f"{self.list_url}&pg={page_num}"
    
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
        table_selectors = ['table', '.board_table', '.basic_table']
        
        for selector in table_selectors:
            table = soup.select_one(selector)
            if table:
                logger.debug(f"테이블을 {selector} 선택자로 찾음")
                break
        
        if not table:
            logger.warning("게시판 테이블을 찾을 수 없습니다")
            return announcements
        
        # tbody 또는 테이블에서 행들 찾기
        tbody = table.find('tbody')
        if tbody:
            rows = tbody.find_all('tr')
        else:
            rows = table.find_all('tr')
        
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for row in rows:
            try:
                cells = row.find_all('td')
                
                # 최소한의 셀 수 확인 (번호, 제목, 첨부파일, 등록일, 등록자, 조회수)
                if len(cells) < 6:
                    continue
                
                # 제목 셀 (두 번째 셀, 인덱스 1)
                title_cell = cells[1]
                
                # 링크 엘리먼트 찾기
                link_elem = title_cell.find('a')
                if not link_elem:
                    continue
                
                # 제목과 URL 추출
                title = link_elem.get_text(strip=True)
                if not title or title in ['제목', '번호']:  # 헤더 행 제외
                    continue
                
                href = link_elem.get('href', '')
                if href.startswith('#') or not href or href == '#none':
                    # JavaScript 함수로 처리되는 경우 (goViewPage2 함수 확인)
                    onclick = link_elem.get('onclick', '')
                    if onclick:
                        # goViewPage2('252446', ''); 패턴에서 viewNo 추출
                        view_match = re.search(r"goViewPage2?\(['\"](\d+)['\"]", onclick)
                        if view_match:
                            view_no = view_match.group(1)
                            # view.do URL 구성 - /social/board/ 경로 포함
                            href = f"/social/board/view.do?m_cd=D019&pg=1&board_code=BO02&category_id=CA92&category_sub_id=&com_certifi_num=&selectyear=&magazine=&title=&search_word=&search_type=&seq_no={view_no}"
                        else:
                            continue
                else:
                    # 직접 링크인 경우도 /social/board/ 경로 추가
                    if href.startswith('view.do'):
                        href = f"/social/board/{href}"
                
                detail_url = urljoin(self.base_url, href)
                
                # 기본 공고 정보
                announcement = {
                    'title': title,
                    'url': detail_url
                }
                
                # 추가 메타데이터 추출
                try:
                    # 첨부파일 여부 (세 번째 셀, 인덱스 2)
                    attach_cell = cells[2]
                    attach_text = attach_cell.get_text(strip=True)
                    if '첨부파일' in attach_text or attach_cell.find('img'):
                        announcement['has_attachment'] = True
                    
                    # 등록일 (네 번째 셀, 인덱스 3)
                    date_cell = cells[3]
                    date_text = date_cell.get_text(strip=True)
                    if date_text and len(date_text) >= 8:  # 날짜 형식 확인
                        announcement['date'] = date_text
                    
                    # 등록자 (다섯 번째 셀, 인덱스 4)
                    writer_cell = cells[4]
                    writer_text = writer_cell.get_text(strip=True)
                    if writer_text:
                        announcement['writer'] = writer_text
                    
                    # 조회수 (여섯 번째 셀, 인덱스 5)
                    views_cell = cells[5]
                    views_text = views_cell.get_text(strip=True)
                    if views_text and views_text.isdigit():
                        announcement['views'] = views_text
                        
                except Exception as e:
                    logger.debug(f"추가 메타데이터 추출 중 오류: {e}")
                
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
        
        # 본문 추출 - 여러 선택자 시도
        content = ""
        content_selectors = [
            '.board_view',
            '.view_content',
            '.detail_content',
            '.content',
            '#content'
        ]
        
        content_area = None
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        if content_area:
            # 불필요한 요소들 제거
            for unwanted in content_area.select('script, style, .btn_area, .board_nav'):
                unwanted.decompose()
            
            # HTML을 마크다운으로 변환
            content = self.h.handle(str(content_area))
        else:
            # Fallback: body 전체에서 텍스트 추출
            logger.warning("본문 영역을 찾을 수 없어 전체 페이지에서 추출합니다")
            # 헤더, 네비게이션 등 제거
            for unwanted in soup.select('header, nav, .header, .nav, .gnb, .snb, .footer, script, style'):
                unwanted.decompose()
            
            content = self.h.handle(str(soup))
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup)
        
        return {
            'content': content,
            'attachments': attachments
        }
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """첨부파일 추출"""
        attachments = []
        
        # 첨부파일 영역 찾기
        attachment_selectors = [
            '.file_list',
            '.attach_list',
            '.board_file',
            '.file_area'
        ]
        
        attachment_area = None
        for selector in attachment_selectors:
            attachment_area = soup.select_one(selector)
            if attachment_area:
                logger.debug(f"첨부파일 영역을 {selector} 선택자로 찾음")
                break
        
        if not attachment_area:
            # 전체 페이지에서 파일 다운로드 링크 찾기
            file_links = soup.find_all('a', href=re.compile(r'(download|file|attach)', re.I))
            
            for link in file_links:
                href = link.get('href', '')
                file_name = link.get_text(strip=True)
                
                if href and file_name:
                    # 상대 URL을 절대 URL로 변환
                    file_url = urljoin(self.base_url, href)
                    
                    attachments.append({
                        'name': file_name,
                        'url': file_url
                    })
                    logger.debug(f"첨부파일 발견: {file_name}")
        else:
            # 첨부파일 영역에서 링크들 추출
            file_links = attachment_area.find_all('a')
            
            for link in file_links:
                href = link.get('href', '')
                file_name = link.get_text(strip=True)
                
                if href and file_name:
                    file_url = urljoin(self.base_url, href)
                    
                    attachments.append({
                        'name': file_name,
                        'url': file_url
                    })
                    logger.debug(f"첨부파일 발견: {file_name}")
        
        logger.info(f"{len(attachments)}개 첨부파일 발견")
        return attachments


# 하위 호환성을 위한 별칭
SocialEnterpriseScraper = EnhancedSocialEnterpriseScraper