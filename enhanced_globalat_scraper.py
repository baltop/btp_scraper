# -*- coding: utf-8 -*-
"""
aT수출종합지원시스템(global.at.or.kr) Enhanced 스크래퍼 - 세션 및 POST 기반
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

class EnhancedGlobalatScraper(StandardTableScraper):
    """aT수출종합지원시스템(global.at.or.kr) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        
        # 향상된 헤더 설정 (차단 방지)
        self.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.session.headers.update(self.headers)
        
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://global.at.or.kr"
        self.list_url = "https://global.at.or.kr/front/board/noticeList.do"
        self.main_url = "https://global.at.or.kr/front/main.do"
        
        # 사이트 특화 설정
        self.verify_ssl = True  # HTTPS 사이트
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        
        # 세션 관리
        self.session_initialized = False
        
    def initialize_session(self):
        """세션 초기화 - 메인 페이지 방문 후 쿠키 설정"""
        if self.session_initialized:
            return True
        
        try:
            logger.info("세션 초기화 시작")
            
            # 메인 페이지 방문으로 세션 쿠키 획득
            response = self.session.get(self.main_url, verify=self.verify_ssl, timeout=self.timeout)
            if response.status_code == 200:
                self.session_initialized = True
                logger.info("세션 초기화 완료")
                return True
            else:
                logger.error(f"메인 페이지 접근 실패: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"세션 초기화 실패: {e}")
            return False
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - POST 요청이므로 기본 URL 반환"""
        return self.list_url
    
    def _get_page_announcements(self, page_num: int) -> List[Dict[str, Any]]:
        """페이지별 공고 목록 가져오기 - POST 요청 방식"""
        if not self.initialize_session():
            logger.error("세션 초기화 실패")
            return []
        
        try:
            # POST 데이터 구성 (JavaScript goMenu 함수 기반)
            post_data = {
                '_mtype': 'F',
                '_dept1': '6',
                '_dept2': '1',
                'page': str(page_num),
                'notice_gb': '01',  # 일반 공지사항
                'searchCondition': '',
                'searchText': ''
            }
            
            logger.info(f"페이지 {page_num} POST 요청: {post_data}")
            
            response = self.session.post(
                self.list_url,
                data=post_data,
                headers={'Referer': self.main_url},
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                logger.warning(f"페이지 {page_num} HTTP 에러: {response.status_code}")
                return []
            
            # 비정상 접근 체크
            if '비정상적인 접근' in response.text:
                logger.error("비정상적인 접근으로 차단됨")
                return []
            
            announcements = self.parse_list_page(response.text)
            logger.info(f"페이지 {page_num}에서 {len(announcements)}개 공고 파싱 완료")
            
            return announcements
            
        except Exception as e:
            logger.error(f"페이지 {page_num} 요청 중 오류: {e}")
            return []
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - global.at.or.kr 사이트 특화"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # global.at.or.kr 사이트 테이블 구조 분석
        # table.boardList 내의 tbody에 공고 목록
        table = soup.find('table', class_='boardList')
        if not table:
            logger.warning("boardList 테이블을 찾을 수 없습니다")
            return announcements
        
        tbody = table.find('tbody')
        if not tbody:
            logger.warning("tbody를 찾을 수 없습니다")
            return announcements
        
        rows = tbody.find_all('tr')
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 5:  # 번호, 구분, 제목, 등록일, 조회수
                    continue
                
                # 제목 셀에서 링크 찾기 (세 번째 셀, class="subject")
                subject_cell = cells[2]
                link_elem = subject_cell.find('a')
                
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                if not title:
                    continue
                
                # JavaScript 함수에서 ID 추출
                # href="javascript:goViewPage('556');"
                onclick = link_elem.get('href', '')
                view_id_match = re.search(r"goViewPage\('(\d+)'\)", onclick)
                
                if not view_id_match:
                    logger.warning(f"공고 ID를 찾을 수 없음: {onclick}")
                    continue
                
                view_id = view_id_match.group(1)
                detail_url = f"{self.base_url}/front/board/noticeView.do?notice_no={view_id}"
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'notice_no': view_id
                }
                
                # 추가 메타 정보 추출
                self._extract_meta_info(cells, announcement)
                
                announcements.append(announcement)
                logger.debug(f"공고 추가: {title[:50]}...")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def _extract_meta_info(self, cells: list, announcement: Dict[str, Any]):
        """테이블 셀에서 메타 정보 추출"""
        try:
            # 번호 (첫 번째 셀)
            if len(cells) > 0:
                number_text = cells[0].get_text(strip=True)
                if number_text.isdigit():
                    announcement['number'] = number_text
            
            # 구분 (두 번째 셀, class="category2")
            if len(cells) > 1:
                category_text = cells[1].get_text(strip=True)
                if category_text:
                    announcement['category'] = category_text
            
            # 등록일 (네 번째 셀, class="date")
            if len(cells) > 3:
                date_text = cells[3].get_text(strip=True)
                if date_text:
                    announcement['date'] = date_text
            
            # 조회수 (다섯 번째 셀, class="hits")
            if len(cells) > 4:
                hits_text = cells[4].get_text(strip=True)
                if hits_text.isdigit():
                    announcement['views'] = hits_text
        
        except Exception as e:
            logger.error(f"메타 정보 추출 중 오류: {e}")
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱 - global.at.or.kr 사이트 특화"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # global.at.or.kr 사이트의 실제 본문 내용 추출
        # 본문은 게시판 상세 페이지 구조에 따라 다양한 선택자 시도
        content_selectors = [
            '.boardView .content',
            '.boardView .view_content',
            '.view_content',
            '.board_content',
            '.content',
            'div[class*="content"]',
            'div[class*="view"]'
        ]
        
        content_area = None
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        # Fallback: 테이블이나 div에서 긴 텍스트 찾기
        if not content_area:
            # 텍스트가 많은 div나 td 찾기
            for div in soup.find_all(['div', 'td']):
                text = div.get_text(strip=True)
                if len(text) > 100 and '첨부파일' not in text and '목록' not in text:
                    content_area = div
                    logger.debug("텍스트 길이 기반으로 본문 영역 추정")
                    break
        
        # 마지막 fallback: body 전체에서 추출
        if not content_area:
            content_area = soup.find('body') or soup
            logger.warning("본문 영역을 찾지 못해 전체 페이지에서 추출")
        
        # HTML을 마크다운으로 변환
        if content_area:
            # 불필요한 태그 제거
            for tag in content_area.find_all(['script', 'style', 'nav', 'header', 'footer']):
                tag.decompose()
            
            content_html = str(content_area)
            content_text = self.h.handle(content_html)
            
            # 내용 정리 - 불필요한 줄바꿈 제거
            content_text = re.sub(r'\n\s*\n\s*\n', '\n\n', content_text)
            content_text = content_text.strip()
        else:
            content_text = "내용을 추출할 수 없습니다."
            
        # 첨부파일 추출
        attachments = self._extract_attachments(soup)
        
        return {
            'content': content_text,
            'attachments': attachments
        }
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """첨부파일 링크 추출 - global.at.or.kr 사이트 특화"""
        attachments = []
        
        try:
            # 첨부파일 섹션 찾기
            attachment_selectors = [
                '.fileList',
                '.attach_list',
                '.file_list',
                'div[class*="file"]',
                'div[class*="attach"]'
            ]
            
            attachment_area = None
            for selector in attachment_selectors:
                attachment_area = soup.select_one(selector)
                if attachment_area:
                    logger.debug(f"첨부파일 영역을 {selector} 선택자로 찾음")
                    break
            
            # 첨부파일 영역이 없으면 전체에서 파일 링크 찾기
            if not attachment_area:
                attachment_area = soup
            
            # 파일 다운로드 링크 찾기
            file_links = attachment_area.find_all('a', href=True)
            
            for link in file_links:
                href = link.get('href', '')
                
                # 파일 다운로드 패턴 확인
                if any(pattern in href.lower() for pattern in ['download', 'file', 'attach']):
                    filename = link.get_text(strip=True)
                    
                    # 파일 아이콘 다음의 텍스트나 title 속성 확인
                    if not filename:
                        filename = link.get('title', '') or link.get('alt', '')
                    
                    # 상위 요소에서 파일명 찾기
                    if not filename:
                        parent = link.parent
                        if parent:
                            filename = parent.get_text(strip=True)
                    
                    if filename and len(filename) > 0:
                        # URL 정리
                        if href.startswith('/'):
                            file_url = urljoin(self.base_url, href)
                        elif href.startswith('javascript:') or href.startswith('Javascript:'):
                            # JavaScript 함수는 원본 그대로 유지 (download_file에서 처리)
                            file_url = href
                        else:
                            file_url = href
                        
                        if file_url:
                            attachment = {
                                'filename': filename,
                                'url': file_url
                            }
                            
                            attachments.append(attachment)
                            logger.info(f"첨부파일 발견: {filename}")
            
            # JavaScript 기반 다운로드 함수들도 확인
            self._extract_js_file_downloads(soup, attachments)
            
        except Exception as e:
            logger.error(f"첨부파일 추출 중 오류: {e}")
        
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment_info: Dict[str, Any] = None) -> bool:
        """파일 다운로드 - JavaScript 함수 처리 특화"""
        try:
            # JavaScript URL인 경우 특별 처리
            if url.startswith('Javascript:downloadFile'):
                return self._download_js_file(url, save_path, attachment_info)
            else:
                # 일반 URL은 부모 클래스 메소드 사용
                return super().download_file(url, save_path, attachment_info)
                
        except Exception as e:
            logger.error(f"파일 다운로드 실패 {url}: {e}")
            return False
    
    def _download_js_file(self, js_url: str, save_path: str, attachment_info: Dict[str, Any] = None) -> bool:
        """JavaScript downloadFile 함수 호출 재현"""
        try:
            logger.info(f"JavaScript 파일 다운로드 시작: {js_url}")
            
            # JavaScript 함수에서 파라미터 추출
            # downloadFile('Mjg2NzAx', 'MjAyNeu...')
            pattern = r"downloadFile\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)"
            match = re.search(pattern, js_url)
            
            if not match:
                logger.error(f"JavaScript 파라미터 추출 실패: {js_url}")
                return False
            
            file_id = match.group(1)
            encoded_filename = match.group(2)
            
            logger.debug(f"파일 ID: {file_id}")
            logger.debug(f"인코딩된 파일명: {encoded_filename[:50]}...")
            
            # POST 데이터 구성 (JavaScript 함수 동작 재현)
            post_data = {
                'addfile_id': file_id,
                'addfile_nm': encoded_filename
            }
            
            # 실제 다운로드 요청
            download_url = f"{self.base_url}/attach/fileDownloadN.do"
            
            response = self.session.post(
                download_url,
                data=post_data,
                headers={
                    'Referer': self.list_url,
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                stream=True,
                verify=self.verify_ssl,
                timeout=self.timeout
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
            logger.info(f"JavaScript 파일 다운로드 완료: {save_path} ({file_size:,} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"JavaScript 파일 다운로드 실패: {e}")
            return False
    
    def _extract_js_file_downloads(self, soup: BeautifulSoup, attachments: List[Dict[str, Any]]):
        """JavaScript 기반 파일 다운로드 패턴 추출"""
        try:
            # script 태그에서 파일 다운로드 함수 찾기
            script_tags = soup.find_all('script')
            for script in script_tags:
                script_content = script.get_text()
                
                # 파일 다운로드 함수 패턴 찾기
                download_patterns = [
                    r'downloadFile\s*\(\s*[\'"]([^\'\"]+)[\'"]\s*,\s*[\'"]([^\'\"]+)[\'"]\s*\)',
                    r'fileDownload\s*\(\s*[\'"]([^\'\"]+)[\'"]\s*\)',
                    r'goFileDown\s*\(\s*[\'"]([^\'\"]+)[\'"]\s*\)'
                ]
                
                for pattern in download_patterns:
                    matches = re.findall(pattern, script_content)
                    for match in matches:
                        if isinstance(match, tuple) and len(match) >= 2:
                            file_id, filename = match[0], match[1]
                            file_url = f"{self.base_url}/front/board/fileDown.do?file_id={file_id}"
                        else:
                            file_id = match if isinstance(match, str) else match[0]
                            filename = f"attachment_{file_id}"
                            file_url = f"{self.base_url}/front/board/fileDown.do?file_id={file_id}"
                        
                        attachment = {
                            'filename': filename,
                            'url': file_url
                        }
                        attachments.append(attachment)
                        logger.info(f"JavaScript 파일 다운로드 발견: {filename}")
        
        except Exception as e:
            logger.error(f"JavaScript 파일 다운로드 추출 중 오류: {e}")
    
    def process_announcement(self, announcement: Dict[str, Any], index: int, output_base: str = 'output'):
        """개별 공고 처리 - global.at.or.kr 특화 (POST 요청 필요)"""
        logger.info(f"공고 처리 중 {index}: {announcement['title']}")
        
        # 폴더 생성
        folder_title = self.sanitize_filename(announcement['title'])[:100]
        folder_name = f"{index:03d}_{folder_title}"
        
        if len(folder_name) > 200:
            folder_title = folder_title[:195]
            folder_name = f"{index:03d}_{folder_title}"
        
        folder_path = os.path.join(output_base, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        # 상세 페이지 가져오기 - POST 요청
        try:
            post_data = {
                '_mtype': 'F',
                '_dept1': '6',
                '_dept2': '1',
                'notice_no': announcement.get('notice_no', ''),
                'notice_gb': '01'
            }
            
            response = self.session.post(
                f"{self.base_url}/front/board/noticeView.do",
                data=post_data,
                headers={'Referer': self.list_url},
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            
            if not response or response.status_code != 200:
                logger.error(f"상세 페이지 가져오기 실패: {announcement['title']}")
                return
                
        except Exception as e:
            logger.error(f"상세 페이지 요청 실패: {e}")
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

# 하위 호환성을 위한 별칭
GlobalatScraper = EnhancedGlobalatScraper