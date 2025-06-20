# -*- coding: utf-8 -*-
"""
Enhanced KPX 스크래퍼 - 향상된 버전
사이트: https://edu.kpx.or.kr/usr/alim/UsrAlimBasc0201.do
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

class EnhancedKPXScraper(StandardTableScraper):
    """KPX 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://edu.kpx.or.kr"
        self.list_url = "https://edu.kpx.or.kr/usr/alim/UsrAlimBasc0201.do"
        self.list_api_url = "https://edu.kpx.or.kr/usr/alim/selectUsrAlimBasc0201List.json"
        self.detail_api_url = "https://edu.kpx.or.kr/usr/alim/selectUsrAlimBasc0201View.json"
        self.file_download_url = "https://edu.kpx.or.kr/download"
        
        # 사이트 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        
        # KPX 특화 설정
        self.page_size = 15  # 한 페이지당 항목 수
        self.csrf_token = None  # CSRF 토큰
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - AJAX API 방식"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: KPX는 API 엔드포인트가 고정
        return self.list_api_url
    
    def _get_page_announcements(self, page_num: int) -> List[Dict[str, Any]]:
        """페이지별 공고 목록 가져오기 - AJAX API 호출"""
        try:
            # 첫 페이지에서 CSRF 토큰 획득
            if page_num == 1 and self.csrf_token is None:
                self._get_csrf_token()
            
            # AJAX API 호출
            api_data = self.fetch_announcements_api(page_num)
            if not api_data:
                logger.warning(f"페이지 {page_num} API 응답을 가져올 수 없습니다")
                return []
            
            # API 응답 파싱
            announcements = self.parse_api_response(api_data)
            
            # 마지막 페이지 감지
            if not announcements and page_num > 1:
                logger.info(f"페이지 {page_num}에 공고가 없어 마지막 페이지로 판단됩니다")
            
            return announcements
            
        except Exception as e:
            logger.error(f"페이지 {page_num} 공고 목록 가져오기 실패: {e}")
            return []
    
    def _get_csrf_token(self):
        """메인 페이지에서 CSRF 토큰 획득"""
        try:
            response = self.session.get(self.list_url, timeout=self.timeout, verify=self.verify_ssl)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # CSRF 토큰 메타 태그 찾기
            csrf_meta = soup.find('meta', attrs={'name': '_csrf'})
            if csrf_meta:
                self.csrf_token = csrf_meta.get('content')
                logger.debug(f"CSRF 토큰 획득: {self.csrf_token[:20]}...")
            else:
                logger.warning("CSRF 토큰을 찾을 수 없습니다")
                
        except Exception as e:
            logger.error(f"CSRF 토큰 획득 실패: {e}")
            self.csrf_token = None
    
    def fetch_announcements_api(self, page_num: int) -> dict:
        """공고 목록 API 호출"""
        try:
            # API 페이로드 구성
            payload = {
                "currentPageNo": page_num,
                "recordCountPerPage": self.page_size,
                "pageSize": self.page_size
            }
            
            # POST 요청으로 API 호출
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'User-Agent': self.headers.get('User-Agent', 'Mozilla/5.0'),
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': self.list_url
            }
            
            # CSRF 토큰이 있으면 헤더에 추가
            if self.csrf_token:
                headers['X-CSRF-TOKEN'] = self.csrf_token
            
            response = self.session.post(
                self.list_api_url,
                json=payload,
                headers=headers,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            
            response.raise_for_status()
            
            # JSON 응답 파싱
            api_data = response.json()
            logger.debug(f"페이지 {page_num} API 응답: {len(api_data)}개 항목")
            
            return api_data
            
        except Exception as e:
            logger.error(f"API 호출 실패 (페이지 {page_num}): {e}")
            return {}
    
    def parse_api_response(self, api_data: dict) -> List[Dict[str, Any]]:
        """API 응답 데이터 파싱"""
        announcements = []
        
        if not isinstance(api_data, list) or len(api_data) == 0:
            logger.warning("API 응답이 예상된 형식이 아닙니다")
            return announcements
        
        for item in api_data:
            try:
                # 필수 필드 확인
                if not item.get('postNo') or not item.get('bbsTtl'):
                    continue
                
                # 상세 페이지 URL 구성 (실제로는 API로 데이터를 가져올 예정)
                detail_url = f"{self.base_url}/usr/alim/UsrAlimBasc0202.do?postNo={item['postNo']}"
                
                announcement = {
                    'title': item.get('bbsTtl', '').strip(),
                    'url': detail_url,
                    'postNo': item.get('postNo'),
                    'writer': item.get('userNm', ''),
                    'date': item.get('modDt', ''),
                    'views': item.get('bbsInqCnt', ''),
                    'level': item.get('lvl', 1),
                    'isFixed': item.get('hghrkPostYn') == 'Y',
                    'isNew': item.get('newYn') == 'Y',
                    'fileMasterId': item.get('fileMasterId'),
                    'content': item.get('bbsContsCnte', '')  # 본문은 목록에 포함됨
                }
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱 완료: {announcement['title'][:50]}...")
                
            except Exception as e:
                logger.error(f"공고 항목 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - API 방식이므로 사용되지 않음"""
        # KPX는 순수 AJAX 기반이므로 이 메소드는 사용되지 않음
        # 하지만 Enhanced 아키텍처 호환성을 위해 구현
        logger.warning("KPX는 API 기반 사이트입니다. HTML 파싱 대신 API 호출을 사용하세요.")
        return []
    
    def fetch_detail_content(self, announcement: Dict[str, Any]) -> Dict[str, Any]:
        """상세 페이지 내용 가져오기 - HTML 파싱으로 첨부파일 추출"""
        try:
            # 본문은 목록 API에서 이미 가져옴
            raw_content = announcement.get('content', '')
            content = self.format_content(announcement, raw_content)
            
            # 첨부파일은 상세 페이지 HTML에서 추출
            detail_url = announcement.get('url', '')
            attachments = []
            if detail_url:
                attachments = self.fetch_attachments_from_html(detail_url)
            
            return {
                'content': content,
                'attachments': attachments
            }
            
        except Exception as e:
            logger.error(f"상세 내용 가져오기 실패: {e}")
            return {'content': '', 'attachments': []}
    
    def format_content(self, announcement: Dict[str, Any], raw_content: str) -> str:
        """목록 API 데이터로 내용 포매팅"""
        content_parts = []
        
        # 제목
        title = announcement.get('title', '')
        if title:
            content_parts.append(f"# {title}\n")
        
        # 메타 정보
        writer = announcement.get('writer', '')
        date = announcement.get('date', '')
        views = announcement.get('views', '')
        
        if any([writer, date, views]):
            meta_info = []
            if writer:
                meta_info.append(f"**작성자**: {writer}")
            if date:
                meta_info.append(f"**작성일**: {date}")
            if views:
                meta_info.append(f"**조회수**: {views}")
            
            content_parts.append(" | ".join(meta_info) + "\n")
        
        # 본문 내용
        if raw_content:
            # 개행 문자 처리
            formatted_content = raw_content.replace('\\n', '\n').replace('<br/>', '\n').replace('<br>', '\n')
            # HTML 태그 제거 (간단한 처리)
            formatted_content = re.sub(r'<[^>]+>', '', formatted_content)
            content_parts.append(f"\n{formatted_content}\n")
        
        return "\n".join(content_parts)
    
    def fetch_attachments_from_html(self, detail_url: str) -> List[Dict[str, Any]]:
        """Playwright로 동적 첨부파일 추출 - JavaScript 실행 후 파싱"""
        try:
            with sync_playwright() as p:
                # 브라우저 시작
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # User-Agent 설정
                page.set_extra_http_headers({
                    'User-Agent': self.headers.get('User-Agent', 'Mozilla/5.0')
                })
                
                # 페이지 이동
                page.goto(detail_url, wait_until='networkidle')
                
                # 첨부파일 영역이 로드될 때까지 대기
                try:
                    page.wait_for_selector('#td_attachFileList', timeout=10000)
                except:
                    logger.debug("첨부파일 영역이 로드되지 않았음")
                
                # 추가 대기 (AJAX 요청 완료 대기)
                time.sleep(2)
                
                # HTML 가져오기
                html_content = page.content()
                browser.close()
                
                # HTML 파싱
                soup = BeautifulSoup(html_content, 'html.parser')
                attachments = self._extract_attachments(soup)
                
                logger.info(f"{len(attachments)}개 첨부파일 발견 ({detail_url})")
                return attachments
            
        except Exception as e:
            logger.error(f"Playwright 첨부파일 추출 실패 ({detail_url}): {e}")
            # Fallback: 일반 requests 시도
            try:
                response = self.session.get(detail_url, timeout=self.timeout, verify=self.verify_ssl)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                attachments = self._extract_attachments(soup)
                logger.info(f"Fallback으로 {len(attachments)}개 첨부파일 발견")
                return attachments
            except Exception as fallback_e:
                logger.error(f"Fallback도 실패: {fallback_e}")
                return []
    
    def parse_attachment_list(self, file_list: List[Dict]) -> List[Dict[str, Any]]:
        """첨부파일 목록 API 응답 파싱"""
        attachments = []
        
        if not isinstance(file_list, list):
            logger.warning("첨부파일 목록이 예상된 형식이 아닙니다")
            return attachments
        
        for file_info in file_list:
            try:
                file_id = file_info.get('fileId')
                file_master_id = file_info.get('fileMasterId')
                file_name = file_info.get('fileNm') or file_info.get('fileName', '')
                
                if file_id and file_master_id and file_name:
                    # 다운로드 URL 구성
                    file_url = f"{self.file_download_url}?fileMasterId={file_master_id}&fileId={file_id}"
                    
                    attachments.append({
                        'name': file_name,
                        'url': file_url,
                        'fileMasterId': file_master_id,
                        'fileId': file_id
                    })
                    logger.debug(f"첨부파일 발견: {file_name}")
                
            except Exception as e:
                logger.error(f"첨부파일 항목 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(attachments)}개 첨부파일 발견")
        return attachments
    
    def fetch_attachments_from_html(self, detail_url: str) -> List[Dict[str, Any]]:
        """상세 페이지 HTML에서 첨부파일 추출"""
        try:
            # 상세 페이지 HTML 가져오기
            response = self.session.get(detail_url, timeout=self.timeout, verify=self.verify_ssl)
            response.raise_for_status()
            
            # HTML 파싱
            soup = BeautifulSoup(response.text, 'html.parser')
            attachments = self._extract_attachments(soup)
            
            return attachments
            
        except Exception as e:
            logger.error(f"첨부파일 HTML 파싱 실패 ({detail_url}): {e}")
            return []
    
    def fetch_detail_api(self, post_no: str) -> dict:
        """상세 내용 API 호출"""
        try:
            # API 페이로드 구성
            payload = {"postNo": post_no}
            
            # POST 요청으로 API 호출
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'User-Agent': self.headers.get('User-Agent', 'Mozilla/5.0'),
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': self.list_url
            }
            
            # CSRF 토큰이 있으면 헤더에 추가
            if self.csrf_token:
                headers['X-CSRF-TOKEN'] = self.csrf_token
            
            response = self.session.post(
                self.detail_api_url,
                json=payload,
                headers=headers,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            
            response.raise_for_status()
            
            # JSON 응답 파싱
            api_data = response.json()
            logger.debug(f"상세 내용 API 응답 받음: {post_no}")
            
            return api_data
            
        except Exception as e:
            logger.error(f"상세 내용 API 호출 실패 ({post_no}): {e}")
            return {}
    
    def parse_detail_content(self, detail_data: dict) -> str:
        """상세 내용 데이터 파싱"""
        if not isinstance(detail_data, list) or len(detail_data) == 0:
            logger.warning("상세 내용 API 응답이 예상된 형식이 아닙니다")
            return ""
        
        item = detail_data[0]
        
        # 기본 정보 수집
        content_parts = []
        
        # 제목
        title = item.get('bbsTtl', '')
        if title:
            content_parts.append(f"# {title}\n")
        
        # 메타 정보
        writer = item.get('userNm', '')
        date = item.get('modDt', '')
        views = item.get('bbsInqCnt', '')
        
        if any([writer, date, views]):
            meta_info = []
            if writer:
                meta_info.append(f"**작성자**: {writer}")
            if date:
                meta_info.append(f"**작성일**: {date}")
            if views:
                meta_info.append(f"**조회수**: {views}")
            
            content_parts.append(" | ".join(meta_info) + "\n")
        
        # 본문 내용
        main_content = item.get('bbsContsCnte', '')
        if main_content:
            # 개행 문자 처리
            main_content = main_content.replace('\\n', '\n').replace('<br/>', '\n').replace('<br>', '\n')
            # HTML 태그 제거 (간단한 처리)
            main_content = re.sub(r'<[^>]+>', '', main_content)
            content_parts.append(f"\n{main_content}\n")
        
        return "\n".join(content_parts)
    
    def parse_detail_attachments(self, detail_data: dict) -> List[Dict[str, Any]]:
        """상세 내용에서 첨부파일 정보 추출"""
        attachments = []
        
        if not isinstance(detail_data, list) or len(detail_data) == 0:
            return attachments
        
        item = detail_data[0]
        file_master_id = item.get('fileMasterId')
        
        if file_master_id:
            # 첨부파일 정보는 별도 API로 가져와야 할 수 있음
            # 여기서는 기본적인 정보만 파싱
            logger.debug(f"첨부파일 마스터 ID 발견: {file_master_id}")
            
            # 실제 파일 다운로드 URL은 JavaScript 함수 P_fileDownload에서 구성
            # 예: P_fileDownload('FM2025022700000000000000411072','FI2025022700000000000000411074')
            # 이는 상세 페이지 HTML에서 추가로 파싱해야 함
            
        return attachments
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱 - 첨부파일 정보 추출용"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup)
        
        return {
            'content': '',  # 내용은 API에서 가져옴
            'attachments': attachments
        }
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """첨부파일 추출 - P_fileDownload JavaScript 함수 파싱"""
        attachments = []
        
        # 첨부파일 영역 찾기
        attachment_area = soup.find('td', id='td_attachFileList')
        if not attachment_area:
            logger.debug("첨부파일 영역(td_attachFileList)을 찾을 수 없습니다")
            return attachments
        
        # JavaScript 다운로드 링크 찾기
        # 예: P_fileDownload('FM2025022700000000000000411072','FI2025022700000000000000411074')
        download_links = attachment_area.find_all('a', href=re.compile(r'javascript:P_fileDownload'))
        
        for link in download_links:
            try:
                href = link.get('href', '')
                file_name_elem = link.find('span', class_='file_name')
                
                if not file_name_elem:
                    # span.file_name이 없으면 링크 텍스트 전체를 파일명으로 사용
                    file_name = link.get_text(strip=True)
                else:
                    file_name = file_name_elem.get_text(strip=True)
                
                if not file_name:
                    continue
                
                # JavaScript 함수에서 파라미터 추출
                # P_fileDownload('FM...','FI...')
                js_match = re.search(r"P_fileDownload\('([^']+)','([^']+)'\)", href)
                if js_match:
                    file_master_id = js_match.group(1)
                    file_id = js_match.group(2)
                    
                    # CSRF 토큰과 함께 다운로드 URL 구성
                    csrf_param = f"_csrf={self.csrf_token}" if self.csrf_token else ""
                    file_url = f"{self.base_url}/download?{csrf_param}&fileMasterId={file_master_id}&fileId={file_id}"
                    
                    attachments.append({
                        'name': file_name,
                        'url': file_url,
                        'fileMasterId': file_master_id,
                        'fileId': file_id
                    })
                    logger.debug(f"첨부파일 발견: {file_name}")
                
            except Exception as e:
                logger.error(f"첨부파일 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(attachments)}개 첨부파일 발견")
        return attachments
    
    def download_file(self, url: str, save_path: str, filename: str = "") -> bool:
        """KPX 전용 파일 다운로드 - CSRF 토큰 및 세션 처리"""
        try:
            # CSRF 토큰이 URL에 없으면 추가
            if self.csrf_token and '_csrf=' not in url:
                separator = '&' if '?' in url else '?'
                url = f"{url}{separator}_csrf={self.csrf_token}"
            
            # 요청 헤더 설정
            headers = {
                'Referer': self.list_url,
                'User-Agent': self.headers.get('User-Agent', 'Mozilla/5.0'),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
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
            if 'text/html' in content_type or 'application/json' in content_type:
                logger.warning(f"파일 다운로드 실패 - HTML/JSON 응답 받음: {url}")
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
KPXScraper = EnhancedKPXScraper