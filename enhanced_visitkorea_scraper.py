#!/usr/bin/env python3
"""
Visit Korea Enhanced 스크래퍼

한국관광품질인증제 사이트의 공지사항을 수집하는 Enhanced 스크래퍼입니다.
Spring Framework 기반 사이트로 requests + BeautifulSoup을 주로 사용합니다.

특징:
- Spring Framework 기반 (.kto 확장자)
- POST 요청 기반 페이지네이션
- UTF-8 한글 파일명 지원
- Form 기반 파일 다운로드
"""

import os
import re
import time
import json
import hashlib
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, unquote, parse_qs
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


class EnhancedVisitKoreaScraper(StandardTableScraper):
    """Visit Korea 전용 스크래퍼 - 향상된 버전
    
    Spring Framework 기반 사이트로 requests + BeautifulSoup을 사용하는 Enhanced 스크래퍼입니다.
    """
    
    def __init__(self):
        super().__init__()
        # 기본 설정
        self.base_url = "https://koreaquality.visitkorea.or.kr"
        self.list_url = "https://koreaquality.visitkorea.or.kr/qualityCenter/notice/noticeList.kto"
        self.ajax_url = "https://koreaquality.visitkorea.or.kr/qualityCenter/notice/selectNoticeKqList.kto"
        self.detail_url = "https://koreaquality.visitkorea.or.kr/qualityCenter/notice/noticeDetail.kto"
        self.download_url = "https://koreaquality.visitkorea.or.kr/downloadFile.kto"
        
        # Visit Korea 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 60
        self.delay_between_requests = 3
        
        # 세션 헤더 설정
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # 중복 검사 설정
        self.processed_titles_file = 'processed_titles_visitkorea.json'
        self.load_processed_titles()
        
        logger.info("Visit Korea Enhanced 스크래퍼 초기화 완료")

    def mark_title_processed(self, title: str):
        """제목을 처리 완료로 표시"""
        title_hash = self.get_title_hash(title)
        self.processed_titles.add(title_hash)
        self.save_processed_titles()

    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - Visit Korea는 AJAX 기반이므로 기본 URL만 반환"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: Visit Korea는 AJAX 요청 사용
        return self.list_url

    def fetch_list_page(self, page_num: int) -> str:
        """AJAX를 통해 목록 페이지 데이터 가져오기"""
        try:
            # 먼저 기본 페이지에 접속하여 세션 설정 (모든 페이지에서)
            if page_num == 1:
                logger.info("기본 페이지 접속하여 세션 설정")
                response = self.session.get(self.list_url, timeout=self.timeout)
                response.encoding = self.default_encoding
            
            # 모든 페이지에 대해 AJAX 요청 사용 (데이터가 동적 로딩되므로)
            logger.info(f"{page_num}페이지 AJAX 요청")
            
            # AJAX 요청 데이터 구성 (수정된 파라미터)
            ajax_data = {
                'pageIndex': str(page_num),  # currentPageNo → pageIndex
                'searchType': '',            # searchCondition → searchType  
                'searchValue': '',           # searchKeyword → searchValue
                'noticeObject': '01'         # bbsId → noticeObject (01: 일반 공지사항)
            }
            
            # AJAX 요청 실행
            response = self.session.post(
                self.ajax_url,
                data=ajax_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Referer': self.list_url,
                    'User-Agent': self.headers['User-Agent']
                },
                timeout=self.timeout
            )
            
            response.encoding = self.default_encoding
            
            if response.status_code == 200:
                logger.info(f"{page_num}페이지 AJAX 요청 성공")
                logger.debug(f"AJAX 응답 길이: {len(response.text)}")
                logger.debug(f"AJAX 응답 시작: {response.text[:500]}")
                
                # JSON 응답인지 확인
                try:
                    json_data = response.json()
                    logger.debug(f"JSON 응답 받음: {json_data.keys() if isinstance(json_data, dict) else type(json_data)}")
                    return response.text
                except:
                    logger.debug("JSON이 아닌 응답 (HTML 등)")
                    return response.text
            else:
                logger.error(f"AJAX 요청 실패: {response.status_code}")
                logger.debug(f"에러 응답: {response.text[:200]}")
                return ""
                
        except Exception as e:
            logger.error(f"페이지 {page_num} 로드 실패: {e}")
            return ""

    def parse_list_page(self, html_content: str = None) -> List[Dict[str, Any]]:
        """목록 페이지 파싱"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors and html_content:
            return super().parse_list_page(html_content)
        
        # Fallback: Visit Korea 특화 로직
        return self._parse_list_fallback(html_content)

    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """Visit Korea 특화 목록 파싱"""
        announcements = []
        
        if not html_content:
            logger.warning("HTML 콘텐츠가 없습니다")
            return announcements
        
        try:
            # JSON 응답인지 먼저 확인
            try:
                json_data = json.loads(html_content)
                logger.info("JSON 응답 파싱")
                return self._parse_json_response(json_data)
            except json.JSONDecodeError:
                logger.debug("JSON이 아님, HTML 파싱 시도")
            
            # HTML 파싱
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # HTML 구조 디버깅
            logger.debug(f"HTML 길이: {len(html_content)}")
            tables = soup.find_all('table')
            logger.debug(f"발견된 테이블 수: {len(tables)}")
            
            # 공지사항 테이블 찾기
            table = soup.find('table')
            if not table:
                logger.warning("공지사항 테이블을 찾을 수 없습니다")
                # HTML 일부를 출력하여 디버깅
                logger.debug(f"HTML 시작 부분: {html_content[:1000]}")
                return announcements
            
            # tbody 내의 모든 행 가져오기
            tbody = table.find('tbody')
            logger.debug(f"tbody 발견: {tbody is not None}")
            
            if not tbody:
                tbody = table
                logger.debug("tbody가 없어서 table 전체 사용")
            
            rows = tbody.find_all('tr')
            logger.info(f"테이블에서 {len(rows)}개 행 발견")
            
            # 테이블 구조 디버깅
            if len(rows) == 0:
                all_trs = table.find_all('tr')
                logger.debug(f"table 전체에서 tr 수: {len(all_trs)}")
                logger.debug(f"테이블 HTML: {str(table)[:500]}")
            
            for i, row in enumerate(rows):
                try:
                    cells = row.find_all('td')
                    if len(cells) < 4:  # 번호, 제목, 등록일, 첨부 최소 4개 컬럼 필요
                        continue
                    
                    # 제목 및 링크 추출 (두 번째 컬럼)
                    title_cell = cells[1]
                    title_link = title_cell.find('a')
                    
                    if not title_link:
                        continue
                    
                    title = title_link.get_text(strip=True)
                    if not title:
                        continue
                    
                    # onclick 속성에서 상세 페이지 파라미터 추출
                    onclick = title_link.get('onclick', '')
                    
                    # 등록일 추출 (세 번째 컬럼)
                    date_text = cells[2].get_text(strip=True)
                    
                    # 첨부파일 여부 확인 (네 번째 컬럼)
                    attachment_cell = cells[3]
                    has_attachment = bool(attachment_cell.find('img'))
                    
                    # onclick에서 상세 페이지 파라미터 추출
                    detail_params = self._extract_detail_params(onclick)
                    
                    announcement = {
                        'title': title,
                        'url': self.detail_url,
                        'date': date_text,
                        'onclick': onclick,
                        'detail_params': detail_params,
                        'has_attachment': has_attachment,
                        'row_index': i
                    }
                    
                    announcements.append(announcement)
                    logger.debug(f"공고 파싱: {title} ({date_text})")
                    
                except Exception as e:
                    logger.error(f"행 파싱 중 오류 (행 {i}): {e}")
                    continue
            
            logger.info(f"{len(announcements)}개 공고 파싱 완료")
            return announcements
            
        except Exception as e:
            logger.error(f"목록 페이지 파싱 실패: {e}")
            return announcements

    def _parse_json_response(self, json_data: dict) -> List[Dict[str, Any]]:
        """JSON API 응답 파싱"""
        announcements = []
        
        try:
            if not isinstance(json_data, dict):
                logger.warning("JSON 데이터가 딕셔너리가 아닙니다")
                return announcements
            
            # rows 배열에서 공고 목록 추출
            rows = json_data.get('rows', [])
            logger.info(f"JSON에서 {len(rows)}개 공고 발견")
            
            for item in rows:
                try:
                    title = item.get('title', '').strip()
                    if not title:
                        continue
                    
                    # 공고 데이터 구성
                    announcement = {
                        'title': title,
                        'url': self.detail_url,
                        'date': item.get('createDt', ''),
                        'notice_no': item.get('noticeNo'),
                        'rn': item.get('rn'),  # 순번
                        'detail_params': {
                            'noticeNo': str(item.get('noticeNo', ''))
                        },
                        'has_attachment': bool(item.get('atchFileId', '')),
                        'atch_file_id': item.get('atchFileId', '')
                    }
                    
                    announcements.append(announcement)
                    logger.debug(f"JSON 공고 파싱: {title} ({announcement['date']})")
                    
                except Exception as e:
                    logger.error(f"JSON 공고 파싱 중 오류: {e}")
                    continue
            
            logger.info(f"JSON에서 {len(announcements)}개 공고 파싱 완료")
            return announcements
            
        except Exception as e:
            logger.error(f"JSON 응답 파싱 실패: {e}")
            return announcements

    def _extract_detail_params(self, onclick: str) -> Dict[str, str]:
        """onclick 속성에서 상세 페이지 파라미터 추출"""
        params = {}
        
        if not onclick:
            return params
        
        try:
            # JavaScript 함수 호출에서 파라미터 추출
            # 예: selectNoticeView('47', 'notice');
            # 예: fn_detail('47');
            
            # 함수명과 파라미터 추출
            match = re.search(r"(\w+)\s*\(\s*([^)]+)\s*\)", onclick)
            if match:
                func_name = match.group(1)
                param_str = match.group(2)
                
                # 파라미터를 쉼표로 분리하고 따옴표 제거
                param_list = [p.strip().strip("'\"") for p in param_str.split(',')]
                
                if func_name in ['selectNoticeView', 'fn_detail'] and param_list:
                    params['noticeId'] = param_list[0]
                    if len(param_list) > 1:
                        params['type'] = param_list[1]
                
                logger.debug(f"상세 페이지 파라미터 추출: {params}")
        
        except Exception as e:
            logger.warning(f"onclick 파라미터 추출 실패: {e}")
        
        return params

    def fetch_detail_page(self, announcement: Dict[str, Any]) -> str:
        """상세 페이지 HTML 가져오기"""
        try:
            detail_params = announcement.get('detail_params', {})
            notice_no = detail_params.get('noticeNo') or announcement.get('notice_no')
            
            if not notice_no:
                logger.warning(f"공고 ID가 없습니다: {announcement.get('title', '')}")
                logger.debug(f"announcement 데이터: {announcement}")
                return ""
            
            # POST 데이터 구성
            post_data = {
                'noticeNo': str(notice_no),  # noticeId → noticeNo
                'noticeObject': '01',        # bbsId → noticeObject
                'searchType': '',            # searchCondition → searchType
                'searchValue': '',           # searchKeyword → searchValue
                'pageIndex': '1'             # currentPageNo → pageIndex
            }
            
            logger.info(f"상세 페이지 요청: {announcement.get('title', '')}")
            
            # POST 요청으로 상세 페이지 가져오기
            response = self.session.post(
                self.detail_url,
                data=post_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
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
        
        # Fallback: Visit Korea 특화 로직
        return self._parse_detail_fallback(html_content)

    def _parse_detail_fallback(self, html_content: str) -> Dict[str, Any]:
        """Visit Korea 특화 상세 페이지 파싱"""
        try:
            if not html_content:
                return {'title': '', 'content': '', 'attachments': []}
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 제목 추출
            title = self._extract_title(soup)
            
            # 본문 내용 추출
            content = self._extract_content(soup)
            
            # 첨부파일 추출
            attachments = self._extract_attachments(soup)
            
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

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """제목 추출"""
        title_selectors = [
            'table tr th',  # 첫 번째 행의 th
            '.title',
            'h1',
            'h2',
            '.subject'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = title_elem.get_text(strip=True)
                # 제목에서 날짜 제거
                title = re.sub(r'\d{4}\.\d{2}\.\d{2}.*$', '', title).strip()
                if title:
                    logger.debug(f"제목을 {selector} 선택자로 찾음")
                    return title
        
        logger.warning("제목을 찾을 수 없습니다")
        return ""

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """본문 추출"""
        content_selectors = [
            'table tr:last-child td',  # 마지막 행의 td (본문)
            '.content',
            '.view_content',
            '.cont',
            'td .내용'
        ]
        
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                content = content_elem.get_text(strip=True)
                if content and len(content) > 20:  # 의미있는 내용인지 확인
                    logger.debug(f"본문을 {selector} 선택자로 찾음")
                    return content
        
        logger.warning("본문을 찾을 수 없습니다")
        return ""

    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """첨부파일 추출"""
        attachments = []
        
        try:
            # 첨부파일 링크 찾기
            file_links = soup.find_all('a', href='#') + soup.find_all('a', onclick=True)
            
            for link in file_links:
                try:
                    onclick = link.get('onclick', '')
                    if 'download' in onclick.lower() or 'file' in onclick.lower():
                        filename = link.get_text(strip=True)
                        if filename and filename not in ['', '#', 'download']:
                            # onclick에서 파일 ID 추출
                            file_params = self._extract_file_params(onclick)
                            
                            attachments.append({
                                'filename': filename,
                                'onclick': onclick,
                                'file_params': file_params
                            })
                            logger.debug(f"첨부파일 발견: {filename}")
                
                except Exception as e:
                    logger.warning(f"첨부파일 링크 처리 중 오류: {e}")
                    continue
            
            logger.info(f"{len(attachments)}개 첨부파일 발견")
            return attachments
            
        except Exception as e:
            logger.error(f"첨부파일 추출 실패: {e}")
            return attachments

    def _extract_file_params(self, onclick: str) -> Dict[str, str]:
        """onclick에서 파일 다운로드 파라미터 추출"""
        params = {}
        
        if not onclick:
            return params
        
        try:
            # JavaScript 함수 호출에서 파라미터 추출
            # 예: fn_fileDown('FILE_20231227_14354354354545.pdf');
            # 예: fileDown('file_id_123');
            
            match = re.search(r"(\w+)\s*\(\s*([^)]+)\s*\)", onclick)
            if match:
                func_name = match.group(1)
                param_str = match.group(2)
                
                # 파라미터를 쉼표로 분리하고 따옴표 제거
                param_list = [p.strip().strip("'\"") for p in param_str.split(',')]
                
                # Visit Korea의 파일 다운로드 패턴 확인
                if ('file' in func_name.lower() or 'download' in func_name.lower()) and param_list:
                    # 첫 번째 파라미터가 파일 식별자인 경우가 많음
                    if param_list[0]:
                        params['fileId'] = param_list[0]
                        if len(param_list) > 1 and param_list[1]:
                            params['fileName'] = param_list[1]
                
                logger.debug(f"파일 다운로드 파라미터 추출: {params} (onclick: {onclick[:50]})")
        
        except Exception as e:
            logger.warning(f"파일 파라미터 추출 실패: {e}")
        
        return params

    def download_file(self, url: str, save_path: str, save_dir: str = None) -> bool:
        """첨부파일 다운로드 (attachment 객체 기반)"""
        # 이 메서드는 호환성을 위해 유지하지만 실제로는 download_attachment 사용
        logger.warning("download_file 메서드는 deprecated입니다. download_attachment를 사용하세요.")
        return False

    def download_attachment(self, attachment: Dict[str, str], save_dir: str) -> bool:
        """첨부파일 다운로드"""
        try:
            filename = attachment.get('filename', 'unknown_file')
            file_params = attachment.get('file_params', {})
            
            if not file_params.get('fileId'):
                logger.warning(f"파일 ID가 없는 파일: {filename}")
                return False
            
            # 파일명 정리
            clean_filename = self.sanitize_filename(filename)
            if not clean_filename.strip():
                clean_filename = f"attachment_{int(time.time())}"
            
            save_path = os.path.join(save_dir, clean_filename)
            
            logger.info(f"파일 다운로드 시작: {filename}")
            
            # POST 데이터 구성
            download_data = {
                'fileId': file_params['fileId']
            }
            
            if file_params.get('fileName'):
                download_data['fileName'] = file_params['fileName']
            
            # 파일 다운로드 요청
            response = self.session.post(
                self.download_url,
                data=download_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'Referer': self.detail_url
                },
                stream=True,
                timeout=120  # 파일 다운로드는 긴 타임아웃
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

    def download_attachments_from_atch_file_id(self, atch_file_id: str, save_dir: str) -> bool:
        """atchFileId를 사용한 첨부파일 다운로드"""
        try:
            if not atch_file_id:
                return False
            
            # atchFileId 형식: "파일ID|파일명" 또는 "파일ID"
            parts = atch_file_id.split('|')
            file_id = parts[0].strip()
            
            if not file_id:
                return False
            
            filename = parts[1].strip() if len(parts) > 1 else f"file_{file_id}"
            
            logger.info(f"atchFileId 파일 다운로드: {filename} (ID: {file_id})")
            
            # 파일 다운로드 요청
            download_data = {
                'atchFileId': file_id
            }
            
            response = self.session.post(
                self.download_url,
                data=download_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Referer': self.detail_url,
                    'User-Agent': self.headers['User-Agent']
                },
                stream=True,
                timeout=120
            )
            
            if response.status_code == 200:
                # 파일명 처리
                clean_filename = self.sanitize_filename(filename)
                save_path = os.path.join(save_dir, clean_filename)
                
                # 파일명 인코딩 재처리
                final_save_path = self._handle_filename_encoding(response, save_path, save_dir)
                
                # 스트리밍 다운로드
                with open(final_save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                # 파일 크기 확인
                if os.path.exists(final_save_path):
                    file_size = os.path.getsize(final_save_path)
                    logger.info(f"atchFileId 다운로드 완료: {final_save_path} ({file_size:,} bytes)")
                    return True
                else:
                    logger.error(f"atchFileId 다운로드 파일이 저장되지 않음: {final_save_path}")
                    return False
            else:
                logger.error(f"atchFileId 파일 다운로드 실패: {response.status_code}")
                logger.debug(f"에러 응답: {response.text[:200]}")
                return False
                
        except Exception as e:
            logger.error(f"atchFileId 파일 다운로드 실패: {e}")
            return False

    def download_attachment_alternative(self, attachment: Dict[str, str], save_dir: str) -> bool:
        """대안 첨부파일 다운로드 - 직접 URL 접근 시도"""
        try:
            filename = attachment.get('filename', 'unknown_file')
            onclick = attachment.get('onclick', '')
            
            logger.info(f"대안 방법으로 파일 다운로드 시도: {filename}")
            
            # onclick에서 파일 경로 추출 시도
            # 예: fn_fileDown('/notice/20231227_152321_8472432828.pdf')
            file_path_match = re.search(r"['\"]([^'\"]*\.(pdf|hwp|doc|docx|xls|xlsx|jpg|png|zip))['\"]", onclick, re.IGNORECASE)
            
            if file_path_match:
                file_path = file_path_match.group(1)
                
                # 절대 URL 구성
                if file_path.startswith('/'):
                    file_url = f"{self.base_url}{file_path}"
                else:
                    file_url = f"{self.base_url}/{file_path}"
                
                logger.info(f"추출된 파일 URL: {file_url}")
                
                # 직접 GET 요청으로 파일 다운로드 시도
                response = self.session.get(
                    file_url,
                    headers={
                        'Referer': self.detail_url,
                        'User-Agent': self.headers['User-Agent']
                    },
                    stream=True,
                    timeout=120
                )
                
                if response.status_code == 200:
                    # 파일명 정리
                    clean_filename = self.sanitize_filename(filename)
                    save_path = os.path.join(save_dir, clean_filename)
                    
                    # 파일명 인코딩 재처리
                    final_save_path = self._handle_filename_encoding(response, save_path, save_dir)
                    
                    # 스트리밍 다운로드
                    with open(final_save_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    
                    # 파일 크기 확인
                    if os.path.exists(final_save_path):
                        file_size = os.path.getsize(final_save_path)
                        if file_size > 0:
                            logger.info(f"대안 다운로드 성공: {final_save_path} ({file_size:,} bytes)")
                            return True
                        else:
                            logger.warning(f"다운로드된 파일이 비어있음: {final_save_path}")
                            os.remove(final_save_path)
                            return False
                    else:
                        logger.error(f"다운로드 파일이 저장되지 않음: {final_save_path}")
                        return False
                else:
                    logger.warning(f"직접 URL 접근 실패 ({response.status_code}): {file_url}")
                    
                    # 2차 시도: base_url 없이
                    if file_path.startswith('/'):
                        alt_url = f"https://koreaquality.visitkorea.or.kr{file_path}"
                        logger.info(f"2차 시도 URL: {alt_url}")
                        
                        response2 = self.session.get(
                            alt_url,
                            headers={
                                'Referer': self.detail_url,
                                'User-Agent': self.headers['User-Agent']
                            },
                            stream=True,
                            timeout=120
                        )
                        
                        if response2.status_code == 200:
                            clean_filename = self.sanitize_filename(filename)
                            save_path = os.path.join(save_dir, clean_filename)
                            final_save_path = self._handle_filename_encoding(response2, save_path, save_dir)
                            
                            with open(final_save_path, 'wb') as f:
                                for chunk in response2.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)
                            
                            if os.path.exists(final_save_path):
                                file_size = os.path.getsize(final_save_path)
                                if file_size > 0:
                                    logger.info(f"2차 시도 성공: {final_save_path} ({file_size:,} bytes)")
                                    return True
                                else:
                                    os.remove(final_save_path)
                    
                    return False
            else:
                logger.warning(f"onclick에서 파일 경로를 찾을 수 없음: {onclick}")
                return False
                
        except Exception as e:
            logger.error(f"대안 파일 다운로드 실패 {filename}: {e}")
            return False

    def scrape_pages(self, max_pages: int = 3, output_base: str = "output") -> bool:
        """여러 페이지 스크래핑 실행"""
        output_dir = os.path.join(output_base, "visitkorea")
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"Visit Korea 스크래핑 시작 - 최대 {max_pages}페이지")
        
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
                        
                        # HTML에서 발견된 첨부파일 처리 (atchFileId는 500 에러로 비활성화)
                        if detail_data.get('attachments'):
                            os.makedirs(attachments_dir, exist_ok=True)
                            
                            for attachment in detail_data['attachments']:
                                if self.download_attachment_alternative(attachment, attachments_dir):
                                    downloaded_count += 1
                                time.sleep(1)  # 다운로드 간격
                        
                        # content.md 파일 생성
                        content_md = self._generate_content_md(
                            detail_data.get('title', title),
                            announcement.get('date', ''),
                            announcement.get('url', ''),
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
            
            logger.info(f"\n=== 스크래핑 완료 ===")
            logger.info(f"총 처리된 공고: {total_processed}개")
            return True
            
        except Exception as e:
            logger.error(f"스크래핑 중 오류 발생: {e}")
            return False

    def _generate_content_md(self, title: str, date: str, url: str, content: str, attachment_count: int) -> str:
        """content.md 파일 내용 생성"""
        md_content = f"# {title}\n\n"
        
        if date:
            md_content += f"**작성일**: {date}\n"
        if url:
            md_content += f"**원본 URL**: {url}\n"
        
        md_content += f"\n---\n# {title}\n\n"
        
        if content:
            md_content += f"{content}\n\n"
        
        if attachment_count > 0:
            md_content += f"**첨부파일**: {attachment_count}개 파일이 attachments 폴더에 저장되었습니다.\n\n"
        
        return md_content


# 하위 호환성을 위한 별칭
VisitKoreaScraper = EnhancedVisitKoreaScraper


def main():
    """테스트 실행"""
    scraper = EnhancedVisitKoreaScraper()
    scraper.scrape_pages(max_pages=1, output_base="output")


if __name__ == "__main__":
    main()