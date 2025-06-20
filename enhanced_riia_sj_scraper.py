# -*- coding: utf-8 -*-
"""
세종지역혁신진흥원(RIIA_SJ) Enhanced 스크래퍼 - UUID 기반 표준 테이블
"""

import requests
from bs4 import BeautifulSoup
import re
import logging
import os
from urllib.parse import urljoin, parse_qs, urlparse, unquote
from enhanced_base_scraper import StandardTableScraper
import time
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class EnhancedRIIASJScraper(StandardTableScraper):
    """세종지역혁신진흥원(RIIA_SJ) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        
        # 향상된 헤더 설정 (차단 방지)
        self.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1',
            'Cache-Control': 'max-age=0',
        })
        self.session.headers.update(self.headers)
        
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://sj.riia.or.kr"
        self.list_url = "https://sj.riia.or.kr/board/businessAnnouncement"
        
        # 사이트 특화 설정
        self.verify_ssl = False  # SSL 인증서 문제 해결
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 2
        
        # 페이지 제한 (사이트에 2페이지만 존재)
        self.max_available_pages = 2
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - RIIA_SJ 페이지네이션 패턴"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: RIIA_SJ 특화 로직
        if page_num == 1:
            return self.list_url
        elif page_num <= self.max_available_pages:
            # 다양한 페이지네이션 패턴 시도
            possible_urls = [
                f"{self.list_url}?page={page_num}",
                f"{self.list_url}?pageNo={page_num}",
                f"{self.list_url}?p={page_num}",
                f"{self.list_url}?pageIndex={page_num}",
                f"{self.list_url}/{page_num}",
            ]
            return possible_urls[0]  # 기본적으로 첫 번째 패턴 사용
        else:
            logger.warning(f"페이지 {page_num}는 최대 페이지 수({self.max_available_pages})를 초과합니다")
            return None
    
    def fetch_page_content(self, url: str) -> str:
        """페이지 내용 가져오기 - 강화된 에러 처리"""
        try:
            response = self.session.get(url, verify=self.verify_ssl, timeout=self.timeout)
            
            # 500 에러인 경우 다른 URL 패턴 시도
            if response.status_code == 500:
                logger.warning(f"500 에러 발생: {url}")
                # URL에서 페이지 번호 추출
                page_num = self._extract_page_number(url)
                if page_num and page_num > 1:
                    # 다른 패턴들 시도
                    alternative_urls = [
                        f"{self.list_url}?pageNo={page_num}",
                        f"{self.list_url}?p={page_num}",
                        f"{self.list_url}?pageIndex={page_num}",
                        f"{self.list_url}/{page_num}",
                    ]
                    
                    for alt_url in alternative_urls:
                        try:
                            logger.info(f"대체 URL 시도: {alt_url}")
                            alt_response = self.session.get(alt_url, verify=self.verify_ssl, timeout=self.timeout)
                            if alt_response.status_code == 200:
                                logger.info(f"대체 URL 성공: {alt_url}")
                                return alt_response.text
                        except Exception as e:
                            logger.debug(f"대체 URL 실패 {alt_url}: {e}")
                            continue
                    
                    # 모든 패턴 실패 시 빈 응답 반환
                    logger.warning(f"페이지 {page_num}의 모든 URL 패턴 실패")
                    return ""
            
            response.raise_for_status()
            return response.text
            
        except Exception as e:
            logger.error(f"페이지 가져오기 실패 {url}: {e}")
            return ""
    
    def _extract_page_number(self, url: str) -> int:
        """URL에서 페이지 번호 추출"""
        patterns = [
            r'[?&]page=(\d+)',
            r'[?&]pageNo=(\d+)',
            r'[?&]p=(\d+)',
            r'[?&]pageIndex=(\d+)',
            r'/(\d+)$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return int(match.group(1))
        return 1
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: 사이트 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """RIIA_SJ 특화된 목록 파싱 로직"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 테이블 찾기 - 여러 후보 시도
        table = None
        for selector in ['table', '.board-table', '.table', 'table.table']:
            if selector == 'table':
                table = soup.find('table')
            else:
                table = soup.select_one(selector)
            if table:
                logger.debug(f"테이블을 {selector} 선택자로 찾음")
                break
        
        if not table:
            logger.warning("공고 목록 테이블을 찾을 수 없습니다")
            return announcements
        
        # tbody 또는 직접 테이블에서 행 찾기
        tbody = table.find('tbody') or table
        rows = tbody.find_all('tr')
        
        # 헤더 행 제외 (첫 번째 행이 헤더인 경우)
        if rows and len(rows) > 0:
            first_row_cells = rows[0].find_all(['th', 'td'])
            if first_row_cells and any('번호' in cell.get_text() for cell in first_row_cells):
                rows = rows[1:]  # 헤더 행 제외
        
        if not rows:
            logger.warning("테이블 행을 찾을 수 없습니다")
            return announcements
        
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for i, row in enumerate(rows):
            try:
                cells = row.find_all(['td', 'th'])
                if len(cells) < 5:  # 번호, 제목, 접수기간, 상태, 작성일, 조회 최소 5개 필요
                    logger.debug(f"행 {i}: 셀 수 부족 ({len(cells)}개)")
                    continue
                
                # 제목 셀에서 링크 찾기 (두 번째 셀)
                title_cell = cells[1] if len(cells) > 1 else cells[0]
                link_elem = title_cell.find('a')
                
                if not link_elem:
                    logger.debug(f"행 {i}: 링크를 찾을 수 없음")
                    continue
                
                # 제목과 URL 추출
                title = link_elem.get_text(strip=True)
                href = link_elem.get('href', '')
                
                if not title or len(title) < 3:
                    logger.debug(f"행 {i}: 제목이 너무 짧음: '{title}'")
                    continue
                
                # URL 정규화 (UUID 기반)
                if href.startswith('/'):
                    detail_url = f"{self.base_url}{href}"
                elif href.startswith('http'):
                    detail_url = href
                else:
                    detail_url = urljoin(self.base_url, href)
                
                # 공고 번호 추출 (첫 번째 셀)
                number = ""
                number_cell = cells[0]
                if number_cell:
                    number_text = number_cell.get_text(strip=True)
                    if number_text and number_text != "번호":
                        number = number_text
                
                # 접수기간 추출 (세 번째 셀)
                period = ""
                if len(cells) > 2:
                    period_cell = cells[2]
                    period = period_cell.get_text(strip=True)
                
                # 상태 추출 (네 번째 셀)
                status = ""
                if len(cells) > 3:
                    status_cell = cells[3]
                    status = status_cell.get_text(strip=True)
                
                # 작성일 추출 (다섯 번째 셀)
                date = ""
                if len(cells) > 4:
                    date_cell = cells[4]
                    date_text = date_cell.get_text(strip=True)
                    # 날짜 패턴 매칭 (YYYY-MM-DD)
                    date_match = re.search(r'(\d{4}-\d{1,2}-\d{1,2})', date_text)
                    if date_match:
                        date = date_match.group(1)
                
                # 조회수 추출 (여섯 번째 셀)
                views = ""
                if len(cells) > 5:
                    views_cell = cells[5]
                    views = views_cell.get_text(strip=True)
                
                logger.debug(f"행 {i}: 공고 발견 - {title[:30]}... (날짜: {date})")
                
                # 공고 정보 구성
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'number': number,
                    'period': period,
                    'status': status,
                    'date': date,
                    'views': views,
                    'summary': ""
                }
                
                announcements.append(announcement)
                
            except Exception as e:
                logger.error(f"행 {i} 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str, announcement_url: str = None) -> Dict[str, Any]:
        """상세 페이지 파싱 - RIIA_SJ 실제 HTML 구조 기반"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 제목 추출
        title = ""
        # 제목 후보들 검색 (h1, h2, h3, h4 순서로)
        for tag in ['h1', 'h2', 'h3', 'h4']:
            title_elem = soup.find(tag)
            if title_elem:
                title_text = title_elem.get_text(strip=True)
                if title_text and len(title_text) > 5:  # 유효한 제목
                    title = title_text
                    logger.debug(f"제목을 {tag} 태그에서 찾음: {title[:50]}...")
                    break
        
        # 본문 내용 추출
        content = ""
        
        # 방법 1: 긴 텍스트를 포함한 div나 section에서 본문 찾기
        content_candidates = []
        for elem in soup.find_all(['div', 'section', 'article', 'main']):
            elem_text = elem.get_text(strip=True)
            if len(elem_text) > 100:  # 충분히 긴 텍스트
                content_candidates.append((len(elem_text), elem_text))
        
        # 가장 긴 텍스트를 본문으로 선택
        if content_candidates:
            content_candidates.sort(key=lambda x: x[0], reverse=True)
            content = content_candidates[0][1]
            logger.debug(f"본문 추출: {len(content)}자")
        
        # 방법 2: 백업 - 전체 텍스트에서 본문 부분 추출
        if not content or len(content) < 50:
            all_text = soup.get_text()
            # 본문 시작점 찾기
            content_start_markers = ['공고', '모집', '지원사업', '신청', '선정', '사업']
            for marker in content_start_markers:
                if marker in all_text:
                    start_idx = all_text.find(marker)
                    content = all_text[start_idx:start_idx+3000]  # 적당한 길이로 제한
                    break
        
        if not content or len(content) < 30:
            logger.warning("본문 영역을 찾을 수 없거나 내용이 부족합니다")
            content = "본문 내용을 추출할 수 없습니다."
        else:
            logger.info(f"본문 추출 성공: {len(content)}자")
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup, announcement_url)
        
        return {
            'title': title,
            'content': content,
            'attachments': attachments
        }
    
    def _extract_attachments(self, soup: BeautifulSoup, page_url: str = None) -> List[Dict[str, Any]]:
        """첨부파일 추출 - RIIA_SJ UUID 기반 다운로드"""
        attachments = []
        
        # 첨부파일 다운로드 링크 찾기 (/file/download?id=UUID 패턴)
        for link in soup.find_all('a'):
            href = link.get('href', '')
            
            # 파일 다운로드 링크 확인
            if '/file/download' in href and 'id=' in href:
                # 파일명 추출 (링크 텍스트에서)
                filename = link.get_text(strip=True)
                
                # 절대 URL로 변환
                if href.startswith('/'):
                    download_url = f"{self.base_url}{href}"
                else:
                    download_url = href
                
                if filename and download_url:
                    attachments.append({
                        'name': filename,
                        'url': download_url
                    })
                    
                    logger.debug(f"UUID 첨부파일 발견: {filename}")
        
        # dl/dt/dd 구조에서도 첨부파일 찾기
        for dl in soup.find_all('dl'):
            dt = dl.find('dt')
            dd = dl.find('dd')
            
            if dt and dd and '첨부' in dt.get_text():
                for link in dd.find_all('a'):
                    href = link.get('href', '')
                    if '/file/download' in href:
                        filename = link.get_text(strip=True)
                        download_url = f"{self.base_url}{href}" if href.startswith('/') else href
                        
                        if filename and download_url:
                            attachments.append({
                                'name': filename,
                                'url': download_url
                            })
                            
                            logger.debug(f"DL 구조 첨부파일 발견: {filename}")
        
        logger.info(f"총 {len(attachments)}개 첨부파일 발견")
        return attachments
    
    def download_file(self, url: str, save_path: str, filename: str = None) -> bool:
        """파일 다운로드 - RIIA_SJ 세션 관리"""
        try:
            logger.info(f"파일 다운로드 시도: {url}")
            
            # 강화된 헤더로 다운로드 시도
            download_headers = self.headers.copy()
            download_headers.update({
                'Referer': self.base_url,
                'Accept': '*/*',
            })
            
            response = self.session.get(
                url, 
                headers=download_headers,
                verify=self.verify_ssl,
                stream=True,
                timeout=120
            )
            
            # 응답 상태 확인
            if response.status_code != 200:
                logger.error(f"파일 다운로드 실패 {url}: HTTP {response.status_code}")
                return False
            
            # Content-Type 확인
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' in content_type:
                logger.warning(f"HTML 응답 수신 (로그인 필요?): {url}")
                return False
            
            # 파일 저장
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # 파일 크기 확인
            file_size = os.path.getsize(save_path)
            if file_size == 0:
                logger.error(f"다운로드된 파일이 비어있음: {save_path}")
                os.remove(save_path)
                return False
            
            logger.info(f"파일 다운로드 완료: {save_path} ({file_size:,} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"파일 다운로드 중 오류 {url}: {e}")
            return False
    
    def _create_meta_info(self, announcement: Dict[str, Any]) -> str:
        """RIIA_SJ 메타 정보 생성"""
        meta_lines = [f"# {announcement['title']}", ""]
        
        # RIIA_SJ 특화 메타 정보
        if 'number' in announcement and announcement['number']:
            meta_lines.append(f"**공고번호**: {announcement['number']}")
        if 'period' in announcement and announcement['period']:
            meta_lines.append(f"**접수기간**: {announcement['period']}")
        if 'status' in announcement and announcement['status']:
            meta_lines.append(f"**상태**: {announcement['status']}")
        if 'date' in announcement and announcement['date']:
            meta_lines.append(f"**작성일**: {announcement['date']}")
        if 'views' in announcement and announcement['views']:
            meta_lines.append(f"**조회수**: {announcement['views']}")
        if 'summary' in announcement and announcement['summary']:
            meta_lines.append(f"**요약**: {announcement['summary']}")
        
        meta_lines.extend([
            f"**원본 URL**: {announcement['url']}",
            "",
            "---",
            ""
        ])
        
        return "\n".join(meta_lines)

# 하위 호환성을 위한 별칭
RIIASJScraper = EnhancedRIIASJScraper