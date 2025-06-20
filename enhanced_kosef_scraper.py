# -*- coding: utf-8 -*-
"""
사회적기업진흥원 스크래퍼 - Enhanced 버전
"""

import re
import os
import time
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, parse_qs, urlparse
from enhanced_base_scraper import StandardTableScraper

logger = logging.getLogger(__name__)

class EnhancedKosefScraper(StandardTableScraper):
    """사회적기업진흥원 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들
        self.base_url = "https://www.socialenterprise.or.kr"
        self.list_url = "https://www.socialenterprise.or.kr/social/board/list.do?m_cd=D019&board_code=BO02&com_certifi_num=&selectyear=&magazine=&search_word=&search_type=&mode=list&category_id=CA92"
        
        # 사이트 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 2  # 서버 부하 방지
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - 설정 주입과 Fallback 패턴"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: 사이트 특화 로직 (pg 파라미터 사용)
        if page_num == 1:
            return self.list_url
        else:
            # pg 파라미터로 페이지네이션
            return f"{self.list_url}&pg={page_num}"
    
    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: 사이트 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> list:
        """KOSEF 특화된 파싱 로직"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 테이블 찾기 - 여러 선택자 시도
        table = None
        for selector in ['.board_tbl', 'table.board_tbl', 'table']:
            table = soup.select_one(selector)
            if table:
                logger.debug(f"테이블을 {selector} 선택자로 찾음")
                break
        
        if not table:
            logger.warning("테이블을 찾을 수 없습니다")
            return announcements
        
        tbody = table.find('tbody')
        if not tbody:
            tbody = table
        
        rows = tbody.find_all('tr')
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 4:  # 최소 필드 확인
                    continue
                
                # 제목 셀 찾기 (두 번째 셀이 제목)
                title_cell = cells[1] if len(cells) > 1 else cells[0]
                
                # 링크 찾기 - JavaScript onclick 처리
                link_elem = title_cell.find('a')
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                if not title:
                    continue
                
                # onclick 함수에서 seq_no 추출
                onclick = link_elem.get('onclick', '')
                seq_no = None
                
                # goViewPage2('252446', ''); 패턴에서 seq_no 추출
                match = re.search(r"goViewPage2\('(\d+)'", onclick)
                if match:
                    seq_no = match.group(1)
                else:
                    # 일반 href 링크도 체크
                    href = link_elem.get('href', '')
                    if href and href != '#none':
                        # view.do URL에서 seq_no 추출
                        match = re.search(r'seq_no=(\d+)', href)
                        if match:
                            seq_no = match.group(1)
                
                if not seq_no:
                    logger.debug(f"seq_no를 찾을 수 없습니다: {title}")
                    continue
                
                # 상세 페이지 URL 구성
                detail_url = f"{self.base_url}/social/board/view.do?m_cd=D019&pg=1&board_code=BO02&category_id=CA92&category_sub_id=&com_certifi_num=&selectyear=&magazine=&title=&search_word=&search_type=&seq_no={seq_no}"
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'seq_no': seq_no
                }
                
                # 추가 필드들 추출 시도
                try:
                    # 작성일 (4번째 셀)
                    if len(cells) >= 4:
                        date_text = cells[3].get_text(strip=True)
                        if date_text:
                            announcement['date'] = date_text
                    
                    # 작성자 (5번째 셀)
                    if len(cells) >= 5:
                        writer_text = cells[4].get_text(strip=True)
                        if writer_text:
                            announcement['writer'] = writer_text
                    
                    # 조회수 (6번째 셀)
                    if len(cells) >= 6:
                        views_text = cells[5].get_text(strip=True)
                        if views_text:
                            announcement['views'] = views_text
                    
                    # 첨부파일 여부 (3번째 셀)
                    if len(cells) >= 3:
                        attach_cell = cells[2]
                        if attach_cell.find('span', class_='icon_r_file'):
                            announcement['has_attachment'] = True
                
                except Exception as e:
                    logger.debug(f"추가 필드 추출 중 오류: {e}")
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱 완료: {title}")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> dict:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 영역 찾기 - 다단계 시도
        content_area = None
        for selector in ['.brd_view', '.board_view', '.view_content', '.content']:
            content_area = soup.select_one(selector)
            if content_area:
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        if not content_area:
            # 전체 내용을 가져오되, 헤더와 사이드바 제거
            for remove_selector in ['#header', '#snb', '#footer', '.search_area_btn']:
                for elem in soup.select(remove_selector):
                    elem.decompose()
            content_area = soup.find('body')
        
        # 본문 텍스트 추출
        if content_area:
            content = self.h.handle(str(content_area))
        else:
            content = "본문을 찾을 수 없습니다."
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup)
        
        return {
            'content': content,
            'attachments': attachments
        }
    
    def _extract_attachments(self, soup: BeautifulSoup) -> list:
        """첨부파일 링크 추출"""
        attachments = []
        
        # 첨부파일 영역 찾기
        attachment_areas = []
        
        # 일반적인 첨부파일 영역 선택자들
        for selector in ['.file_list', '.attach_list', '.brd_file', '.file_area']:
            areas = soup.select(selector)
            attachment_areas.extend(areas)
        
        # 첨부파일 링크 찾기
        for area in attachment_areas:
            file_links = area.find_all('a', href=True)
            for link in file_links:
                href = link.get('href', '')
                if 'download' in href.lower() or 'file' in href.lower():
                    file_name = link.get_text(strip=True)
                    if file_name:
                        file_url = urljoin(self.base_url, href)
                        attachments.append({
                            'name': file_name,
                            'url': file_url
                        })
        
        # JavaScript 기반 파일 다운로드 찾기
        script_texts = soup.find_all('script')
        for script in script_texts:
            if script.string:
                # fileDown 등의 함수 찾기
                file_patterns = [
                    r"fileDown\('([^']+)'\)",
                    r"fn_fileDown\('([^']+)'\)",
                    r"downloadFile\('([^']+)'\)"
                ]
                
                for pattern in file_patterns:
                    matches = re.findall(pattern, script.string)
                    for match in matches:
                        file_url = f"{self.base_url}/social/board/fileDown.do?file_id={match}"
                        attachments.append({
                            'name': f"첨부파일_{len(attachments)+1}",
                            'url': file_url
                        })
        
        # 직접적인 파일 링크 찾기 (확장자 기반)
        all_links = soup.find_all('a', href=True)
        file_extensions = ['.pdf', '.hwp', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.rar']
        
        for link in all_links:
            href = link.get('href', '')
            if any(ext in href.lower() for ext in file_extensions):
                file_name = link.get_text(strip=True) or os.path.basename(href)
                file_url = urljoin(self.base_url, href)
                
                # 중복 체크
                if not any(att['url'] == file_url for att in attachments):
                    attachments.append({
                        'name': file_name,
                        'url': file_url
                    })
        
        logger.info(f"{len(attachments)}개 첨부파일 발견")
        return attachments

# 하위 호환성을 위한 별칭
KosefScraper = EnhancedKosefScraper