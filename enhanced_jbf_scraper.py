# -*- coding: utf-8 -*-
"""
전남바이오진흥원(JBF) 스크래퍼 - 향상된 아키텍처
JavaScript 파일 다운로드와 표준 테이블 구조 처리
"""

from enhanced_base_scraper import StandardTableScraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin, parse_qs
import re
import logging
import os

logger = logging.getLogger(__name__)

class EnhancedJBFScraper(StandardTableScraper):
    """전남바이오진흥원 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "http://www.jbf.kr"
        self.list_url = "http://www.jbf.kr/main/board.action?cmsid=101050200000"
        
        # JBF 특화 설정
        self.verify_ssl = False  # SSL 인증서 문제
        self.default_encoding = 'utf-8'
    
    def get_list_url(self, page_num: int) -> str:
        """페이지 번호에 따른 목록 URL 반환"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: 기존 JBF 특화 로직
        return f"{self.list_url}&pageIndex={page_num}"
    
    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: 기존 JBF 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> list:
        """기존 방식의 목록 파싱 (Fallback)"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # JBF의 게시판 테이블 구조
        table = soup.find('table', class_='basic_table')
        if not table:
            logger.warning("basic_table 클래스를 가진 테이블을 찾을 수 없습니다")
            return announcements
        
        # 테이블의 tbody 찾기
        tbody = table.find('tbody')
        if not tbody:
            tbody = table
        
        logger.info(f"테이블에서 {len(tbody.find_all('tr'))}개 행 발견")
        
        for row in tbody.find_all('tr'):
            try:
                # JBF는 class='tl'인 td에 제목이 있음
                title_cell = row.find('td', class_='tl')
                
                if title_cell:
                    # 링크 찾기
                    link_tag = title_cell.find('a')
                    if link_tag:
                        title = link_tag.get_text(strip=True)
                        if not title:
                            continue
                        
                        # URL 구성
                        href = link_tag.get('href', '')
                        detail_url = self._extract_detail_url(href)
                        
                        if detail_url:
                            announcement = {
                                'title': title,
                                'url': detail_url
                            }
                            
                            # 추가 정보 추출 (작성자, 날짜 등)
                            self._extract_additional_fields(row, announcement)
                            
                            announcements.append(announcement)
                            
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def _extract_detail_url(self, href: str) -> str:
        """상세 페이지 URL 추출 - JBF 특화"""
        if not href or href.startswith('#'):
            return None
        
        if href.startswith('http'):
            return href
        
        # board.action이 있으면 /main/을 추가해야 함
        if 'board.action' in href and not href.startswith('/main/'):
            href = '/main/' + href.lstrip('/')
        
        return urljoin(self.base_url, href)
    
    def _extract_additional_fields(self, row, announcement: dict):
        """추가 필드 추출"""
        try:
            # JBF 테이블 구조에 따른 추가 정보 추출
            tds = row.find_all('td')
            
            # 일반적인 게시판 구조: 번호, 제목, 작성자, 날짜, 조회수
            if len(tds) >= 4:
                # 작성자 (보통 3번째 td)
                if len(tds) > 2:
                    writer_text = tds[2].get_text(strip=True)
                    if writer_text:
                        announcement['writer'] = writer_text
                
                # 날짜 (보통 4번째 td)
                if len(tds) > 3:
                    date_text = tds[3].get_text(strip=True)
                    if date_text:
                        announcement['date'] = date_text
                
                # 조회수 (보통 5번째 td)
                if len(tds) > 4:
                    views_text = tds[4].get_text(strip=True)
                    if views_text:
                        announcement['views'] = views_text
                        
        except Exception as e:
            logger.error(f"추가 필드 추출 중 오류: {e}")
    
    def parse_detail_page(self, html_content: str) -> dict:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        result = {
            'content': '',
            'attachments': []
        }
        
        try:
            # 본문 추출
            content = self._extract_content(soup)
            result['content'] = content
            
            # 첨부파일 추출
            attachments = self._extract_attachments(soup)
            result['attachments'] = attachments
            
            logger.debug(f"상세 페이지 파싱 완료 - 내용: {len(content)}자, 첨부파일: {len(attachments)}개")
            
        except Exception as e:
            logger.error(f"상세 페이지 파싱 중 오류: {e}")
        
        return result
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """본문 내용 추출 - JBF 특화"""
        content_area = None
        
        # JBF의 다양한 본문 컨테이너 시도
        content_selectors = [
            '.table_con',
            '.view_con', 
            '.board_view',
            '.content'
        ]
        
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        if not content_area:
            # 대체 방법: td.content 클래스
            content_area = soup.find('td', class_='content')
            if content_area:
                logger.debug("본문을 td.content로 찾음")
        
        if not content_area:
            # 대체 방법: 가장 큰 텍스트 블록 찾기
            all_divs = soup.find_all(['div', 'td'])
            if all_divs:
                content_area = max(all_divs, key=lambda x: len(x.get_text()))
                logger.debug("본문을 최대 텍스트 블록으로 추정")
        
        if content_area:
            # HTML을 마크다운으로 변환
            return self.h.handle(str(content_area))
        else:
            logger.warning("본문 내용을 찾을 수 없습니다")
            logger.debug(f"HTML 길이: {len(str(soup))}")
            return ""
    
    def _extract_attachments(self, soup: BeautifulSoup) -> list:
        """첨부파일 목록 추출 - JBF 특화"""
        attachments = []
        file_areas = []
        
        # JBF의 첨부파일 영역 찾기
        
        # 패턴 1: div.file 클래스
        file_area = soup.find('div', class_='file')
        if file_area:
            file_areas.append(file_area)
            logger.debug("첨부파일 영역을 div.file로 찾음")
        
        # 패턴 2: '첨부파일' 텍스트가 있는 th와 같은 행의 td
        for th in soup.find_all('th'):
            if '첨부파일' in th.get_text():
                parent_tr = th.find_parent('tr')
                if parent_tr:
                    td = parent_tr.find('td')
                    if td:
                        file_areas.append(td)
                        logger.debug("첨부파일 영역을 '첨부파일' th의 td로 찾음")
        
        # 패턴 3: 일반적인 파일 링크 패턴
        if not file_areas:
            # 전체 페이지에서 파일 다운로드 관련 링크 찾기
            file_links = soup.find_all('a', href=True)
            for link in file_links:
                href = link.get('href', '')
                onclick = link.get('onclick', '')
                if 'fileDown' in href or 'fn_fileDown' in onclick or 'download' in href.lower():
                    file_areas.append(link.parent or link)
                    break
        
        # 파일 링크 추출
        for area in file_areas:
            for link in area.find_all('a'):
                file_name = link.get_text(strip=True)
                href = link.get('href', '')
                onclick = link.get('onclick', '')
                
                file_url = None
                
                # JBF의 JavaScript 파일 다운로드 처리
                if onclick and 'fn_fileDown' in onclick:
                    # JavaScript 함수에서 파일 다운로드 파라미터 추출
                    # 예: fn_fileDown('파일ID')
                    match = re.search(r"fn_fileDown\('([^']+)'\)", onclick)
                    if match:
                        file_id = match.group(1)
                        file_url = f"{self.base_url}/main/fileDown.action?file_id={file_id}"
                        logger.debug(f"JavaScript 파일 다운로드 URL 생성: {file_url}")
                
                # 직접 링크 처리
                elif href and not href.startswith('#'):
                    if href.startswith('http'):
                        file_url = href
                    else:
                        file_url = urljoin(self.base_url, href)
                    logger.debug(f"직접 파일 링크: {file_url}")
                
                # 파일명이 있고 URL이 유효하면 추가
                if file_name and file_url and not file_name.isspace():
                    # 중복 체크
                    if not any(att['url'] == file_url for att in attachments):
                        attachments.append({
                            'name': file_name,
                            'url': file_url
                        })
                        logger.debug(f"첨부파일 추가: {file_name}")
        
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment_info: dict = None) -> bool:
        """파일 다운로드 - JBF 맞춤형"""
        try:
            logger.info(f"파일 다운로드 시작: {url}")
            
            # JBF 특화 헤더 설정
            headers = self.headers.copy()
            headers['Referer'] = self.base_url
            
            response = self.session.get(
                url, 
                headers=headers, 
                stream=True, 
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # 실제 파일명 추출 (기본 구현 사용)
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
JBFScraper = EnhancedJBFScraper