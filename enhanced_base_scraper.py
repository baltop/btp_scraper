# -*- coding: utf-8 -*-
"""
향상된 베이스 스크래퍼 - 설정 주입 및 특화된 베이스 클래스들
"""

import requests
from bs4 import BeautifulSoup
import os
import time
import html2text
from urllib.parse import urljoin, urlparse, parse_qs
import re
import json
import logging
import chardet
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)

class EnhancedBaseScraper(ABC):
    """향상된 베이스 스크래퍼 - 설정 주입 지원"""
    
    def __init__(self):
        # 기본 설정
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # HTML to text 변환기
        self.h = html2text.HTML2Text()
        self.h.ignore_links = False
        self.h.ignore_images = False
        
        # 기본값들
        self.verify_ssl = True
        self.default_encoding = 'auto'
        self.timeout = 30
        self.delay_between_requests = 1
        self.delay_between_pages = 2
        
        # 설정 객체 (선택적)
        self.config = None
        
        # 베이스 URL들 (하위 클래스에서 설정)
        self.base_url = None
        self.list_url = None
        
        # 중복 체크 관련
        self.processed_titles_file = None
        self.processed_titles = set()
        self.enable_duplicate_check = True
        self.duplicate_threshold = 3  # 동일 제목 3개 발견시 조기 종료
        
    def set_config(self, config):
        """설정 객체 주입"""
        self.config = config
        
        # 설정에서 값들 적용
        if config:
            self.base_url = config.base_url
            self.list_url = config.list_url
            self.verify_ssl = config.ssl_verify
            
            if config.encoding != 'auto':
                self.default_encoding = config.encoding
            
            # 헤더 업데이트
            if hasattr(config, 'user_agent') and config.user_agent:
                self.headers['User-Agent'] = config.user_agent
                self.session.headers.update(self.headers)
    
    @abstractmethod
    def get_list_url(self, page_num: int) -> str:
        """페이지 번호에 따른 목록 URL 반환"""
        pass
        
    @abstractmethod
    def parse_list_page(self, html_content: Union[str, int]) -> List[Dict[str, Any]]:
        """목록 페이지 파싱"""
        pass
        
    @abstractmethod
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱"""
        pass
    
    def get_page(self, url: str, **kwargs) -> Optional[requests.Response]:
        """페이지 가져오기 - 향상된 버전"""
        try:
            # 기본 옵션들
            options = {
                'verify': self.verify_ssl,
                'timeout': self.timeout,
                **kwargs
            }
            
            response = self.session.get(url, **options)
            
            # 인코딩 처리
            self._fix_encoding(response)
            
            return response
            
        except Exception as e:
            logger.error(f"페이지 가져오기 실패 {url}: {e}")
            return None
    
    def post_page(self, url: str, data: Dict[str, Any] = None, **kwargs) -> Optional[requests.Response]:
        """POST 요청"""
        try:
            options = {
                'verify': self.verify_ssl,
                'timeout': self.timeout,
                **kwargs
            }
            
            response = self.session.post(url, data=data, **options)
            self._fix_encoding(response)
            
            return response
            
        except Exception as e:
            logger.error(f"POST 요청 실패 {url}: {e}")
            return None
    
    def _fix_encoding(self, response: requests.Response):
        """응답 인코딩 자동 수정"""
        if response.encoding is None or response.encoding == 'ISO-8859-1':
            if self.default_encoding == 'auto':
                # 자동 감지 시도
                try:
                    detected = chardet.detect(response.content[:10000])
                    if detected['confidence'] > 0.7:
                        response.encoding = detected['encoding']
                    else:
                        response.encoding = response.apparent_encoding or 'utf-8'
                except:
                    response.encoding = 'utf-8'
            else:
                response.encoding = self.default_encoding
    
    def download_file(self, url: str, save_path: str, attachment_info: Dict[str, Any] = None) -> bool:
        """파일 다운로드 - 향상된 버전"""
        try:
            logger.info(f"파일 다운로드 시작: {url}")
            
            # 다운로드 헤더 설정
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
    
    def _extract_filename(self, response: requests.Response, default_path: str) -> str:
        """Content-Disposition에서 실제 파일명 추출"""
        content_disposition = response.headers.get('Content-Disposition', '')
        
        if not content_disposition:
            return default_path
        
        # RFC 5987 형식 우선 시도 (filename*=UTF-8''filename.ext)
        rfc5987_match = re.search(r"filename\*=([^']*)'([^']*)'(.+)", content_disposition)
        if rfc5987_match:
            encoding = rfc5987_match.group(1) or 'utf-8'
            filename = rfc5987_match.group(3)
            try:
                from urllib.parse import unquote
                filename = unquote(filename, encoding=encoding)
                save_dir = os.path.dirname(default_path)
                return os.path.join(save_dir, self.sanitize_filename(filename))
            except:
                pass
        
        # 일반적인 filename 파라미터 시도
        filename_match = re.search(r'filename[^;=\n]*=(([\'"]).*?\2|[^;\n]*)', content_disposition)
        if filename_match:
            filename = filename_match.group(1).strip('"\'')
            
            # 다양한 인코딩 시도
            for encoding in ['utf-8', 'euc-kr', 'cp949']:
                try:
                    if encoding == 'utf-8':
                        # UTF-8로 잘못 해석된 경우 복구 시도
                        decoded = filename.encode('latin-1').decode('utf-8')
                    else:
                        decoded = filename.encode('latin-1').decode(encoding)
                    
                    if decoded and not decoded.isspace():
                        save_dir = os.path.dirname(default_path)
                        clean_filename = self.sanitize_filename(decoded.replace('+', ' '))
                        return os.path.join(save_dir, clean_filename)
                except:
                    continue
        
        return default_path
    
    def sanitize_filename(self, filename: str) -> str:
        """파일명 정리 - 향상된 버전"""
        from urllib.parse import unquote
        
        # URL 디코딩
        try:
            filename = unquote(filename)
        except:
            pass
        
        # 특수문자 제거
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # 연속된 공백을 하나로
        filename = re.sub(r'\s+', ' ', filename)
        
        # 파일명 길이 제한 (확장자 보존)
        if len(filename) > 200:
            name_parts = filename.rsplit('.', 1)
            if len(name_parts) == 2:
                name, ext = name_parts
                filename = name[:200-len(ext)-1] + '.' + ext
            else:
                filename = filename[:200]
        
        return filename.strip()
    
    def normalize_title(self, title: str) -> str:
        """제목 정규화 - 중복 체크용"""
        if not title:
            return ""
        
        # 앞뒤 공백 제거
        normalized = title.strip()
        
        # 연속된 공백을 하나로
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # 특수문자 제거 (일부 허용)
        normalized = re.sub(r'[^\w\s가-힣()-]', '', normalized)
        
        # 소문자 변환 (영문의 경우)
        normalized = normalized.lower()
        
        return normalized
    
    def get_title_hash(self, title: str) -> str:
        """제목의 해시값 생성"""
        normalized = self.normalize_title(title)
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    def load_processed_titles(self, output_base: str = 'output'):
        """처리된 제목 목록 로드"""
        if not self.enable_duplicate_check:
            return
        
        # 사이트별 파일명 생성
        site_name = self.__class__.__name__.replace('Scraper', '').lower()
        self.processed_titles_file = os.path.join(output_base, f'processed_titles_{site_name}.json')
        
        try:
            if os.path.exists(self.processed_titles_file):
                with open(self.processed_titles_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 제목 해시만 로드
                    self.processed_titles = set(data.get('title_hashes', []))
                    logger.info(f"기존 처리된 공고 {len(self.processed_titles)}개 로드")
            else:
                self.processed_titles = set()
                logger.info("새로운 처리된 제목 파일 생성")
        except Exception as e:
            logger.error(f"처리된 제목 로드 실패: {e}")
            self.processed_titles = set()
    
    def save_processed_titles(self):
        """처리된 제목 목록 저장"""
        if not self.enable_duplicate_check or not self.processed_titles_file:
            return
        
        try:
            os.makedirs(os.path.dirname(self.processed_titles_file), exist_ok=True)
            
            data = {
                'title_hashes': list(self.processed_titles),
                'last_updated': datetime.now().isoformat(),
                'total_count': len(self.processed_titles)
            }
            
            with open(self.processed_titles_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"처리된 제목 {len(self.processed_titles)}개 저장 완료")
        except Exception as e:
            logger.error(f"처리된 제목 저장 실패: {e}")
    
    def is_title_processed(self, title: str) -> bool:
        """제목이 이미 처리되었는지 확인"""
        if not self.enable_duplicate_check:
            return False
        
        title_hash = self.get_title_hash(title)
        return title_hash in self.processed_titles
    
    def add_processed_title(self, title: str):
        """처리된 제목 추가"""
        if not self.enable_duplicate_check:
            return
        
        title_hash = self.get_title_hash(title)
        self.processed_titles.add(title_hash)
    
    def filter_new_announcements(self, announcements: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], bool]:
        """새로운 공고만 필터링 - 중복 임계값 체크 포함"""
        if not self.enable_duplicate_check:
            return announcements, False
        
        new_announcements = []
        duplicate_count = 0
        
        for ann in announcements:
            title = ann.get('title', '')
            if not self.is_title_processed(title):
                new_announcements.append(ann)
            else:
                duplicate_count += 1
                logger.debug(f"이미 처리된 공고 스킵: {title[:150]}...")
                
                # 중복 임계값 도달시 조기 종료 신호
                if duplicate_count >= self.duplicate_threshold:
                    logger.info(f"연속 중복 공고 {duplicate_count}개 발견 - 조기 종료 신호")
                    break
        
        should_stop = duplicate_count >= self.duplicate_threshold
        logger.info(f"전체 {len(announcements)}개 중 새로운 공고 {len(new_announcements)}개, 중복 {duplicate_count}개 발견")
        
        return new_announcements, should_stop
    
    def process_announcement(self, announcement: Dict[str, Any], index: int, output_base: str = 'output'):
        """개별 공고 처리 - 향상된 버전"""
        logger.info(f"공고 처리 중 {index}: {announcement['title']}")
        
        # 폴더 생성 - 원래 방식으로 복원 (번호 + 제목)
        folder_title = self.sanitize_filename(announcement['title'])[:150]
        folder_name = f"{index:03d}_{folder_title}"
        folder_path = os.path.join(output_base, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        # 상세 페이지 가져오기
        response = self.get_page(announcement['url'])
        if not response:
            logger.error(f"상세 페이지 가져오기 실패: {announcement['title']}")
            return
        
        # 상세 내용 파싱
        try:
            detail = self.parse_detail_page(response.text)
            logger.info(f"상세 페이지 파싱 완료 - 내용길이: {len(detail['content'])}, 첨부파일: {len(detail['attachments'])}")
        except Exception as e:
            logger.error(f"상세 페이지 파싱 실패: {e}")
            return
        
        # 메타 정보 생성
        meta_info = self._create_meta_info(announcement)
        
        # 본문 저장
        content_path = os.path.join(folder_path, 'content.md')
        with open(content_path, 'w', encoding='utf-8') as f:
            f.write(meta_info + detail['content'])
        
        logger.info(f"내용 저장 완료: {content_path}")
        
        # 첨부파일 다운로드
        self._download_attachments(detail['attachments'], folder_path)
        
        # 처리된 제목으로 추가
        self.add_processed_title(announcement['title'])
        
        # 요청 간 대기
        if self.delay_between_requests > 0:
            time.sleep(self.delay_between_requests)
    
    def _create_meta_info(self, announcement: Dict[str, Any]) -> str:
        """메타 정보 생성"""
        meta_lines = [f"# {announcement['title']}", ""]
        
        # 동적으로 메타 정보 추가
        meta_fields = {
            'writer': '작성자',
            'date': '작성일',
            'period': '접수기간',
            'status': '상태',
            'organization': '기관',
            'views': '조회수'
        }
        
        for field, label in meta_fields.items():
            if field in announcement and announcement[field]:
                meta_lines.append(f"**{label}**: {announcement[field]}")
        
        meta_lines.extend([
            f"**원본 URL**: {announcement['url']}",
            "",
            "---",
            ""
        ])
        
        return "\n".join(meta_lines)
    
    def _download_attachments(self, attachments: List[Dict[str, Any]], folder_path: str):
        """첨부파일 다운로드"""
        if not attachments:
            logger.info("첨부파일이 없습니다")
            return
        
        logger.info(f"{len(attachments)}개 첨부파일 다운로드 시작")
        attachments_folder = os.path.join(folder_path, 'attachments')
        os.makedirs(attachments_folder, exist_ok=True)
        
        for i, attachment in enumerate(attachments):
            try:
                logger.info(f"  첨부파일 {i+1}: {attachment['name']}")
                
                # 파일명 처리
                file_name = self.sanitize_filename(attachment['name'])
                if not file_name or file_name.isspace():
                    file_name = f"attachment_{i+1}"
                
                file_path = os.path.join(attachments_folder, file_name)
                
                # 파일 다운로드
                success = self.download_file(attachment['url'], file_path, attachment)
                if not success:
                    logger.warning(f"첨부파일 다운로드 실패: {attachment['name']}")
                
            except Exception as e:
                logger.error(f"첨부파일 처리 중 오류: {e}")
    
    def scrape_pages(self, max_pages: int = 4, output_base: str = 'output'):
        """여러 페이지 스크래핑 - 중복 체크 지원"""
        logger.info(f"스크래핑 시작: 최대 {max_pages}페이지")
        
        # 처리된 제목 목록 로드
        self.load_processed_titles(output_base)
        
        announcement_count = 0
        processed_count = 0
        early_stop = False
        stop_reason = ""
        
        for page_num in range(1, max_pages + 1):
            logger.info(f"페이지 {page_num} 처리 중")
            
            try:
                # 목록 가져오기 및 파싱
                announcements = self._get_page_announcements(page_num)
                
                if not announcements:
                    logger.warning(f"페이지 {page_num}에 공고가 없습니다")
                    if page_num == 1:
                        logger.error("첫 페이지에 공고가 없습니다. 사이트 구조를 확인해주세요.")
                        stop_reason = "첫 페이지 공고 없음"
                    else:
                        logger.info("마지막 페이지에 도달했습니다.")
                        stop_reason = "마지막 페이지 도달"
                    break
                
                logger.info(f"페이지 {page_num}에서 {len(announcements)}개 공고 발견")
                
                # 새로운 공고만 필터링 및 중복 임계값 체크
                new_announcements, should_stop = self.filter_new_announcements(announcements)
                
                # 중복 임계값 도달시 조기 종료
                if should_stop:
                    logger.info(f"중복 공고 {self.duplicate_threshold}개 연속 발견으로 조기 종료")
                    early_stop = True
                    stop_reason = f"중복 {self.duplicate_threshold}개 연속"
                    break
                
                # 새로운 공고가 없으면 조기 종료 (연속된 페이지에서)
                if not new_announcements and page_num > 1:
                    logger.info("새로운 공고가 없어 스크래핑 조기 종료")
                    early_stop = True
                    stop_reason = "새로운 공고 없음"
                    break
                
                # 각 공고 처리
                for ann in new_announcements:
                    announcement_count += 1
                    processed_count += 1
                    self.process_announcement(ann, announcement_count, output_base)
                
                # 페이지 간 대기
                if page_num < max_pages and self.delay_between_pages > 0:
                    time.sleep(self.delay_between_pages)
                
            except Exception as e:
                logger.error(f"페이지 {page_num} 처리 중 오류: {e}")
                stop_reason = f"오류: {e}"
                break
        
        # 처리된 제목 목록 저장
        self.save_processed_titles()
        
        if early_stop:
            logger.info(f"스크래핑 완료: 총 {processed_count}개 새로운 공고 처리 (조기종료: {stop_reason})")
        else:
            logger.info(f"스크래핑 완료: 총 {processed_count}개 새로운 공고 처리")
    
    def _get_page_announcements(self, page_num: int) -> List[Dict[str, Any]]:
        """페이지별 공고 목록 가져오기 - 기본 구현"""
        page_url = self.get_list_url(page_num)
        response = self.get_page(page_url)
        
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


class StandardTableScraper(EnhancedBaseScraper):
    """표준 HTML 테이블 기반 게시판용 스크래퍼"""
    
    def get_list_url(self, page_num: int) -> str:
        """표준 페이지네이션 URL 생성"""
        if not self.config:
            # 하위 클래스에서 직접 구현
            return super().get_list_url(page_num)
        
        pagination = self.config.pagination
        if pagination.get('type') == 'query_param':
            param = pagination.get('param', 'page')
            if page_num == 1:
                return self.list_url
            else:
                separator = '&' if '?' in self.list_url else '?'
                return f"{self.list_url}{separator}{param}={page_num}"
        
        return self.list_url
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """표준 테이블 파싱 - 설정 기반"""
        if not self.config or not self.config.selectors:
            # 하위 클래스에서 직접 구현
            return super().parse_list_page(html_content)
        
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        selectors = self.config.selectors
        
        # 테이블 찾기
        table = soup.select_one(selectors.get('table', 'table'))
        if not table:
            return announcements
        
        # 행들 찾기
        rows = table.select(selectors.get('rows', 'tr'))
        
        for row in rows:
            try:
                # 제목 링크 찾기
                link_elem = row.select_one(selectors.get('title_link', 'a[href]'))
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                if not title:
                    continue
                
                # URL 구성
                href = link_elem.get('href', '')
                detail_url = urljoin(self.base_url, href)
                
                announcement = {
                    'title': title,
                    'url': detail_url
                }
                
                # 추가 필드들 (선택적)
                field_selectors = {
                    'status': 'status',
                    'writer': 'writer', 
                    'date': 'date',
                    'period': 'period'
                }
                
                for field, selector_key in field_selectors.items():
                    if selector_key in selectors:
                        elem = row.select_one(selectors[selector_key])
                        if elem:
                            announcement[field] = elem.get_text(strip=True)
                
                announcements.append(announcement)
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        return announcements


class AjaxAPIScraper(EnhancedBaseScraper):
    """AJAX/JSON API 기반 스크래퍼"""
    
    def get_list_url(self, page_num: int) -> str:
        """API URL 반환"""
        return getattr(self.config, 'api_url', self.list_url)
    
    def _get_page_announcements(self, page_num: int) -> List[Dict[str, Any]]:
        """API를 통한 공고 목록 가져오기"""
        if not self.config or not self.config.api_config:
            return super()._get_page_announcements(page_num)
        
        api_config = self.config.api_config
        api_url = getattr(self.config, 'api_url', self.list_url)
        
        # 요청 데이터 구성
        data = api_config.get('data_fields', {}).copy()
        
        # 페이지 번호 추가
        pagination = self.config.pagination
        if pagination.get('type') == 'post_data':
            param = pagination.get('param', 'page')
            data[param] = str(page_num)
        
        # API 호출
        if api_config.get('method', 'POST').upper() == 'POST':
            response = self.post_page(api_url, data=data)
        else:
            response = self.get_page(api_url, params=data)
        
        if not response:
            return []
        
        try:
            json_data = response.json()
            return self.parse_api_response(json_data, page_num)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}")
            return []
    
    def parse_api_response(self, json_data: Dict[str, Any], page_num: int) -> List[Dict[str, Any]]:
        """API 응답 파싱 - 하위 클래스에서 구현"""
        return self.parse_list_page(json_data)


class JavaScriptScraper(EnhancedBaseScraper):
    """JavaScript 실행이 필요한 사이트용 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        # Playwright나 Selenium 등을 위한 설정
        self.browser_options = {
            'headless': True,
            'timeout': 30000
        }
    
    def extract_js_data(self, html_content: str, pattern: str) -> List[str]:
        """JavaScript에서 데이터 추출"""
        matches = re.findall(pattern, html_content, re.DOTALL)
        return matches


