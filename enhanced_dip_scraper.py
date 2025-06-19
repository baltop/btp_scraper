# -*- coding: utf-8 -*-
"""
대구디지털산업진흥원(DIP) 전용 스크래퍼 - 향상된 버전
"""

import re
import os
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
from enhanced_base_scraper import StandardTableScraper
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class EnhancedDipScraper(StandardTableScraper):
    """대구디지털산업진흥원(DIP) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://www.dip.or.kr"
        self.list_url = "https://www.dip.or.kr/home/notice/businessbbs/boardList.ubs?fboardcd=business"
        
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
            # DIP 특화 페이지네이션 파라미터
            base_params = "sfpsize=10&fboardcd=business&sfkind=&sfcategory=&sfstdt=&sfendt=&sfsearch=ftitle&sfkeyword="
            return f"{self.base_url}/home/notice/businessbbs/boardList.ubs?{base_params}&sfpage={page_num}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: 사이트 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """DIP 특화된 파싱 로직 - 실제 HTML 구조 기반"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # DIP 실제 구조: 각 공고별로 table이 분리되어 있음
        # table[caption="게시판 목록"] 찾기
        tables = soup.find_all('table')
        
        # caption이 "게시판 목록"인 테이블들 찾기
        board_tables = []
        for table in tables:
            caption = table.find('caption')
            if caption and '게시판 목록' in caption.get_text():
                board_tables.append(table)
        
        logger.info(f"게시판 목록 테이블 {len(board_tables)}개 발견")
        
        for table in board_tables:
            try:
                tbody = table.find('tbody')
                if not tbody:
                    continue
                
                tr = tbody.find('tr')
                if not tr:
                    continue
                
                # onclick 속성에서 JavaScript 함수 파라미터 추출
                onclick = tr.get('onclick', '')
                if not onclick:
                    continue
                
                # 패턴: javascript:read('dipadmin','8568')
                match = re.search(r"read\('([^']+)','([^']+)'\)", onclick)
                if not match:
                    continue
                
                board_type = match.group(1)  # 'dipadmin'
                board_num = match.group(2)   # 게시글 번호
                
                # td 요소들에서 정보 추출
                tds = tr.find_all('td')
                if len(tds) < 8:  # 최소 8개 필요
                    continue
                
                # 제목은 두 번째 td에서 링크로 추출
                title_td = tds[1] if len(tds) > 1 else None
                if not title_td:
                    continue
                
                title_link = title_td.find('a')
                if not title_link:
                    continue
                
                title = title_link.get_text(strip=True)
                if not title:
                    continue
                
                # 상세 페이지 URL 생성
                detail_url = f"{self.base_url}/home/notice/businessbbs/boardRead.ubs"
                detail_params = f"sfpsize=10&fboardcd=business&sfkind=&sfcategory=&sfstdt=&sfendt=&sfsearch=ftitle&sfkeyword=&fboardnum={board_num}&sfpage=1"
                full_detail_url = f"{detail_url}?{detail_params}"
                
                announcement = {
                    'title': title,
                    'url': full_detail_url,
                    'board_num': board_num
                }
                
                # 추가 정보 추출
                try:
                    # 상태 (첫 번째 td)
                    if len(tds) > 0:
                        status_text = tds[0].get_text(strip=True)
                        if status_text:
                            announcement['status'] = status_text
                    
                    # 번호 (세 번째 td에서 "번호 XXXX" 형식)
                    if len(tds) > 2:
                        num_text = tds[2].get_text(strip=True)
                        if '번호' in num_text:
                            number = num_text.replace('번호', '').strip()
                            if number.isdigit():
                                announcement['number'] = number
                    
                    # 주관기관 (네 번째 td에서 "주관 DIP" 형식)
                    if len(tds) > 3:
                        org_text = tds[3].get_text(strip=True)
                        if '주관' in org_text:
                            organization = org_text.replace('주관', '').strip()
                            if organization:
                                announcement['organization'] = organization
                    
                    # 분류 (다섯 번째 td에서 "분류 사업" 형식)
                    if len(tds) > 4:
                        cat_text = tds[4].get_text(strip=True)
                        if '분류' in cat_text:
                            category = cat_text.replace('분류', '').strip()
                            if category:
                                announcement['category'] = category
                    
                    # 첨부파일 여부 (여섯 번째 td에서 "첨부" 텍스트 확인)
                    if len(tds) > 5:
                        attach_text = tds[5].get_text(strip=True)
                        if '첨부' in attach_text:
                            announcement['has_attachment'] = True
                    
                    # 기간 (일곱 번째 td에서 "기간 2025-05-26 ~ 2025-06-13" 형식)
                    if len(tds) > 6:
                        period_text = tds[6].get_text(strip=True)
                        if '기간' in period_text:
                            period = period_text.replace('기간', '').strip()
                            if '~' in period:
                                announcement['period'] = period
                    
                    # 등록일 (여덟 번째 td에서 "등록일 2025-05-26" 형식)
                    if len(tds) > 7:
                        date_text = tds[7].get_text(strip=True)
                        if '등록일' in date_text:
                            date = date_text.replace('등록일', '').strip()
                            if date:
                                announcement['date'] = date
                    
                    # 조회수 (아홉 번째 td에서 "조회수 14" 형식)
                    if len(tds) > 8:
                        views_text = tds[8].get_text(strip=True)
                        if '조회수' in views_text:
                            views = views_text.replace('조회수', '').strip()
                            if views.isdigit():
                                announcement['views'] = views
                    
                    # D-day 정보 (제목 td 내부의 span)
                    dday_spans = title_td.find_all('span')
                    for span in dday_spans:
                        span_text = span.get_text(strip=True)
                        if span_text.startswith('D-'):
                            announcement['d_day'] = span_text
                    
                except Exception as e:
                    logger.warning(f"추가 정보 추출 중 오류: {e}")
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱 완료: {title[:50]}...")
                
            except Exception as e:
                logger.error(f"테이블 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(board_tables)}개 테이블 처리, {len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str, url: str = None) -> Dict[str, Any]:
        """상세 페이지 파싱 - DIP 실제 구조 기반"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        result = {
            'content': '',
            'attachments': []
        }
        
        # URL에서 board_num 추출
        board_num = None
        if url:
            board_match = re.search(r'fboardnum=(\d+)', url)
            if board_match:
                board_num = board_match.group(1)
                logger.debug(f"URL에서 board_num 추출: {board_num}")
        
        # DIP 특화: 본문 영역 찾기
        content_area = soup.find('div', class_='read__content')
        
        if content_area:
            # read__content 영역에서 본문 추출
            try:
                result['content'] = self.h.handle(str(content_area))
                logger.debug("read__content 영역에서 본문 추출 완료")
            except Exception as e:
                logger.error(f"HTML to Markdown 변환 실패: {e}")
                result['content'] = content_area.get_text(separator='\n', strip=True)
        else:
            # Fallback: 다양한 선택자로 본문 찾기
            content_selectors = [
                '.board-read-content',
                '.content',
                '.read-content',
                '#content',
                '.board-content'
            ]
            
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    try:
                        result['content'] = self.h.handle(str(content_elem))
                        logger.debug(f"{selector} 선택자로 본문 추출 완료")
                        break
                    except Exception as e:
                        logger.error(f"HTML to Markdown 변환 실패: {e}")
                        result['content'] = content_elem.get_text(separator='\n', strip=True)
                        break
            else:
                # 최종 Fallback: 전체 페이지에서 추출
                logger.warning("본문 영역을 찾을 수 없어 전체 페이지에서 추출")
                # 불필요한 요소들 제거
                for tag in soup(['script', 'style', 'nav', 'header', 'footer', '.navigation', '.sidebar']):
                    tag.decompose()
                result['content'] = soup.get_text(separator='\n', strip=True)
        
        # 첨부파일 찾기 (board_num 전달)
        result['attachments'] = self._extract_attachments(soup, board_num)
        
        logger.info(f"상세 페이지 파싱 완료 - 내용길이: {len(result['content'])}, 첨부파일: {len(result['attachments'])}")
        return result
    
    def _extract_attachments(self, soup: BeautifulSoup, board_num: str = None) -> List[Dict[str, Any]]:
        """첨부파일 추출 - DIP 실제 구조 기반"""
        attachments = []
        
        # board_num이 없으면 URL에서 추출 시도
        if not board_num:
            # 현재 페이지 URL에서 fboardnum 추출
            page_url = soup.find('link', {'rel': 'canonical'})
            if page_url:
                url = page_url.get('href', '')
                board_match = re.search(r'fboardnum=(\d+)', url)
                if board_match:
                    board_num = board_match.group(1)
        
        # DIP 실제 구조: 첨부파일 영역 찾기
        # 실제 HTML 구조에서 "첨부파일" 텍스트를 포함하는 영역 찾기
        attachment_sections = soup.find_all(text=re.compile(r'첨부파일|첨부'))
        
        for section_text in attachment_sections:
            # 부모 요소에서 파일 링크 찾기
            parent = section_text.parent
            if parent:
                # 부모의 부모까지 탐색해서 링크 찾기
                for level in range(3):  # 최대 3단계까지 올라가며 탐색
                    if not parent:
                        break
                    
                    # 현재 레벨에서 다운로드 링크 찾기
                    links = parent.find_all('a')
                    for link in links:
                        onclick = link.get('onclick', '')
                        href = link.get('href', '')
                        
                        # onclick 또는 href에서 download() 함수 찾기
                        download_source = onclick if onclick and 'download(' in onclick else href
                        
                        if download_source and 'download(' in download_source:
                            download_match = re.search(r'download\((\d+)\)', download_source)
                            if download_match:
                                file_num = download_match.group(1)  # ffilenum
                                file_name = link.get_text(strip=True)
                                
                                if not file_name:
                                    file_name = f"attachment_{file_num}"
                                
                                # DIP의 실제 다운로드 URL (POST 요청)
                                file_url = f"{self.base_url}/home/notice/businessbbs/boardDownLoad.ubs"
                                
                                attachment = {
                                    'name': file_name,
                                    'url': file_url,
                                    'file_num': file_num,  # ffilenum
                                    'board_num': board_num,  # fboardnum
                                    'type': 'post_download'  # POST 요청임을 표시
                                }
                                
                                attachments.append(attachment)
                                logger.debug(f"첨부파일 발견: {file_name} (ffilenum: {file_num}, fboardnum: {board_num})")
                    
                    parent = parent.parent
        
        # Fallback: 전체 페이지에서 download() 패턴 찾기
        if not attachments:
            logger.debug("첨부파일 영역에서 파일을 찾지 못해 전체 페이지 검색")
            
            all_links = soup.find_all('a')
            for link in all_links:
                onclick = link.get('onclick', '')
                href = link.get('href', '')
                
                # onclick 또는 href에서 download() 함수 찾기
                download_source = onclick if onclick and 'download(' in onclick else href
                
                if download_source and 'download(' in download_source:
                    download_match = re.search(r'download\((\d+)\)', download_source)
                    if download_match:
                        file_num = download_match.group(1)  # ffilenum
                        file_name = link.get_text(strip=True)
                        
                        if not file_name:
                            file_name = f"attachment_{file_num}"
                        
                        # 실제 확인된 다운로드 URL
                        file_url = f"{self.base_url}/home/notice/businessbbs/boardDownLoad.ubs"
                        
                        attachment = {
                            'name': file_name,
                            'url': file_url,
                            'file_num': file_num,  # ffilenum
                            'board_num': board_num,  # fboardnum
                            'type': 'post_download'
                        }
                        
                        attachments.append(attachment)
                        logger.debug(f"Fallback 첨부파일 발견: {file_name} (ffilenum: {file_num}, fboardnum: {board_num})")
        
        logger.info(f"총 {len(attachments)}개 첨부파일 발견 (board_num: {board_num})")
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment_info: dict = None) -> bool:
        """DIP 특화 파일 다운로드 - POST 요청 처리"""
        try:
            logger.info(f"파일 다운로드 시작: {url}")
            
            # DIP의 POST 다운로드 처리
            if attachment_info and attachment_info.get('type') == 'post_download':
                file_num = attachment_info.get('file_num')  # ffilenum
                board_num = attachment_info.get('board_num')  # fboardnum
                
                if not file_num:
                    logger.error("POST 다운로드를 위한 file_num이 없습니다")
                    return False
                
                if not board_num:
                    logger.error("POST 다운로드를 위한 board_num이 없습니다")
                    return False
                
                # POST 요청 데이터 준비 (실제 확인된 DIP 파라미터)
                post_data = {
                    'fboardnum': board_num,  # 게시글 번호
                    'fboardcd': 'business',  # 게시판 코드 (항상 business)
                    'ffilenum': file_num,    # 파일 번호
                    '_csrf': ''              # CSRF 토큰 (현재 빈값)
                }
                
                # 다운로드 헤더 설정
                download_headers = self.headers.copy()
                download_headers['Referer'] = self.base_url
                download_headers['Content-Type'] = 'application/x-www-form-urlencoded'
                
                logger.debug(f"POST 다운로드 요청: URL={url}, data={post_data}")
                
                response = self.session.post(
                    url,
                    data=post_data,
                    headers=download_headers,
                    stream=True,
                    timeout=self.timeout,
                    verify=self.verify_ssl
                )
                response.raise_for_status()
                
            else:
                # 일반 GET 다운로드 (부모 클래스 방식)
                download_headers = self.headers.copy()
                if self.base_url:
                    download_headers['Referer'] = self.base_url
                
                response = self.session.get(
                    url,
                    headers=download_headers,
                    stream=True,
                    timeout=self.timeout,
                    verify=self.verify_ssl
                )
                response.raise_for_status()
            
            # 실제 파일명 추출
            actual_filename = self._extract_filename(response, save_path)
            if actual_filename != save_path:
                save_path = actual_filename
            
            # 파일 저장
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(save_path)
            logger.info(f"다운로드 완료: {save_path} ({file_size:,} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"파일 다운로드 실패 {url}: {e}")
            return False


# 하위 호환성을 위한 별칭
DipScraper = EnhancedDipScraper