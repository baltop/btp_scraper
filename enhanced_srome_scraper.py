#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced SROME 스크래퍼

한국산업기술기획평가원(KEIT) SROME 시스템의 공지사항을 수집하는 Enhanced 스크래퍼입니다.

특징:
- JavaScript 기반 동적 페이지
- f_detail() 함수로 상세 페이지 접근
- POST 요청 기반 페이지네이션
- UTF-8 한글 파일명 지원
"""

import os
import re
import time
import json
import hashlib
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, unquote, parse_qs, urlparse
import requests
from bs4 import BeautifulSoup

# Enhanced base scraper import
try:
    from enhanced_base_scraper import StandardTableScraper
except ImportError:
    print("enhanced_base_scraper를 찾을 수 없습니다. 기본 클래스를 생성합니다.")
    
    class StandardTableScraper:
        def __init__(self):
            self.config = None
            self.session = requests.Session()
            self.headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            self.session.headers.update(self.headers)
            self.timeout = 30
            self.delay_between_requests = 2
            self.duplicate_threshold = 3
            self.processed_titles_file = None
            self.processed_titles = set()
            
            # HTML to text 변환기
            import html2text
            self.h = html2text.HTML2Text()
            self.h.ignore_links = False
            self.h.ignore_images = False

        def sanitize_filename(self, filename: str) -> str:
            return re.sub(r'[<>:"/\\|?*]', '_', filename)

        def normalize_title_for_hash(self, title: str) -> str:
            normalized = re.sub(r'\s+', ' ', title.strip())
            normalized = re.sub(r'[^\w\s가-힣]', '', normalized)
            return normalized.lower()

        def get_title_hash(self, title: str) -> str:
            normalized = self.normalize_title_for_hash(title)
            return hashlib.md5(normalized.encode('utf-8')).hexdigest()

        def is_title_processed(self, title: str) -> bool:
            title_hash = self.get_title_hash(title)
            return title_hash in self.processed_titles

        def mark_title_processed(self, title: str):
            title_hash = self.get_title_hash(title)
            self.processed_titles.add(title_hash)
            self.save_processed_titles()

        def load_processed_titles(self):
            if self.processed_titles_file and os.path.exists(self.processed_titles_file):
                try:
                    with open(self.processed_titles_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self.processed_titles = set(data.get('processed_titles', []))
                except Exception as e:
                    logging.warning(f"기존 처리 목록 로드 실패: {e}")

        def save_processed_titles(self):
            if self.processed_titles_file:
                try:
                    with open(self.processed_titles_file, 'w', encoding='utf-8') as f:
                        json.dump({'processed_titles': list(self.processed_titles)}, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    logging.error(f"처리 목록 저장 실패: {e}")

        def filter_new_announcements(self, announcements: List[Dict[str, Any]]) -> tuple:
            new_announcements = []
            duplicate_count = 0
            
            for ann in announcements:
                title = ann.get('title', '')
                if not self.is_title_processed(title):
                    new_announcements.append(ann)
                    duplicate_count = 0
                else:
                    duplicate_count += 1
                    logging.info(f"중복 제목 발견: {title}")
                    if duplicate_count >= self.duplicate_threshold:
                        logging.info(f"연속 {self.duplicate_threshold}개 중복 발견. 조기 종료합니다.")
                        return new_announcements, True
            
            return new_announcements, False

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EnhancedSROMEScraper(StandardTableScraper):
    """SROME 전용 스크래퍼 - 향상된 버전
    
    한국산업기술기획평가원(KEIT) SROME 시스템을 위한 Enhanced 스크래퍼입니다.
    """
    
    def __init__(self):
        super().__init__()
        # 기본 설정
        self.base_url = "https://srome.keit.re.kr"
        self.list_url = "https://srome.keit.re.kr/srome/biz/perform/opnnPrpsl/retrieveTaskAnncmListView.do"
        self.detail_url = "https://srome.keit.re.kr/srome/biz/perform/opnnPrpsl/retrieveTaskAnncmInfoView.do"
        self.file_download_url = "https://srome.keit.re.kr/srome/biz/common/file/downloadAtchItechFile.do"
        
        # SROME 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 60
        self.delay_between_requests = 3
        
        # 기본 파라미터
        self.default_params = {
            'prgmId': 'XPG201040000',
            'rcveStatus': 'A'
        }
        
        # 세션 헤더 설정
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': self.base_url
        })
        
        # 중복 검사 설정
        self.processed_titles_file = 'processed_titles_srome.json'
        self.load_processed_titles()
        
        logger.info("SROME Enhanced 스크래퍼 초기화 완료")

    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - SROME는 POST 요청 사용"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: SROME는 POST 요청이므로 기본 URL만 반환
        return self.list_url

    def fetch_list_page(self, page_num: int) -> str:
        """POST 요청을 통해 목록 페이지 데이터 가져오기"""
        try:
            logger.info(f"{page_num}페이지 POST 요청")
            
            # POST 요청 데이터 구성
            post_data = self.default_params.copy()
            post_data.update({
                'pageIndex': str(page_num),
                'pageUnit': '10',  # 페이지당 항목 수
                'searchCnd': '',
                'searchWrd': ''
            })
            
            # POST 요청 실행
            response = self.session.post(
                self.list_url,
                data=post_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': self.list_url,
                    'User-Agent': self.headers['User-Agent']
                },
                timeout=self.timeout
            )
            
            response.encoding = self.default_encoding
            
            if response.status_code == 200:
                logger.info(f"{page_num}페이지 POST 요청 성공")
                logger.debug(f"응답 길이: {len(response.text)}")
                return response.text
            else:
                logger.error(f"POST 요청 실패: {response.status_code}")
                return ""
                
        except Exception as e:
            logger.error(f"페이지 {page_num} 로드 실패: {e}")
            return ""

    def parse_list_page(self, html_content: str = None) -> List[Dict[str, Any]]:
        """목록 페이지 파싱"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors and html_content:
            return super().parse_list_page(html_content)
        
        # Fallback: SROME 특화 로직
        return self._parse_list_fallback(html_content)

    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """SROME 특화 목록 파싱"""
        announcements = []
        
        if not html_content:
            logger.warning("HTML 콘텐츠가 없습니다")
            return announcements
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            logger.info("SROME 목록 페이지 파싱 시작")
            
            # f_detail 함수 호출 패턴을 가진 요소 찾기
            onclick_elements = soup.find_all(attrs={'onclick': True})
            
            for element in onclick_elements:
                try:
                    onclick = element.get('onclick', '')
                    
                    # f_detail 함수 호출 패턴 매칭
                    # 예: f_detail('I13715', '2025')
                    detail_match = re.search(r"f_detail\s*\(\s*['\"]([^'\"]+)['\"],\s*['\"](\d{4})['\"]", onclick)
                    if not detail_match:
                        continue
                    
                    ancm_id = detail_match.group(1)
                    bsns_year = detail_match.group(2)
                    
                    # 제목 추출
                    title = self._extract_title_from_element(element)
                    if not title:
                        continue
                    
                    # 추가 정보 추출 (부모 행에서)
                    date_info = self._extract_date_info(element)
                    
                    announcement = {
                        'title': title,
                        'ancm_id': ancm_id,
                        'bsns_year': bsns_year,
                        'onclick': onclick,
                        'date': date_info.get('date', ''),
                        'deadline': date_info.get('deadline', ''),
                        'detail_params': {
                            'ancmId': ancm_id,
                            'bsnsYy': bsns_year,
                            'prgmId': self.default_params['prgmId']
                        }
                    }
                    
                    announcements.append(announcement)
                    logger.debug(f"공고 파싱: {title}")
                    
                except Exception as e:
                    logger.error(f"요소 파싱 중 오류: {e}")
                    continue
            
            logger.info(f"{len(announcements)}개 공고 파싱 완료")
            return announcements
            
        except Exception as e:
            logger.error(f"목록 페이지 파싱 실패: {e}")
            return announcements

    def _extract_title_from_element(self, element) -> str:
        """요소에서 제목 추출"""
        # 1. span.title 찾기
        title_span = element.find('span', class_='title')
        if title_span:
            return title_span.get_text(strip=True)
        
        # 2. 직접 텍스트에서 추출
        element_text = element.get_text(strip=True)
        if '공고' in element_text and len(element_text) > 10:
            return element_text
        
        # 3. 부모 요소에서 찾기
        parent = element.parent
        if parent:
            parent_text = parent.get_text(strip=True)
            if '공고' in parent_text and len(parent_text) > 10:
                return parent_text
        
        return ""

    def _extract_date_info(self, element) -> Dict[str, str]:
        """날짜 정보 추출"""
        date_info = {'date': '', 'deadline': ''}
        
        try:
            # 부모 행에서 날짜 정보 찾기
            parent_row = element.find_parent('tr') or element.find_parent('div', class_='row')
            
            if parent_row:
                row_text = parent_row.get_text()
                
                # 날짜 패턴 찾기 (YYYY-MM-DD, YYYY.MM.DD 등)
                date_patterns = [
                    r'\d{4}-\d{2}-\d{2}',
                    r'\d{4}\.\d{2}\.\d{2}',
                    r'\d{4}/\d{2}/\d{2}'
                ]
                
                for pattern in date_patterns:
                    dates = re.findall(pattern, row_text)
                    if dates:
                        date_info['date'] = dates[0]
                        if len(dates) > 1:
                            date_info['deadline'] = dates[1]
                        break
        
        except Exception as e:
            logger.debug(f"날짜 정보 추출 실패: {e}")
        
        return date_info

    def fetch_detail_page(self, announcement: Dict[str, Any]) -> str:
        """상세 페이지 HTML 가져오기"""
        try:
            detail_params = announcement.get('detail_params', {})
            ancm_id = detail_params.get('ancmId')
            bsns_yy = detail_params.get('bsnsYy')
            prgm_id = detail_params.get('prgmId')
            
            if not all([ancm_id, bsns_yy]):
                logger.warning(f"필수 파라미터가 없습니다: {announcement.get('title', '')}")
                logger.debug(f"파라미터: ancmId={ancm_id}, bsnsYy={bsns_yy}, prgmId={prgm_id}")
                return ""
            
            # POST 데이터 구성 (실제 웹사이트와 동일한 파라미터 사용)
            post_data = {
                'ancmId': ancm_id,
                'bsnsYy': bsns_yy,
                'prgmId': prgm_id or self.default_params['prgmId'],
                'rcveStatus': self.default_params['rcveStatus']
            }
            
            logger.info(f"상세 페이지 요청: {announcement.get('title', '')}")
            
            # POST 요청으로 상세 페이지 가져오기
            response = self.session.post(
                self.detail_url,
                data=post_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': self.list_url
                },
                timeout=self.timeout
            )
            
            response.encoding = self.default_encoding
            
            if response.status_code == 200:
                logger.debug(f"상세 페이지 로드 성공: {announcement.get('title', '')}")
                return response.text
            else:
                logger.error(f"상세 페이지 로드 실패: {response.status_code}")
                return ""
                
        except Exception as e:
            logger.error(f"상세 페이지 로드 실패: {e}")
            return ""

    def parse_detail_page(self, html_content: str = None) -> Dict[str, Any]:
        """상세 페이지 파싱"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors and html_content:
            return super().parse_detail_page(html_content)
        
        # Fallback: SROME 특화 로직
        return self._parse_detail_fallback(html_content)

    def _parse_detail_fallback(self, html_content: str) -> Dict[str, Any]:
        """SROME 특화 상세 페이지 파싱"""
        try:
            if not html_content:
                return {'title': '', 'content': '', 'attachments': []}
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 제목 추출
            title = self._extract_detail_title(soup)
            
            # 본문 내용 추출
            content = self._extract_detail_content(soup)
            
            # 첨부파일 추출
            attachments = self._extract_detail_attachments(soup)
            
            result = {
                'title': title,
                'content': content,
                'attachments': attachments
            }
            
            logger.debug(f"상세 페이지 파싱 완료 - 첨부파일: {len(attachments)}개")
            return result
            
        except Exception as e:
            logger.error(f"상세 페이지 파싱 실패: {e}")
            return {'title': '', 'content': '', 'attachments': []}

    def _extract_detail_title(self, soup: BeautifulSoup) -> str:
        """상세 페이지 제목 추출"""
        title_selectors = [
            'h1',
            'h2',
            '.title',
            '.subject',
            'table tr th'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = title_elem.get_text(strip=True)
                if title and len(title) > 5:
                    logger.debug(f"제목을 {selector} 선택자로 찾음")
                    return title
        
        logger.warning("제목을 찾을 수 없습니다")
        return ""

    def _extract_detail_content(self, soup: BeautifulSoup) -> str:
        """상세 페이지 본문 추출"""
        content_selectors = [
            '.content',
            '.view_content',
            '.cont',
            'table td',
            '.board_view'
        ]
        
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                # HTML을 마크다운으로 변환
                content_html = str(content_elem)
                content_md = self.h.handle(content_html)
                
                if content_md and len(content_md.strip()) > 20:
                    logger.debug(f"본문을 {selector} 선택자로 찾음")
                    return content_md.strip()
        
        logger.warning("본문을 찾을 수 없습니다")
        return ""

    def _extract_detail_attachments(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """상세 페이지 첨부파일 추출 - SROME 특화"""
        attachments = []
        
        try:
            # 1. 모든 링크 요소 찾기
            all_links = soup.find_all('a')
            
            for link in all_links:
                try:
                    onclick = link.get('onclick', '')
                    href = link.get('href', '')
                    filename = link.get_text(strip=True)
                    
                    # 파일 다운로드 관련 패턴 확인
                    is_download_link = (
                        'download' in onclick.lower() or
                        'file' in onclick.lower() or
                        'downloadAtchItechFile' in onclick or
                        'atchDocId' in href or
                        'atchFileId' in href or
                        ('.hwp' in filename.lower() or '.pdf' in filename.lower() or 
                         '.zip' in filename.lower() or '.doc' in filename.lower())
                    )
                    
                    if is_download_link and filename and filename not in ['', '#', 'download', '다운로드']:
                        file_params = {}
                        
                        # 1. onclick에서 파라미터 추출
                        if onclick:
                            file_params = self._extract_file_params(onclick)
                        
                        # 2. href에서 직접 파라미터 추출 (URL 파라미터 방식)
                        if not file_params and href and href != '#':
                            file_params = self._extract_params_from_url(href)
                        
                        # 3. 부모 요소에서 data 속성 확인
                        if not file_params:
                            parent = link.parent
                            if parent:
                                for attr in parent.attrs:
                                    if 'atch' in attr.lower():
                                        file_params[attr] = parent.attrs[attr]
                        
                        attachment = {
                            'filename': filename,
                            'onclick': onclick,
                            'href': href,
                            'file_params': file_params
                        }
                        
                        attachments.append(attachment)
                        logger.debug(f"첨부파일 발견: {filename} - 파라미터: {len(file_params)}개")
                
                except Exception as e:
                    logger.warning(f"첨부파일 링크 처리 중 오류: {e}")
                    continue
            
            # 중복 제거
            unique_attachments = []
            seen_filenames = set()
            
            for attachment in attachments:
                filename = attachment['filename']
                if filename not in seen_filenames:
                    unique_attachments.append(attachment)
                    seen_filenames.add(filename)
            
            logger.info(f"{len(unique_attachments)}개 첨부파일 발견 (중복 제거 후)")
            return unique_attachments
            
        except Exception as e:
            logger.error(f"첨부파일 추출 실패: {e}")
            return attachments
    
    def _extract_params_from_url(self, url: str) -> Dict[str, str]:
        """URL에서 파라미터 추출"""
        params = {}
        
        try:
            from urllib.parse import urlparse, parse_qs
            
            if '?' in url:
                parsed = urlparse(url)
                query_params = parse_qs(parsed.query)
                
                for key, value_list in query_params.items():
                    if value_list:
                        params[key] = value_list[0]
                
                logger.debug(f"URL에서 파라미터 추출: {params}")
        
        except Exception as e:
            logger.debug(f"URL 파라미터 추출 실패: {e}")
        
        return params

    def _extract_file_params(self, onclick: str) -> Dict[str, str]:
        """onclick에서 파일 다운로드 파라미터 추출 - SROME 특화"""
        params = {}
        
        if not onclick:
            return params
        
        try:
            # SROME의 파일 다운로드 패턴
            # 예: downloadAtchItechFile('base64_atchDocId', 'base64_atchFileId')
            # 또는 단순 다운로드 링크
            
            # Base64 파라미터 패턴 찾기
            base64_pattern = r"downloadAtchItechFile\s*\(\s*['\"]([^'\"]+)['\"],\s*['\"]([^'\"]+)['\"]"
            match = re.search(base64_pattern, onclick)
            
            if match:
                params['atchDocId'] = match.group(1)
                params['atchFileId'] = match.group(2)
                logger.debug(f"Base64 파라미터 추출: atchDocId={params['atchDocId'][:20]}..., atchFileId={params['atchFileId'][:20]}...")
                return params
            
            # 대안 패턴 시도
            general_pattern = r"(\w+)\s*\(\s*['\"]([^'\"]+)['\"](?:,\s*['\"]([^'\"]+)['\"])?"
            match = re.search(general_pattern, onclick)
            
            if match:
                func_name = match.group(1)
                param1 = match.group(2)
                param2 = match.group(3) if match.group(3) else None
                
                if 'download' in func_name.lower() or 'file' in func_name.lower():
                    # 첫 번째 파라미터를 atchDocId로, 두 번째를 atchFileId로 간주
                    params['atchDocId'] = param1
                    if param2:
                        params['atchFileId'] = param2
                    else:
                        # 단일 파라미터인 경우 atchFileId로 사용
                        params['atchFileId'] = param1
                
                logger.debug(f"일반 파라미터 추출: {params}")
        
        except Exception as e:
            logger.warning(f"파일 파라미터 추출 실패: {e}")
        
        return params

    def download_attachment(self, attachment: Dict[str, str], save_dir: str) -> bool:
        """첨부파일 다운로드 - SROME 특화"""
        try:
            filename = attachment.get('filename', 'unknown_file')
            file_params = attachment.get('file_params', {})
            
            # SROME의 새로운 파라미터 구조 확인
            atch_doc_id = file_params.get('atchDocId')
            atch_file_id = file_params.get('atchFileId')
            
            if not atch_doc_id and not atch_file_id:
                logger.warning(f"필수 파라미터가 없는 파일: {filename}")
                logger.debug(f"파일 파라미터: {file_params}")
                return False
            
            # 파일명 정리
            clean_filename = self.sanitize_filename(filename)
            if not clean_filename.strip() or clean_filename == '다운로드':
                clean_filename = f"attachment_{int(time.time())}.file"
            
            save_path = os.path.join(save_dir, clean_filename)
            
            logger.info(f"파일 다운로드 시작: {filename}")
            
            # SROME 파일 다운로드 파라미터 구성
            download_params = {}
            
            if atch_doc_id:
                download_params['atchDocId'] = atch_doc_id
            if atch_file_id:
                download_params['atchFileId'] = atch_file_id
            
            logger.debug(f"다운로드 파라미터: {download_params}")
            
            # GET 요청으로 파일 다운로드 (SROME는 GET 방식 사용)
            response = self.session.get(
                self.file_download_url,
                params=download_params,
                headers={
                    'Referer': self.detail_url,
                    'User-Agent': self.headers['User-Agent']
                },
                stream=True,
                timeout=120
            )
            
            if response.status_code == 200:
                # 파일명 인코딩 처리
                final_save_path = self._handle_filename_encoding(response, save_path, save_dir)
                
                # 스트리밍 다운로드
                with open(final_save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                # 파일 크기 확인
                if os.path.exists(final_save_path):
                    file_size = os.path.getsize(final_save_path)
                    logger.info(f"다운로드 완료: {final_save_path} ({file_size:,} bytes)")
                    return True
                else:
                    logger.error(f"다운로드 파일이 저장되지 않음: {final_save_path}")
                    return False
            else:
                logger.error(f"파일 다운로드 실패: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"파일 다운로드 실패 {filename}: {e}")
            return False

    def _handle_filename_encoding(self, response: requests.Response, default_path: str, save_dir: str) -> str:
        """응답 헤더에서 파일명 추출 및 인코딩 처리"""
        content_disposition = response.headers.get('Content-Disposition', '')
        
        if content_disposition:
            # RFC 5987 형식 우선 처리
            rfc5987_match = re.search(r"filename\*=([^']*)'([^']*)'(.+)", content_disposition)
            if rfc5987_match:
                encoding, lang, filename = rfc5987_match.groups()
                try:
                    filename = unquote(filename, encoding=encoding or 'utf-8')
                    clean_filename = self.sanitize_filename(filename)
                    return os.path.join(save_dir, clean_filename)
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
                            decoded = filename.encode('latin-1').decode('utf-8')
                        else:
                            decoded = filename.encode('latin-1').decode(encoding)
                        
                        if decoded and not decoded.isspace():
                            clean_filename = self.sanitize_filename(decoded.replace('+', ' '))
                            return os.path.join(save_dir, clean_filename)
                    except:
                        continue
        
        return default_path

    def scrape_pages(self, max_pages: int = 3, output_base: str = "output") -> bool:
        """여러 페이지 스크래핑 실행"""
        output_dir = os.path.join(output_base, "srome")
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"SROME 스크래핑 시작 - 최대 {max_pages}페이지")
        
        try:
            total_processed = 0
            
            for page_num in range(1, max_pages + 1):
                logger.info(f"\n=== {page_num}페이지 처리 시작 ===")
                
                # 페이지 HTML 가져오기
                html_content = self.fetch_list_page(page_num)
                if not html_content:
                    logger.error(f"{page_num}페이지 로드 실패")
                    break
                
                # 목록 파싱
                announcements = self.parse_list_page(html_content)
                if not announcements:
                    logger.warning(f"{page_num}페이지에 공고가 없습니다")
                    break
                
                # 중복 검사 및 필터링
                new_announcements, should_stop = self.filter_new_announcements(announcements)
                
                if not new_announcements:
                    logger.info(f"{page_num}페이지에 새로운 공고가 없습니다")
                    if should_stop:
                        logger.info("중복 임계값 도달. 스크래핑을 종료합니다.")
                        break
                    continue
                
                logger.info(f"{len(new_announcements)}개 새로운 공고 처리 시작")
                
                # 각 공고 처리
                for i, announcement in enumerate(new_announcements):
                    try:
                        title = announcement.get('title', f'공고_{page_num}_{i+1}')
                        logger.info(f"처리 중: {title}")
                        
                        # 상세 페이지 HTML 가져오기
                        detail_html = self.fetch_detail_page(announcement)
                        if not detail_html:
                            logger.error(f"상세 페이지 로드 실패: {title}")
                            continue
                        
                        # 상세 내용 파싱
                        detail_data = self.parse_detail_page(detail_html)
                        
                        # 폴더 생성
                        safe_title = self.sanitize_filename(title)
                        folder_name = f"{total_processed + 1:03d}_{safe_title}"
                        announcement_dir = os.path.join(output_dir, folder_name)
                        os.makedirs(announcement_dir, exist_ok=True)
                        
                        # 첨부파일 다운로드
                        attachments_dir = os.path.join(announcement_dir, 'attachments')
                        downloaded_count = 0
                        
                        if detail_data.get('attachments'):
                            os.makedirs(attachments_dir, exist_ok=True)
                            
                            for attachment in detail_data['attachments']:
                                if self.download_attachment(attachment, attachments_dir):
                                    downloaded_count += 1
                                time.sleep(1)  # 다운로드 간격
                        
                        # content.md 파일 생성
                        content_md = self._generate_content_md(
                            detail_data.get('title', title),
                            announcement.get('date', ''),
                            announcement.get('deadline', ''),
                            f"{self.detail_url}?ancmId={announcement.get('ancm_id', '')}&bsnsYear={announcement.get('bsns_year', '')}&prgmId={self.default_params['prgmId']}",
                            detail_data.get('content', ''),
                            downloaded_count
                        )
                        
                        content_file = os.path.join(announcement_dir, 'content.md')
                        with open(content_file, 'w', encoding='utf-8') as f:
                            f.write(content_md)
                        
                        # 처리 완료 표시
                        self.mark_title_processed(title)
                        total_processed += 1
                        
                        logger.info(f"처리 완료: {title} (첨부파일: {downloaded_count}개)")
                        
                        time.sleep(self.delay_between_requests)
                        
                    except Exception as e:
                        logger.error(f"공고 처리 중 오류: {e}")
                        continue
                
                logger.info(f"{page_num}페이지 처리 완료")
                
                # 조기 종료 조건 확인
                if should_stop:
                    logger.info("중복 임계값 도달. 스크래핑을 종료합니다.")
                    break
                
                time.sleep(self.delay_between_requests * 2)  # 페이지 간격
            
            logger.info(f"\n=== 스크래핑 완료 ===")
            logger.info(f"총 처리된 공고: {total_processed}개")
            return True
            
        except Exception as e:
            logger.error(f"스크래핑 중 오류 발생: {e}")
            return False

    def _generate_content_md(self, title: str, date: str, deadline: str, url: str, content: str, attachment_count: int) -> str:
        """content.md 파일 내용 생성"""
        md_content = f"# {title}\n\n"
        
        if date:
            md_content += f"**등록일**: {date}\n"
        if deadline:
            md_content += f"**마감일**: {deadline}\n"
        if url:
            md_content += f"**원본 URL**: {url}\n"
        
        md_content += f"\n---\n\n"
        
        if content:
            md_content += f"{content}\n\n"
        
        if attachment_count > 0:
            md_content += f"**첨부파일**: {attachment_count}개 파일이 attachments 폴더에 저장되었습니다.\n\n"
        
        return md_content


# 하위 호환성을 위한 별칭
SROMEScraper = EnhancedSROMEScraper


def main():
    """테스트 실행"""
    scraper = EnhancedSROMEScraper()
    scraper.scrape_pages(max_pages=3, output_base="output")


if __name__ == "__main__":
    main()