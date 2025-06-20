# -*- coding: utf-8 -*-
"""
한국산업안전보건공단(KOSHA) 전용 스크래퍼 - 향상된 버전
"""

from enhanced_base_scraper import StandardTableScraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin, parse_qs, urlparse
import re
import logging

logger = logging.getLogger(__name__)

class EnhancedKoshaScraper(StandardTableScraper):
    """한국산업안전보건공단(KOSHA) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://www.kosha.or.kr"
        self.list_url = "https://www.kosha.or.kr/kosha/report/notice.do"
        
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
            offset = (page_num - 1) * 10
            return f"{self.list_url}?mode=list&articleLimit=10&article.offset={offset}"
    
    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: 사이트 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> list:
        """KOSHA 사이트별 특화된 파싱 로직"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # KOSHA 특화: Board-list-type01 클래스를 가진 테이블 찾기
        table = soup.find('table', class_='Board-list-type01')
        if not table:
            logger.warning("Board-list-type01 클래스를 가진 테이블을 찾을 수 없습니다")
            # 대체 테이블 찾기
            table = soup.find('table')
            if not table:
                logger.error("테이블을 찾을 수 없습니다")
                return announcements
        
        # tbody 찾기 (없으면 table 자체 사용)
        tbody = table.find('tbody')
        if not tbody:
            tbody = table
        
        logger.info(f"테이블에서 {len(tbody.find_all('tr'))}개 행 발견")
        
        for row in tbody.find_all('tr'):
            try:
                cells = row.find_all('td')
                if len(cells) < 6:  # 번호, 제목, 작성자, 등록일, 첨부, 조회 (최소 6개)
                    continue
                
                # 제목 셀 (두 번째 셀)
                title_cell = cells[1]
                
                # 'board-list-title' 클래스가 있는지 확인
                if not title_cell.get('class') or 'board-list-title' not in title_cell.get('class', []):
                    logger.debug(f"제목 셀이 아닌 행 스킵: {title_cell.get('class')}")
                    continue
                
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
                
                # KOSHA 특화: 상대 경로를 완전한 URL로 변환
                if href.startswith('?'):
                    detail_url = f"{self.list_url}{href}"
                else:
                    detail_url = urljoin(self.base_url, href)
                
                announcement = {
                    'title': title,
                    'url': detail_url
                }
                
                # 추가 정보 추출 (있다면)
                try:
                    # 작성자 (세 번째 셀)
                    if len(cells) > 2 and cells[2].get('class') and 'board-list-writer' in cells[2].get('class', []):
                        announcement['writer'] = cells[2].get_text(strip=True)
                    
                    # 등록일 (네 번째 셀)
                    if len(cells) > 3 and cells[3].get('class') and 'board-list-date' in cells[3].get('class', []):
                        announcement['date'] = cells[3].get_text(strip=True)
                    
                    # 조회수 (여섯 번째 셀)
                    if len(cells) > 5 and cells[5].get('class') and 'board-list-view' in cells[5].get('class', []):
                        announcement['views'] = cells[5].get_text(strip=True)
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
        """본문 내용 추출 - 향상된 디버깅"""
        content_parts = []
        
        # 디버깅: HTML 구조 확인
        logger.debug("=== HTML 구조 디버깅 시작 ===")
        
        # 모든 테이블 확인
        tables = soup.find_all('table')
        logger.debug(f"페이지에서 {len(tables)}개 테이블 발견")
        
        for i, table in enumerate(tables):
            summary = table.get('summary', '')
            if summary:
                logger.debug(f"테이블 {i+1}: summary='{summary}'")
            
            # 상세 페이지 테이블 찾기
            if 'summary' in table.attrs and '상세' in summary:
                logger.debug(f"상세 페이지 테이블 발견: {summary}")
                # 이 테이블의 모든 tr.view-body 찾기
                view_body_rows = table.find_all('tr', class_='view-body')
                logger.debug(f"view-body 행 {len(view_body_rows)}개 발견")
                
                for j, row in enumerate(view_body_rows):
                    p17_cells = row.find_all('td', class_='p17')
                    logger.debug(f"view-body 행 {j+1}에서 p17 셀 {len(p17_cells)}개 발견")
                    
                    for k, cell in enumerate(p17_cells):
                        text_content = cell.get_text(strip=True)
                        logger.debug(f"p17 셀 {k+1} 텍스트 길이: {len(text_content)}")
                        if len(text_content) > 50:
                            logger.debug(f"p17 셀 {k+1} 미리보기: {text_content[:100]}...")
        
        # KOSHA 특화: 본문 영역 찾기
        # 1. view-body 클래스를 가진 tr 찾기
        content_row = soup.find('tr', class_='view-body')
        if content_row:
            content_td = content_row.find('td', class_='p17')
            if content_td:
                text_content = content_td.get_text(strip=True)
                logger.debug(f"본문을 view-body > p17 선택자로 찾음: {len(text_content)}자")
                if len(text_content) > 10:  # 의미있는 내용이 있다면
                    content_parts.append(self.h.handle(str(content_td)))
        
        # 2. 더 구체적인 선택자 시도
        if not content_parts:
            specific_table = soup.find('table', attrs={'summary': re.compile(r'상세|게시판')})
            if specific_table:
                logger.debug("상세 페이지 테이블에서 본문 재탐색")
                content_row = specific_table.find('tr', class_='view-body')
                if content_row:
                    content_td = content_row.find('td', class_='p17')
                    if content_td:
                        text_content = content_td.get_text(strip=True)
                        logger.debug(f"구체적 선택자로 찾은 본문: {len(text_content)}자")
                        if len(text_content) > 10:
                            content_parts.append(self.h.handle(str(content_td)))
        
        # 3. 모든 view-body 행 확인
        if not content_parts:
            all_view_body = soup.find_all('tr', class_='view-body')
            logger.debug(f"전체 {len(all_view_body)}개 view-body 행 발견")
            
            for i, row in enumerate(all_view_body):
                all_p17 = row.find_all('td', class_='p17')
                for j, cell in enumerate(all_p17):
                    text_content = cell.get_text(strip=True)
                    logger.debug(f"view-body 행 {i+1}, p17 셀 {j+1}: {len(text_content)}자")
                    if len(text_content) > 50:
                        logger.debug(f"충분한 내용 발견 - 사용: {text_content[:100]}...")
                        content_parts.append(self.h.handle(str(cell)))
                        break
                if content_parts:
                    break
        
        # 4. hwpEditorBoardContent 확인
        if not content_parts:
            hwp_content = soup.find('div', id='hwpEditorBoardContent')
            if hwp_content:
                logger.debug("본문을 hwpEditorBoardContent로 찾음")
                content_parts.append(self.h.handle(str(hwp_content)))
        
        # 5. 클래스명이 없는 p17 셀들도 확인
        if not content_parts:
            logger.debug("클래스명 없는 p17 속성 셀들 확인")
            all_tds = soup.find_all('td')
            for td in all_tds:
                if 'p17' in str(td.get('class', [])) or td.get('class') == ['p17']:
                    text_content = td.get_text(strip=True)
                    if len(text_content) > 50:
                        logger.debug(f"일반 p17 셀에서 본문 발견: {len(text_content)}자")
                        content_parts.append(self.h.handle(str(td)))
                        break
        
        # 6. 최종 대체 방법: 긴 텍스트가 있는 td 찾기
        if not content_parts:
            logger.warning("표준 본문 영역을 찾을 수 없어 대체 방법 시도")
            all_tds = soup.find_all('td')
            for td in all_tds:
                text = td.get_text(strip=True)
                if len(text) > 100:  # 100자 이상인 경우 본문으로 간주
                    logger.debug(f"긴 텍스트 영역을 본문으로 사용: {len(text)}자")
                    content_parts.append(self.h.handle(str(td)))
                    break
        
        logger.debug("=== HTML 구조 디버깅 완료 ===")
        
        if not content_parts:
            logger.warning("본문 내용을 찾을 수 없습니다")
            return "본문 내용을 추출할 수 없습니다."
        
        return "\n\n".join(content_parts)
    
    def _extract_attachments(self, soup: BeautifulSoup) -> list:
        """첨부파일 추출 - 향상된 디버깅"""
        attachments = []
        
        logger.debug("=== 첨부파일 추출 디버깅 시작 ===")
        
        # 1. view-down 클래스 영역 확인
        attach_area = soup.find('td', class_='view-down')
        if attach_area:
            logger.debug("view-down 영역 발견")
            
            # 모든 링크 확인
            all_links = attach_area.find_all('a')
            logger.debug(f"view-down 영역에서 {len(all_links)}개 링크 발견")
            
            for i, link in enumerate(all_links):
                href = link.get('href', '')
                text = link.get_text(strip=True)
                logger.debug(f"링크 {i+1}: href='{href}', text='{text}'")
        else:
            logger.debug("view-down 영역을 찾을 수 없음")
        
        # 2. 전체 페이지에서 mode=download 링크 확인
        all_download_links = soup.find_all('a', href=re.compile(r'mode=download'))
        logger.debug(f"전체 페이지에서 {len(all_download_links)}개 다운로드 링크 발견")
        
        for i, link in enumerate(all_download_links):
            href = link.get('href', '')
            text = link.get_text(strip=True)
            logger.debug(f"다운로드 링크 {i+1}: href='{href}', text='{text}'")
        
        # 3. view-downbox 영역 확인 (드롭다운 메뉴)
        downbox = soup.find('div', class_='view-downbox')
        if downbox:
            logger.debug("view-downbox 영역 발견")
            box_links = downbox.find_all('a')
            logger.debug(f"view-downbox에서 {len(box_links)}개 링크 발견")
            
            for i, link in enumerate(box_links):
                href = link.get('href', '')
                text = link.get_text(strip=True)
                logger.debug(f"박스 링크 {i+1}: href='{href}', text='{text}'")
        else:
            logger.debug("view-downbox 영역을 찾을 수 없음")
        
        # 4. 실제 첨부파일 추출
        # KOSHA 특화: view-down 클래스를 가진 td에서 첨부파일 찾기
        if attach_area:
            # 다운로드 링크 찾기 (mode=download가 포함된 링크)
            download_links = attach_area.find_all('a', href=re.compile(r'mode=download'))
            
            for link in download_links:
                try:
                    href = link.get('href', '')
                    if not href:
                        continue
                    
                    # 파일 URL 구성 - KOSHA 특화
                    if href.startswith('?'):
                        file_url = f"{self.list_url}{href}"
                    else:
                        file_url = urljoin(self.base_url, href)
                    
                    # 파일명 추출 (링크 텍스트에서)
                    filename = link.get_text(strip=True)
                    if not filename:
                        # href에서 파일명 추출 시도
                        parsed_url = urlparse(href)
                        query_params = parse_qs(parsed_url.query)
                        attach_no = query_params.get('attachNo', [''])[0]
                        article_no = query_params.get('articleNo', [''])[0]
                        filename = f"attachment_{attach_no}_{article_no}"
                    
                    attachment = {
                        'filename': filename,
                        'url': file_url
                    }
                    
                    attachments.append(attachment)
                    logger.debug(f"첨부파일 발견: {filename}")
                    
                except Exception as e:
                    logger.error(f"첨부파일 추출 중 오류: {e}")
                    continue
        
        # 5. view-downbox에서도 추출 시도
        if not attachments and downbox:
            download_links = downbox.find_all('a', href=re.compile(r'mode=download'))
            
            for link in download_links:
                try:
                    href = link.get('href', '')
                    if not href:
                        continue
                    
                    # KOSHA 특화 URL 구성
                    if href.startswith('?'):
                        file_url = f"{self.list_url}{href}"
                    else:
                        file_url = urljoin(self.base_url, href)
                    filename = link.get_text(strip=True) or f"attachment_{len(attachments)+1}"
                    
                    attachment = {
                        'filename': filename,
                        'url': file_url
                    }
                    
                    attachments.append(attachment)
                    logger.debug(f"박스에서 첨부파일 발견: {filename}")
                    
                except Exception as e:
                    logger.error(f"박스 첨부파일 추출 중 오류: {e}")
                    continue
        
        logger.debug("=== 첨부파일 추출 디버깅 완료 ===")
        logger.info(f"{len(attachments)}개 첨부파일 발견")
        return attachments

# 하위 호환성을 위한 별칭
KoshaScraper = EnhancedKoshaScraper