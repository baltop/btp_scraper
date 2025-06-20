# -*- coding: utf-8 -*-
"""
함께일하는재단(hamkke.org) Enhanced 스크래퍼
"""

import requests
from bs4 import BeautifulSoup
import re
import logging
import os
import json
from urllib.parse import urljoin, unquote
from enhanced_base_scraper import StandardTableScraper
import time
from typing import Dict, List, Any
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

class EnhancedHamkkeScraper(StandardTableScraper):
    """함께일하는재단(hamkke.org) 전용 스크래퍼 - 향상된 버전 (JavaScript 기반)"""
    
    def __init__(self):
        super().__init__()
        
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://hamkke.org"
        self.list_url = "https://hamkke.org/business"
        
        # 사이트 특화 설정
        self.verify_ssl = True  # HTTPS 사이트
        self.default_encoding = 'utf-8'
        self.timeout = 60  # JavaScript 로딩을 위한 긴 타임아웃
        self.delay_between_requests = 2  # JavaScript 사이트용 긴 대기
        self.requires_javascript = True  # JavaScript 필수
        
        # Playwright 브라우저 설정
        self.playwright = None
        self.browser = None
        self.page = None
        
        # 향상된 헤더 설정
        self.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.session.headers.update(self.headers)
    
    def __enter__(self):
        """Context manager for Playwright"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.page = self.browser.new_page()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        if self.page:
            self.page.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - JavaScript 기반 사이트는 URL 동일"""
        # JavaScript 기반 사이트는 페이지네이션이 "더보기" 방식
        return self.list_url
    
    def fetch_page_with_playwright(self, url: str) -> str:
        """Playwright를 사용한 JavaScript 페이지 로딩"""
        try:
            if not self.page:
                logger.error("Playwright 페이지가 초기화되지 않았습니다")
                return ""
            
            logger.debug(f"Playwright로 페이지 로딩: {url}")
            self.page.goto(url, timeout=30000)
            
            # JavaScript 로딩 대기
            self.page.wait_for_timeout(3000)
            
            # 추가 콘텐츠 로딩 대기 (더보기 버튼 등)
            try:
                self.page.wait_for_selector('.business-item', timeout=10000)
            except:
                logger.warning("business-item 선택자를 찾을 수 없습니다")
            
            html_content = self.page.content()
            logger.debug(f"페이지 콘텐츠 길이: {len(html_content)}")
            return html_content
            
        except Exception as e:
            logger.error(f"Playwright 페이지 로딩 실패 {url}: {e}")
            return ""
    
    def extract_business_data_from_js(self, html_content: str) -> List[Dict[str, Any]]:
        """HTML에서 JavaScript businessData 객체 추출 (수정된 패턴)"""
        try:
            # businessData JavaScript 객체 찾기 (객체 형태)
            business_data_pattern = r'var\s+businessData\s*=\s*(\{[^;]+\});'
            match = re.search(business_data_pattern, html_content, re.DOTALL)
            
            if not match:
                # 다른 패턴 시도
                business_data_pattern = r'businessData\s*:\s*(\{.*?\}),'
                match = re.search(business_data_pattern, html_content, re.DOTALL)
            
            if not match:
                logger.warning("businessData JavaScript 객체를 찾을 수 없습니다")
                return []
            
            business_data_json = match.group(1)
            business_data = json.loads(business_data_json)
            
            # business 배열 추출
            business_items = business_data.get('business', [])
            logger.info(f"JavaScript에서 {len(business_items)}개 비즈니스 데이터 추출")
            return business_items
            
        except json.JSONDecodeError as e:
            logger.error(f"businessData JSON 파싱 오류: {e}")
            return []
        except Exception as e:
            logger.error(f"businessData 추출 중 오류: {e}")
            return []
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - JavaScript 데이터 기반"""
        announcements = []
        
        # JavaScript에서 데이터 추출 시도
        business_data = self.extract_business_data_from_js(html_content)
        
        if business_data:
            # JavaScript 데이터 사용
            for item in business_data:
                try:
                    announcement = {
                        'id': item.get('ID'),
                        'title': item.get('title', '').strip(),
                        'url': item.get('permalink', ''),
                        'date': item.get('posting_date', ''),
                        'publish': item.get('publish', False),
                        'subscription': item.get('subscription', False)
                    }
                    
                    # 제목이 있는 경우만 추가
                    if announcement['title']:
                        announcements.append(announcement)
                        logger.debug(f"공고 추가: {announcement['title'][:50]}...")
                
                except Exception as e:
                    logger.error(f"비즈니스 데이터 파싱 중 오류: {e}")
                    continue
        else:
            # Fallback: DOM 파싱
            announcements = self._parse_list_page_dom(html_content)
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def _parse_list_page_dom(self, html_content: str) -> List[Dict[str, Any]]:
        """DOM 기반 파싱 (JavaScript 추출 실패 시 fallback) - 수정된 선택자"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 비즈니스 링크들 직접 찾기 (/archives/business/ 패턴)
        business_links = soup.find_all('a', href=re.compile(r'/archives/business/\d+'))
        
        if not business_links:
            logger.warning("DOM에서 비즈니스 링크를 찾을 수 없습니다")
            return announcements
        
        logger.info(f"DOM에서 {len(business_links)}개 비즈니스 링크 발견")
        
        for link in business_links:
            try:
                title = link.get_text(strip=True)
                href = link.get('href', '')
                
                if not title or not href:
                    continue
                
                detail_url = urljoin(self.base_url, href)
                
                announcement = {
                    'title': title,
                    'url': detail_url
                }
                
                # 상위 요소에서 날짜 정보 찾기
                parent = link.find_parent()
                if parent:
                    date_elem = parent.find('span', class_='date') or parent.find('time')
                    if date_elem:
                        announcement['date'] = date_elem.get_text(strip=True)
                
                announcements.append(announcement)
                logger.debug(f"DOM 공고 추가: {title[:50]}...")
                
            except Exception as e:
                logger.error(f"DOM 파싱 중 오류: {e}")
                continue
        
        return announcements
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱 - WordPress 구조 기반 개선"""
        
        # JavaScript에서 데이터 추출 시도
        business_view = self.extract_business_view_from_js(html_content)
        
        if business_view:
            # JavaScript 데이터 사용 - hamkke.org 구조에 맞게 수정
            content_text = self._extract_content_from_business_view(business_view)
            attachments = self._extract_attachments_from_js(business_view)
        else:
            # Fallback: DOM 파싱 (WordPress 구조에 맞게 개선)
            result = self._parse_detail_page_dom(html_content)
            content_text = result['content']
            attachments = result['attachments']
        
        return {
            'content': content_text,
            'attachments': attachments
        }
    
    def extract_business_view_from_js(self, html_content: str) -> Dict[str, Any]:
        """HTML에서 JavaScript businessView 객체 추출"""
        try:
            # businessView JavaScript 객체 찾기
            business_view_pattern = r'var\s+businessView\s*=\s*(\{.*?\});'
            match = re.search(business_view_pattern, html_content, re.DOTALL)
            
            if not match:
                # 다른 패턴 시도
                business_view_pattern = r'businessView\s*:\s*(\{.*?\}),'
                match = re.search(business_view_pattern, html_content, re.DOTALL)
            
            if not match:
                logger.warning("businessView JavaScript 객체를 찾을 수 없습니다")
                return {}
            
            business_view_json = match.group(1)
            business_view = json.loads(business_view_json)
            
            logger.debug("JavaScript에서 businessView 데이터 추출 성공")
            return business_view
            
        except json.JSONDecodeError as e:
            logger.error(f"businessView JSON 파싱 오류: {e}")
            return {}
        except Exception as e:
            logger.error(f"businessView 추출 중 오류: {e}")
            return {}
    
    def _extract_content_from_business_view(self, business_view: Dict[str, Any]) -> str:
        """JavaScript businessView에서 콘텐츠 추출 - hamkke.org 특화"""
        content_parts = []
        
        try:
            fields = business_view.get('fields', {})
            
            # 사업 목적
            purpose = fields.get('business_purpose', '').strip()
            if purpose:
                content_parts.append(f"## 사업 목적\n\n{purpose}")
            
            # 선정 대상
            selected = fields.get('business_selected', '').strip()
            if selected:
                content_parts.append(f"## 선정 대상\n\n{selected}")
            
            # 지원 내용
            application = fields.get('business_application', '').strip()
            if application:
                content_parts.append(f"## 지원 내용\n\n{application}")
            
            # 사업 일정
            schedule = fields.get('business_schedule', '').strip()
            if schedule:
                content_parts.append(f"## 사업 일정\n\n{schedule}")
            
            # 신청 방법
            app_way = fields.get('business_application_way', {})
            if isinstance(app_way, dict) and app_way.get('description'):
                content_parts.append(f"## 신청 방법\n\n{app_way['description']}")
            
            # 연락처
            contact = fields.get('business_contact', '').strip()
            if contact:
                content_parts.append(f"## 문의\n\n{contact}")
            
            # 주최/주관
            host = fields.get('business_host', '').strip()
            supervisor = fields.get('business_supervisor', '').strip()
            if host or supervisor:
                org_info = []
                if host:
                    org_info.append(f"**주최**: {host}")
                if supervisor:
                    org_info.append(f"**주관**: {supervisor}")
                content_parts.append(f"## 주최/주관\n\n{' / '.join(org_info)}")
            
            # 모집 기간
            sub_date = fields.get('business_subscription_date', {})
            if isinstance(sub_date, dict) and (sub_date.get('start') or sub_date.get('end')):
                start = sub_date.get('start', '')
                end = sub_date.get('end', '')
                date_info = f"**신청 기간**: {start} ~ {end}"
                content_parts.append(f"## 신청 기간\n\n{date_info}")
            
            if content_parts:
                full_content = '\n\n'.join(content_parts)
                logger.debug(f"JavaScript에서 추출한 콘텐츠 길이: {len(full_content)}")
                return full_content
            else:
                logger.warning("JavaScript businessView에서 콘텐츠를 찾을 수 없습니다")
                return "콘텐츠를 추출할 수 없습니다."
                
        except Exception as e:
            logger.error(f"JavaScript 콘텐츠 추출 중 오류: {e}")
            return "콘텐츠 추출 중 오류가 발생했습니다."
    
    def _extract_attachments_from_js(self, business_view: Dict[str, Any]) -> List[Dict[str, Any]]:
        """JavaScript businessView에서 첨부파일 추출 - hamkke.org 구조 특화"""
        attachments = []
        
        try:
            fields = business_view.get('fields', {})
            business_attachments = fields.get('business_attachments', [])
            
            for attachment_item in business_attachments:
                attachment_data = attachment_item.get('business_attachment', {})
                
                filename = attachment_data.get('filename', '')
                file_url = attachment_data.get('url', '')
                file_size = attachment_data.get('filesize', 0)
                title = attachment_data.get('title', '')
                
                if filename and file_url:
                    attachment = {
                        'filename': filename,
                        'url': file_url,
                        'size': file_size,
                        'title': title
                    }
                    attachments.append(attachment)
                    logger.info(f"첨부파일 발견: {filename} ({file_size:,} bytes)")
            
            logger.debug(f"JavaScript에서 {len(attachments)}개 첨부파일 추출")
            
        except Exception as e:
            logger.error(f"JavaScript 첨부파일 추출 중 오류: {e}")
        
        return attachments
    
    def _parse_detail_page_dom(self, html_content: str) -> Dict[str, Any]:
        """DOM 기반 상세 페이지 파싱 - WordPress/hamkke.org 구조 특화"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 영역 찾기 - hamkke.org WordPress 구조에 맞게 수정
        content_area = None
        
        # hamkke.org 특화 선택자들
        selectors = [
            '.entry-content',           # WordPress 표준
            '.post-content', 
            '.wp-block-group',          # Gutenberg 블록
            '.wp-block-columns',        # 칼럼 블록
            '.single-content',          # 단일 포스트 내용
            'article .content',         # 아티클 내 콘텐츠
            '#post-content',            # ID 기반
            '.elementor-widget-text-editor',  # Elementor 텍스트 에디터
            'main .content',            # 메인 영역 내 콘텐츠
            'article',                  # 전체 아티클
            'main'                      # 메인 태그 전체
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                # 가장 긴 텍스트를 가진 요소 선택
                content_area = max(elements, key=lambda x: len(x.get_text(strip=True)))
                logger.debug(f"{selector}에서 본문 영역 발견 (길이: {len(content_area.get_text(strip=True))})")
                break
        
        if content_area:
            # 불필요한 태그 제거
            for tag in content_area.find_all(['script', 'style', 'nav', 'header', 'footer', '.nav', '.navigation']):
                tag.decompose()
            
            # 이미지 URL을 절대 URL로 변환
            for img in content_area.find_all('img'):
                src = img.get('src', '')
                if src and not src.startswith('http'):
                    img['src'] = urljoin(self.base_url, src)
            
            content_html = str(content_area)
            content_text = self.h.handle(content_html)
            content_text = re.sub(r'\n\s*\n\s*\n', '\n\n', content_text).strip()
            
            # 최소 길이 확인 (너무 짧으면 다른 선택자 시도)
            if len(content_text) < 50:
                logger.warning(f"추출된 내용이 너무 짧습니다 ({len(content_text)}자): {content_text[:50]}")
                # 전체 body에서 텍스트 추출 시도
                body = soup.find('body')
                if body:
                    # 네비게이션, 헤더, 푸터 제거
                    for unwanted in body.find_all(['nav', 'header', 'footer', '.header', '.footer', '.nav']):
                        unwanted.decompose()
                    
                    content_text = self.h.handle(str(body))
                    content_text = re.sub(r'\n\s*\n\s*\n', '\n\n', content_text).strip()
        else:
            content_text = "내용을 추출할 수 없습니다."
            logger.warning("어떤 선택자로도 본문 영역을 찾을 수 없습니다")
        
        # 첨부파일 추출
        attachments = self._extract_attachments_dom(soup)
        
        logger.debug(f"최종 콘텐츠 길이: {len(content_text)}자")
        
        return {
            'content': content_text,
            'attachments': attachments
        }
    
    def _extract_attachments_dom(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """DOM에서 첨부파일 추출 - WordPress/hamkke.org 구조 특화"""
        attachments = []
        
        # 다양한 첨부파일 패턴 찾기
        patterns = [
            # 직접 파일 링크
            r'\.(pdf|hwp|docx?|xlsx?|pptx?|zip|rar)$',
            # WordPress 업로드 경로
            r'/wp-content/uploads/.*\.(pdf|hwp|docx?|xlsx?|pptx?|zip|rar)$',
            # 다운로드 파라미터가 있는 경우
            r'download.*\.(pdf|hwp|docx?|xlsx?|pptx?|zip|rar)',
            # 첨부파일 ID 방식
            r'attachment_id=\d+',
            # 파일 다운로드 액션
            r'action=download'
        ]
        
        for pattern in patterns:
            file_links = soup.find_all('a', href=re.compile(pattern, re.I))
            
            for link in file_links:
                href = link.get('href', '')
                if not href:
                    continue
                
                file_url = urljoin(self.base_url, href)
                
                # 파일명 추출 우선순위
                filename = ""
                
                # 1. 링크 텍스트에서
                link_text = link.get_text(strip=True)
                if link_text and not link_text.lower() in ['다운로드', 'download', '첨부파일']:
                    filename = link_text
                
                # 2. title 속성에서
                if not filename:
                    filename = link.get('title', '').strip()
                
                # 3. URL에서 파일명 추출
                if not filename:
                    from urllib.parse import urlparse, unquote
                    parsed_url = urlparse(href)
                    filename = os.path.basename(unquote(parsed_url.path))
                
                # 4. 기본 파일명
                if not filename:
                    filename = f"attachment_{len(attachments)+1}"
                
                attachment = {
                    'filename': filename,
                    'url': file_url,
                    'size': 0  # DOM에서는 크기 정보 없음
                }
                
                # 중복 방지
                if not any(att['url'] == file_url for att in attachments):
                    attachments.append(attachment)
                    logger.info(f"DOM 첨부파일 발견: {filename}")
        
        # WordPress 미디어 라이브러리 링크 추가 검색
        media_links = soup.find_all('a', href=re.compile(r'/wp-content/uploads/', re.I))
        for link in media_links:
            href = link.get('href', '')
            # 이미지가 아닌 파일들만
            if not re.search(r'\.(jpg|jpeg|png|gif|webp|svg)$', href, re.I):
                file_url = urljoin(self.base_url, href)
                filename = os.path.basename(href)
                
                attachment = {
                    'filename': filename,
                    'url': file_url,
                    'size': 0
                }
                
                # 중복 방지
                if not any(att['url'] == file_url for att in attachments):
                    attachments.append(attachment)
                    logger.info(f"미디어 라이브러리 파일 발견: {filename}")
        
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment_info: Dict[str, Any] = None) -> bool:
        """파일 다운로드 - 함께일하는재단 특화"""
        try:
            response = self.session.get(url, stream=True, verify=self.verify_ssl, timeout=60)
            response.raise_for_status()
            
            # 실제 파일명 추출 (향상된 인코딩 처리)
            actual_filename = self._extract_filename(response, save_path)
            if actual_filename != save_path:
                save_path = actual_filename
            
            # 스트리밍 다운로드
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
    
    def _extract_filename(self, response: requests.Response, default_path: str) -> str:
        """향상된 파일명 추출 - 한글 파일명 처리"""
        save_dir = os.path.dirname(default_path)
        
        content_disposition = response.headers.get('Content-Disposition', '')
        
        if content_disposition:
            # RFC 5987 형식 우선 처리
            rfc5987_match = re.search(r"filename\*=([^']*)'([^']*)'(.+)", content_disposition)
            if rfc5987_match:
                encoding, lang, filename = rfc5987_match.groups()
                try:
                    filename = unquote(filename, encoding=encoding or 'utf-8')
                    return os.path.join(save_dir, self.sanitize_filename(filename))
                except:
                    pass
            
            # 일반 filename 파라미터 처리
            filename_match = re.search(r'filename[^;=\n]*=([\'"]*)(.*?)\1', content_disposition)
            if filename_match:
                filename = filename_match.group(2)
                
                # 다양한 인코딩 시도
                for encoding in ['utf-8', 'euc-kr', 'cp949']:
                    try:
                        if encoding == 'utf-8':
                            # URL 디코딩 먼저 시도
                            try:
                                decoded = unquote(filename, encoding='utf-8')
                                if decoded != filename:  # 실제로 디코딩된 경우
                                    clean_filename = self.sanitize_filename(decoded)
                                    return os.path.join(save_dir, clean_filename)
                            except:
                                pass
                            
                            # UTF-8 직접 디코딩
                            decoded = filename.encode('latin-1').decode('utf-8')
                        else:
                            decoded = filename.encode('latin-1').decode(encoding)
                        
                        if decoded and not decoded.isspace():
                            clean_filename = self.sanitize_filename(decoded.replace('+', ' '))
                            return os.path.join(save_dir, clean_filename)
                    except:
                        continue
        
        return default_path
    
    def scrape_pages(self, max_pages: int, output_base: str):
        """JavaScript 기반 사이트용 스크래핑 메인 로직"""
        logger.info(f"JavaScript 기반 스크래핑 시작: 최대 {max_pages}페이지")
        
        with self:  # Playwright context manager
            # 부모 클래스의 스크래핑 로직 사용
            super().scrape_pages(max_pages, output_base)
    
    def _get_page_content(self, url: str) -> str:
        """JavaScript 기반 페이지 콘텐츠 가져오기 - Playwright 사용"""
        if self.page:
            return self.fetch_page_with_playwright(url)
        else:
            # Fallback to regular requests
            logger.warning("Playwright 페이지가 없어서 일반 requests 사용")
            response = self.session.get(url, verify=self.verify_ssl, timeout=self.timeout)
            response.raise_for_status()
            return response.text

# 하위 호환성을 위한 별칭
HamkkeScraper = EnhancedHamkkeScraper