class SessionBasedScraper(EnhancedBaseScraper):
    """세션 관리가 필요한 사이트용 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        self.session_initialized = False
        self.session_data = {}
    
    def initialize_session(self):
        """세션 초기화 - 하위 클래스에서 구현"""
        if self.session_initialized:
            return True
        
        # 기본적으로 첫 페이지 방문으로 세션 초기화
        try:
            response = self.get_page(self.base_url or self.list_url)
            if response:
                self.session_initialized = True
                return True
        except Exception as e:
            logger.error(f"세션 초기화 실패: {e}")
        
        return False
    
    def _get_page_announcements(self, page_num: int) -> List[Dict[str, Any]]:
        """세션 확인 후 공고 목록 가져오기"""
        if not self.initialize_session():
            logger.error("세션 초기화 실패")
            return []
        
        return super()._get_page_announcements(page_num)


class PlaywrightScraper(EnhancedBaseScraper):
    """Playwright 브라우저 자동화 기반 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        self.browser = None
        self.page = None
        self.browser_options = {
            'headless': True,
            'timeout': 30000
        }
    
    async def initialize_browser(self):
        """브라우저 초기화 - 하위 클래스에서 Playwright 구현"""
        # 실제 Playwright 구현은 하위 클래스에서
        pass
    
    async def cleanup_browser(self):
        """브라우저 정리"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()