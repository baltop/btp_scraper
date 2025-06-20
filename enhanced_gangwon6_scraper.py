# -*- coding: utf-8 -*-
"""
Enhanced 강원6차산업지원센터 스크래퍼 - 향상된 버전
사이트: https://gangwon6.co.kr/information/notices
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

class EnhancedGangwon6Scraper(StandardTableScraper):
    """강원6차산업지원센터 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://gangwon6.co.kr"
        self.list_url = "https://gangwon6.co.kr/information/notices"
        
        # 사이트 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        
        # Gangwon6 특화 설정
        self.aws_s3_base = "gangwon6.s3.ap-northeast-2.amazonaws.com"
        self.api_base_url = "https://api.gangwon6.co.kr"
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 API URL 생성 - REST API 기반"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: Gangwon6 API 직접 호출
        guest_id = int(time.time() * 1000)  # 현재 타임스탬프 (밀리초)
        return f"{self.api_base_url}/api/notices?page={page_num}&column=title&word=&guest_id={guest_id}"
    
    def get_page(self, url: str, **kwargs) -> requests.Response:
        """페이지 가져오기 - Nuxt.js JavaScript 렌더링 필요"""
        # Gangwon6는 모든 페이지가 Nuxt.js 기반이므로 Playwright 사용
        if '/information/notices' in url:
            return self._get_page_with_playwright(url)
        else:
            # 외부 링크나 파일 다운로드는 requests 사용
            return super().get_page(url, **kwargs)
    
    def _get_page_with_playwright(self, url: str, page_num: int = 1) -> requests.Response:
        """Playwright를 사용한 JavaScript 렌더링 페이지 가져오기"""
        try:
            # 목록 페이지인지 상세 페이지인지 확인
            is_list_page = url == self.list_url or ('/notices' in url and not url.split('/')[-1].isdigit())
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # 페이지 로드
                page.goto(url, wait_until="networkidle", timeout=30000)
                
                if is_list_page:
                    # 목록 페이지 처리
                    # 특정 페이지로 이동 (2페이지 이상)
                    if page_num > 1:
                        # go_Page JavaScript 함수 실행
                        try:
                            page.evaluate(f"go_Page({page_num})")
                            page.wait_for_load_state("networkidle", timeout=15000)
                        except Exception as e:
                            logger.warning(f"페이지 {page_num} 이동 실패: {e}")
                    
                    # 동적 콘텐츠 로드 대기
                    page.wait_for_timeout(3000)  # 3초 대기
                    
                    # 테이블이 로드될 때까지 대기
                    page.wait_for_selector('table tbody tr', timeout=15000)
                else:
                    # 상세 페이지 처리 - 짧은 대기 시간
                    page.wait_for_timeout(2000)  # 2초만 대기
                    
                    # 본문이나 콘텐츠 영역이 로드될 때까지 대기 (선택적)
                    try:
                        page.wait_for_selector('main, .content, .container', timeout=5000)
                    except:
                        pass  # 타임아웃되어도 계속 진행
                
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
            return super().get_page(url)
    
    def _get_page_announcements(self, page_num: int) -> List[Dict[str, Any]]:
        """페이지별 공고 목록 가져오기 - API 직접 호출"""
        try:
            # API 직접 호출
            api_url = self.get_list_url(page_num)
            logger.info(f"API 호출: {api_url}")
            
            response = self.session.get(api_url, timeout=self.timeout)
            response.raise_for_status()
            
            # JSON 응답 파싱
            api_data = response.json()
            
            # API 데이터에서 공고 목록 추출
            announcements = self.parse_api_response(api_data)
            
            # 마지막 페이지 감지
            if not announcements and page_num > 1:
                logger.info(f"페이지 {page_num}에 공고가 없어 마지막 페이지로 판단됩니다")
            
            return announcements
            
        except Exception as e:
            logger.error(f"페이지 {page_num} API 호출 중 오류: {e}")
            return []
    
    def parse_api_response(self, api_data: dict) -> List[Dict[str, Any]]:
        """API 응답 파싱 - JSON 데이터 처리"""
        announcements = []
        
        try:
            data_list = api_data.get('data', [])
            logger.info(f"API에서 {len(data_list)}개 공고 발견")
            
            for item in data_list:
                try:
                    # 필수 필드 확인
                    if not item.get('id') or not item.get('title'):
                        continue
                    
                    # 상세 페이지 URL 구성
                    detail_url = f"{self.base_url}/information/notices/{item.get('id')}"
                    
                    announcement = {
                        'title': item.get('title', '').strip(),
                        'url': detail_url,
                        'id': item.get('id'),
                        'date': item.get('createdAt', ''),  # API 응답에 따라 조정 필요
                        'description': item.get('description', '')
                    }
                    
                    announcements.append(announcement)
                    logger.debug(f"API 공고 파싱 완료: {announcement['title'][:50]}...")
                    
                except Exception as e:
                    logger.error(f"API 항목 파싱 중 오류: {e}")
                    continue
            
            logger.info(f"API에서 {len(announcements)}개 공고 파싱 완료")
            return announcements
            
        except Exception as e:
            logger.error(f"API 응답 파싱 실패: {e}")
            return announcements

    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - 레거시 호환성용 (사용 안함)"""
        # API 기반으로 변경되어 더 이상 사용하지 않음
        # 기존 Enhanced 아키텍처와의 호환성을 위해 유지
        logger.warning("parse_list_page는 더 이상 사용되지 않습니다. parse_api_response를 사용하세요.")
        return []
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """Gangwon6 특화 목록 파싱"""
        announcements = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 테이블 찾기 - 여러 선택자 시도
            table = None
            for selector in ['table', '.notice-list table', '.board-table']:
                table = soup.find('table') if selector == 'table' else soup.select_one(selector)
                if table:
                    logger.debug(f"테이블을 {selector} 선택자로 찾음")
                    break
            
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
                    if len(cells) < 3:  # 최소 번호, 제목, 날짜 필요
                        continue
                    
                    # 제목 셀에서 링크 찾기 (보통 두 번째 열)
                    title_cell = cells[1] if len(cells) > 1 else cells[0]
                    link_elem = title_cell.find('a')
                    
                    if not link_elem:
                        continue
                    
                    # 제목 추출
                    title = link_elem.get_text(strip=True)
                    if not title:
                        continue
                    
                    # 상세 페이지 URL 구성
                    href = link_elem.get('href', '')
                    if href.startswith('/'):
                        detail_url = urljoin(self.base_url, href)
                    else:
                        detail_url = href
                    
                    # 날짜 추출 (세 번째 또는 네 번째 셀)
                    date_cell = cells[2] if len(cells) > 2 else None
                    date_text = date_cell.get_text(strip=True) if date_cell else ''
                    
                    # 번호 추출
                    number_cell = cells[0]
                    number_text = number_cell.get_text(strip=True) if number_cell else ''
                    
                    # 조회수 추출 (마지막 셀)
                    views_cell = cells[-1] if len(cells) > 3 else None
                    views_text = views_cell.get_text(strip=True) if views_cell else ''
                    
                    announcement = {
                        'title': title,
                        'url': detail_url,
                        'date': date_text,
                        'number': number_text,
                        'views': views_text
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
        
        # 제목 추출 - 다양한 선택자 시도
        title_elem = None
        for selector in ['h1', 'h2', '.title', '.notice-title', '.page-title']:
            title_elem = soup.select_one(selector)
            if title_elem:
                title_text = title_elem.get_text(strip=True)
                if title_text and len(title_text) > 5:  # 의미있는 제목만
                    content_parts.append(f"# {title_text}\n")
                    logger.debug(f"제목을 {selector} 선택자로 찾음: {title_text[:50]}...")
                    break
        
        # 본문 내용 찾기 - Gangwon6 Nuxt.js 특화
        content_text = ""
        
        # 1. 먼저 특정 선택자들 시도
        content_selectors = [
            '.notice-detail',
            '.detail-content', 
            '.view-content',
            '.notice-content',
            '.board-content',
            'main .content',
            '.container .content'
        ]
        
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                content_text = content_area.get_text(separator='\n', strip=True)
                if len(content_text) > 50:  # 의미있는 콘텐츠만
                    logger.debug(f"본문을 {selector} 선택자로 찾음")
                    break
        
        # 2. 선택자로 찾지 못했다면 p 태그들에서 추출
        if not content_text or len(content_text) < 50:
            paragraphs = soup.find_all('p')
            paragraph_texts = []
            for p in paragraphs:
                p_text = p.get_text(strip=True)
                if len(p_text) > 10:  # 짧은 텍스트는 제외
                    paragraph_texts.append(p_text)
            
            if paragraph_texts:
                content_text = '\n\n'.join(paragraph_texts)
                logger.debug(f"본문을 p 태그들에서 추출: {len(paragraphs)}개 단락")
        
        # 3. 그래도 없으면 긴 텍스트를 가진 div에서 추출
        if not content_text or len(content_text) < 50:
            divs = soup.find_all('div')
            long_text_divs = []
            
            for div in divs:
                div_text = div.get_text(strip=True)
                # 네비게이션이나 메뉴 텍스트 제외
                if (len(div_text) > 100 and 
                    '메뉴' not in div_text[:50] and 
                    '지원센터' not in div_text[:20] and
                    '주요사업' not in div_text[:20]):
                    long_text_divs.append((div, div_text))
            
            if long_text_divs:
                # 가장 긴 텍스트를 가진 div 선택
                long_text_divs.sort(key=lambda x: len(x[1]), reverse=True)
                content_text = long_text_divs[0][1]
                logger.debug(f"본문을 긴 div 텍스트에서 추출: {len(content_text)}자")
        
        if content_text:
            content_parts.append(f"\n{content_text}\n")
        else:
            logger.warning("본문 영역을 찾을 수 없습니다")
        
        return "\n".join(content_parts)
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """첨부파일 추출 - AWS S3 직접 링크 방식"""
        attachments = []
        
        try:
            # 첨부파일 영역 찾기 - 다양한 선택자 시도
            file_selectors = [
                '.body-file ul li a',
                '.attachment-list a', 
                '.file-list a',
                '.attach a',
                '.download a',
                'a[href*=".pdf"]',
                'a[href*=".hwp"]',
                'a[href*=".doc"]',
                'a[href*=".xls"]',
                'a[href*="s3"]',
                'a[href*="download"]',
                'a[href*="file"]'
            ]
            
            found_links = set()  # 중복 제거용
            
            for selector in file_selectors:
                links = soup.select(selector)
                for link in links:
                    try:
                        href = link.get('href', '')
                        filename = link.get_text(strip=True)
                        
                        if not href or not filename or len(filename) < 3:
                            continue
                        
                        # 이미 처리된 링크는 건너뛰기
                        if href in found_links:
                            continue
                        found_links.add(href)
                        
                        # 파일 확장자 확인
                        file_extensions = ['.pdf', '.hwp', '.hwpx', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar']
                        is_file = any(ext in href.lower() or ext in filename.lower() for ext in file_extensions)
                        
                        # AWS S3 링크이거나 파일 확장자가 있는 경우만 처리
                        if not (is_file or 's3' in href or 'download' in href or 'file' in href):
                            continue
                        
                        # AWS S3 링크 처리
                        if self.aws_s3_base in href or href.startswith('https://gangwon6.s3.'):
                            file_url = href
                        elif href.startswith('/'):
                            file_url = urljoin(self.base_url, href)
                        else:
                            file_url = href
                        
                        # 파일명 정리 (괄호 안의 크기 정보 제거)
                        clean_filename = re.sub(r'\([^)]+\)$', '', filename).strip()
                        
                        # URL 인코딩된 파일명 디코딩 시도
                        try:
                            decoded_filename = unquote(clean_filename)
                            if decoded_filename != clean_filename:
                                clean_filename = decoded_filename
                        except:
                            pass
                        
                        # 파일명이 너무 짧거나 의미없는 경우 href에서 추출 시도
                        if len(clean_filename) < 5 or clean_filename in ['파일', '다운로드', '첨부']:
                            try:
                                url_filename = href.split('/')[-1].split('?')[0]
                                if '.' in url_filename and len(url_filename) > 5:
                                    clean_filename = unquote(url_filename)
                            except:
                                pass
                        
                        attachments.append({
                            'name': clean_filename,
                            'url': file_url,
                            'original_text': filename,
                            'found_by': selector
                        })
                        logger.debug(f"첨부파일 발견 ({selector}): {clean_filename}")
                        
                    except Exception as e:
                        logger.error(f"첨부파일 파싱 중 오류: {e}")
                        continue
            
            logger.info(f"{len(attachments)}개 첨부파일 발견")
            return attachments
            
        except Exception as e:
            logger.error(f"첨부파일 추출 실패: {e}")
            return attachments
    
    def download_file(self, url: str, save_path: str, filename: str = "") -> bool:
        """Gangwon6 전용 파일 다운로드 - AWS S3 지원"""
        try:
            # 요청 헤더 설정
            headers = {
                'Referer': self.base_url,
                'User-Agent': self.headers.get('User-Agent', 'Mozilla/5.0'),
                'Accept': 'application/octet-stream,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
            
            # AWS S3 URL인 경우 Referer 제거 (CORS 정책)
            if self.aws_s3_base in url:
                headers.pop('Referer', None)
            
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
Gangwon6Scraper = EnhancedGangwon6Scraper