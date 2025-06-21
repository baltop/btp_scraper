# -*- coding: utf-8 -*-
"""
전북특별자치도 사회적경제지원센터(JBSOS) Enhanced 스크래퍼 - 그누보드 리스트 기반
URL: https://www.jbsos.or.kr/bbs/board.php?bo_table=s_sub04_01
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

class EnhancedJBSOSScraper(StandardTableScraper):
    """전북특별자치도 사회적경제지원센터(JBSOS) 전용 스크래퍼 - 향상된 버전"""
    
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
        self.base_url = "https://www.jbsos.or.kr"
        self.list_url = "https://www.jbsos.or.kr/bbs/board.php?bo_table=s_sub04_01"
        
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
        """목록 페이지 파싱 - JBSOS 사이트 특화 (실제 HTML 구조 기반)"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 실제 JBSOS 사이트 HTML 구조 분석
        # 지원사업공고 목록은 <ul> 태그 내부의 <li> 요소들로 구성
        
        # 다양한 선택자로 목록 찾기
        list_selectors = [
            'ul li',  # 기본 리스트 구조
            '.board_list li',  # 게시판 리스트
            '.list_wrap li',  # 리스트 래퍼
            '.notice_list li',  # 공지사항 리스트
            'tbody tr',  # 테이블 구조 폴백
            'table tr'  # 테이블 구조 폴백
        ]
        
        items = []
        for selector in list_selectors:
            items = soup.select(selector)
            if len(items) > 3:  # 의미있는 항목 수가 있으면 사용
                logger.debug(f"JBSOS 목록을 {selector} 선택자로 찾음: {len(items)}개")
                break
        
        if not items:
            logger.warning("JBSOS 목록 항목을 찾을 수 없습니다")
            return announcements
        
        # 첫 번째 항목은 보통 헤더이므로 제외하고 파싱
        for item in items[1:]:
            try:
                # 링크 요소 찾기 (다양한 패턴)
                link_elem = item.find('a', href=True)
                if not link_elem:
                    continue
                
                # 제목 추출
                title = link_elem.get_text(strip=True)
                if not title or len(title) < 3:
                    continue
                
                # 상세 페이지 URL 구성
                href = link_elem.get('href', '')
                detail_url = urljoin(self.base_url, href)
                
                # 유효한 상세 페이지 URL인지 확인
                if 'wr_id=' not in detail_url:
                    continue
                
                announcement = {
                    'title': title,
                    'url': detail_url
                }
                
                # 추가 메타 정보 추출
                self._extract_meta_info_from_item(item, announcement)
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱: {title[:50]}...")
                
            except Exception as e:
                logger.error(f"항목 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 JBSOS 공고 파싱 완료")
        return announcements
    
    def _extract_meta_info_from_item(self, item, announcement: Dict[str, Any]):
        """리스트 항목에서 메타 정보 추출 - 실제 HTML 구조 기반"""
        try:
            # 텍스트 노드들을 순서대로 추출
            text_nodes = [node.strip() for node in item.stripped_strings if node.strip()]
            
            # 공지사항 여부 확인 - strong 태그나 '공지' 텍스트 포함 여부
            if item.find('strong') or any('공지' in text for text in text_nodes):
                announcement['is_notice'] = True
                announcement['status'] = '공지'
            else:
                announcement['is_notice'] = False
            
            # 텍스트 노드에서 패턴 매칭으로 정보 추출
            for text in text_nodes:
                # 날짜 패턴 (예: "25-04-23", "2025-04-23")
                date_pattern = r'\d{2,4}-\d{1,2}-\d{1,2}'
                if re.match(date_pattern, text):
                    announcement['date'] = text
                
                # 조회수 패턴 (예: "1458", "1,458")
                views_pattern = r'^\d{1,3}(,\d{3})*$'
                if re.match(views_pattern, text) and int(text.replace(',', '')) > 0:
                    announcement['views'] = text
                
                # 작성자 패턴 (예: "광역센터", "관리자")
                if text in ['광역센터', '관리자', '센터', '담당자']:
                    announcement['author'] = text
            
            # 첨부파일 여부 확인 (아이콘이나 특별한 마크업 존재)
            if item.find('em') or item.find('i') or '첨부' in str(item):
                announcement['has_attachment'] = True
            else:
                announcement['has_attachment'] = False
                
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
            
            logger.info(f"JBSOS 상세 페이지 파싱 완료 - 내용: {len(content_text)}자, 첨부파일: {len(attachments)}개")
            
        except Exception as e:
            logger.error(f"JBSOS 상세 페이지 파싱 실패: {e}")
        
        return result
    
    def _extract_content(self, soup: BeautifulSoup, title_text: str) -> str:
        """본문 내용 추출 - JBSOS 사이트 실제 구조 기반"""
        content_parts = []
        
        # 제목 추가 (페이지 제목에서 불필요한 부분 제거)
        if title_text:
            clean_title = title_text.replace('> 지원사업공고 | 전북소상공인광역지원센터', '').strip()
            if clean_title:
                content_parts.append(f"# {clean_title}\n")
        
        # 1. 세부정보 테이블 추출 (신청기간, 신청대상 등)
        detail_info = self._extract_detail_info(soup)
        if detail_info:
            content_parts.append("\n## 공고 정보")
            content_parts.extend(detail_info)
        
        # 2. 메인 콘텐츠 영역 찾기 - JBSOS 사이트 특화
        content_selectors = [
            'article',  # HTML5 아티클 태그
            '.view_content',  # 일반적인 게시판 본문
            '.content',  # 콘텐츠 영역
            '.bo_v_con',  # 그누보드 본문 클래스
            '.post_content'  # 포스트 콘텐츠
        ]
        
        main_content = None
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        if main_content:
            # 불필요한 요소 제거
            for tag in main_content.find_all(['script', 'style', 'nav']):
                tag.decompose()
            
            # HTML을 마크다운으로 변환
            content_html = str(main_content)
            markdown_content = self.h.handle(content_html)
            content_parts.append("\n## 본문 내용")
            content_parts.append(markdown_content)
        else:
            # 폴백: article 태그로 전체 본문 영역 찾기
            article = soup.find('article')
            if article:
                # 페이지 정보 섹션 제외
                page_info = article.find('div', string=re.compile(r'페이지 정보'))
                if page_info and page_info.parent:
                    page_info.parent.decompose()
                
                # 본문 섹션 찾기
                content_section = article.find('div', string=re.compile(r'본문'))
                if content_section and content_section.parent:
                    content_html = str(content_section.parent)
                    markdown_content = self.h.handle(content_html)
                    content_parts.append("\n## 본문 내용")
                    content_parts.append(markdown_content)
        
        # 3. 관련링크 추출
        link_section = soup.find('h2', string=re.compile(r'관련링크'))
        if link_section:
            next_list = link_section.find_next_sibling('ul')
            if next_list:
                links = next_list.find_all('a')
                if links:
                    content_parts.append("\n## 관련링크")
                    for link in links:
                        url = link.get('href', '')
                        text = link.get_text(strip=True)
                        if url and text:
                            content_parts.append(f"- [{text}]({url})")
        
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
                        '사업내용', '지원내용', '신청방법', '선정기준',
                        '모집분야', '신청자격', '신청기간', '문의처'
                    ]
                    
                    if any(field in header for field in important_fields):
                        detail_info.append(f"**{header}**: {value}")
        
        return detail_info
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """첨부파일 추출 - JBSOS 사이트 실제 구조 기반"""
        attachments = []
        
        # JBSOS 사이트의 실제 첨부파일 구조
        # - 첨부파일 섹션: <h2>첨부파일</h2> 다음의 <ul> 리스트
        # - 다운로드 링크: download.php?bo_table=s_sub04_01&wr_id=422&no=0&nonce=...
        
        # 1. 첨부파일 헤딩 찾기
        attachment_headings = [
            soup.find('h2', string=re.compile(r'첨부파일', re.I)),
            soup.find('h3', string=re.compile(r'첨부파일', re.I)),
            soup.find('strong', string=re.compile(r'첨부파일', re.I)),
            soup.find('div', string=re.compile(r'첨부파일', re.I))
        ]
        
        for heading in attachment_headings:
            if heading:
                # 헤딩 다음 형제 요소에서 리스트 찾기
                next_sibling = heading.find_next_sibling()
                if next_sibling and next_sibling.name == 'ul':
                    links = next_sibling.find_all('a', href=re.compile(r'download\.php'))
                    
                    for link in links:
                        try:
                            href = link.get('href', '')
                            file_name = link.get_text(strip=True)
                            
                            # 파일 크기 정보 제거 (예: "파일명.pdf (160.1K)" -> "파일명.pdf")
                            if '(' in file_name and ')' in file_name:
                                file_name = re.sub(r'\s*\([^)]+\)\s*$', '', file_name)
                            
                            # 파일 확장자 확인
                            valid_extensions = ['.pdf', '.hwp', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.ppt', '.pptx', '.jpg', '.png', '.gif']
                            if file_name and any(ext in file_name.lower() for ext in valid_extensions):
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
        
        # 2. 대안 방법: 전체 페이지에서 download.php 링크 직접 찾기
        if not attachments:
            all_download_links = soup.find_all('a', href=re.compile(r'download\.php'))
            logger.debug(f"전체 페이지에서 {len(all_download_links)}개 다운로드 링크 발견")
            
            for link in all_download_links:
                try:
                    href = link.get('href', '')
                    file_name = link.get_text(strip=True)
                    
                    # 파일 크기 정보 제거
                    if '(' in file_name and ')' in file_name:
                        file_name = re.sub(r'\s*\([^)]+\)\s*$', '', file_name)
                    
                    # 유효한 파일명인지 확인
                    valid_extensions = ['.pdf', '.hwp', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.ppt', '.pptx', '.jpg', '.png', '.gif']
                    if file_name and len(file_name) >= 3 and any(ext in file_name.lower() for ext in valid_extensions):
                        file_url = urljoin(self.base_url, href)
                        
                        # 중복 제거
                        if not any(att['name'] == file_name for att in attachments):
                            attachment = {
                                'name': file_name,
                                'url': file_url
                            }
                            attachments.append(attachment)
                            logger.debug(f"첨부파일 발견 (전체 검색): {file_name}")
                
                except Exception as e:
                    logger.debug(f"첨부파일 링크 처리 중 오류: {e}")
                    continue
        
        logger.info(f"{len(attachments)}개 첨부파일 발견")
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment_info: Dict[str, Any] = None) -> bool:
        """파일 다운로드 - JBSOS 사이트 특화 (nonce 토큰 처리)"""
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
JBSOSScraper = EnhancedJBSOSScraper