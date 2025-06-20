# -*- coding: utf-8 -*-
"""
한국농업기술진흥원(KOAT) Enhanced 스크래퍼 - JavaScript 기반 페이지네이션
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

class EnhancedKOATScraper(StandardTableScraper):
    """한국농업기술진흥원(KOAT) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        
        # 향상된 헤더 설정 (차단 방지)
        self.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1',
        })
        self.session.headers.update(self.headers)
        
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://www.koat.or.kr"
        self.list_url = "https://www.koat.or.kr/board/business/list.do"
        
        # 사이트 특화 설정
        self.verify_ssl = True  # HTTPS 사이트
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - POST 요청 기반 페이지네이션"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: KOAT는 POST 요청으로 페이지네이션 처리
        return self.list_url
    
    def _get_page_announcements(self, page_num: int) -> List[Dict[str, Any]]:
        """페이지별 공고 목록 가져오기 - POST 요청 처리"""
        try:
            if page_num == 1:
                # 첫 페이지는 GET 요청
                response = self.get_page(self.list_url)
            else:
                # 2페이지부터는 POST 요청으로 pageLink 함수 모방
                post_data = {
                    'pageIndex': str(page_num),
                    'searchCondition': '',
                    'searchKeyword': ''
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
            
        except Exception as e:
            logger.error(f"페이지 {page_num} 가져오기 중 오류: {e}")
            return []
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: 사이트 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """KOAT 특화된 목록 파싱 로직 - row/cell 구조 처리"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 테이블 찾기 - 캡션으로 식별
        table = None
        for t in soup.find_all('table'):
            caption = t.find('caption')
            if caption and '사업공고' in caption.get_text():
                table = t
                logger.info("사업공고 게시판 테이블 발견")
                break
        
        if not table:
            logger.warning("사업공고 게시판 테이블을 찾을 수 없습니다")
            return announcements
        
        # rowgroup에서 데이터 행들 찾기 (헤더 제외)
        rowgroups = table.find_all(['rowgroup', 'tbody'])
        data_rows = []
        
        for rowgroup in rowgroups:
            rows = rowgroup.find_all(['row', 'tr'])
            # 첫 번째 rowgroup은 헤더일 가능성이 높으므로 스킵
            if len(rows) == 1 and ('번호' in rows[0].get_text() or '제목' in rows[0].get_text()):
                logger.debug("헤더 rowgroup 스킵")
                continue
            data_rows.extend(rows)
        
        # 대체 방법: 모든 row 요소 찾기
        if not data_rows:
            data_rows = table.find_all(['row', 'tr'])
            logger.info(f"테이블에서 {len(data_rows)}개 행 발견")
        else:
            logger.info(f"데이터 rowgroup에서 {len(data_rows)}개 행 발견")
        
        for i, row in enumerate(data_rows):
            try:
                # cell 또는 td 요소 찾기
                cells = row.find_all(['cell', 'td'])
                if len(cells) < 4:  # 최소 4개 컬럼 필요
                    logger.debug(f"행 {i}: 컬럼 수 부족 ({len(cells)}개)")
                    continue
                
                # 헤더 행 스킵
                if i == 0 and ('번호' in cells[0].get_text() or '제목' in cells[1].get_text()):
                    logger.debug("헤더 행 스킵")
                    continue
                
                # 컬럼 파싱 (6개 컬럼: 번호, 제목, 첨부파일, 작성자, 등록일, 조회수)
                number_cell = cells[0]  # 번호
                title_cell = cells[1]   # 제목
                attach_cell = cells[2] if len(cells) > 2 else None  # 첨부파일
                author_cell = cells[3] if len(cells) > 3 else None  # 작성자
                date_cell = cells[4] if len(cells) > 4 else None    # 등록일
                views_cell = cells[5] if len(cells) > 5 else None   # 조회수
                
                # 제목과 링크 추출
                link_elem = title_cell.find('a')
                if not link_elem:
                    logger.debug(f"행 {i}: 링크 없음")
                    continue
                
                title = link_elem.get_text(strip=True)
                if not title:
                    logger.debug(f"행 {i}: 제목 없음")
                    continue
                
                # href가 #인 경우 JavaScript 기반 네비게이션 처리
                href = link_elem.get('href', '')
                onclick = link_elem.get('onclick', '')
                detail_url = None
                
                if href and href != '#':
                    # 직접 링크가 있는 경우
                    detail_url = urljoin(self.base_url, href)
                elif onclick:
                    # JavaScript 함수에서 상세 페이지 정보 추출
                    # KOAT 특화: postLink(ID) 패턴
                    patterns = [
                        r"postLink\((\d+)\)",  # KOAT 특화 패턴
                        r"fn_view\('([^']+)'\)",
                        r"viewDetail\('([^']+)'\)",
                        r"goView\('([^']+)'\)",
                        r"javascript:.*?(\d+)"
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, onclick)
                        if match:
                            board_id = match.group(1)
                            detail_url = f"{self.base_url}/board/business/{board_id}/view.do"
                            logger.debug(f"JavaScript에서 상세 URL 추출: {detail_url}")
                            break
                
                # URL이 없는 경우 번호 기반으로 추정 (이제 사용되지 않을 것)
                if not detail_url:
                    number = number_cell.get_text(strip=True)
                    if number.isdigit():
                        detail_url = f"{self.base_url}/board/business/{number}/view.do"
                        logger.debug(f"번호 기반 상세 URL 생성: {detail_url}")
                
                if not detail_url:
                    logger.debug(f"행 {i}: 상세 URL 추출 실패 - {title[:30]}")
                    continue
                
                # 번호 추출
                number = number_cell.get_text(strip=True)
                
                # 작성자 추출
                author = author_cell.get_text(strip=True) if author_cell else ""
                
                # 등록일 추출
                date = date_cell.get_text(strip=True) if date_cell else ""
                
                # 조회수 추출
                views = views_cell.get_text(strip=True) if views_cell else ""
                
                # 첨부파일 여부 확인
                has_attachment = False
                if attach_cell:
                    # 첨부파일 아이콘이나 이미지 확인
                    attach_img = attach_cell.find('img')
                    attach_text = attach_cell.get_text(strip=True)
                    if attach_img or '첨부' in attach_text or attach_text:
                        has_attachment = True
                
                # 공고 정보 구성
                announcement = {
                    'number': number,
                    'title': title,
                    'url': detail_url,
                    'author': author,
                    'date': date,
                    'views': views,
                    'has_attachment': has_attachment
                }
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱 완료: {title[:50]}...")
                
            except Exception as e:
                logger.error(f"행 {i} 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str, announcement_url: str = None) -> Dict[str, Any]:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 내용 추출 - 여러 선택자 시도
        content_selectors = [
            '.view-content',
            '.board-view-content', 
            '.content-area',
            '.view-area',
            'div[class*="content"]',
            'div[class*="view"]'
        ]
        
        content_area = None
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        # 선택자로 찾지 못한 경우 테이블 기반 검색
        if not content_area:
            # 테이블에서 본문 영역 찾기
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    for cell in cells:
                        text = cell.get_text(strip=True)
                        # 본문으로 보이는 긴 텍스트 영역 찾기
                        if len(text) > 100:  # 100자 이상인 경우 본문으로 간주
                            content_area = cell
                            logger.debug("테이블에서 본문 영역 발견")
                            break
                    if content_area:
                        break
                if content_area:
                    break
        
        # 본문 텍스트 추출
        if content_area:
            content = self.h.handle(str(content_area))
            content = content.strip()
        else:
            logger.warning("본문 영역을 찾을 수 없습니다")
            content = "본문 내용을 추출할 수 없습니다."
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup)
        
        return {
            'content': content,
            'attachments': attachments
        }
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """첨부파일 추출 - fn_borad_file_down 함수 기반"""
        attachments = []
        
        # JavaScript 함수 기반 첨부파일 링크 찾기
        for link in soup.find_all('a'):
            onclick = link.get('onclick', '')
            href = link.get('href', '')
            
            # JavaScript 방식: fn_borad_file_down(fileId) 패턴
            if 'fn_borad_file_down' in onclick:
                # fn_borad_file_down(12220) 형태에서 파일 ID 추출
                match = re.search(r"fn_borad_file_down\((\d+)\)", onclick)
                if match:
                    file_id = match.group(1)
                    filename = link.get_text(strip=True)
                    
                    if filename:
                        # KOAT 특화: POST 방식 다운로드 URL 표시 (실제 다운로드는 특별 처리)
                        download_url = f"{self.base_url}/download.do"
                        
                        attachments.append({
                            'name': filename,
                            'url': download_url,
                            'file_id': file_id,
                            'download_method': 'POST'  # 특별 처리 필요 표시
                        })
                        
                        logger.debug(f"첨부파일 발견: {filename} (ID: {file_id})")
            
            # href에서 JavaScript URL 발견하는 경우 처리
            elif href and 'fn_borad_file_down' in href:
                # href="javascript:fn_borad_file_down(12220);" 형태 처리
                match = re.search(r'fn_borad_file_down\((\d+)\)', href)
                if match:
                    file_id = match.group(1)
                    filename = link.get_text(strip=True)
                    
                    if filename:
                        # KOAT 특화: POST 방식 다운로드 URL 표시 (실제 다운로드는 특별 처리)
                        download_url = f"{self.base_url}/download.do"
                        
                        attachments.append({
                            'name': filename,
                            'url': download_url,
                            'file_id': file_id,
                            'download_method': 'POST'  # 특별 처리 필요 표시
                        })
                        
                        logger.debug(f"href JavaScript 첨부파일 발견: {filename} (ID: {file_id})")
            
            # 직접 다운로드 링크 방식
            elif href and ('download' in href.lower() or 'file' in href.lower()):
                file_url = urljoin(self.base_url, href)
                filename = link.get_text(strip=True) or "첨부파일"
                
                attachments.append({
                    'name': filename,
                    'url': file_url
                })
                
                logger.debug(f"직접 첨부파일 발견: {filename}")
        
        logger.info(f"총 {len(attachments)}개 첨부파일 발견")
        return attachments
    
    def _create_meta_info(self, announcement: Dict[str, Any]) -> str:
        """KOAT 메타 정보 생성"""
        meta_lines = [f"# {announcement['title']}", ""]
        
        # KOAT 특화 메타 정보
        if 'number' in announcement and announcement['number']:
            meta_lines.append(f"**번호**: {announcement['number']}")
        if 'author' in announcement and announcement['author']:
            meta_lines.append(f"**작성자**: {announcement['author']}")
        if 'date' in announcement and announcement['date']:
            meta_lines.append(f"**등록일**: {announcement['date']}")
        if 'views' in announcement and announcement['views']:
            meta_lines.append(f"**조회수**: {announcement['views']}")
        if 'has_attachment' in announcement:
            meta_lines.append(f"**첨부파일**: {'있음' if announcement['has_attachment'] else '없음'}")
        
        meta_lines.extend([
            f"**원본 URL**: {announcement['url']}",
            "",
            "---",
            ""
        ])
        
        return "\n".join(meta_lines)
    
    def download_file(self, url: str, save_path: str, attachment_info: Dict[str, Any] = None) -> bool:
        """파일 다운로드 - KOAT 특화 (POST 방식 지원)"""
        try:
            logger.info(f"파일 다운로드 시작: {url}")
            
            # KOAT 특화: POST 방식 다운로드 처리
            if attachment_info and attachment_info.get('download_method') == 'POST' and 'file_id' in attachment_info:
                file_id = attachment_info['file_id']
                logger.info(f"KOAT POST 다운로드: 파일 ID {file_id}")
                
                # Referer 헤더 설정 (상세 페이지 URL 필요)
                download_headers = self.headers.copy()
                download_headers.update({
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': f"{self.base_url}/board/business/view.do"  # 일반적인 상세 페이지 패턴
                })
                
                # POST 데이터 구성 (form-encoded)
                post_data = {
                    'mode': '1',
                    'key': str(file_id)
                }
                
                logger.debug(f"POST 데이터: {post_data}")
                logger.debug(f"요청 헤더: Content-Type={download_headers.get('Content-Type')}")
                
                # POST 요청으로 파일 다운로드
                response = self.session.post(
                    url,
                    data=post_data,
                    headers=download_headers,
                    stream=True,
                    verify=self.verify_ssl,
                    timeout=60
                )
                
                logger.info(f"응답 상태: {response.status_code}")
                
            else:
                # 일반적인 GET 요청 다운로드
                download_headers = self.headers.copy()
                download_headers['Referer'] = self.base_url
                
                response = self.session.get(
                    url, 
                    headers=download_headers,
                    stream=True, 
                    verify=self.verify_ssl, 
                    timeout=60
                )
            
            response.raise_for_status()
            
            # Content-Type 확인
            content_type = response.headers.get('content-type', '').lower()
            logger.info(f"Content-Type: {content_type}")
            
            # Content-Length 확인
            content_length = response.headers.get('content-length')
            if content_length:
                file_size = int(content_length)
                logger.info(f"예상 파일 크기: {file_size:,} bytes")
                
                # 0바이트 파일 체크
                if file_size == 0:
                    logger.warning("서버에서 0바이트 파일을 반환했습니다")
                    return False
            
            # 실제 파일명 추출
            actual_filename = self._extract_filename(response, save_path)
            if actual_filename != save_path:
                save_path = actual_filename
                logger.info(f"파일명 업데이트: {os.path.basename(save_path)}")
            
            # 디렉토리 생성
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # 파일 저장
            downloaded_size = 0
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
            
            # 다운로드 완료 확인
            if os.path.exists(save_path):
                actual_size = os.path.getsize(save_path)
                logger.info(f"다운로드 완료: {save_path} ({actual_size:,} bytes)")
                
                # 0바이트 파일 체크
                if actual_size == 0:
                    logger.warning("다운로드된 파일이 0바이트입니다")
                    os.remove(save_path)
                    return False
                
                # 파일 타입 검증
                if save_path.lower().endswith('.pdf'):
                    with open(save_path, 'rb') as f:
                        header = f.read(4)
                        if not header.startswith(b'%PDF'):
                            logger.warning(f"PDF 파일 검증 실패: {save_path}")
                
                return True
            else:
                logger.error("파일 저장 실패")
                return False
                
        except requests.RequestException as e:
            logger.error(f"파일 다운로드 실패 {url}: {e}")
            return False
        except Exception as e:
            logger.error(f"파일 저장 중 오류 {save_path}: {e}")
            return False

# 하위 호환성을 위한 별칭
KOATScraper = EnhancedKOATScraper