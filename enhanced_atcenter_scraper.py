# -*- coding: utf-8 -*-
"""
ATCENTER (농업기술실용화재단) 전용 Enhanced 스크래퍼
사이트: https://www.at.or.kr/article/apko364000/list.action
특징: 표준 HTML 테이블, GET 파라미터 페이지네이션, User-Agent 검증
"""

from enhanced_base_scraper import StandardTableScraper
from bs4 import BeautifulSoup
import requests
import os
import re
import time
import logging
from urllib.parse import urljoin, urlparse, parse_qs
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class EnhancedAtcenterScraper(StandardTableScraper):
    """ATCENTER 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (fallback용)
        self.base_url = "https://www.at.or.kr"
        self.list_url = "https://www.at.or.kr/article/apko364000/list.action"
        
        # 사이트 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        
        # ATCENTER 특화 헤더 (User-Agent 검증 우회)
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none'
        })
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - GET 파라미터 기반"""
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: ATCENTER는 at.condition.currentPage 파라미터 사용
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}?at.condition.currentPage={page_num}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - 테이블 기반"""
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """ATCENTER 특화 목록 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 공지사항 목록 테이블 찾기
        table = soup.find('table')
        if not table:
            logger.warning("공고 목록 테이블을 찾을 수 없습니다")
            return announcements
        
        # caption으로 올바른 테이블 확인
        caption = table.find('caption')
        if caption and '공지사항 목록' not in caption.get_text():
            logger.warning("공지사항 목록 테이블이 아닙니다")
            return announcements
        
        # tbody 또는 table에서 행 찾기
        tbody = table.find('tbody') or table
        rows = tbody.find_all('tr')
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for row in rows:
            try:
                # th와 td를 모두 고려
                cells = row.find_all(['th', 'td'])
                if len(cells) < 5:  # 실제로는 5개 컬럼: [번호(th)] [제목(td)] [부서명(td)] [파일(td)] [조회수(td)] [작성일(td)]
                    continue
                
                # ATCENTER 실제 테이블 구조 확인
                # 첫 번째가 th(번호), 나머지가 td
                if len(cells) == 6:
                    # 6개 컬럼인 경우: [번호] [제목] [부서명] [파일] [조회수] [작성일]
                    num_cell = cells[0]      # 번호 (th)
                    title_cell = cells[1]    # 제목 (td)
                    dept_cell = cells[2]     # 부서명 (td)
                    file_cell = cells[3]     # 파일 (td)
                    view_cell = cells[4]     # 조회수 (td)
                    date_cell = cells[5]     # 작성일 (td)
                elif len(cells) == 5:
                    # 5개 컬럼인 경우: [제목] [부서명] [파일] [조회수] [작성일]
                    num_cell = None
                    title_cell = cells[0]    # 제목 (첫 번째 컬럼)
                    dept_cell = cells[1]     # 부서명
                    file_cell = cells[2]     # 파일
                    view_cell = cells[3]     # 조회수
                    date_cell = cells[4]     # 작성일
                else:
                    continue
                
                # 제목 및 상세 페이지 링크 추출
                link_elem = title_cell.find('a')
                if not link_elem:
                    logger.debug("링크를 찾을 수 없는 행 건너뛰기")
                    continue
                
                title = link_elem.get_text(strip=True)
                href = link_elem.get('href', '')
                
                if not title or not href:
                    continue
                
                # 상세 페이지 URL 구성
                if href.startswith('/'):
                    detail_url = urljoin(self.base_url, href)
                elif href.startswith('view.action'):
                    detail_url = f"{self.base_url}/article/apko364000/{href}"
                else:
                    detail_url = urljoin(self.base_url, href)
                
                # 기타 정보 추출
                num = num_cell.get_text(strip=True) if num_cell else ''
                department = dept_cell.get_text(strip=True)
                views = view_cell.get_text(strip=True)
                date = date_cell.get_text(strip=True)
                
                # 첨부파일 여부 확인
                has_attachment = bool(file_cell.find('a'))
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'num': num,
                    'department': department,
                    'views': views,
                    'date': date,
                    'has_attachment': has_attachment,
                    'original_atcenter_url': self.list_url
                }
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱: {title[:50]}...")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱"""
        if self.config and self.config.selectors:
            return super().parse_detail_page(html_content)
        
        return self._parse_detail_fallback(html_content)
    
    def _parse_detail_fallback(self, html_content: str) -> Dict[str, Any]:
        """ATCENTER 특화 상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 영역 찾기
        content_area = None
        content_selectors = [
            '.board_view',
            '.view_content',
            '.detail_content',
            '.content_area',
            '#content',
            '.content'
        ]
        
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        if not content_area:
            # ATCENTER 특화: 전체 문서에서 본문 추정
            # 스크립트, 스타일, 네비게이션 등 제외하고 본문 텍스트가 많은 영역 찾기
            body = soup.find('body')
            if body:
                # 불필요한 요소들 제거
                for unwanted in body.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                    unwanted.decompose()
                
                # 충분한 텍스트가 있는 영역 찾기
                main_content = body.find('main') or body.find('article') or body
                content_area = main_content
                logger.debug("전체 본문 영역 사용")
        
        # 본문을 마크다운으로 변환
        if content_area:
            # 불필요한 요소 제거
            for unwanted in content_area.find_all(['script', 'style', 'nav', 'header', 'footer']):
                unwanted.decompose()
            
            content_html = str(content_area)
            content_markdown = self.h.handle(content_html)
        else:
            content_markdown = "본문을 찾을 수 없습니다."
            logger.warning("본문 영역을 찾을 수 없음")
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup)
        
        # 제목 추출 시도
        title = ""
        title_selectors = ['h1', 'h2', 'h3', '.title', '.subject', '.view_title']
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = title_elem.get_text(strip=True)
                if title:
                    break
        
        return {
            'title': title,
            'content': content_markdown,
            'attachments': attachments,
            'url': self.base_url
        }
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """첨부파일 추출 - ATCENTER 시스템 특화"""
        attachments = []
        
        try:
            # ATCENTER 특화 다운로드 링크 패턴
            # /download.action?attachId=XXXXX 형태
            download_links = soup.find_all('a', href=re.compile(r'/download\.action\?attachId='))
            
            for link in download_links:
                href = link.get('href', '')
                filename = link.get_text(strip=True)
                
                # 다운로드 URL 구성
                if href.startswith('/'):
                    file_url = urljoin(self.base_url, href)
                else:
                    file_url = href
                
                # 파일명이 비어있으면 URL에서 추출 시도
                if not filename:
                    if 'fileName=' in href:
                        # fileName 파라미터에서 추출
                        parsed = urlparse(href)
                        params = parse_qs(parsed.query)
                        if 'fileName' in params:
                            filename = params['fileName'][0]
                    
                    if not filename:
                        # attachId를 기반으로 임시 파일명 생성
                        attach_id_match = re.search(r'attachId=(\w+)', href)
                        if attach_id_match:
                            attach_id = attach_id_match.group(1)
                            filename = f"attachment_{attach_id}"
                        else:
                            filename = f"attachment_{len(attachments)+1}"
                
                if filename and len(filename.strip()) > 0:
                    attachments.append({
                        'name': filename,
                        'filename': filename,
                        'url': file_url,
                        'type': 'direct_link'
                    })
                    logger.debug(f"ATCENTER 첨부파일 발견: {filename}")
            
            # 추가 패턴: 일반적인 파일 링크들
            file_links = soup.find_all('a', href=re.compile(r'\.(pdf|hwp|hwpx|doc|docx|xls|xlsx|ppt|pptx|zip|jpg|jpeg|png|gif)$', re.IGNORECASE))
            
            seen_urls = set(att['url'] for att in attachments)
            for link in file_links:
                href = link.get('href', '')
                if href and href not in seen_urls:
                    file_url = urljoin(self.base_url, href)
                    filename = link.get_text(strip=True) or os.path.basename(href)
                    
                    if filename and len(filename) > 2:
                        attachments.append({
                            'name': filename,
                            'filename': filename,
                            'url': file_url,
                            'type': 'file_link'
                        })
                        seen_urls.add(href)
            
            logger.info(f"{len(attachments)}개 첨부파일 발견")
            for att in attachments:
                logger.debug(f"- {att['filename']} ({att.get('type', 'unknown')})")
            
        except Exception as e:
            logger.error(f"첨부파일 추출 중 오류: {e}")
        
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment: dict = None, **kwargs) -> bool:
        """첨부파일 다운로드 - ATCENTER 시스템 특화"""
        logger.info(f"파일 다운로드 시작: {attachment.get('filename', 'unknown') if attachment else 'unknown'}")
        
        try:
            # ATCENTER 파일 다운로드 헤더 설정
            download_headers = self.session.headers.copy()
            download_headers.update({
                'Referer': self.base_url,
                'Accept': 'application/pdf,application/zip,application/octet-stream,*/*',
            })
            
            response = self.session.get(
                url,
                headers=download_headers,
                timeout=self.timeout,
                verify=self.verify_ssl,
                stream=True
            )
            
            response.raise_for_status()
            
            # 스트리밍 다운로드
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(save_path)
            logger.info(f"다운로드 완료: {save_path} ({file_size:,} bytes)")
            
            return True
            
        except Exception as e:
            logger.error(f"파일 다운로드 실패: {e}")
            return False
    
    def _create_meta_info(self, announcement: Dict[str, Any]) -> str:
        """ATCENTER 특화 메타 정보 생성"""
        meta_lines = [f"# {announcement['title']}", ""]
        
        # ATCENTER 특화 메타 정보
        if announcement.get('num'):
            meta_lines.append(f"**번호**: {announcement['num']}")
        if announcement.get('department'):
            meta_lines.append(f"**부서명**: {announcement['department']}")
        if announcement.get('date'):
            meta_lines.append(f"**작성일**: {announcement['date']}")
        if announcement.get('views'):
            meta_lines.append(f"**조회수**: {announcement['views']}")
        
        meta_lines.extend([
            f"**원본 URL**: {announcement['url']}",
            f"**ATCENTER 목록 URL**: {announcement.get('original_atcenter_url', 'N/A')}",
            "",
            "---",
            ""
        ])
        
        return "\n".join(meta_lines)


# 하위 호환성을 위한 별칭
AtcenterScraper = EnhancedAtcenterScraper