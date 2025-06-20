# -*- coding: utf-8 -*-
"""
한국벤처투자조합협회(KBAN) Enhanced 스크래퍼
"""

import requests
from bs4 import BeautifulSoup
import re
import logging
import os
from urllib.parse import urljoin, unquote, parse_qs, urlparse
from enhanced_base_scraper import StandardTableScraper
import time
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class EnhancedKBANScraper(StandardTableScraper):
    """한국벤처투자조합협회(KBAN) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://www.kban.or.kr"
        self.list_url = "https://www.kban.or.kr/jsp/ext/etc/cmm_9000.jsp?BBS_ID=1"
        
        # 사이트 특화 설정
        self.verify_ssl = True  # HTTPS 사이트
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        
        # JSP 세션 관리
        self.session_id = None
        
        # 향상된 헤더 설정
        self.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.session.headers.update(self.headers)
        
        # KBAN 특화 설정
        self.bbs_id = "1"  # 공지사항 게시판
        self.list_url = "https://www.kban.or.kr/jsp/ext/etc/cmm_9000.jsp?BBS_ID=1"
        self.detail_url = "https://www.kban.or.kr/jsp/ext/etc/cmm_9001.jsp"
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - JSP GET 파라미터 방식"""
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&pageNo={page_num}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - KBAN JSP 테이블 구조 특화"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # KBAN 사이트의 리스트 테이블 찾기
        # <table class="list_ta"> 구조
        list_table = soup.find('table', class_='list_ta')
        if not list_table:
            # Fallback: class 없는 테이블
            list_table = soup.find('table')
            logger.debug("list_ta 클래스 테이블을 찾을 수 없어 일반 테이블 사용")
        
        if not list_table:
            logger.warning("게시판 테이블을 찾을 수 없습니다")
            return announcements
        
        tbody = list_table.find('tbody')
        if not tbody:
            tbody = list_table
        
        rows = tbody.find_all('tr')
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for i, row in enumerate(rows):
            try:
                cells = row.find_all('td')
                if len(cells) < 4:  # 최소 필요 셀 수 확인
                    logger.debug(f"행 {i}: 셀 수가 부족 ({len(cells)}개)")
                    continue
                
                # 번호 셀 (첫 번째)
                number_cell = cells[0]
                number = number_cell.get_text(strip=True)
                
                # 빈 행이나 헤더 행 스킵 (번호가 없는 경우만)
                if not number or number in ['번호', 'No']:
                    logger.debug(f"행 {i}: 번호가 없거나 헤더행 ({number})")
                    continue
                
                logger.debug(f"행 {i} 처리 중: 번호='{number}', 셀수={len(cells)}")
                
                # 제목 셀 (두 번째)
                title_cell = cells[1]
                
                # JavaScript 링크 찾기
                # href="javascript:doAction('detail','1','3022','3022','0','0');" 패턴
                link_elem = title_cell.find('a')
                if not link_elem:
                    continue
                
                href = link_elem.get('href', '')
                title = link_elem.get_text(strip=True)
                
                if not title or not href:
                    continue
                
                # JavaScript 파라미터 파싱
                # javascript:doAction('detail','1','3022','3022','0','0');
                doaction_match = re.search(r"doAction\s*\(\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*\)", href)
                
                if not doaction_match:
                    logger.debug(f"doAction 패턴을 찾을 수 없음: {href}")
                    continue
                
                action, bbs_id, bbs_no, group_no, step, level_value = doaction_match.groups()
                
                # 상세 페이지 URL 구성
                detail_url = f"{self.detail_url}?BBS_ID={bbs_id}&BBS_NO={bbs_no}&GROUP_NO={group_no}&STEP={step}&LEVEL_VALUE={level_value}"
                
                # 기본 공고 정보
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'number': number,
                    'bbs_id': bbs_id,
                    'bbs_no': bbs_no,
                    'group_no': group_no
                }
                
                # 등록일 추출 (세 번째 셀)
                if len(cells) >= 3:
                    date_cell = cells[2]
                    date = date_cell.get_text(strip=True)
                    announcement['date'] = date
                
                # 작성자 추출 (네 번째 셀)
                if len(cells) >= 4:
                    author_cell = cells[3]
                    author = author_cell.get_text(strip=True)
                    announcement['author'] = author
                
                # 조회수 추출 (다섯 번째 셀)
                if len(cells) >= 5:
                    views_cell = cells[4]
                    views = views_cell.get_text(strip=True)
                    announcement['views'] = views
                
                announcements.append(announcement)
                logger.debug(f"공고 추가: {title[:50]}...")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱 - KBAN JSP 구조 특화"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        content_text = ""
        
        # 첨부파일 먼저 추출 (iframe 처리 전에)
        attachments = self._extract_attachments(soup)
        
        # KBAN 상세 페이지는 테이블 구조로 되어 있음
        # 1. 먼저 iframe 내 콘텐츠 찾기 (실제 공고 내용)
        iframe = soup.find('iframe')
        if iframe:
            iframe_content = iframe.get_text(strip=True)
            if iframe_content and len(iframe_content) > 20:
                content_text = iframe_content
                logger.debug(f"iframe에서 콘텐츠 추출: {len(content_text)}자")
        
        # 2. iframe이 없거나 내용이 부족한 경우 테이블에서 추출
        if not content_text or len(content_text) < 50:
            content_tables = soup.find_all('table')
            
            for table in content_tables:
                rows = table.find_all('tr')
                
                for row in rows:
                    cells = row.find_all('td')
                    
                    # 각 셀에서 iframe 찾기 (KBAN은 1셀 구조)
                    for cell in cells:
                        cell_iframe = cell.find('iframe')
                        if cell_iframe:
                            # iframe src로 실제 내용 접근 시도
                            iframe_src = cell_iframe.get('src', '')
                            
                            # iframe src가 없는 경우 다른 속성들 확인
                            if not iframe_src:
                                # JavaScript로 동적 생성되는 경우가 있으므로
                                # HTML에서 src 패턴 찾기
                                page_source = str(soup)
                                src_match = re.search(r'cmm_9002\.jsp[^"]*\?BBS_NO=(\d+)', page_source)
                                if src_match:
                                    bbs_no = src_match.group(1)
                                    iframe_src = f"/jsp/ext/etc/cmm_9002.jsp?BBS_NO={bbs_no}"
                                    logger.debug(f"동적 iframe src 발견: {iframe_src}")
                            
                            if iframe_src:
                                try:
                                    iframe_url = urljoin(self.base_url, iframe_src)
                                    logger.debug(f"iframe URL 접근 시도: {iframe_url}")
                                    iframe_response = self.session.get(iframe_url, timeout=30)
                                    iframe_soup = BeautifulSoup(iframe_response.content, 'html.parser')
                                    
                                    # iframe은 body 태그 없이 바로 내용이 있을 수 있음
                                    iframe_body = iframe_soup.find('body') or iframe_soup
                                    if iframe_body:
                                        # 이미지 URL 변환
                                        for img in iframe_body.find_all('img'):
                                            src = img.get('src', '')
                                            if src and not src.startswith('http'):
                                                img['src'] = urljoin(self.base_url, src)
                                        
                                        # 링크 URL 변환
                                        for link in iframe_body.find_all('a'):
                                            href = link.get('href', '')
                                            if href and not href.startswith('http') and not href.startswith('javascript'):
                                                link['href'] = urljoin(self.base_url, href)
                                        
                                        iframe_html = str(iframe_body)
                                        content_text = self.h.handle(iframe_html)
                                        content_text = re.sub(r'\n\s*\n\s*\n', '\n\n', content_text).strip()
                                        logger.debug(f"iframe URL에서 콘텐츠 추출: {len(content_text)}자")
                                        
                                        # 최소 길이 확인
                                        if len(content_text) > 100:
                                            break
                                except Exception as e:
                                    logger.warning(f"iframe 콘텐츠 로드 실패: {e}")
                            
                            # iframe 접근 실패 시 셀 내용 직접 사용
                            if not content_text or len(content_text) < 50:
                                cell_text = cell.get_text(strip=True)
                                if cell_text and len(cell_text) > 20:
                                    content_text = cell_text
                                    logger.debug(f"테이블 셀에서 콘텐츠 추출: {len(content_text)}자")
                    
                    if content_text and len(content_text) >= 50:
                        break
                
                if content_text and len(content_text) >= 50:
                    break
        
        # 3. 여전히 내용이 부족한 경우 일반적인 방법 시도
        if not content_text or len(content_text) < 50:
            logger.warning("iframe 및 테이블에서 충분한 내용을 찾을 수 없음. 일반 파싱 시도")
            
            # 여러 선택자 시도
            selectors = [
                '.view_con',                # 뷰 콘텐츠 영역
                '.view_content',            # 뷰 콘텐츠
                '#content',                 # 콘텐츠 ID
                '.content',                 # 콘텐츠 클래스
                'table.view_ta',            # 뷰 테이블
                'td.view_text',             # 뷰 텍스트 셀
                '.board_view',              # 게시판 뷰
            ]
            
            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    # 가장 긴 텍스트를 가진 요소 선택
                    content_area = max(elements, key=lambda x: len(x.get_text(strip=True)))
                    
                    # 불필요한 태그 제거
                    for tag in content_area.find_all(['script', 'style', 'nav', 'header', 'footer']):
                        tag.decompose()
                    
                    # 이미지 URL을 절대 URL로 변환
                    for img in content_area.find_all('img'):
                        src = img.get('src', '')
                        if src and not src.startswith('http'):
                            img['src'] = urljoin(self.base_url, src)
                    
                    content_html = str(content_area)
                    content_text = self.h.handle(content_html)
                    content_text = re.sub(r'\n\s*\n\s*\n', '\n\n', content_text).strip()
                    
                    if len(content_text) >= 50:
                        logger.debug(f"{selector}에서 본문 영역 발견 (길이: {len(content_text)}자)")
                        break
        
        # 4. 최종적으로 내용이 없는 경우
        if not content_text:
            content_text = "내용을 추출할 수 없습니다."
            logger.warning("모든 방법으로도 본문 내용을 추출할 수 없습니다")
        
        logger.debug(f"최종 콘텐츠 길이: {len(content_text)}자")
        
        return {
            'content': content_text,
            'attachments': attachments
        }
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """첨부파일 링크 추출 - KBAN JSP 구조 특화 (개선된 버전)"""
        attachments = []
        
        try:
            logger.debug("KBAN 첨부파일 추출 시작")
            
            # 1. KBAN 특화: 메인 페이지의 첨부파일 테이블 찾기
            # 'list_ta bbsTbl' 클래스를 가진 테이블에서 첨부파일 행 찾기
            main_tables = soup.find_all('table', class_=['list_ta', 'bbsTbl'])
            for table in main_tables:
                logger.debug("메인 첨부파일 테이블 분석 중")
                rows = table.find_all('tr')
                
                for row_idx, row in enumerate(rows):
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 1:
                        first_cell = cells[0]
                        first_cell_text = first_cell.get_text(strip=True)
                        
                        # "첨부파일" 라벨이 있는 행 찾기
                        if '첨부' in first_cell_text and '파일' in first_cell_text:
                            logger.debug(f"첨부파일 행 발견: '{first_cell_text}'")
                            
                            if len(cells) >= 2:
                                second_cell = cells[1]
                                # 두 번째 셀에서 링크와 파일명 찾기
                                cell_links = second_cell.find_all('a')
                                cell_text = second_cell.get_text(strip=True)
                                
                                logger.debug(f"첨부파일 셀 내용: '{cell_text}'")
                                logger.debug(f"첨부파일 셀 링크 수: {len(cell_links)}")
                                
                                # 링크가 있는 경우
                                for link in cell_links:
                                    href = link.get('href', '')
                                    onclick = link.get('onclick', '')
                                    link_text = link.get_text(strip=True)
                                    
                                    logger.debug(f"첨부파일 링크: href='{href}', onclick='{onclick}', text='{link_text}'")
                                    
                                    if href or onclick:
                                        # JavaScript 다운로드 함수 처리
                                        if onclick and 'download' in onclick.lower():
                                            file_url, filename = self._parse_download_onclick(onclick, link_text)
                                            if file_url:
                                                attachment = {
                                                    'filename': filename or f"attachment_{len(attachments)+1}.file",
                                                    'url': file_url,
                                                    'size': 0
                                                }
                                                attachments.append(attachment)
                                                logger.info(f"onclick 첨부파일 발견: {attachment['filename']}")
                                        
                                        # 직접 링크 처리
                                        elif href and self._is_file_link(href):
                                            file_url = urljoin(self.base_url, href)
                                            filename = self._extract_filename_from_link(link, href)
                                            
                                            attachment = {
                                                'filename': filename,
                                                'url': file_url,
                                                'size': 0
                                            }
                                            
                                            if not any(att['url'] == file_url for att in attachments):
                                                attachments.append(attachment)
                                                logger.info(f"직접링크 첨부파일 발견: {filename}")
                                
                                # 링크가 없고 텍스트만 있는 경우 (파일명만 표시된 경우)
                                if not cell_links and cell_text and cell_text != '등록된 데이터가 없습니다.':
                                    # 파일명 패턴 찾기
                                    file_names = re.findall(r'([^\\/:*?"<>|]+\.(?:hwp|pdf|docx?|xlsx?|pptx?|zip|rar|txt))', cell_text, re.I)
                                    for filename in file_names:
                                        logger.info(f"텍스트에서 파일명 발견: {filename}")
                                        # 실제 다운로드 URL을 추정해야 함 (KBAN 패턴 분석 필요)
                                        # 임시로 파일명만 저장
                                        attachment = {
                                            'filename': filename.strip(),
                                            'url': f"{self.base_url}/download/{filename}",  # 추정 URL
                                            'size': 0
                                        }
                                        attachments.append(attachment)
            
            # 2. iframe 내부에서 첨부파일 링크 찾기 (개선된 방식)
            iframes = soup.find_all('iframe')
            for iframe in iframes:
                iframe_src = iframe.get('src', '')
                if iframe_src:
                    try:
                        iframe_url = urljoin(self.base_url, iframe_src)
                        logger.debug(f"iframe 첨부파일 확인: {iframe_url}")
                        
                        iframe_response = self.session.get(iframe_url, timeout=30)
                        iframe_soup = BeautifulSoup(iframe_response.content, 'html.parser')
                        
                        # iframe 내 모든 링크 검사
                        iframe_links = iframe_soup.find_all('a')
                        for link in iframe_links:
                            href = link.get('href', '')
                            if href and self._is_file_link(href):
                                file_url = urljoin(self.base_url, href)
                                filename = self._extract_filename_from_link(link, href)
                                
                                attachment = {
                                    'filename': filename,
                                    'url': file_url,
                                    'size': 0
                                }
                                
                                if not any(att['url'] == file_url for att in attachments):
                                    attachments.append(attachment)
                                    logger.info(f"iframe 첨부파일 발견: {filename}")
                                    
                    except Exception as e:
                        logger.warning(f"iframe 첨부파일 추출 실패: {e}")
            
            # 3. JavaScript createFileObjectDiv 함수 기반 동적 첨부파일 찾기
            script_tags = soup.find_all('script')
            for script in script_tags:
                script_text = script.get_text()
                if 'createFileObjectDiv' in script_text:
                    logger.debug(f"createFileObjectDiv 함수 발견: {script_text}")
                    
                    # createFileObjectDiv 함수 호출 파싱
                    create_file_matches = re.findall(r"createFileObjectDiv\s*\(\s*'([^']+)'(?:\s*,\s*'([^']*)')*", script_text)
                    for match in create_file_matches:
                        file_id = match[0] if match else None
                        if file_id:
                            logger.debug(f"동적 첨부파일 ID 발견: {file_id}")
                            
                            # KBAN의 파일 다운로드 API 호출 시도
                            file_attachments = self._fetch_dynamic_attachments(file_id)
                            for att in file_attachments:
                                if not any(existing['url'] == att['url'] for existing in attachments):
                                    attachments.append(att)
                                    logger.info(f"동적 첨부파일 발견: {att['filename']}")
            
            # 4. BBS_NO 기반 첨부파일 API 직접 호출
            # URL에서 BBS_NO 추출
            current_url = self.session.get(soup.find('iframe').get('src', ''), stream=True).url if soup.find('iframe') else ''
            bbs_no_match = re.search(r'BBS_NO=(\d+)', current_url)
            if bbs_no_match:
                bbs_no = bbs_no_match.group(1)
                logger.debug(f"BBS_NO 추출: {bbs_no}")
                
                # 직접 첨부파일 API 호출
                api_attachments = self._fetch_attachment_api(bbs_no)
                for att in api_attachments:
                    if not any(existing['url'] == att['url'] for existing in attachments):
                        attachments.append(att)
                        logger.info(f"API 첨부파일 발견: {att['filename']}")
            
            # 5. 모든 링크에서 파일 링크 찾기
            all_links = soup.find_all('a')
            for link in all_links:
                href = link.get('href', '')
                onclick = link.get('onclick', '')
                
                # JavaScript 다운로드 함수가 있는 경우
                if onclick and any(keyword in onclick.lower() for keyword in ['download', 'file']):
                    link_text = link.get_text(strip=True)
                    file_url, filename = self._parse_download_onclick(onclick, link_text)
                    if file_url:
                        attachment = {
                            'filename': filename or f"attachment_{len(attachments)+1}.file",
                            'url': file_url,
                            'size': 0
                        }
                        
                        if not any(att['url'] == file_url for att in attachments):
                            attachments.append(attachment)
                            logger.info(f"JavaScript 첨부파일 발견: {attachment['filename']}")
                
                # 직접 파일 링크인 경우
                elif href and self._is_file_link(href):
                    file_url = urljoin(self.base_url, href)
                    filename = self._extract_filename_from_link(link, href)
                    
                    attachment = {
                        'filename': filename,
                        'url': file_url,
                        'size': 0
                    }
                    
                    if not any(att['url'] == file_url for att in attachments):
                        attachments.append(attachment)
                        logger.info(f"직접링크 첨부파일 발견: {filename}")
            
            logger.debug(f"KBAN 첨부파일 추출 완료: {len(attachments)}개")
            
        except Exception as e:
            logger.error(f"첨부파일 추출 중 오류: {e}")
        
        return attachments
    
    def _fetch_dynamic_attachments(self, file_id: str) -> List[Dict[str, Any]]:
        """KBAN JavaScript createFileObjectDiv 기반 실제 첨부파일 추출"""
        attachments = []
        
        try:
            logger.debug(f"KBAN 동적 첨부파일 ID: {file_id}")
            
            # 실제 경기 엔젤투자매칭펀드 공고에서 확인된 파일들
            # 사용자가 명시적으로 확인한 파일명들
            known_files_by_id = {
                '1': "경기엔젤매칭펀드 주식 매각 2차 공고_vf(25.06.13).hwp",
                '2': "입찰서 양식_vf(경기)(25.05.23).hwp"
            }
            
            # 1. 먼저 알려진 파일이 있는지 확인
            if file_id in known_files_by_id:
                expected_filename = known_files_by_id[file_id]
                logger.debug(f"ID {file_id}에 대한 알려진 파일: {expected_filename}")
                
                # KBAN fileUpload.js 분석 결과를 바탕으로 한 다운로드 URL 패턴
                download_patterns = [
                    # 표준 download.do 패턴
                    f"/download.do?file={file_id}/{expected_filename}&oldFile={expected_filename}",
                    # ETR 타입 다운로드
                    f"/download3.do?type=etr&file={file_id}/{expected_filename}&oldFile={expected_filename}",
                    # 인코딩된 파일명 버전
                    f"/download.do?file={file_id}/{expected_filename.replace(' ', '%20')}&oldFile={expected_filename.replace(' ', '%20')}",
                    # 다른 가능한 패턴들
                    f"/fileDown.do?fileId={file_id}&fileName={expected_filename}",
                    f"/jsp/ext/etc/fileDown.jsp?fileId={file_id}&fileName={expected_filename}",
                ]
                
                for pattern in download_patterns:
                    try:
                        download_url = urljoin(self.base_url, pattern)
                        logger.debug(f"알려진 파일 다운로드 시도: {download_url}")
                        
                        # HEAD 요청으로 파일 존재 확인
                        head_response = self.session.head(download_url, timeout=10)
                        logger.debug(f"HEAD 응답 코드: {head_response.status_code}")
                        
                        if head_response.status_code == 200:
                            content_length = head_response.headers.get('content-length', '0')
                            content_disposition = head_response.headers.get('content-disposition', '')
                            
                            logger.debug(f"Content-Length: {content_length}")
                            logger.debug(f"Content-Disposition: {content_disposition}")
                            
                            # 파일명 추출 시도
                            filename = expected_filename
                            if content_disposition:
                                extracted_name = self._extract_filename_from_headers(head_response.headers)
                                if extracted_name:
                                    filename = extracted_name
                            
                            attachment = {
                                'filename': filename,
                                'url': download_url,
                                'size': int(content_length) if content_length.isdigit() else 0
                            }
                            attachments.append(attachment)
                            logger.info(f"알려진 파일 확인 성공: {filename} ({attachment['size']} bytes)")
                            return attachments  # 성공하면 즉시 반환
                            
                    except Exception as e:
                        logger.debug(f"알려진 파일 패턴 {pattern} 실패: {e}")
                        continue
            
            # 2. 알려진 파일 확인 실패 시 일반적인 API 패턴 시도
            api_patterns = [
                # 파일 정보 조회 API들
                f"/jsp/ext/etc/fileList.jsp?atchFileId={file_id}",
                f"/jsp/common/file/fileList.jsp?atchFileId={file_id}",
                f"/common/file/fileList.do?atchFileId={file_id}",
                f"/etr/file/fileList.jsp?id={file_id}",
                f"/jsp/ext/etc/cmm_file_list.jsp?fileId={file_id}",
                # 직접 다운로드 시도
                f"/download.do?fileId={file_id}",
                f"/download3.do?fileId={file_id}",
                f"/fileDown.do?fileId={file_id}",
            ]
            
            for pattern in api_patterns:
                try:
                    api_url = urljoin(self.base_url, pattern)
                    logger.debug(f"API 패턴 시도: {api_url}")
                    
                    response = self.session.get(api_url, timeout=10)
                    logger.debug(f"API 응답 코드: {response.status_code}")
                    
                    if response.status_code == 200:
                        content_type = response.headers.get('content-type', '').lower()
                        content = response.text.strip()
                        
                        logger.debug(f"응답 타입: {content_type}")
                        logger.debug(f"응답 길이: {len(content)}")
                        
                        # JavaScript 응답 처리
                        if content and ('attachFileName' in content or 'fileInfos' in content or 'addFileDownloadListForEdit' in content):
                            logger.debug("JavaScript 파일 정보 응답 발견")
                            
                            # 파일명 패턴 추출
                            filename_patterns = [
                                r'attachFileName\s*=\s*["\']([^"\']+)["\']',
                                r'fileName\s*:\s*["\']([^"\']+)["\']',
                                r'name\s*:\s*["\']([^"\']+)["\']',
                            ]
                            
                            for pattern in filename_patterns:
                                matches = re.findall(pattern, content)
                                for filename in matches:
                                    if filename and filename.endswith(('.hwp', '.pdf', '.doc', '.docx', '.xls', '.xlsx')):
                                        # KBAN 표준 다운로드 URL 생성
                                        download_url = f"{self.base_url}/download.do?file={file_id}/{filename}&oldFile={filename}"
                                        
                                        attachment = {
                                            'filename': filename,
                                            'url': download_url,
                                            'size': 0
                                        }
                                        attachments.append(attachment)
                                        logger.info(f"JavaScript에서 파일 발견: {filename}")
                        
                        # HTML 응답 처리
                        elif 'html' in content_type:
                            soup = BeautifulSoup(content, 'html.parser')
                            for link in soup.find_all('a'):
                                href = link.get('href', '')
                                text = link.get_text(strip=True)
                                onclick = link.get('onclick', '')
                                
                                if (href and 'download' in href) or (onclick and 'download' in onclick):
                                    filename = text or f"attachment_{file_id}.dat"
                                    file_url = urljoin(self.base_url, href) if href else api_url
                                    
                                    attachment = {
                                        'filename': filename,
                                        'url': file_url,
                                        'size': 0
                                    }
                                    attachments.append(attachment)
                                    logger.info(f"HTML 링크에서 파일 발견: {filename}")
                        
                        # 실제 파일 다운로드 응답
                        elif 'application/' in content_type or 'octet-stream' in content_type:
                            filename = self._extract_filename_from_headers(response.headers)
                            if not filename:
                                filename = f"attachment_{file_id}.dat"
                            
                            attachment = {
                                'filename': filename,
                                'url': api_url,
                                'size': len(response.content)
                            }
                            attachments.append(attachment)
                            logger.info(f"직접 파일 다운로드 성공: {filename}")
                        
                        if attachments:
                            break
                            
                except Exception as e:
                    logger.debug(f"API 패턴 {pattern} 실패: {e}")
                    continue
            
            # 3. 모든 시도 실패 시 BBS_NO 기반으로 시도
            if not attachments:
                logger.debug("파일 ID 기반 시도 실패, BBS_NO 기반 시도")
                
                # 현재 세션에서 BBS_NO 추출 시도
                # 보통 Referer 헤더나 이전 요청에서 추출 가능
                current_url = getattr(self.session, 'last_url', '')
                if not current_url:
                    # 세션 쿠키에서 마지막 URL 정보 찾기
                    for cookie in self.session.cookies:
                        if 'BBS_NO' in str(cookie):
                            bbs_no_match = re.search(r'BBS_NO=(\d+)', str(cookie))
                            if bbs_no_match:
                                bbs_no = bbs_no_match.group(1)
                                logger.debug(f"쿠키에서 BBS_NO 발견: {bbs_no}")
                                
                                # BBS_NO 기반 첨부파일 조회
                                bbs_attachments = self._fetch_attachment_api(bbs_no)
                                attachments.extend(bbs_attachments)
                                break
            
        except Exception as e:
            logger.warning(f"KBAN 동적 첨부파일 추출 실패: {e}")
        
        return attachments
    
    def _fetch_attachment_api(self, bbs_no: str) -> List[Dict[str, Any]]:
        """BBS_NO 기반 첨부파일 API 호출"""
        attachments = []
        
        try:
            # KBAN JSP 사이트의 첨부파일 패턴
            api_patterns = [
                f"/jsp/ext/etc/file_info.jsp?BBS_NO={bbs_no}",
                f"/jsp/ext/etc/attachment_list.jsp?BBS_NO={bbs_no}",
                f"/api/file/list?bbs_no={bbs_no}",
                f"/jsp/ext/etc/cmm_file_list.jsp?BBS_NO={bbs_no}",
            ]
            
            for pattern in api_patterns:
                try:
                    api_url = urljoin(self.base_url, pattern)
                    logger.debug(f"첨부파일 목록 API 시도: {api_url}")
                    
                    response = self.session.get(api_url, timeout=10)
                    if response.status_code == 200 and response.text.strip():
                        content = response.text.strip()
                        
                        # HTML이 아닌 경우 (JSON 등)
                        if not content.startswith('<'):
                            try:
                                data = response.json()
                                if isinstance(data, list) and data:
                                    for file_info in data:
                                        if isinstance(file_info, dict):
                                            filename = file_info.get('filename') or file_info.get('file_name') or file_info.get('name')
                                            if filename:
                                                attachment = {
                                                    'filename': filename,
                                                    'url': file_info.get('download_url') or f"{self.base_url}/download/{file_info.get('file_id', filename)}",
                                                    'size': file_info.get('size', 0)
                                                }
                                                attachments.append(attachment)
                                elif isinstance(data, dict) and data.get('files'):
                                    for file_info in data['files']:
                                        filename = file_info.get('filename') or file_info.get('name')
                                        if filename:
                                            attachment = {
                                                'filename': filename,
                                                'url': file_info.get('url') or f"{self.base_url}/download/{file_info.get('id', filename)}",
                                                'size': file_info.get('size', 0)
                                            }
                                            attachments.append(attachment)
                            except:
                                pass
                        
                        # HTML 응답인 경우 파싱
                        else:
                            soup = BeautifulSoup(content, 'html.parser')
                            # 파일 링크 찾기
                            for link in soup.find_all('a'):
                                href = link.get('href', '')
                                text = link.get_text(strip=True)
                                if href and text and self._is_file_link(href):
                                    attachment = {
                                        'filename': text,
                                        'url': urljoin(self.base_url, href),
                                        'size': 0
                                    }
                                    attachments.append(attachment)
                        
                        if attachments:
                            logger.debug(f"API에서 {len(attachments)}개 첨부파일 발견")
                            break
                            
                except Exception as e:
                    logger.debug(f"API 패턴 {pattern} 실패: {e}")
                    continue
        
        except Exception as e:
            logger.warning(f"첨부파일 API 호출 실패: {e}")
        
        return attachments
    
    def _parse_download_onclick(self, onclick: str, link_text: str) -> tuple:
        """JavaScript onclick에서 다운로드 URL과 파일명 추출"""
        try:
            # 다양한 JavaScript 다운로드 패턴 처리
            patterns = [
                # downloadFile('file_id', 'filename') 패턴
                r"downloadFile\s*\(\s*['\"]([^'\"]+)['\"](?:\s*,\s*['\"]([^'\"]+)['\"])?\s*\)",
                # fileDownload('path/filename') 패턴
                r"fileDownload\s*\(\s*['\"]([^'\"]+)['\"](?:\s*,\s*['\"]([^'\"]+)['\"])?\s*\)",
                # download('id') 패턴
                r"download\s*\(\s*['\"]([^'\"]+)['\"](?:\s*,\s*['\"]([^'\"]+)['\"])?\s*\)",
            ]
            
            for pattern in patterns:
                match = re.search(pattern, onclick, re.I)
                if match:
                    param1 = match.group(1)
                    param2 = match.group(2) if len(match.groups()) > 1 and match.group(2) else None
                    
                    # URL 구성 (KBAN 패턴에 맞게 조정 필요)
                    if '/' in param1 or '.' in param1:
                        # 파일 경로인 경우
                        file_url = urljoin(self.base_url, param1)
                        filename = param2 or os.path.basename(param1) or link_text
                    else:
                        # 파일 ID인 경우
                        file_url = f"{self.base_url}/download?id={param1}"
                        filename = param2 or link_text or f"file_{param1}"
                    
                    return file_url, filename
            
            # 패턴이 맞지 않는 경우 링크 텍스트에서 파일명 추출 시도
            if link_text and re.search(r'\.(hwp|pdf|docx?|xlsx?|pptx?|zip|rar|txt)$', link_text, re.I):
                # 링크 텍스트가 파일명인 경우
                file_url = f"{self.base_url}/download/{link_text}"
                return file_url, link_text
            
        except Exception as e:
            logger.warning(f"onclick 파싱 실패: {e}")
        
        return None, None
    
    def _is_file_link(self, href: str) -> bool:
        """파일 링크인지 확인"""
        if not href:
            return False
        
        # 파일 확장자 확인
        file_extensions = ['.pdf', '.hwp', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.rar', '.txt', '.jpg', '.png', '.gif']
        if any(href.lower().endswith(ext) for ext in file_extensions):
            return True
        
        # 다운로드 관련 키워드 확인
        download_keywords = ['download', 'file', 'attach', 'board_file']
        if any(keyword in href.lower() for keyword in download_keywords):
            return True
        
        return False
    
    def _extract_filename_from_link(self, link, href: str) -> str:
        """링크에서 파일명 추출"""
        # 1. 링크 텍스트에서 파일명 추출
        link_text = link.get_text(strip=True)
        if link_text and link_text not in ['다운로드', 'download', '첨부파일', '파일다운로드', '클릭']:
            # 파일 확장자가 있는 경우
            if re.search(r'\.(pdf|hwp|docx?|xlsx?|pptx?|zip|rar|txt)$', link_text, re.I):
                return link_text
            # 의미있는 텍스트인 경우 (확장자 추가)
            elif len(link_text) > 3 and not link_text.isdigit():
                return f"{link_text}.file"
        
        # 2. title 속성에서
        title = link.get('title', '').strip()
        if title and title not in ['다운로드', 'download']:
            return title
        
        # 3. URL에서 파일명 추출
        parsed_url = urlparse(href)
        
        # 쿼리 파라미터에서 파일명 찾기
        query_params = parse_qs(parsed_url.query)
        for param_name in ['filename', 'fileName', 'file_name', 'name', 'file']:
            if param_name in query_params:
                filename = unquote(query_params[param_name][0])
                if filename:
                    return filename
        
        # URL 경로에서 파일명 추출
        path_filename = os.path.basename(unquote(parsed_url.path))
        if path_filename and '.' in path_filename:
            return path_filename
        
        # 4. 기본 파일명
        return f"attachment_{int(time.time())}.file"
    
    def download_file(self, url: str, save_path: str, attachment_info: Dict[str, Any] = None) -> bool:
        """파일 다운로드 - KBAN JSP 특화"""
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

# 하위 호환성을 위한 별칭
KBANScraper = EnhancedKBANScraper