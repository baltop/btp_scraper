# -*- coding: utf-8 -*-
"""
Enhanced 음성상공회의소 스크래퍼 - 향상된 버전
사이트: https://eumseongcci.korcham.net/front/board/boardContentsListPage.do?boardId=10585&menuId=871
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

logger = logging.getLogger(__name__)

class EnhancedEumseongcciScraper(StandardTableScraper):
    """음성상공회의소 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://eumseongcci.korcham.net"
        self.list_url = "https://eumseongcci.korcham.net/front/board/boardContentsListPage.do?boardId=10585&menuId=871"
        self.list_ajax_url = "https://eumseongcci.korcham.net/front/board/boardContentsList.do"
        self.detail_url = "https://eumseongcci.korcham.net/front/board/boardContentsView.do"
        self.download_url = "https://eumseongcci.korcham.net/downloadUrl.do"
        
        # 사이트 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        
        # 음성상공회의소 특화 설정
        self.page_size = 15  # 한 페이지당 항목 수
        self.board_id = "10585"
        self.menu_id = "871"
        
        # 세션 초기화 (메인 페이지 접근으로 세션 쿠키 설정)
        self._initialize_session()
    
    def _initialize_session(self):
        """세션 초기화 - 메인 페이지 접근으로 필요한 쿠키 설정"""
        try:
            logger.debug("세션 초기화: 메인 페이지 접근")
            response = self.session.get(
                self.list_url,
                timeout=self.timeout,
                verify=False,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            logger.debug(f"세션 초기화 완료: {response.status_code}")
        except Exception as e:
            logger.warning(f"세션 초기화 실패: {e}")
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - AJAX 방식"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: 음성상공회의소는 AJAX 엔드포인트가 고정
        return self.list_ajax_url
    
    def _get_page_announcements(self, page_num: int) -> List[Dict[str, Any]]:
        """페이지별 공고 목록 가져오기 - AJAX POST 요청"""
        try:
            # AJAX POST 요청으로 목록 데이터 가져오기
            html_content = self.fetch_page_content_ajax(page_num)
            if not html_content:
                logger.warning(f"페이지 {page_num} AJAX 응답을 가져올 수 없습니다")
                return []
            
            # HTML 파싱
            announcements = self.parse_list_page(html_content)
            
            # 마지막 페이지 감지
            if not announcements and page_num > 1:
                logger.info(f"페이지 {page_num}에 공고가 없어 마지막 페이지로 판단됩니다")
            
            return announcements
            
        except Exception as e:
            logger.error(f"페이지 {page_num} 공고 목록 가져오기 실패: {e}")
            return []
    
    def fetch_page_content_ajax(self, page_num: int) -> str:
        """AJAX 요청으로 페이지 내용 가져오기"""
        try:
            # POST 데이터 구성
            post_data = {
                'miv_pageNo': str(page_num),
                'miv_pageSize': str(self.page_size),
                'boardId': self.board_id,
                'menuId': self.menu_id,
                'searchKey': 'A',  # 전체 검색
                'searchTxt': ''    # 검색어 없음
            }
            
            # 요청 헤더 설정
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': self.list_url,
                'User-Agent': self.headers.get('User-Agent', 'Mozilla/5.0')
            }
            
            # AJAX POST 요청
            response = self.session.post(
                self.list_ajax_url,
                data=post_data,
                headers=headers,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            
            response.raise_for_status()
            response.encoding = self.default_encoding
            
            logger.debug(f"페이지 {page_num} AJAX 응답 받음 ({len(response.text)} bytes)")
            return response.text
            
        except Exception as e:
            logger.error(f"AJAX 요청 실패 (페이지 {page_num}): {e}")
            return ""
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: 음성상공회의소 특화 파싱
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """음성상공회의소 특화 목록 파싱"""
        announcements = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 테이블 찾기 (.boardlist table 구조)
            table = soup.find('table')
            if not table:
                logger.warning("테이블을 찾을 수 없습니다")
                return announcements
            
            tbody = table.find('tbody')
            if not tbody:
                tbody = table
            
            logger.info(f"테이블에서 {len(tbody.find_all('tr'))}개 행 발견")
            
            # 각 행 파싱
            for row in tbody.find_all('tr'):
                try:
                    cells = row.find_all('td')
                    if len(cells) < 2:  # 최소 번호, 제목 필요
                        continue
                    
                    # 제목 셀에서 링크 찾기
                    title_cell = cells[1]  # 두 번째 컬럼이 제목
                    link_elem = title_cell.find('a', href=re.compile(r'javascript:contentsView'))
                    
                    if not link_elem:
                        continue
                    
                    # 제목 추출
                    title = link_elem.get_text(strip=True)
                    if not title:
                        continue
                    
                    # JavaScript 함수에서 ID 추출
                    # contentsView('117426') 형태
                    href = link_elem.get('href', '')
                    id_match = re.search(r"contentsView\('(\d+)'\)", href)
                    if not id_match:
                        continue
                    
                    content_id = id_match.group(1)
                    
                    # 상세 페이지 URL 구성 (POST 요청으로 접근해야 함)
                    detail_url = self.detail_url
                    
                    announcement = {
                        'title': title,
                        'url': detail_url,  # 실제로는 사용하지 않음
                        'content_id': content_id,
                        'number': cells[0].get_text(strip=True) if cells[0] else '',
                        'use_post_method': True  # POST 방식 사용 플래그
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
    
    def fetch_detail_content(self, announcement: Dict[str, Any]) -> Dict[str, Any]:
        """상세 페이지 내용 가져오기 - POST 요청으로 상세 페이지 접근"""
        try:
            content_id = announcement.get('content_id', '')
            if not content_id:
                logger.warning("content_id가 없습니다")
                return {'content': '', 'attachments': []}
            
            # POST 데이터로 상세 페이지 요청 (최소한의 필수 파라미터만)
            post_data = {
                'contId': content_id,
                'boardId': self.board_id
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': self.list_url,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            logger.debug(f"POST 요청: {self.detail_url}, data={post_data}")
            
            response = self.session.post(
                self.detail_url,
                data=post_data,
                headers=headers,
                timeout=self.timeout,
                verify=False  # SSL 검증 비활성화
            )
            
            response.raise_for_status()
            response.encoding = self.default_encoding
            
            # HTML 파싱
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 본문 내용 추출
            content = self._extract_content(soup, announcement)
            
            # 첨부파일 추출
            attachments = self._extract_attachments(soup)
            
            return {
                'content': content,
                'attachments': attachments
            }
            
        except Exception as e:
            logger.error(f"상세 내용 가져오기 실패: {e}", exc_info=True)
            return {'content': '', 'attachments': []}
    
    def _extract_content(self, soup: BeautifulSoup, announcement: Dict[str, Any]) -> str:
        """본문 내용 추출"""
        content_parts = []
        
        # 제목
        title = announcement.get('title', '')
        if title:
            content_parts.append(f"# {title}\n")
        
        # 메타 정보 추출 시도
        meta_info = []
        
        # 작성일, 조회수 등 찾기 (테이블 형태로 되어 있을 가능성)
        detail_table = soup.find('table', class_=re.compile(r'.*view.*|.*detail.*'))
        if detail_table:
            for row in detail_table.find_all('tr'):
                cells = row.find_all(['th', 'td'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    if key and value and any(keyword in key for keyword in ['작성일', '등록일', '조회']):
                        meta_info.append(f"**{key}**: {value}")
        
        if meta_info:
            content_parts.append(" | ".join(meta_info) + "\n")
        
        # 본문 내용 찾기 - 음성상공회의소 특화
        content_area = None
        
        # 음성상공회의소 특화 선택자들 시도
        for selector in ['td.td_p', '.td_p', 'td[class="td_p"]', 
                        '.board_view_content', '.view_content', '.content']:
            content_area = soup.select_one(selector)
            if content_area:
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        # 선택자로 찾지 못하면 테이블 기반으로 찾기
        if not content_area:
            # 테이블에서 본문이 들어있는 셀 찾기
            tables = soup.find_all('table')
            for table in tables:
                for cell in table.find_all('td'):
                    if cell.get_text(strip=True) and len(cell.get_text(strip=True)) > 100:
                        content_area = cell
                        logger.debug("테이블 셀에서 본문을 찾음")
                        break
                if content_area:
                    break
        
        if content_area:
            # HTML을 마크다운으로 변환
            content_text = content_area.get_text(separator='\n', strip=True)
            content_parts.append(f"\n{content_text}\n")
        else:
            logger.warning("본문 영역을 찾을 수 없습니다")
        
        return "\n".join(content_parts)
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """첨부파일 추출 - 실제 첨부파일만 식별"""
        attachments = []
        
        # 1. down() 함수를 사용하는 다운로드 링크 찾기 (실제 첨부파일)
        download_links = soup.find_all('a', href=re.compile(r'javascript:down\('))
        
        for link in download_links:
            try:
                href = link.get('href', '')
                filename = link.get_text(strip=True)
                
                # down() 함수에서 파라미터 추출
                # down('url', 'original_filename') 형태
                down_match = re.search(r"down\('([^']+)',\s*'([^']+)'\)", href)
                if down_match:
                    file_path = down_match.group(1)
                    original_filename = down_match.group(2)
                    
                    # 다운로드 URL 구성
                    file_url = f"{self.download_url}?file_path={file_path}&orignl_file_nm={original_filename}"
                    
                    attachments.append({
                        'name': original_filename or filename,
                        'url': file_url,
                        'file_path': file_path,
                        'type': 'attachment'
                    })
                    logger.debug(f"첨부파일 발견: {original_filename}")
                
            except Exception as e:
                logger.error(f"첨부파일 파싱 중 오류: {e}")
                continue
        
        # 2. 첨부파일 목록 영역에서 추가 첨부파일 찾기
        # 첨부파일 목록이 별도 영역으로 구성되어 있는 경우
        attach_sections = soup.find_all(['div', 'table', 'ul'], class_=re.compile(r'.*attach.*|.*file.*'))
        for section in attach_sections:
            # 첨부파일 영역 내의 링크들 찾기
            links = section.find_all('a')
            for link in links:
                href = link.get('href', '')
                filename = link.get_text(strip=True)
                
                # 다운로드 링크 패턴 확인
                if (href and 
                    ('download' in href or 'file' in href or href.startswith('/upload')) and
                    not href.startswith('javascript:') and
                    filename and len(filename) > 0):
                    
                    # 절대 URL 변환
                    file_url = urljoin(self.base_url, href)
                    
                    # 중복 방지
                    if filename not in [att['name'] for att in attachments]:
                        attachments.append({
                            'name': filename,
                            'url': file_url,
                            'type': 'attachment'
                        })
                        logger.debug(f"첨부파일 목록에서 발견: {filename}")
        
        # 3. 본문 내 실제 첨부파일 이미지만 추출 (사이트 로고/네비게이션 이미지 제외)
        content_area = soup.find('td', class_='td_p') or soup.find('div', class_=re.compile(r'.*content.*'))
        if content_area:
            images = content_area.find_all('img')
            for img in images:
                try:
                    src = img.get('src', '')
                    if src and self._is_content_image(src):
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
                                'type': 'content_image'
                            })
                            logger.debug(f"본문 이미지 발견: {file_name}")
                    
                except Exception as e:
                    logger.error(f"이미지 파일 처리 중 오류: {e}")
                    continue
        
        logger.info(f"{len(attachments)}개 첨부파일 발견")
        return attachments
    
    def _is_content_image(self, src: str) -> bool:
        """실제 본문 내용의 이미지인지 판단 (사이트 로고/네비게이션 이미지 제외)"""
        # 사이트 로고, 네비게이션 등 제외할 패턴들
        exclude_patterns = [
            'logo', 'nav', 'menu', 'header', 'footer', 'icon', 'btn', 'button',
            'top_', 'bottom_', 'home.png', 'home.gif', 'arrow', 'bullet',
            '/common/', '/images/', '/img/', '/resource/', '/static/',
            'ui_', 'bg_', 'dot_', 'line_'
        ]
        
        # 본문 내용 이미지일 가능성이 높은 패턴들
        content_patterns = [
            '/upload/', '/board/', '/attach/', '/file/', '/content/',
            'editor/', 'smarteditor/', 'ckeditor/'
        ]
        
        src_lower = src.lower()
        
        # 제외 패턴에 해당하면 False
        for pattern in exclude_patterns:
            if pattern in src_lower:
                return False
        
        # 본문 내용 패턴에 해당하면 True
        for pattern in content_patterns:
            if pattern in src_lower:
                return True
        
        # 파일 확장자로 판단 (이미지 파일이면서 크기가 있는 경우)
        if any(src_lower.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']):
            # 파일명에 날짜나 숫자가 많이 포함되어 있으면 실제 첨부파일일 가능성 높음
            import re
            if re.search(r'\d{8}|\d{10}|\d{4}_\d{2}', src_lower):
                return True
        
        return False
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱 - Enhanced 아키텍처 호환성용"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 본문 내용 추출 (간단한 형태)
            content_area = soup.find('div', {'class': re.compile(r'.*content.*|.*view.*')})
            content = ""
            if content_area:
                content = content_area.get_text(separator='\n', strip=True)
            
            # 첨부파일 추출
            attachments = self._extract_attachments(soup)
            
            return {
                'content': content,
                'attachments': attachments
            }
            
        except Exception as e:
            logger.error(f"상세 페이지 파싱 실패: {e}")
            return {'content': '', 'attachments': []}
    
    def download_file(self, url: str, save_path: str, filename: str = "") -> bool:
        """음성상공회의소 전용 파일 다운로드"""
        try:
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
    
    def process_announcement(self, announcement: Dict[str, Any], index: int, output_base: str = 'output'):
        """개별 공고 처리 - POST 방식으로 오버라이드"""
        logger.info(f"공고 처리 중 {index}: {announcement['title']}")
        
        # 폴더 생성
        folder_title = self.sanitize_filename(announcement['title'])[:100]
        folder_name = f"{index:03d}_{folder_title}"
        
        if len(folder_name) > 200:
            folder_name = folder_name[:200]
        
        folder_path = os.path.join(output_base, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        # 상세 내용 가져오기 (POST 방식)
        detail_result = self.fetch_detail_content(announcement)
        
        if not detail_result or not detail_result.get('content'):
            logger.error(f"상세 페이지 가져오기 실패: {announcement['title']}")
            return
        
        # 메타 정보 생성
        meta_info = self._create_meta_info(announcement)
        
        # 원본 URL 추가
        original_url = f"{self.base_url}/front/board/boardContentsView.do?contId={announcement.get('content_id', '')}"
        content_with_meta = f"{meta_info}\n**원본 URL**: {original_url}\n\n---\n\n{detail_result['content']}"
        
        # content.md 파일 저장
        content_file_path = os.path.join(folder_path, 'content.md')
        with open(content_file_path, 'w', encoding='utf-8') as f:
            f.write(content_with_meta)
        
        logger.info(f"내용 저장 완료: {content_file_path}")
        
        # 첨부파일 다운로드
        attachments = detail_result.get('attachments', [])
        if attachments:
            self._download_attachments(attachments, folder_path)
        else:
            logger.info("첨부파일이 없습니다")
        
        # 처리된 제목으로 추가
        self.add_processed_title(announcement['title'])
        
        # 요청 간 대기
        if self.delay_between_requests > 0:
            time.sleep(self.delay_between_requests)


# 하위 호환성을 위한 별칭
EumseongcciScraper = EnhancedEumseongcciScraper