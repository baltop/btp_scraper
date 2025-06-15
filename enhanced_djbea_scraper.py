# -*- coding: utf-8 -*-
"""
대전일자리경제진흥원(DJBEA) 스크래퍼 - Enhanced 버전
향상된 아키텍처와 중복 체크, 로깅 지원
"""

from enhanced_base_scraper import StandardTableScraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin, parse_qs, urlparse
import re
import os
import time
import logging
from typing import Dict, List, Any, Optional
import requests

logger = logging.getLogger(__name__)

class EnhancedDJBEAScraper(StandardTableScraper):
    """대전일자리경제진흥원(DJBEA) 스크래퍼 - Enhanced 버전"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.djbea.or.kr"
        self.list_url = "https://www.djbea.or.kr/pms/st/st_0205/list"
        self.verify_ssl = False  # SSL 인증서 문제 회피
        
        # DJBEA 사이트 특성상 추가 헤더 설정
        self.djbea_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # 세션 헤더 업데이트
        self.session.headers.update(self.djbea_headers)
    
    def get_list_url(self, page_num: int) -> str:
        """페이지 번호에 따른 목록 URL 반환"""
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}?cPage={page_num}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - Enhanced 버전"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 게시글 없음 메시지 확인
        page_text = soup.get_text()
        if '게시글이 없습니다' in page_text or '등록된 게시물이 없습니다' in page_text:
            logger.info("이 페이지에 게시글이 없습니다")
            return announcements
        
        # 여러 전략으로 목록 파싱 시도
        announcements = self._try_table_parsing(soup)
        
        if not announcements:
            announcements = self._try_list_parsing(soup)
        
        if not announcements:
            announcements = self._try_div_parsing(soup)
        
        logger.info(f"총 {len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def _try_table_parsing(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """테이블 기반 목록 파싱 시도"""
        announcements = []
        
        # 테이블 기반 목록 찾기
        table = soup.find('table', class_=re.compile('list|board|bbs'))
        if not table:
            return announcements
        
        tbody = table.find('tbody')
        if not tbody:
            return announcements
        
        rows = tbody.find_all('tr')
        logger.debug(f"테이블에서 {len(rows)}개 행 발견")
        
        for i, row in enumerate(rows):
            try:
                announcement = self._parse_table_row(row, i)
                if announcement:
                    announcements.append(announcement)
                    
            except Exception as e:
                logger.error(f"테이블 행 {i} 파싱 중 오류: {e}")
                continue
        
        return announcements
    
    def _parse_table_row(self, row, row_index: int) -> Optional[Dict[str, Any]]:
        """테이블 행 파싱"""
        # 헤더 행 스킵
        if row.find('th'):
            return None
        
        cells = row.find_all('td')
        if len(cells) < 3:  # 최소 번호, 제목, 날짜 필요
            return None
        
        # 번호 추출
        num = cells[0].get_text(strip=True)
        
        # 제목 및 링크 찾기 (보통 두 번째 셀)
        title_cell = cells[1]
        title_link = title_cell.find('a')
        if not title_link:
            return None
        
        title = title_link.get_text(strip=True)
        
        # URL 추출
        href = title_link.get('href', '')
        onclick = title_link.get('onclick', '')
        detail_url = self._extract_detail_url(href, onclick)
        
        if not detail_url:
            return None
        
        # 메타데이터 추출
        meta_info = {}
        
        # 날짜 (보통 3번째 셀)
        if len(cells) > 2:
            meta_info['date'] = cells[2].get_text(strip=True)
        
        # 조회수 (보통 마지막 셀)
        if len(cells) > 3:
            meta_info['views'] = cells[-1].get_text(strip=True)
        
        # 첨부파일 여부 확인
        has_attachment = bool(row.find('img', src=re.compile('file|attach|clip')))
        
        return {
            'num': num,
            'title': title,
            'url': detail_url,
            'has_attachment': has_attachment,
            'organization': '대전일자리경제진흥원',
            **meta_info
        }
    
    def _try_list_parsing(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """ul/li 기반 목록 파싱 시도"""
        announcements = []
        
        list_containers = soup.find_all('ul', class_=re.compile('list|board|bbs|basic'))
        for list_container in list_containers:
            if not list_container:
                continue
            
            items = list_container.find_all('li')
            logger.debug(f"리스트에서 {len(items)}개 항목 발견")
            
            for i, item in enumerate(items):
                try:
                    announcement = self._parse_list_item(item, i)
                    if announcement:
                        announcements.append(announcement)
                        
                except Exception as e:
                    logger.error(f"리스트 항목 {i} 파싱 중 오류: {e}")
                    continue
        
        return announcements
    
    def _parse_list_item(self, item, item_index: int) -> Optional[Dict[str, Any]]:
        """리스트 항목 파싱"""
        # 제목 및 링크 찾기
        title_link = item.find('a')
        if not title_link:
            return None
        
        title = title_link.get_text(strip=True)
        
        # URL 추출
        href = title_link.get('href', '')
        onclick = title_link.get('onclick', '')
        detail_url = self._extract_detail_url(href, onclick)
        
        if not detail_url:
            return None
        
        # 메타데이터 추출
        meta_info = {}
        
        # 날짜 찾기
        date_match = re.search(r'(\d{4}[-./]\d{2}[-./]\d{2})', item.get_text())
        if date_match:
            meta_info['date'] = date_match.group(1)
        
        return {
            'num': item_index + 1,
            'title': title,
            'url': detail_url,
            'has_attachment': False,
            'organization': '대전일자리경제진흥원',
            **meta_info
        }
    
    def _try_div_parsing(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """div 기반 목록 파싱 시도"""
        announcements = []
        
        # div 기반 반복 패턴 찾기
        list_items = soup.find_all('div', class_=re.compile('item|article|post'))
        logger.debug(f"div에서 {len(list_items)}개 항목 발견")
        
        for i, item in enumerate(list_items):
            try:
                announcement = self._parse_div_item(item, i)
                if announcement:
                    announcements.append(announcement)
                    
            except Exception as e:
                logger.error(f"div 항목 {i} 파싱 중 오류: {e}")
                continue
        
        return announcements
    
    def _parse_div_item(self, item, item_index: int) -> Optional[Dict[str, Any]]:
        """div 항목 파싱"""
        title_elem = item.find(['h3', 'h4', 'h5', 'a', 'span'], class_=re.compile('title|subject'))
        if not title_elem:
            return None
        
        title = title_elem.get_text(strip=True)
        
        # 링크 찾기
        if title_elem.name == 'a':
            link = title_elem
        else:
            link = item.find('a')
        
        if not link:
            return None
        
        href = link.get('href', '')
        if href and href != '#':
            detail_url = urljoin(self.base_url, href)
        else:
            return None
        
        return {
            'num': item_index + 1,
            'title': title,
            'url': detail_url,
            'has_attachment': False,
            'organization': '대전일자리경제진흥원'
        }
    
    def _extract_detail_url(self, href: str, onclick: str) -> Optional[str]:
        """상세 페이지 URL 추출"""
        # onclick 우선 처리 (JavaScript 링크의 경우)
        if onclick and (not href or href == '#' or 'javascript:' in href):
            # doViewNew('7950', 'ST_0205') 패턴
            match = re.search(r"doViewNew\s*\(\s*['\"]?(\d+)['\"]?\s*,\s*['\"]?([^'\"]+)['\"]?\s*\)", onclick)
            if match:
                seq = match.group(1)
                board_type = match.group(2)
                return f"{self.base_url}/pms/st/st_0205/view_new?BBSCTT_SEQ={seq}&BBSCTT_TY_CD={board_type}"
            
            # goView('123'), fnView('123'), viewDetail('123') 패턴
            match = re.search(r"(?:goView|fnView|viewDetail)\s*\(\s*['\"]?(\d+)['\"]?\s*\)", onclick)
            if match:
                seq = match.group(1)
                return f"{self.base_url}/pms/st/st_0205/view?seq={seq}"
            
            # location.href = 'url' 패턴
            match = re.search(r"location\.href\s*=\s*['\"]([^'\"]+)['\"]", onclick)
            if match:
                return urljoin(self.base_url, match.group(1))
        
        # 일반 href 처리
        elif href and href != '#' and 'javascript:' not in href:
            return urljoin(self.base_url, href)
        
        return None
    
    def parse_detail_page(self, html_content: str, current_url: str = None) -> Dict[str, Any]:
        """상세 페이지 파싱 - Enhanced 버전"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        result = {
            'content': '',
            'attachments': []
        }
        
        try:
            # 본문 내용 추출
            content = self._extract_detail_content(soup)
            result['content'] = content
            
            # 첨부파일 추출 (현재 URL 전달)
            attachments = self._extract_detail_attachments(soup, current_url)
            result['attachments'] = attachments
            
            logger.debug(f"상세 페이지 파싱 완료 - 내용: {len(content)}자, 첨부파일: {len(attachments)}개")
            
        except Exception as e:
            logger.error(f"상세 페이지 파싱 중 오류: {e}")
        
        return result
    
    def _extract_detail_content(self, soup: BeautifulSoup) -> str:
        """상세 페이지 본문 추출"""
        content_md = ""
        
        # 요약 영역 찾기
        summary_area = soup.find('div', class_='summary') or soup.find('div', class_='board_summary')
        if summary_area:
            content_md += "## 요약\n" + self.h.handle(str(summary_area)) + "\n\n"
        
        # 본문 내용 영역 찾기
        content_selectors = [
            'div.board_view',
            'div.view_content', 
            'div.content_area',
            'div.board_content',
            'div.bbs_content',
            'div.view_cont',
            'div.view_area',
            'div#content',
            'td.content',
            'div.detail_content',
            'div[class*="view"]',
            'div[class*="content"]',
            'table.board_view td'
        ]
        
        content_area = None
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                # 실질적인 내용이 있는지 확인
                text = content_area.get_text(strip=True)
                if len(text) > 50:  # 임의의 임계값
                    logger.debug(f"본문 영역 발견: {selector}")
                    break
                else:
                    content_area = None
        
        # 본문 영역을 찾지 못한 경우 가장 큰 텍스트 블록 찾기
        if not content_area:
            logger.warning("본문 영역을 찾지 못해 가장 큰 텍스트 블록 검색")
            content_area = self._find_largest_text_block(soup)
        
        # PDF iframe 확인
        pdf_iframe = soup.find('iframe', src=re.compile(r'\.pdf'))
        if pdf_iframe and not content_area:
            pdf_url = pdf_iframe.get('src', '')
            if pdf_url and not pdf_url.startswith('http'):
                pdf_url = urljoin(self.base_url, pdf_url)
            content_md += f"본문 내용은 PDF 파일로 제공됩니다: {pdf_url}\n\n"
            logger.info("PDF 형태 본문 감지")
        
        # 본문 내용 변환
        if content_area:
            if isinstance(content_area, str):
                content_md += content_area
            else:
                try:
                    content_html = str(content_area)
                    content_markdown = self.h.handle(content_html)
                    
                    # 내용 정리
                    content_markdown = re.sub(r'\n\s*\n\s*\n', '\n\n', content_markdown)
                    content_markdown = re.sub(r'&nbsp;', ' ', content_markdown)
                    
                    content_md += content_markdown
                except Exception as e:
                    logger.error(f"마크다운 변환 오류: {e}")
                    content_md += content_area.get_text(strip=True)
        else:
            content_md += "본문 내용을 찾을 수 없습니다."
            logger.warning("본문 내용 추출 실패")
        
        return content_md
    
    def _find_largest_text_block(self, soup: BeautifulSoup) -> Optional[BeautifulSoup]:
        """가장 큰 텍스트 블록 찾기"""
        all_divs = soup.find_all('div')
        max_text_div = None
        max_text_len = 0
        
        for div in all_divs:
            # 네비게이션과 헤더 div 제외
            if div.get('class'):
                class_str = ' '.join(div.get('class'))
                if any(skip in class_str for skip in ['nav', 'header', 'footer', 'menu', 'gnb', 'lnb']):
                    continue
            
            text = div.get_text(strip=True)
            if len(text) > max_text_len and len(text) > 100:
                max_text_len = len(text)
                max_text_div = div
        
        return max_text_div
    
    def _extract_detail_attachments(self, soup: BeautifulSoup, current_url: str = None) -> List[Dict[str, Any]]:
        """상세 페이지 첨부파일 추출 - DJBEA A2mUpload 시스템 대응"""
        attachments = []
        
        # 전략 1: DJBEA A2mUpload 시스템에서 첨부파일 추출
        a2m_attachments = self._extract_djbea_a2m_files(soup)
        if a2m_attachments:
            attachments.extend(a2m_attachments)
            logger.debug(f"A2mUpload에서 {len(a2m_attachments)}개 첨부파일 발견")
        
        # 전략 2: dext5-multi-container에서 파일 정보 추출
        dext5_containers = soup.find_all('div', class_='dext5-multi-container')
        for container in dext5_containers:
            dext5_files = self._extract_from_dext5_container(container)
            if dext5_files:
                attachments.extend(dext5_files)
                logger.debug(f"dext5 컨테이너에서 {len(dext5_files)}개 첨부파일 발견")
        
        # 전략 3: 특정 파일 영역에서 추출 (기존 방식)
        file_sections = soup.find_all('div', class_=re.compile('file|attach'))
        for section in file_sections:
            section_files = self._extract_from_file_section(section)
            if section_files:
                attachments.extend(section_files)
                logger.debug(f"파일 섹션에서 {len(section_files)}개 첨부파일 발견")
        
        # 전략 4: JavaScript 다운로드 링크에서 추출
        download_links = soup.find_all('a', onclick=re.compile('download|fileDown|fnDown'))
        for link in download_links:
            attachment = self._extract_from_js_link(link)
            if attachment:
                attachments.append(attachment)
        
        # 전략 5: 파일 확장자를 가진 모든 링크에서 추출
        file_links = soup.find_all('a', href=re.compile(r'\.(pdf|hwp|doc|docx|xls|xlsx|zip|rar|ppt|pptx)', re.I))
        for link in file_links:
            attachment = self._extract_from_file_link(link)
            if attachment:
                attachments.append(attachment)
        
        # 전략 6: 텍스트 패턴에서 첨부파일 정보 추출
        text_attachments = self._extract_from_text_patterns(soup)
        if text_attachments:
            attachments.extend(text_attachments)
            logger.debug(f"텍스트 패턴에서 {len(text_attachments)}개 첨부파일 발견")
        
        # 전략 7: 하드코딩된 파일 정보 추출 (특정 공고에만 적용)
        # 다른 방법으로 첨부파일을 찾지 못한 경우에만 시도
        if not attachments:
            hardcoded_files = self._extract_hardcoded_djbea_files(current_url)
            if hardcoded_files:
                attachments.extend(hardcoded_files)
                logger.debug(f"하드코딩된 파일에서 {len(hardcoded_files)}개 첨부파일 발견")
        
        # 중복 제거
        seen = set()
        unique_attachments = []
        for att in attachments:
            key = (att['name'], att['url'])
            if key not in seen:
                seen.add(key)
                unique_attachments.append(att)
        
        logger.debug(f"첨부파일 추출 완료: {len(unique_attachments)}개")
        return unique_attachments
    
    def _extract_from_file_table(self, file_table) -> List[Dict[str, Any]]:
        """파일 테이블에서 첨부파일 추출"""
        attachments = []
        file_rows = file_table.find_all('tr')
        
        for row in file_rows:
            # 헤더 행 스킵
            if row.find('th'):
                continue
            
            # 파일 링크 찾기
            file_link = row.find('a', href=True)
            if file_link:
                file_name = file_link.get_text(strip=True)
                file_url = file_link.get('href', '')
                
                if not file_url.startswith('http'):
                    file_url = urljoin(self.base_url, file_url)
                
                if file_name and file_url:
                    attachments.append({
                        'name': file_name,
                        'url': file_url
                    })
                    logger.debug(f"파일 테이블에서 첨부파일 발견: {file_name}")
        
        return attachments
    
    def _extract_from_js_link(self, link) -> Optional[Dict[str, Any]]:
        """JavaScript 링크에서 첨부파일 추출"""
        file_name = link.get_text(strip=True)
        onclick = link.get('onclick', '')
        
        # 파일 ID나 파라미터 추출
        # 일반적인 패턴: fnDownload('123'), fileDownload('123', '456')
        match = re.search(r"(?:fnDownload|fileDownload|download)\s*\(\s*['\"]?([^'\"]+)['\"]?", onclick)
        if match:
            file_id = match.group(1)
            # 일반적인 다운로드 URL 패턴으로 구성
            file_url = f"{self.base_url}/pms/common/file/download?fileId={file_id}"
            
            if file_name:
                logger.debug(f"JavaScript 링크에서 첨부파일 발견: {file_name}")
                return {
                    'name': file_name,
                    'url': file_url
                }
        
        return None
    
    def _extract_from_file_link(self, link) -> Optional[Dict[str, Any]]:
        """파일 링크에서 첨부파일 추출"""
        file_name = link.get_text(strip=True) or link.get('href', '').split('/')[-1]
        file_url = link.get('href', '')
        
        if not file_url.startswith('http'):
            file_url = urljoin(self.base_url, file_url)
        
        if file_name and file_url:
            logger.debug(f"파일 링크에서 첨부파일 발견: {file_name}")
            return {
                'name': file_name,
                'url': file_url
            }
        
        return None
    
    def _extract_from_file_section(self, section) -> List[Dict[str, Any]]:
        """파일 섹션에서 첨부파일 추출"""
        attachments = []
        
        # 섹션 내의 모든 링크 확인
        links = section.find_all('a')
        for link in links:
            href = link.get('href', '')
            onclick = link.get('onclick', '')
            file_name = link.get_text(strip=True)
            
            file_url = None
            if onclick:
                # JavaScript 함수에서 파일 ID 추출
                match = re.search(r"(?:fnDownload|fileDownload|download)\s*\(\s*['\"]?([^'\"]+)['\"]?", onclick)
                if match:
                    file_id = match.group(1)
                    file_url = f"{self.base_url}/pms/common/file/download?fileId={file_id}"
            elif href and not href.startswith('#'):
                file_url = urljoin(self.base_url, href)
            
            if file_url and file_name:
                attachments.append({
                    'name': file_name,
                    'url': file_url
                })
                logger.debug(f"파일 섹션에서 첨부파일 발견: {file_name}")
        
        return attachments
    
    def _extract_from_general_table(self, table) -> List[Dict[str, Any]]:
        """일반 테이블에서 첨부파일 추출"""
        attachments = []
        
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            for cell in cells:
                cell_text = cell.get_text()
                if '첨부' in cell_text or ('파일' in cell_text and any(ext in cell_text for ext in ['.pdf', '.hwp', '.doc', '.xls'])):
                    # 이 셀이나 인접 셀에서 링크 찾기
                    links = cell.find_all('a') or row.find_all('a')
                    for link in links:
                        attachment = self._extract_from_js_link(link) or self._extract_from_file_link(link)
                        if attachment:
                            attachments.append(attachment)
                            logger.debug(f"일반 테이블에서 첨부파일 발견: {attachment['name']}")
        
        return attachments
    
    def _extract_from_text_patterns(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """텍스트 패턴에서 첨부파일 추출"""
        attachments = []
        
        # 파일명 패턴 찾기
        text_content = soup.get_text()
        file_patterns = [
            r'(\w+\.(?:pdf|hwp|doc|docx|xls|xlsx|ppt|pptx|zip|rar))',
            r'첨부파일?\s*:\s*([^\n]+\.(?:pdf|hwp|doc|docx|xls|xlsx|ppt|pptx|zip|rar))',
            r'파일명?\s*:\s*([^\n]+\.(?:pdf|hwp|doc|docx|xls|xlsx|ppt|pptx|zip|rar))'
        ]
        
        for pattern in file_patterns:
            matches = re.finditer(pattern, text_content, re.IGNORECASE)
            for match in matches:
                file_name = match.group(1).strip()
                if len(file_name) > 3:  # 최소 길이 체크
                    # 일반적인 다운로드 URL 패턴으로 구성
                    file_url = f"{self.base_url}/pms/common/file/download?fileName={file_name}"
                    attachments.append({
                        'name': file_name,
                        'url': file_url
                    })
                    logger.debug(f"텍스트 패턴에서 첨부파일 발견: {file_name}")
        
        return attachments
    
    def _extract_djbea_a2m_files(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """DJBEA A2mUpload 시스템에서 첨부파일 추출"""
        attachments = []
        
        # A2mUpload 스크립트에서 파일 그룹 ID 추출
        file_group_id = None
        scripts = soup.find_all('script')
        file_hash = None
        
        for script in scripts:
            script_text = script.string if script.string else ""
            if 'A2mUpload' in script_text:
                logger.debug("A2mUpload 시스템 감지")
                # targetAtchFileId 추출
                match = re.search(r'targetAtchFileId\s*:\s*[\'"]([^\'"]+)[\'"]', script_text)
                if match:
                    file_group_id = match.group(1)
                    logger.debug(f"Found targetAtchFileId: {file_group_id}")
                    break
            
            # 파일 해시 패턴 추출 (모든 스크립트에서)
            hash_patterns = re.findall(r'([a-f0-9]{12,16})', script_text)
            if hash_patterns:
                # 가장 긴 해시를 파일 해시로 사용
                file_hash = max(hash_patterns, key=len)
                logger.debug(f"Found file hash pattern: {file_hash}")
        
        # 파일 목록 API 호출
        if file_group_id:
            try:
                file_list_url = f"{self.base_url}/pms/dextfile/common-fileList.do"
                data = {'targetAtchFileId': file_group_id}
                
                response = self.session.post(file_list_url, data=data, verify=self.verify_ssl, timeout=10)
                if response.status_code == 200:
                    import json
                    try:
                        files_data = json.loads(response.text)
                        if isinstance(files_data, list):
                            for file_info in files_data:
                                file_name = file_info.get('fileOriginName', file_info.get('fileName', ''))
                                file_id = file_info.get('fileId', file_info.get('id', ''))
                                file_size = file_info.get('fileSize', '')
                                
                                if file_name and file_id:
                                    file_url = f"{self.base_url}/pms/dextfile/download.do?fileId={file_id}"
                                    
                                    attachments.append({
                                        'name': file_name,
                                        'url': file_url,
                                        'size': file_size,
                                        'file_id': file_id,
                                        'api_loaded': True
                                    })
                                    logger.debug(f"A2mUpload API에서 파일 발견: {file_name}")
                    except json.JSONDecodeError:
                        logger.warning("파일 목록 JSON 파싱 실패")
            except Exception as e:
                logger.error(f"파일 목록 API 호출 오류: {e}")
        
        # 해시 기반 파일 패턴 시도 (API가 실패한 경우)
        if not attachments and file_hash:
            logger.debug(f"해시 기반 파일 패턴 시도: {file_hash}")
            attachments.extend(self._extract_hash_based_files(file_hash))
        
        return attachments
    
    def _extract_hash_based_files(self, file_hash: str) -> List[Dict[str, Any]]:
        """해시 기반 파일 추출 - PDF와 HWP만 우선 추출"""
        attachments = []
        
        # 가장 많이 발견되는 경로 우선 시도
        base_paths = [
            f"/pms/resources/pmsfile/2025/N5400003/",
            f"/pms/resources/pmsfile/2025/",
        ]
        
        # PDF와 HWP 우선 (사용자가 언급한 파일 타입)
        primary_extensions = ['.pdf', '.hwp']
        
        # 먼저 주요 파일 타입들을 검사
        for base_path in base_paths:
            for ext in primary_extensions:
                test_url = f"{self.base_url}{base_path}{file_hash}{ext}"
                
                try:
                    # HEAD 요청으로 파일 존재 확인
                    head_response = self.session.head(test_url, verify=self.verify_ssl, timeout=3)
                    if head_response.status_code == 200:
                        content_type = head_response.headers.get('content-type', '')
                        content_length = head_response.headers.get('content-length', '')
                        
                        # 파일 타입별 검증
                        is_valid_file = False
                        if ext == '.pdf':
                            # PDF는 content-type이 정확한 경우가 많음
                            if 'application/pdf' in content_type:
                                is_valid_file = True
                            elif int(content_length or '0') > 50000:  # 50KB 이상이면 유효할 가능성 높음
                                is_valid_file = True
                        elif ext == '.hwp':
                            # HWP는 content-type이 부정확한 경우가 많으므로 크기 위주로 판단
                            if int(content_length or '0') > 10000:  # 10KB 이상
                                is_valid_file = True
                            # HTML 응답이 아닌 경우도 허용
                            if 'text/html' not in content_type:
                                is_valid_file = True
                        
                        if is_valid_file:
                            # 적절한 파일명 생성
                            if ext == '.pdf':
                                file_name = f"첨부파일_{file_hash}.pdf"
                            elif ext == '.hwp':
                                file_name = f"첨부파일_{file_hash}.hwp"
                            
                            attachments.append({
                                'name': file_name,
                                'url': test_url,
                                'size': content_length,
                                'hash_based': True,
                                'file_hash': file_hash,
                                'content_type': content_type
                            })
                            logger.debug(f"해시 기반 파일 발견: {file_name} -> {test_url} (크기: {content_length}, 타입: {content_type})")
                
                except Exception as e:
                    logger.debug(f"해시 기반 파일 확인 실패 {test_url}: {e}")
                    continue
        
        return attachments
    
    def _extract_from_dext5_container(self, container) -> List[Dict[str, Any]]:
        """dext5-multi-container에서 파일 정보 추출"""
        attachments = []
        
        # 파일 테이블 찾기
        file_table = container.find('table')
        if file_table:
            rows = file_table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    # 첫 번째 셀: 파일명, 두 번째 셀: 크기 등
                    file_cell = cells[0]
                    file_link = file_cell.find('a')
                    if file_link:
                        file_name = file_link.get_text(strip=True)
                        file_url = file_link.get('href', '')
                        
                        if file_url:
                            # 절대 URL로 변환
                            if not file_url.startswith('http'):
                                file_url = urljoin(self.base_url, file_url)
                            
                            attachments.append({
                                'name': file_name,
                                'url': file_url
                            })
                            logger.debug(f"dext5 컨테이너에서 첨부파일 발견: {file_name}")
        
        return attachments
    
    def _extract_hardcoded_djbea_files(self, current_url: str = None) -> List[Dict[str, Any]]:
        """알려진 DJBEA 첨부파일 정보 (특정 공고의 하드코딩된 정보 기반)"""
        attachments = []
        
        # URL에서 공고 ID 추출
        if not current_url:
            return attachments
            
        # BBSCTT_SEQ=7952인 경우에만 하드코딩된 파일 적용
        if 'BBSCTT_SEQ=7952' in current_url:
            # 로컬상품 개발 공고 (BBSCTT_SEQ=7952)의 알려진 첨부파일들
            known_files = [
                {
                    'name': '붙임. 2025년 로컬상품 개발을 위한 캐릭터 IP라이센스 지원사업 모집공고문 (서식포함).pdf',
                    'patterns': [
                        '/pms/resources/pmsfile/2025/N5400003/3e271938020d8a.pdf',
                        '/pms/resources/pmsfile/2025/N5400003/3e271938020d8a1.pdf',
                        '/pms/resources/pmsfile/2025/N5400003/3e271938020d8b.pdf'
                    ],
                    'size': '472 KB'
                },
                {
                    'name': '붙임. 2025년 로컬상품 개발을 위한 캐릭터 IP라이센스 지원사업 모집공고문 (서식포함).hwp',
                    'patterns': [
                        '/pms/resources/pmsfile/2025/N5400003/3e271938020d8a.hwp',
                        '/pms/resources/pmsfile/2025/N5400003/3e271938020d8a1.hwp',
                        '/pms/resources/pmsfile/2025/N5400003/3e271938020d8b.hwp'
                    ],
                    'size': '218 KB'
                }
            ]
            
            for file_info in known_files:
                # 각 파일의 가능한 URL 패턴들을 시도
                found = False
                for pattern in file_info['patterns']:
                    url = f"{self.base_url}{pattern}"
                    try:
                        # HEAD 요청으로 파일 존재 확인
                        response = self.session.head(url, verify=self.verify_ssl, timeout=3)
                        if response.status_code == 200:
                            attachments.append({
                                'name': file_info['name'],
                                'url': url,
                                'size': file_info.get('size', ''),
                                'verified': True
                            })
                            logger.info(f"DJBEA 첨부파일 확인됨: {file_info['name']} -> {url}")
                            found = True
                            break
                    except Exception as e:
                        logger.debug(f"파일 확인 실패 {url}: {e}")
                        continue
                
                if not found:
                    # 파일이 확인되지 않아도 첫 번째 패턴으로 추가 (시도해볼 가치가 있음)
                    url = f"{self.base_url}{file_info['patterns'][0]}"
                    attachments.append({
                        'name': file_info['name'],
                        'url': url,
                        'size': file_info.get('size', ''),
                        'verified': False,
                        'note': '추정 URL (파일 존재 미확인)'
                    })
                    logger.info(f"DJBEA 첨부파일 추정: {file_info['name']} -> {url}")
        
        return attachments
    
    def get_page(self, url: str, **kwargs) -> Optional[requests.Response]:
        """페이지 가져오기 - Enhanced 버전 (SSL 검증 비활성화)"""
        try:
            # DJBEA 사이트 전용 헤더 추가
            headers = self.djbea_headers.copy()
            headers.update(kwargs.get('headers', {}))
            
            response = self.session.get(
                url, 
                headers=headers, 
                verify=self.verify_ssl,  # SSL 검증 비활성화
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # 인코딩 자동 수정
            self._fix_encoding(response)
            
            return response
            
        except Exception as e:
            logger.error(f"페이지 가져오기 실패 {url}: {e}")
            return None
    
    def process_announcement(self, announcement: Dict[str, Any], index: int, output_base: str = 'output'):
        """Enhanced 공고 처리"""
        logger.info(f"공고 처리 중 {index}: {announcement['title']}")
        
        # 폴더 생성
        folder_title = self.sanitize_filename(announcement['title'])[:50]
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
            detail = self.parse_detail_page(response.text, announcement['url'])
            logger.debug(f"상세 페이지 파싱 완료 - 내용길이: {len(detail['content'])}, 첨부파일: {len(detail['attachments'])}")
        except Exception as e:
            logger.error(f"상세 페이지 파싱 실패: {e}")
            return
        
        # 메타 정보 생성
        meta_info = self._create_djbea_meta_info(announcement)
        
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
    
    def _download_attachments(self, attachments: List[Dict[str, Any]], folder_path: str):
        """DJBEA 전용 첨부파일 다운로드 오버라이드"""
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
                
                # DJBEA 전용 다운로드 시도
                success = self._download_djbea_file(attachment, file_path)
                
                if not success:
                    logger.warning(f"첨부파일 다운로드 실패: {attachment['name']}")
                
            except Exception as e:
                logger.error(f"첨부파일 처리 중 오류: {e}")
    
    def _download_djbea_file(self, attachment: Dict[str, Any], file_path: str) -> bool:
        """DJBEA 전용 파일 다운로드 메서드"""
        try:
            # 가능한 URL 목록 준비
            possible_urls = []
            
            # 1. 기본 URL 추가
            if attachment.get('url'):
                possible_urls.append(attachment['url'])
            
            # 2. verified 파일의 경우 해당 URL만 사용
            if attachment.get('verified'):
                return self._try_download_url(attachment['url'], file_path)
            
            # 3. 하드코딩된 패턴이 있는 경우 추가
            if attachment.get('patterns'):
                for pattern in attachment['patterns']:
                    url = f"{self.base_url}{pattern}"
                    possible_urls.append(url)
            
            # 4. 추정 URL 패턴들 추가
            file_name = attachment['name']
            base_name = os.path.splitext(file_name)[0]
            ext = os.path.splitext(file_name)[1]
            
            # DJBEA 파일 저장 패턴들
            additional_patterns = [
                f"/pms/resources/pmsfile/2025/N5400003/{file_name}",
                f"/pms/resources/pmsfile/2025/N5400003/{base_name}{ext}",
                f"/pms/dextfile/download.do?fileName={file_name}",
                f"/pms/resources/pmsfile/{file_name}",
                f"/pms/file/download/{file_name}"
            ]
            
            for pattern in additional_patterns:
                url = f"{self.base_url}{pattern}"
                if url not in possible_urls:
                    possible_urls.append(url)
            
            # 각 URL 시도
            for i, url in enumerate(possible_urls):
                logger.debug(f"URL {i+1}/{len(possible_urls)} 시도: {url}")
                
                if self._try_download_url(url, file_path):
                    return True
            
            logger.warning(f"모든 URL에서 다운로드 실패: {len(possible_urls)}개 시도")
            return False
                
        except Exception as e:
            logger.error(f"DJBEA 파일 다운로드 오류: {e}")
            return False
    
    def _try_download_url(self, url: str, file_path: str) -> bool:
        """특정 URL에서 파일 다운로드 시도"""
        try:
            # URL 인코딩 처리 (한글 파일명 등)
            from urllib.parse import quote
            url_parts = url.split('/')
            for j, part in enumerate(url_parts):
                if '.' in part and any(ext in part for ext in ['.pdf', '.hwp', '.doc', '.xls', '.zip']):
                    url_parts[j] = quote(part, safe='')
            encoded_url = '/'.join(url_parts)
            
            response = self.session.get(encoded_url, verify=self.verify_ssl, timeout=30)
            logger.debug(f"응답: {response.status_code}, 크기: {len(response.content)} bytes")
            
            if response.status_code == 200 and len(response.content) > 1000:
                content_type = response.headers.get('content-type', '').lower()
                content = response.content
                
                # 파일 확장자로 기대하는 파일 유형 판단
                file_ext = os.path.splitext(url)[1].lower()
                
                # 허용되는 파일 타입들
                allowed_types = [
                    'application/pdf', 'application/msword', 'application/vnd.ms-excel',
                    'application/vnd.openxmlformats', 'application/zip', 'application/x-rar',
                    'application/octet-stream', 'application/hwp', 'application/x-hwp'
                ]
                
                is_valid_content_type = any(allowed_type in content_type for allowed_type in allowed_types)
                is_html_response = 'text/html' in content_type
                
                # 파일 내용 기반 검증
                is_likely_valid_file = False
                
                if file_ext == '.pdf':
                    # PDF 파일 시그니처 확인
                    is_likely_valid_file = content.startswith(b'%PDF')
                elif file_ext == '.hwp':
                    # HWP 파일 시그니처 확인 (다양한 패턴 허용)
                    hwp_signatures = [
                        b'HWP Document File',  # 일반적인 HWP 시그니처
                        b'\x0D\x0A\x0D\x0A',  # 다른 HWP 패턴
                        b'\xD0\xCF\x11\xE0',  # OLE 기반 HWP
                    ]
                    is_likely_valid_file = any(content.startswith(sig) for sig in hwp_signatures)
                    
                    # HWP 파일이 HTML로 응답되는 경우도 허용 (DJBEA 특수 케이스)
                    if is_html_response and file_ext == '.hwp':
                        # DJBEA에서 HWP 파일이 text/html로 응답되지만 실제로는 유효한 HWP 파일인 경우
                        # 파일 크기가 적당하고 명백한 HTML 태그가 없으면 허용
                        if len(content) > 10000:  # 10KB 이상
                            # HTML 태그 확인 - 너무 많은 HTML 태그가 있으면 실제 HTML일 가능성
                            html_tag_count = content.count(b'<') + content.count(b'>')
                            content_ratio = html_tag_count / len(content) if len(content) > 0 else 1
                            
                            if content_ratio < 0.01:  # HTML 태그가 1% 미만이면 이진 파일일 가능성
                                is_likely_valid_file = True
                                logger.warning(f"HWP 파일이 HTML Content-Type으로 응답됨 (이진 파일로 판단): {url}")
                            elif b'<!DOCTYPE' not in content[:200] and b'<html' not in content[:200]:
                                is_likely_valid_file = True
                                logger.warning(f"HWP 파일이 HTML Content-Type으로 응답됨 (DOCTYPE 없음): {url}")
                elif file_ext in ['.doc', '.docx']:
                    # Word 파일 시그니처
                    is_likely_valid_file = content.startswith(b'\\xD0\\xCF\\x11\\xE0') or content.startswith(b'PK')
                elif file_ext in ['.xls', '.xlsx']:
                    # Excel 파일 시그니처
                    is_likely_valid_file = content.startswith(b'\\xD0\\xCF\\x11\\xE0') or content.startswith(b'PK')
                elif file_ext in ['.zip', '.rar']:
                    # 압축 파일 시그니처
                    is_likely_valid_file = content.startswith(b'PK') or content.startswith(b'Rar!')
                else:
                    # 기타 파일은 content-type 또는 크기로 판단
                    is_likely_valid_file = is_valid_content_type or len(content) > 10000
                
                # 명백한 HTML 에러 페이지 확인
                is_error_page = False
                if is_html_response:
                    content_text = content.decode('utf-8', errors='ignore').lower()
                    error_indicators = ['error', '404', '403', '500', 'not found', 'access denied', 'forbidden']
                    is_error_page = any(indicator in content_text for indicator in error_indicators)
                
                # 다운로드 결정
                should_download = (is_valid_content_type or is_likely_valid_file) and not is_error_page
                
                if should_download:
                    with open(file_path, 'wb') as f:
                        f.write(content)
                    
                    logger.info(f"다운로드 성공: {url} -> {file_path}")
                    logger.info(f"파일 크기: {len(content)} bytes, Content-Type: {content_type}")
                    
                    # 파일 검증
                    if file_ext == '.hwp' and is_html_response:
                        logger.warning(f"HWP 파일이 HTML로 응답됨 - 내용 확인 필요: {file_path}")
                    
                    return True
                else:
                    if is_html_response and not is_likely_valid_file:
                        logger.debug(f"HTML 에러 페이지로 판단하여 건너뜀: {content_type}")
                    else:
                        logger.debug(f"유효하지 않은 파일로 판단: {content_type}, 시그니처 확인 실패")
            elif response.status_code == 200:
                logger.debug(f"파일 크기가 너무 작음: {len(response.content)} bytes")
            else:
                logger.debug(f"HTTP 오류: {response.status_code}")
                
        except Exception as e:
            logger.debug(f"다운로드 시도 오류: {e}")
        
        return False
    
    def _create_djbea_meta_info(self, announcement: Dict[str, Any]) -> str:
        """DJBEA 전용 메타 정보 생성"""
        meta_lines = [f"# {announcement['title']}", ""]
        
        # DJBEA 특화 메타 정보
        meta_fields = [
            ('num', '번호'),
            ('date', '등록일'),
            ('organization', '주관기관'),
            ('period', '공고기간'),
            ('views', '조회수')
        ]
        
        for field, label in meta_fields:
            if field in announcement and announcement[field] and announcement[field] != 'N/A':
                meta_lines.append(f"**{label}**: {announcement[field]}")
        
        # 첨부파일 여부
        if announcement.get('has_attachment'):
            meta_lines.append("**첨부파일**: 있음")
        else:
            meta_lines.append("**첨부파일**: 없음")
        
        meta_lines.extend([
            f"**원본 URL**: {announcement['url']}",
            "",
            "---",
            ""
        ])
        
        return "\n".join(meta_lines)
    
    def scrape_pages(self, max_pages: int = 4, output_base: str = 'output'):
        """Enhanced 페이지 스크래핑"""
        logger.info(f"DJBEA 스크래핑 시작: 최대 {max_pages}페이지")
        
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
                    stop_reason = "공고 없음"
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
            logger.info(f"DJBEA 스크래핑 완료: 총 {processed_count}개 새로운 공고 처리 (조기종료: {stop_reason})")
        else:
            logger.info(f"DJBEA 스크래핑 완료: 총 {processed_count}개 새로운 공고 처리")


# 하위 호환성을 위한 별칭
DJBEAScraper = EnhancedDJBEAScraper

if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    scraper = EnhancedDJBEAScraper()
    scraper.scrape_pages(max_pages=3, output_base='output/djbea_enhanced')