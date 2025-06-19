# -*- coding: utf-8 -*-
"""
전북특별자치도경제통상진흥원(JBBA) Enhanced 스크래퍼 - 표준 HTML 테이블 기반
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

class EnhancedJBBAScraper(StandardTableScraper):
    """전북특별자치도경제통상진흥원(JBBA) 전용 스크래퍼 - 향상된 버전"""
    
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
        self.base_url = "https://www.jbba.kr"
        self.list_url = "https://www.jbba.kr/bbs/board.php?bo_table=sub01_09"
        
        # 사이트 특화 설정
        self.verify_ssl = True  # HTTPS 사이트
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - GET 파라미터 방식"""
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&page={page_num}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - JBBA 사이트 특화"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # JBBA 사이트 테이블 구조 분석
        # 공고 목록이 테이블 형태로 되어 있음
        table = soup.find('table')
        if not table:
            logger.warning("테이블을 찾을 수 없습니다")
            return announcements
        
        tbody = table.find('tbody')
        if not tbody:
            # tbody가 없는 경우 table에서 직접 tr 찾기
            tbody = table
        
        rows = tbody.find_all('tr')
        logger.info(f"JBBA 테이블에서 {len(rows)}개 행 발견")
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 4:  # 번호, 사업명, 접수일, 담당자
                    continue
                
                # 사업명 셀에서 링크 찾기 (두 번째 셀)
                title_cell = cells[1]
                link_elem = title_cell.find('a')
                
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
                
                # 추가 메타 정보 추출
                self._extract_meta_info(cells, announcement)
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱: {title[:50]}...")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 JBBA 공고 파싱 완료")
        return announcements
    
    def _extract_meta_info(self, cells: list, announcement: Dict[str, Any]):
        """추가 메타 정보 추출"""
        try:
            # 번호 (첫 번째 셀)
            if len(cells) > 0:
                number_text = cells[0].get_text(strip=True)
                if number_text.isdigit():
                    announcement['number'] = number_text
            
            # 접수일 (세 번째 셀)
            if len(cells) > 2:
                date_text = cells[2].get_text(strip=True)
                announcement['date'] = date_text
            
            # 담당자 (네 번째 셀)
            if len(cells) > 3:
                contact_text = cells[3].get_text(strip=True)
                announcement['contact'] = contact_text
            
            # 사업명에서 상태 정보 추출 (D-XX, 마감 등)
            title_cell = cells[1]
            full_text = title_cell.get_text(strip=True)
            
            # 상태 정보 패턴 매칭 (D-11, D-8, 마감 등)
            status_patterns = [
                r'(D-\d+)',     # D-11, D-8 등
                r'(마감)',       # 마감
                r'(진행중)',     # 진행중
                r'(종료)'        # 종료
            ]
            
            for pattern in status_patterns:
                match = re.search(pattern, full_text)
                if match:
                    announcement['status'] = match.group(1)
                    break
                    
        except Exception as e:
            logger.debug(f"메타 정보 추출 중 오류: {e}")
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        result = {
            'content': '',
            'attachments': []
        }
        
        try:
            # 페이지 제목
            page_title = soup.find('title')
            title_text = page_title.get_text() if page_title else ''
            
            # 본문 내용 추출
            content_text = self._extract_content(soup, title_text)
            result['content'] = content_text
            
            # 첨부파일 추출
            attachments = self._extract_attachments(soup)
            result['attachments'] = attachments
            
            logger.info(f"JBBA 상세 페이지 파싱 완료 - 내용: {len(content_text)}자, 첨부파일: {len(attachments)}개")
            
        except Exception as e:
            logger.error(f"JBBA 상세 페이지 파싱 실패: {e}")
        
        return result
    
    def _extract_content(self, soup: BeautifulSoup, title_text: str) -> str:
        """본문 내용 추출"""
        content_parts = []
        
        # 제목 추가
        if title_text:
            clean_title = title_text.replace('::전북특별자치도경제통상진흥원::', '').strip()
            if clean_title:
                content_parts.append(f"# {clean_title}\n")
        
        # JBBA 사이트 특화 콘텐츠 추출
        # 1. 세부정보 테이블 추출
        detail_info = self._extract_detail_info(soup)
        if detail_info:
            content_parts.extend(detail_info)
        
        # 2. 메인 콘텐츠 영역 찾기
        content_selectors = [
            'article',
            '.board_view_content',
            '.view_content',
            '.content',
            '#content'
        ]
        
        main_content = None
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        if main_content:
            # HTML을 마크다운으로 변환
            content_html = str(main_content)
            markdown_content = self.h.handle(content_html)
            content_parts.append(markdown_content)
        else:
            # 폴백: 전체 페이지에서 의미있는 텍스트 추출
            logger.debug("메인 콘텐츠 영역을 찾을 수 없어 전체 페이지에서 추출")
            
            # 네비게이션 및 불필요한 요소 제거
            for tag in soup.find_all(['script', 'style', 'nav', 'header', 'footer']):
                tag.decompose()
            
            # 본문 영역 추출
            body_content = soup.find('body')
            if body_content:
                # 의미있는 텍스트 블록 찾기
                text_blocks = []
                for p in body_content.find_all(['p', 'div']):
                    text = p.get_text(strip=True)
                    if text and len(text) > 20:
                        text_blocks.append(text)
                
                if text_blocks:
                    content_parts.extend(text_blocks[:10])  # 상위 10개 블록만
        
        return '\n\n'.join(content_parts)
    
    def _extract_detail_info(self, soup: BeautifulSoup) -> List[str]:
        """세부정보 테이블 추출"""
        detail_info = []
        
        # 테이블에서 구조화된 정보 추출
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['th', 'td'])
                if len(cells) == 2:
                    header = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    
                    # 중요한 정보만 추출
                    important_fields = [
                        '지원분야', '지원대상', '접수일정', '공고일정', 
                        '담당부서', '담당자', '전화번호', '공고번호',
                        '사업내용', '지원내용', '신청방법', '선정기준'
                    ]
                    
                    if any(field in header for field in important_fields):
                        detail_info.append(f"**{header}**: {value}")
        
        return detail_info
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """첨부파일 추출"""
        attachments = []
        
        # JBBA 사이트 첨부파일 패턴 분석
        # 첨부파일 섹션 찾기
        attachment_sections = [
            soup.find('div', class_=re.compile(r'첨부')),
            soup.find('div', string=re.compile(r'첨부파일')),
            soup.find('h2', string=re.compile(r'첨부파일'))
        ]
        
        for section in attachment_sections:
            if section:
                # 섹션 근처의 링크들 찾기
                container = section.find_parent() or section
                links = container.find_all('a', href=re.compile(r'download\.php'))
                
                for link in links:
                    try:
                        href = link.get('href', '')
                        
                        # 파일명 추출 (링크 텍스트에서)
                        file_name = link.get_text(strip=True)
                        
                        # 파일 크기 정보 제거 (예: "파일명.pdf (217.5K)" -> "파일명.pdf")
                        if '(' in file_name and ')' in file_name:
                            file_name = re.sub(r'\s*\([^)]+\)\s*$', '', file_name)
                        
                        # 파일 확장자 확인
                        if file_name and any(ext in file_name.lower() for ext in ['.pdf', '.hwp', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.ppt', '.pptx', '.jpg', '.png']):
                            file_url = urljoin(self.base_url, href)
                            
                            attachment = {
                                'name': file_name,
                                'url': file_url
                            }
                            attachments.append(attachment)
                            logger.debug(f"첨부파일 발견: {file_name}")
                    
                    except Exception as e:
                        logger.debug(f"첨부파일 링크 처리 중 오류: {e}")
                        continue
                
                # 첫 번째 유효한 섹션에서 찾았으면 중단
                if attachments:
                    break
        
        # 대안 방법: 전체 페이지에서 download.php 링크 찾기
        if not attachments:
            all_download_links = soup.find_all('a', href=re.compile(r'download\.php'))
            for link in all_download_links:
                try:
                    href = link.get('href', '')
                    file_name = link.get_text(strip=True)
                    
                    # 파일 크기 정보 제거
                    if '(' in file_name and ')' in file_name:
                        file_name = re.sub(r'\s*\([^)]+\)\s*$', '', file_name)
                    
                    if file_name and any(ext in file_name.lower() for ext in ['.pdf', '.hwp', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.ppt', '.pptx']):
                        file_url = urljoin(self.base_url, href)
                        
                        attachment = {
                            'name': file_name,
                            'url': file_url
                        }
                        attachments.append(attachment)
                        logger.debug(f"첨부파일 발견 (대안방법): {file_name}")
                
                except Exception as e:
                    logger.debug(f"첨부파일 링크 처리 중 오류: {e}")
                    continue
        
        logger.info(f"{len(attachments)}개 첨부파일 발견")
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment_info: Dict[str, Any] = None) -> bool:
        """파일 다운로드 - JBBA 사이트 특화"""
        try:
            logger.info(f"파일 다운로드 시작: {url}")
            
            # 다운로드 헤더 설정
            download_headers = self.headers.copy()
            download_headers['Referer'] = self.list_url
            
            response = self.session.get(
                url, 
                headers=download_headers, 
                stream=True, 
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            
            # 실제 파일명 추출 (Content-Disposition 헤더에서)
            actual_filename = self._extract_filename_from_response(response, save_path)
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
    
    def _extract_filename_from_response(self, response: requests.Response, default_path: str) -> str:
        """응답에서 실제 파일명 추출 - 한글 파일명 처리 개선"""
        content_disposition = response.headers.get('Content-Disposition', '')
        
        if content_disposition:
            # RFC 5987 형식 우선 시도 (filename*=UTF-8''filename.ext)
            rfc5987_match = re.search(r"filename\*=([^']*)'([^']*)'(.+)", content_disposition)
            if rfc5987_match:
                encoding = rfc5987_match.group(1) or 'utf-8'
                filename = rfc5987_match.group(3)
                try:
                    filename = unquote(filename, encoding=encoding)
                    save_dir = os.path.dirname(default_path)
                    return os.path.join(save_dir, self.sanitize_filename(filename))
                except:
                    pass
            
            # 일반적인 filename 파라미터 시도
            filename_match = re.search(r'filename[^;=\n]*=(([\'"]).*?\2|[^;\n]*)', content_disposition)
            if filename_match:
                filename = filename_match.group(1).strip('"\' ')
                
                # 다양한 인코딩 시도: UTF-8, EUC-KR, CP949
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


# 하위 호환성을 위한 별칭
JBBAScraper = EnhancedJBBAScraper