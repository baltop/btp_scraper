# -*- coding: utf-8 -*-
"""
Enhanced 금융보안원 Fintech 스크래퍼 - 향상된 버전
사이트: https://fintech.or.kr/web/board/boardContentsListPage.do?board_id=3&menu_id=6300&miv_pageNo=
"""

import re
import requests
import json
import os
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, unquote
import logging
from enhanced_base_scraper import StandardTableScraper
from typing import Dict, List, Any
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

class EnhancedFintechScraper(StandardTableScraper):
    """금융보안원 Fintech 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://fintech.or.kr"
        self.list_url = "https://fintech.or.kr/web/board/boardContentsListPage.do?board_id=3&menu_id=6300&miv_pageNo="
        self.detail_url = "https://fintech.or.kr/web/board/boardContentsView.do"
        
        # 사이트 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        
        # Fintech 특화 설정
        self.board_id = "3"
        self.menu_id = "6300"
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - GET 파라미터 방식"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: Fintech는 miv_pageNo 파라미터 사용
        return f"https://fintech.or.kr/web/board/boardContentsListPage.do?board_id=3&menu_id=6300&miv_pageNo={page_num}"
    
    def get_page(self, url: str, **kwargs) -> requests.Response:
        """페이지 가져오기 - 목록 페이지만 Playwright 사용"""
        # 목록 페이지인지 확인
        is_list_page = 'boardContentsListPage.do' in url
        
        if is_list_page:
            # 목록 페이지는 Playwright 사용 (동적 렌더링 필요)
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    
                    # 페이지 로드 - 더 짧은 타임아웃
                    page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    
                    # 테이블이 로드될 때까지 대기 - 더 짧은 타임아웃
                    page.wait_for_selector('table', timeout=5000)
                    
                    # HTML 컨텐츠 가져오기
                    html_content = page.content()
                    browser.close()
                    
                    # requests.Response 객체 모방
                    class MockResponse:
                        def __init__(self, text, status_code=200, encoding='utf-8'):
                            self.text = text
                            self.status_code = status_code
                            self.encoding = encoding
                            self.headers = {'Content-Type': 'text/html;charset=UTF-8'}
                        
                        def raise_for_status(self):
                            if self.status_code >= 400:
                                raise requests.HTTPError(f"{self.status_code} Error")
                    
                    return MockResponse(html_content)
                    
            except Exception as e:
                logger.warning(f"Playwright 로딩 실패, requests로 폴백: {e}")
                return super().get_page(url, **kwargs)
        else:
            # 상세 페이지는 requests 직접 사용 (빠른 속도)
            return super().get_page(url, **kwargs)
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: Fintech 특화 파싱
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """Fintech 특화 목록 파싱"""
        announcements = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 테이블 찾기
            table = soup.find('table')
            if not table:
                logger.warning("테이블을 찾을 수 없습니다")
                return announcements
            
            tbody = table.find('tbody') or table
            rows = tbody.find_all('tr')
            
            logger.info(f"테이블에서 {len(rows)}개 행 발견")
            
            # 각 행 파싱
            for row in rows:
                try:
                    cells = row.find_all('td')
                    if len(cells) < 4:  # 최소 번호, 제목, 날짜, 조회수 필요
                        continue
                    
                    # 제목 셀에서 링크 찾기 (두 번째 열)
                    title_cell = cells[1]
                    link_elem = title_cell.find('a', href=re.compile(r'javascript:contentsView'))
                    
                    if not link_elem:
                        continue
                    
                    # 제목 추출
                    title = link_elem.get_text(strip=True)
                    if not title:
                        continue
                    
                    # JavaScript 함수에서 ID 추출
                    # contentsView('099f147a848c48babc64eeaa536b5ae2') 형태
                    href = link_elem.get('href', '')
                    id_match = re.search(r"contentsView\('([^']+)'\)", href)
                    if not id_match:
                        continue
                    
                    content_id = id_match.group(1)
                    
                    # 상세 페이지 URL 구성
                    detail_url = f"{self.detail_url}?board_id={self.board_id}&menu_id={self.menu_id}&contents_id={content_id}"
                    
                    # 날짜 추출
                    date_cell = cells[3] if len(cells) > 3 else None
                    date_text = date_cell.get_text(strip=True) if date_cell else ''
                    
                    announcement = {
                        'title': title,
                        'url': detail_url,
                        'content_id': content_id,
                        'date': date_text,
                        'number': cells[0].get_text(strip=True) if cells[0] else '',
                        'views': cells[4].get_text(strip=True) if len(cells) > 4 else ''
                    }
                    
                    announcements.append(announcement)
                    logger.debug(f"공고 파싱 완료: {title[:50]}...")
                    
                except Exception as e:
                    logger.error(f"행 파싱 중 오류: {e}")
                    continue
            
            logger.info(f"{len(announcements)}개 공고 파싱 완료")
            return announcements
            
        except Exception as e:
            logger.error(f"목록 페이지 파싱 실패: {e}")
            return announcements
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱 - Enhanced 아키텍처 호환성용"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 본문 내용 추출
            content = self._extract_content(soup)
            
            # 첨부파일 추출
            attachments = self._extract_attachments(soup)
            
            return {
                'content': content,
                'attachments': attachments
            }
            
        except Exception as e:
            logger.error(f"상세 페이지 파싱 실패: {e}")
            return {'content': '', 'attachments': []}
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """본문 내용 추출"""
        content_parts = []
        
        # 본문 내용 찾기 - Fintech 특화
        content_area = None
        
        # Fintech 특화 선택자들 시도
        for selector in ['.content', '.view_content', '.board_view_content']:
            content_area = soup.select_one(selector)
            if content_area:
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        if content_area:
            # HTML을 마크다운으로 변환
            content_text = content_area.get_text(separator='\n', strip=True)
            content_parts.append(f"\n{content_text}\n")
        else:
            logger.warning("본문 영역을 찾을 수 없습니다")
        
        return "\n".join(content_parts)
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """첨부파일 추출 - 직접 다운로드 링크 방식"""
        attachments = []
        
        try:
            # fileidDownLoad.do 링크 찾기 (Fintech 특화)
            download_links = soup.find_all('a', href=re.compile(r'fileidDownLoad\.do'))
            
            for link in download_links:
                try:
                    href = link.get('href', '')
                    filename = link.get_text(strip=True)
                    
                    # 파일 ID 추출
                    # fileidDownLoad.do?file_id=BBA480BE44EA11F09056F220EF342366 형태
                    file_id_match = re.search(r'file_id=([A-F0-9]+)', href)
                    if file_id_match:
                        file_id = file_id_match.group(1)
                        
                        # 절대 URL 구성
                        if href.startswith('http'):
                            file_url = href
                        else:
                            file_url = urljoin(self.base_url, href)
                        
                        # 파일명에서 괄호 안의 크기 정보 제거
                        clean_filename = re.sub(r'\([^)]+\)$', '', filename).strip()
                        
                        attachments.append({
                            'name': clean_filename,
                            'url': file_url,
                            'file_id': file_id,
                            'original_text': filename
                        })
                        logger.debug(f"첨부파일 발견: {clean_filename}")
                    
                except Exception as e:
                    logger.error(f"첨부파일 파싱 중 오류: {e}")
                    continue
            
            # 추가로 이미지 파일 찾기 (본문 내 업로드 이미지만, 아이콘 제외)
            images = soup.find_all('img')
            for img in images:
                try:
                    src = img.get('src', '')
                    if src and ('upload' in src or 'file' in src):
                        # 아이콘 파일 제외
                        if 'icon' in src.lower() or src.endswith('icon_file.png'):
                            continue
                            
                        # 상대 URL을 절대 URL로 변환
                        if src.startswith('/'):
                            file_url = urljoin(self.base_url, src)
                        elif not src.startswith('http'):
                            file_url = urljoin(self.base_url, src)
                        else:
                            file_url = src
                        
                        # 파일명 추출
                        file_name = src.split('/')[-1]
                        if '?' in file_name:
                            file_name = file_name.split('?')[0]
                        
                        try:
                            file_name = unquote(file_name)
                        except:
                            pass
                        
                        if file_name and file_name not in [att['name'] for att in attachments]:
                            attachments.append({
                                'name': file_name,
                                'url': file_url,
                                'type': 'image'
                            })
                            logger.debug(f"이미지 파일 발견: {file_name}")
                    
                except Exception as e:
                    logger.error(f"이미지 파일 처리 중 오류: {e}")
                    continue
            
            logger.info(f"{len(attachments)}개 첨부파일 발견")
            return attachments
            
        except Exception as e:
            logger.error(f"첨부파일 추출 실패: {e}")
            return attachments
    
    def download_file(self, url: str, save_path: str, filename: str = "") -> bool:
        """Fintech 전용 파일 다운로드"""
        try:
            # 요청 헤더 설정
            headers = {
                'Referer': self.list_url,
                'User-Agent': self.headers.get('User-Agent', 'Mozilla/5.0'),
                'Accept': 'application/octet-stream,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
            
            # 파일 다운로드 요청
            response = self.session.get(
                url,
                headers=headers,
                timeout=60,  # 파일 다운로드는 긴 타임아웃
                verify=self.verify_ssl,
                stream=True
            )
            
            response.raise_for_status()
            
            # Content-Type 확인으로 성공 여부 검증
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' in content_type and 'image' not in content_type:
                logger.warning(f"파일 다운로드 실패 - HTML 응답 받음: {url}")
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
                logger.warning(f"빈 파일 다운로드됨: {save_path}")
                os.remove(save_path)
                return False
            
            logger.info(f"파일 다운로드 성공: {save_path} ({file_size:,} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"파일 다운로드 실패 {url}: {e}")
            # 실패한 파일이 있으면 삭제
            if os.path.exists(save_path):
                try:
                    os.remove(save_path)
                except:
                    pass
            return False


# 하위 호환성을 위한 별칭
FintechScraper = EnhancedFintechScraper