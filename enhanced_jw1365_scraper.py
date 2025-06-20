# -*- coding: utf-8 -*-
"""
Enhanced 1365 자원봉사포털 스크래퍼 - 향상된 버전
사이트: https://www.1365.go.kr/vols/P9420/bbs/bbs.do?bbsNo=994100&titleNm=%EB%AA%A9%EB%A1%9D
"""

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, unquote
import logging
from enhanced_base_scraper import StandardTableScraper
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class EnhancedJW1365Scraper(StandardTableScraper):
    """1365 자원봉사포털 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://www.1365.go.kr"
        self.list_url = "https://www.1365.go.kr/vols/P9420/bbs/bbs.do?bbsNo=994100&titleNm=%EB%AA%A9%EB%A1%9D"
        
        # 사이트 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - POST 요청 방식"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: 1365는 POST 요청으로 페이지네이션 처리
        return self.list_url
    
    def _get_page_announcements(self, page_num: int) -> List[Dict[str, Any]]:
        """페이지별 공고 목록 가져오기 - POST 요청 처리"""
        # 첫 페이지는 GET 요청
        if page_num == 1:
            response = self.get_page(self.list_url)
        else:
            # 2페이지부터는 POST 요청
            post_data = {
                'bbsNo': '994100',
                'titleNm': '목록',
                'cPage': str(page_num),
                'searchFlag': 'search'
            }
            response = self.post_page(self.list_url, data=post_data)
        
        if not response:
            logger.warning(f"페이지 {page_num} 응답을 가져올 수 없습니다")
            return []
        
        # 페이지가 에러 상태거나 잘못된 경우 감지
        if response.status_code >= 400:
            logger.warning(f"페이지 {page_num} HTTP 에러: {response.status_code}")
            return []
        
        announcements = self.parse_list_page(response.text)
        
        # 추가 마지막 페이지 감지 로직
        if not announcements and page_num > 1:
            logger.info(f"페이지 {page_num}에 공고가 없어 마지막 페이지로 판단됩니다")
        
        return announcements
    
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
        table_selectors = ['table', '.board_list table', '.board_nomal table']
        
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
                
                # 최소한의 셀 수 확인 (번호, 제목, 작성자, 작성일, 조회수)
                if len(cells) < 5:
                    continue
                
                # 제목 셀 (두 번째 셀, 인덱스 1)
                title_cell = cells[1]
                
                # 링크 엘리먼트 찾기
                link_elem = title_cell.find('a')
                if not link_elem:
                    continue
                
                # 제목과 JavaScript 함수 추출
                title = link_elem.get_text(strip=True)
                if not title or title in ['제목', '번호']:  # 헤더 행 제외
                    continue
                
                href = link_elem.get('href', '')
                if href.startswith('javascript:'):
                    # JavaScript 함수에서 파라미터 추출: show(994100,2066,0)
                    js_match = re.search(r'show\((\d+),(\d+),(\d+)\)', href)
                    if js_match:
                        bbs_no = js_match.group(1)
                        bbsctt_no = js_match.group(2)
                        bbsctt_answer_no = js_match.group(3)
                        
                        # 상세 페이지 URL 구성
                        detail_url = f"{self.base_url}/vols/P9420/bbs/bbs.do?type=show&bbsNo={bbs_no}&bbsctt_no={bbsctt_no}&bbsctt_answer_no={bbsctt_answer_no}&titleNm=상세보기"
                    else:
                        continue
                else:
                    # 직접 링크인 경우
                    detail_url = urljoin(self.base_url, href)
                
                # 기본 공고 정보
                announcement = {
                    'title': title,
                    'url': detail_url
                }
                
                # 추가 메타데이터 추출
                try:
                    # 작성자 (세 번째 셀, 인덱스 2)
                    writer_cell = cells[2]
                    writer_text = writer_cell.get_text(strip=True)
                    if writer_text:
                        announcement['writer'] = writer_text
                    
                    # 작성일 (네 번째 셀, 인덱스 3)
                    date_cell = cells[3]
                    date_text = date_cell.get_text(strip=True)
                    if date_text and len(date_text) >= 8:  # 날짜 형식 확인
                        announcement['date'] = date_text
                    
                    # 조회수 (다섯 번째 셀, 인덱스 4)
                    views_cell = cells[4]
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
            '.content_view',
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
            for unwanted in content_area.select('script, style, .btn_area, .board_nav, .location, .content_header'):
                unwanted.decompose()
            
            # HTML을 마크다운으로 변환
            content = self.h.handle(str(content_area))
        else:
            # Fallback: body 전체에서 텍스트 추출
            logger.warning("본문 영역을 찾을 수 없어 전체 페이지에서 추출합니다")
            # 헤더, 네비게이션 등 제거
            for unwanted in soup.select('header, nav, .header, .nav, .gnb, .snb, .footer, script, style, .location'):
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
        
        # 1365 사이트는 대부분 이미지나 링크가 본문에 포함되어 있음
        # 이미지 파일 추출
        images = soup.find_all('img')
        for img in images:
            src = img.get('src', '')
            if src and (src.startswith('/upload') or 'upload' in src):
                # 상대 URL을 절대 URL로 변환
                file_url = urljoin(self.base_url, src)
                
                # 파일명 추출
                file_name = src.split('/')[-1]
                if not file_name:
                    file_name = f"image_{len(attachments)+1}.jpg"
                
                # URL 디코딩으로 한글 파일명 복구
                try:
                    file_name = unquote(file_name)
                except:
                    pass
                
                attachments.append({
                    'name': file_name,
                    'url': file_url
                })
                logger.debug(f"이미지 파일 발견: {file_name}")
        
        # 다운로드 링크 찾기 (PDF, HWP 등)
        download_links = soup.find_all('a', href=re.compile(r'\.(pdf|hwp|doc|docx|xls|xlsx|ppt|pptx|zip)$', re.I))
        for link in download_links:
            href = link.get('href', '')
            file_name = link.get_text(strip=True) or href.split('/')[-1]
            
            if href:
                file_url = urljoin(self.base_url, href)
                
                # URL 디코딩으로 한글 파일명 복구
                try:
                    file_name = unquote(file_name)
                except:
                    pass
                
                attachments.append({
                    'name': file_name,
                    'url': file_url
                })
                logger.debug(f"다운로드 링크 발견: {file_name}")
        
        logger.info(f"{len(attachments)}개 첨부파일 발견")
        return attachments


# 하위 호환성을 위한 별칭
JW1365Scraper = EnhancedJW1365Scraper