# -*- coding: utf-8 -*-
"""
경북바이오산업연구원(GIB) 스크래퍼 - Enhanced 버전
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

class EnhancedGIBScraper(StandardTableScraper):
    """경북바이오산업연구원(GIB) 스크래퍼 - Enhanced 버전"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://gib.re.kr"
        self.list_url = "https://gib.re.kr/module/bbs/list.php?mid=/news/notice"
        
        # GIB 사이트 특성상 추가 헤더 설정
        self.gib_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # 세션 헤더 업데이트
        self.session.headers.update(self.gib_headers)
    
    def get_list_url(self, page_num: int) -> str:
        """페이지 번호에 따른 목록 URL 반환"""
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&page={page_num}"
    
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
        table = soup.find('table')
        if not table:
            return announcements
        
        # tbody 또는 테이블의 모든 tr 찾기
        tbody = table.find('tbody')
        if tbody:
            rows = tbody.find_all('tr')
        else:
            rows = table.find_all('tr')[1:]  # 헤더 제외
        
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
        """테이블 행 파싱 - GIB 특화"""
        cells = row.find_all('td')
        if len(cells) < 6:  # 순번, 상태, 제목, 파일, 글쓴이, 날짜, 조회
            return None
        
        # 제목 셀에서 링크 찾기 (일반적으로 3번째 셀)
        title_cell = cells[2]  # 제목 셀
        link_elem = title_cell.find('a')
        
        detail_url = None
        
        if not link_elem:
            # JavaScript 함수 호출 방식 확인
            onclick = title_cell.get('onclick', '')
            if not onclick:
                # 부모 tr에서 onclick 확인
                onclick = row.get('onclick', '')
            
            if onclick:
                detail_url = self._extract_goview_url(onclick)
            else:
                return None
        else:
            # 직접 링크가 있는 경우
            href = link_elem.get('href', '')
            onclick = link_elem.get('onclick', '')
            
            if href.startswith('javascript:') or onclick:
                # href나 onclick에서 goView 파라미터 추출
                js_code = href if href.startswith('javascript:') else onclick
                detail_url = self._extract_goview_url(js_code)
            elif href.startswith('http'):
                detail_url = href
            elif href.startswith('/'):
                detail_url = self.base_url + href
            elif href.startswith('?'):
                detail_url = self.base_url + "/module/bbs/view.php" + href
            else:
                detail_url = urljoin(self.base_url, href)
        
        if not detail_url:
            return None
        
        # 제목 추출
        title = title_cell.get_text(strip=True)
        # 파일 아이콘 등 제거
        title = re.sub(r'\s*첨부파일\s*있음\s*', '', title)
        
        # 메타데이터 추출
        meta_info = {}
        
        # 상태 (2번째 셀)
        if len(cells) > 1:
            meta_info['status'] = cells[1].get_text(strip=True)
        
        # 글쓴이 (5번째 셀)
        if len(cells) > 4:
            meta_info['writer'] = cells[4].get_text(strip=True)
        
        # 날짜 (6번째 셀)
        if len(cells) > 5:
            meta_info['date'] = cells[5].get_text(strip=True)
        
        # 조회수 (7번째 셀)
        if len(cells) > 6:
            meta_info['views'] = cells[6].get_text(strip=True)
        
        # 첨부파일 여부 확인 (4번째 셀 또는 제목에서)
        has_attachment = '첨부파일 있음' in row.get_text()
        
        return {
            'num': row_index + 1,
            'title': title,
            'url': detail_url,
            'has_attachment': has_attachment,
            'organization': '경북바이오산업연구원',
            **meta_info
        }
    
    def _extract_goview_url(self, js_code: str) -> Optional[str]:
        """goView JavaScript 함수에서 URL 추출"""
        # goView(cur_row, rdno, rdnoorg) 패턴에서 파라미터 추출
        goview_match = re.search(r'goView\((\d+),\s*(\d+),\s*(\d+)\)', js_code)
        if goview_match:
            cur_row = goview_match.group(1)
            rdno = goview_match.group(2)
            rdnoorg = goview_match.group(3)
            return f"{self.base_url}/module/bbs/view.php?mid=/news/notice&cur_row={cur_row}&rdno={rdno}&rdnoorg={rdnoorg}"
        
        logger.debug(f"goView 파라미터 추출 실패: {js_code}")
        return None
    
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
        
        if href.startswith('javascript:') or onclick:
            js_code = href if href.startswith('javascript:') else onclick
            detail_url = self._extract_goview_url(js_code)
        else:
            detail_url = urljoin(self.base_url, href)
        
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
            'organization': '경북바이오산업연구원',
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
            'organization': '경북바이오산업연구원'
        }
    
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
            
            # 첨부파일 추출
            attachments = self._extract_detail_attachments(soup)
            result['attachments'] = attachments
            
            logger.debug(f"상세 페이지 파싱 완료 - 내용: {len(content)}자, 첨부파일: {len(attachments)}개")
            
        except Exception as e:
            logger.error(f"상세 페이지 파싱 중 오류: {e}")
        
        return result
    
    def _extract_detail_content(self, soup: BeautifulSoup) -> str:
        """상세 페이지 본문 추출"""
        content_md = ""
        
        # GIB 특화 본문 선택자들
        content_selectors = [
            'div.bbs_content',
            'div.bbs_B_content',
            'div.board_view_content',
            'div.view_content',
            'div.content',
            'td.content',
            'div#content',
            '.article_content',
            '.post_content',
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
        
        # 본문 내용 변환
        if content_area:
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
    
    def _extract_detail_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """상세 페이지 첨부파일 추출 - GIB 특화"""
        attachments = []
        
        # 전략 1: GIB downloadAttFile 함수 찾기
        gib_attachments = self._extract_gib_download_files(soup)
        if gib_attachments:
            attachments.extend(gib_attachments)
            logger.debug(f"GIB downloadAttFile에서 {len(gib_attachments)}개 첨부파일 발견")
        
        # 전략 2: 첨부파일 영역에서 추출
        attachment_areas = soup.find_all(['div'], class_=['div_attf_view_list', 'div_attf_view'])
        for area in attachment_areas:
            area_files = self._extract_from_attachment_area(area)
            if area_files:
                attachments.extend(area_files)
                logger.debug(f"첨부파일 영역에서 {len(area_files)}개 첨부파일 발견")
        
        # 전략 3: 일반적인 다운로드 링크
        download_links = soup.find_all('a', href=re.compile(r'download|file|attach', re.I))
        for link in download_links:
            attachment = self._extract_from_download_link(link)
            if attachment:
                attachments.append(attachment)
        
        # 전략 4: 파일 확장자를 가진 모든 링크
        file_links = soup.find_all('a', href=re.compile(r'\.(pdf|hwp|doc|docx|xls|xlsx|zip|rar|ppt|pptx)', re.I))
        for link in file_links:
            attachment = self._extract_from_file_link(link)
            if attachment:
                attachments.append(attachment)
        
        # 중복 제거
        seen = set()
        unique_attachments = []
        for att in attachments:
            key = (att['name'], att.get('url', ''))
            if key not in seen:
                seen.add(key)
                unique_attachments.append(att)
        
        logger.debug(f"첨부파일 추출 완료: {len(unique_attachments)}개")
        return unique_attachments
    
    def _extract_gib_download_files(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """GIB downloadAttFile 함수 호출에서 첨부파일 추출"""
        attachments = []
        
        # downloadAttFile 함수 호출 찾기 (a 태그와 span 태그 모두 확인)
        download_links = soup.find_all(lambda tag: tag.get('onclick') and 'downloadAttFile' in tag.get('onclick', ''))
        
        for link in download_links:
            onclick = link.get('onclick', '')
            # downloadAttFile('md_bbs', '1', '5653', '1') 패턴에서 파라미터 추출
            match = re.search(r"downloadAttFile\(\s*['\"]([^'\"]*)['\"],\s*['\"]([^'\"]*)['\"],\s*['\"]([^'\"]*)['\"],\s*['\"]([^'\"]*)['\"]", onclick)
            if match:
                attf_flag = match.group(1)  # 'md_bbs'
                seno = match.group(2)       # board number
                atnum = match.group(3)      # record number
                atpath = match.group(4)     # attachment sequence
                
                file_name = link.get_text(strip=True)
                if not file_name:
                    file_name = f"attachment_{atpath}"
                
                # GIB 특별한 다운로드 정보 구성
                download_info = {
                    'name': file_name,
                    'url': 'gib_download',  # 특별한 표시
                    'attf_flag': attf_flag,
                    'seno': seno,
                    'atnum': atnum,
                    'atpath': atpath,
                    'gib_download': True
                }
                
                attachments.append(download_info)
                logger.debug(f"GIB 첨부파일 발견: {file_name} (params: {attf_flag}, {seno}, {atnum}, {atpath})")
        
        return attachments
    
    def _extract_from_attachment_area(self, area) -> List[Dict[str, Any]]:
        """첨부파일 영역에서 파일 추출"""
        attachments = []
        
        # 영역 내의 모든 링크 확인
        links = area.find_all('a')
        for link in links:
            href = link.get('href', '')
            onclick = link.get('onclick', '')
            file_name = link.get_text(strip=True)
            
            if onclick and 'downloadAttFile' in onclick:
                # GIB 특화 다운로드 함수
                attachment = self._extract_gib_download_files_single(link)
                if attachment:
                    attachments.append(attachment)
            elif href and any(ext in href.lower() for ext in ['.pdf', '.hwp', '.doc', '.xls', '.zip']):
                # 직접 다운로드 링크
                file_url = urljoin(self.base_url, href)
                if file_name:
                    attachments.append({
                        'name': file_name,
                        'url': file_url
                    })
        
        return attachments
    
    def _extract_gib_download_files_single(self, link) -> Optional[Dict[str, Any]]:
        """단일 링크에서 GIB 다운로드 정보 추출"""
        onclick = link.get('onclick', '')
        match = re.search(r"downloadAttFile\(\s*['\"]([^'\"]*)['\"],\s*['\"]([^'\"]*)['\"],\s*['\"]([^'\"]*)['\"],\s*['\"]([^'\"]*)['\"]", onclick)
        if match:
            file_name = link.get_text(strip=True)
            if not file_name:
                file_name = f"attachment_{match.group(4)}"
            
            return {
                'name': file_name,
                'url': 'gib_download',
                'attf_flag': match.group(1),
                'seno': match.group(2),
                'atnum': match.group(3),
                'atpath': match.group(4),
                'gib_download': True
            }
        return None
    
    def _extract_from_download_link(self, link) -> Optional[Dict[str, Any]]:
        """일반 다운로드 링크에서 첨부파일 추출"""
        href = link.get('href', '')
        onclick = link.get('onclick', '')
        file_name = link.get_text(strip=True)
        
        if onclick:
            # JavaScript 다운로드 함수
            file_id_match = re.search(r'[\'"]([^\'",]+)[\'"]', onclick)
            if file_id_match:
                file_id = file_id_match.group(1)
                file_url = f"{self.base_url}/module/bbs/download.php?file_id={file_id}"
                if not file_name:
                    file_name = f"file_{file_id}"
                
                return {
                    'name': file_name,
                    'url': file_url
                }
        elif href:
            file_url = urljoin(self.base_url, href)
            if not file_name:
                file_name = href.split('/')[-1]
            
            return {
                'name': file_name,
                'url': file_url
            }
        
        return None
    
    def _extract_from_file_link(self, link) -> Optional[Dict[str, Any]]:
        """파일 링크에서 첨부파일 추출"""
        href = link.get('href', '')
        file_name = link.get_text(strip=True) or href.split('/')[-1]
        
        if href:
            file_url = urljoin(self.base_url, href)
            return {
                'name': file_name,
                'url': file_url
            }
        
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
        meta_info = self._create_gib_meta_info(announcement)
        
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
        """GIB 전용 첨부파일 다운로드 오버라이드"""
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
                
                # GIB 전용 다운로드 시도
                success = self._download_gib_file(attachment, file_path)
                
                if not success:
                    logger.warning(f"첨부파일 다운로드 실패: {attachment['name']}")
                
            except Exception as e:
                logger.error(f"첨부파일 처리 중 오류: {e}")
    
    def _download_gib_file(self, attachment: Dict[str, Any], file_path: str) -> bool:
        """GIB 전용 파일 다운로드 메서드"""
        try:
            if attachment.get('gib_download') and attachment.get('url') == 'gib_download':
                # GIB 특화 2단계 다운로드 처리
                return self._download_gib_special_file(attachment, file_path)
            else:
                # 일반 다운로드
                url = attachment.get('url', '')
                if url and url != 'gib_download':
                    return self.download_file_with_session(url, file_path)
                else:
                    logger.warning(f"유효하지 않은 다운로드 URL: {attachment}")
                    return False
                
        except Exception as e:
            logger.error(f"GIB 파일 다운로드 오류: {e}")
            return False
    
    def _download_gib_special_file(self, attachment_info: Dict[str, Any], save_path: str) -> bool:
        """GIB 첨부파일 다운로드 (2단계 과정)"""
        try:
            logger.debug(f"GIB 특별 다운로드: {attachment_info['name']}")
            
            # 1단계: download.php로 POST 요청
            download_url = f"{self.base_url}/lib/php/pub/download.php"
            
            # POST 데이터 구성
            post_data = {
                'attf_flag': attachment_info['attf_flag'],
                'seno': attachment_info['seno'],
                'atnum': attachment_info['atnum'],
                'atpath': attachment_info['atpath']
            }
            
            # 헤더 설정
            headers = self.gib_headers.copy()
            headers.update({
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': self.base_url + '/module/bbs/view.php'
            })
            
            # 1단계 요청
            response = self.session.post(download_url, data=post_data, headers=headers, verify=self.verify_ssl, timeout=self.timeout)
            
            if response.status_code != 200:
                logger.warning(f"1단계 요청 실패: {response.status_code}")
                return False
            
            # 2단계: download_open.php로 자동 리다이렉트 또는 직접 호출
            download_open_url = f"{self.base_url}/lib/php/pub/download_open.php"
            
            # 2단계 요청 (같은 데이터로)
            response = self.session.post(download_open_url, data=post_data, headers=headers, stream=True, verify=self.verify_ssl, timeout=self.timeout)
            
            if response.status_code != 200:
                logger.warning(f"2단계 요청 실패: {response.status_code}")
                return False
            
            # Content-Disposition 헤더에서 실제 파일명 추출
            content_disposition = response.headers.get('Content-Disposition', '')
            if content_disposition:
                filename = self._extract_filename_from_header(content_disposition)
                if filename:
                    # 파일명이 유효하면 save_path 업데이트
                    save_dir = os.path.dirname(save_path)
                    save_path = os.path.join(save_dir, self.sanitize_filename(filename))
            
            # 파일 저장
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(save_path)
            logger.info(f"다운로드 성공: {save_path} ({file_size:,} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"GIB 특별 파일 다운로드 오류: {e}")
            return False
    
    def _extract_filename_from_header(self, content_disposition: str) -> Optional[str]:
        """Content-Disposition 헤더에서 파일명 추출"""
        import re
        
        # RFC 5987 형식: filename*=UTF-8''filename
        rfc5987_match = re.search(r"filename\*=([^']*)'([^']*)'([^;]+)", content_disposition)
        if rfc5987_match:
            encoding = rfc5987_match.group(1) or 'utf-8'
            filename = rfc5987_match.group(3)
            try:
                from urllib.parse import unquote
                filename = unquote(filename, encoding=encoding)
                return filename
            except:
                pass
        
        # 일반 형식: filename="filename" 또는 filename=filename
        filename_match = re.search(r'filename[^;=\n]*=(([\'"]).*?\2|[^;\n]*)', content_disposition)
        if filename_match:
            filename = filename_match.group(1).strip('"\'')
            # 인코딩 문제 해결 시도
            try:
                filename = filename.encode('latin-1').decode('utf-8')
            except:
                try:
                    filename = filename.encode('latin-1').decode('euc-kr')
                except:
                    pass
            
            # + 문자를 공백으로 변환
            filename = filename.replace('+', ' ')
            return filename
        
        return None
    
    def _create_gib_meta_info(self, announcement: Dict[str, Any]) -> str:
        """GIB 전용 메타 정보 생성"""
        meta_lines = [f"# {announcement['title']}", ""]
        
        # GIB 특화 메타 정보
        meta_fields = [
            ('num', '번호'),
            ('status', '상태'),
            ('writer', '작성자'),
            ('date', '작성일'),
            ('views', '조회수'),
            ('organization', '주관기관')
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
        logger.info(f"GIB 스크래핑 시작: 최대 {max_pages}페이지")
        
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
            logger.info(f"GIB 스크래핑 완료: 총 {processed_count}개 새로운 공고 처리 (조기종료: {stop_reason})")
        else:
            logger.info(f"GIB 스크래핑 완료: 총 {processed_count}개 새로운 공고 처리")


# 하위 호환성을 위한 별칭
GIBScraper = EnhancedGIBScraper

if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    scraper = EnhancedGIBScraper()
    scraper.scrape_pages(max_pages=3, output_base='output/gib_enhanced')