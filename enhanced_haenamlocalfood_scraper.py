# -*- coding: utf-8 -*-
"""
해남로컬푸드(haenamlocalfood.kr) Enhanced 스크래퍼
"""

import requests
from bs4 import BeautifulSoup
import re
import logging
import os
from urllib.parse import urljoin, unquote
from enhanced_base_scraper import StandardTableScraper
import time
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class EnhancedHaenamLocalFoodScraper(StandardTableScraper):
    """해남로컬푸드(haenamlocalfood.kr) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://haenamlocalfood.kr"
        self.list_url = "https://haenamlocalfood.kr/bbs/board.php?bo_table=lf4_1"
        
        # 사이트 특화 설정
        self.verify_ssl = True  # HTTPS 사이트
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        
        # 향상된 헤더 설정
        self.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.session.headers.update(self.headers)
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - 그누보드 GET 파라미터 방식"""
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&page={page_num}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - 해남로컬푸드 그누보드 5 구조 특화"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 해남로컬푸드 사이트의 리스트 구조 찾기
        # 그누보드 5의 표준 구조: ul.board_list_ul
        board_list = soup.find('ul', class_='board_list_ul')
        if not board_list:
            # Fallback: .list_01 컨테이너 내 ul 찾기
            list_container = soup.find('div', class_='list_01')
            if list_container:
                board_list = list_container.find('ul')
                logger.debug("list_01 컨테이너에서 ul 발견")
        
        if not board_list:
            # 마지막 fallback: 첫 번째 ul
            board_list = soup.find('ul')
            logger.debug("첫 번째 ul을 사용")
        
        if not board_list:
            logger.warning("게시판 리스트를 찾을 수 없습니다")
            return announcements
        
        list_items = board_list.find_all('li')
        logger.info(f"리스트에서 {len(list_items)}개 항목 발견")
        
        for item in list_items:
            try:
                # 제목 및 링크 추출
                subject_div = item.find('div', class_='bo_subject')
                if not subject_div:
                    continue
                
                link_elem = subject_div.find('a', class_='bo_subjecta')
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                if not title:
                    continue
                
                href = link_elem.get('href', '')
                detail_url = urljoin(self.base_url, href)
                
                # wr_id 추출 (그누보드 고유 ID)
                wr_id_match = re.search(r'wr_id=(\d+)', href)
                wr_id = wr_id_match.group(1) if wr_id_match else ""
                
                # 기본 공고 정보
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'wr_id': wr_id
                }
                
                # 번호 추출 (bo_chk div에서)
                chk_div = item.find('div', class_='bo_chk')
                if chk_div:
                    number = chk_div.get_text(strip=True)
                    announcement['number'] = number
                
                # 작성자 추출 (sv_member span에서)
                author_span = item.find('span', class_='sv_member')
                if author_span:
                    author = author_span.get_text(strip=True)
                    announcement['author'] = author
                
                # 날짜/시간 추출 (datetime span에서)
                datetime_span = item.find('span', class_='datetime')
                if datetime_span:
                    datetime = datetime_span.get_text(strip=True)
                    announcement['datetime'] = datetime
                
                announcements.append(announcement)
                logger.debug(f"공고 추가: {title[:50]}...")
                
            except Exception as e:
                logger.error(f"리스트 항목 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱 - 해남로컬푸드 그누보드 5 구조 특화"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 그누보드 5의 표준 본문 영역 찾기
        content_area = None
        
        # 1. bo_v_con div에서 본문 찾기 (그누보드 표준)
        content_div = soup.find('div', id='bo_v_con')
        if content_div:
            content_area = content_div
            logger.debug("bo_v_con에서 본문 영역 발견")
        
        # 2. Fallback: section#bo_v_atc 내에서 본문 찾기
        if not content_area:
            article_section = soup.find('section', id='bo_v_atc')
            if article_section:
                content_area = article_section
                logger.debug("bo_v_atc 섹션에서 본문 영역 발견")
        
        # 3. 마지막 fallback: article 태그 전체
        if not content_area:
            content_area = soup.find('article')
            if content_area:
                logger.debug("article 태그 전체를 본문 영역으로 사용")
        
        # HTML을 마크다운으로 변환
        if content_area:
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
        """첨부파일 링크 추출 - 해남로컬푸드 그누보드 5 구조 특화"""
        attachments = []
        
        try:
            # 그누보드 5 표준 첨부파일 섹션 찾기
            file_section = soup.find('section', id='bo_v_file')
            if not file_section:
                logger.debug("첨부파일 섹션(bo_v_file)을 찾을 수 없습니다")
                return attachments
            
            # 첨부파일 링크들 찾기
            file_links = file_section.find_all('a', class_='view_file_download')
            
            for link in file_links:
                href = link.get('href', '')
                if not href:
                    continue
                
                file_url = urljoin(self.base_url, href)
                
                # 파일명 추출 (strong 태그에서)
                strong_elem = link.find('strong')
                filename = strong_elem.get_text(strip=True) if strong_elem else ""
                
                # 파일명이 없으면 링크 전체 텍스트에서 추출
                if not filename:
                    filename = link.get_text(strip=True)
                
                # 파일 크기 및 다운로드 횟수 추출
                li_parent = link.find_parent('li')
                file_size = ""
                download_count = ""
                
                if li_parent:
                    li_text = li_parent.get_text()
                    
                    # 파일 크기 추출 (45.5K) 형식
                    size_match = re.search(r'\(([^)]+)\)', li_text)
                    if size_match:
                        file_size = size_match.group(1)
                    
                    # 다운로드 횟수 추출 (1회 다운로드) 형식
                    download_match = re.search(r'(\d+)회 다운로드', li_text)
                    if download_match:
                        download_count = download_match.group(1)
                
                if filename:
                    attachment = {
                        'filename': filename,
                        'url': file_url,
                        'size': file_size,
                        'download_count': download_count
                    }
                    
                    attachments.append(attachment)
                    logger.info(f"첨부파일 발견: {filename} ({file_size})")
            
        except Exception as e:
            logger.error(f"첨부파일 추출 중 오류: {e}")
        
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment_info: Dict[str, Any] = None) -> bool:
        """파일 다운로드 - 해남로컬푸드 특화 (그누보드 다운로드 처리)"""
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
HaenamLocalFoodScraper = EnhancedHaenamLocalFoodScraper