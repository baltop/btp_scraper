# -*- coding: utf-8 -*-
"""
경남행복내일센터(gnlife5064.kr) Enhanced 스크래퍼
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

class EnhancedGnlifeScraper(StandardTableScraper):
    """경남행복내일센터(gnlife5064.kr) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "http://gnlife5064.kr"
        self.list_url = "http://gnlife5064.kr/bbs/board.php?bo_table=notice"
        
        # 사이트 특화 설정
        self.verify_ssl = False  # HTTP 사이트 (SSL 없음)
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        
        # 향상된 헤더 설정
        self.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.session.headers.update(self.headers)
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - PHP GET 파라미터 방식"""
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&page={page_num}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - gnlife5064.kr 사이트 특화"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # gnlife5064.kr 사이트의 테이블 구조 찾기
        # 공지사항 목록을 포함하는 테이블 찾기
        table = soup.find('table')
        if not table:
            logger.warning("테이블을 찾을 수 없습니다")
            return announcements
        
        tbody = table.find('tbody')
        if not tbody:
            tbody = table
        
        rows = tbody.find_all('tr')
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 6:  # 번호, 상태, 제목, 글쓴이, 조회, 날짜
                    continue
                
                # 제목 셀에서 링크 찾기 (세 번째 셀)
                title_cell = cells[2]
                link_elem = title_cell.find('a')
                
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                if not title:
                    continue
                
                href = link_elem.get('href', '')
                detail_url = urljoin(self.base_url, href)
                
                # wr_id 추출
                wr_id_match = re.search(r'wr_id=(\d+)', href)
                wr_id = wr_id_match.group(1) if wr_id_match else ""
                
                # 기본 공고 정보
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'wr_id': wr_id
                }
                
                # 번호 (첫 번째 셀)
                if len(cells) > 0:
                    number = cells[0].get_text(strip=True)
                    announcement['number'] = number
                
                # 상태 (두 번째 셀)
                if len(cells) > 1:
                    status = cells[1].get_text(strip=True)
                    announcement['status'] = status
                
                # 글쓴이 (네 번째 셀)
                if len(cells) > 3:
                    author = cells[3].get_text(strip=True)
                    announcement['author'] = author
                
                # 조회수 (다섯 번째 셀)
                if len(cells) > 4:
                    views = cells[4].get_text(strip=True)
                    announcement['views'] = views
                
                # 날짜 (여섯 번째 셀)
                if len(cells) > 5:
                    date = cells[5].get_text(strip=True)
                    announcement['date'] = date
                
                announcements.append(announcement)
                logger.debug(f"공고 추가: {title[:50]}...")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱 - gnlife5064.kr 사이트 특화"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # gnlife5064.kr 사이트의 article 구조에서 본문 추출
        article = soup.find('article')
        if not article:
            logger.warning("article 태그를 찾을 수 없습니다")
            return {
                'content': "내용을 찾을 수 없습니다.",
                'attachments': []
            }
        
        # 제목 추출
        title_elem = article.find('h3')
        page_title = title_elem.get_text(strip=True) if title_elem else ""
        
        # 본문 영역 찾기
        content_area = None
        
        # "본문" 헤더를 찾고 그 다음 div 사용
        content_div = article.find('div', class_='content')
        if content_div:
            content_area = content_div
            logger.debug("content 클래스를 통해 콘텐츠 영역 발견")
        
        # Fallback: article 내의 div들 중에서 콘텐츠가 있는 것 찾기
        if not content_area:
            divs = article.find_all('div')
            for div in divs:
                text = div.get_text(strip=True)
                if len(text) > 50:  # 충분한 텍스트가 있는 div 찾기
                    content_area = div
                    logger.debug("텍스트 길이 기반으로 콘텐츠 영역 추정")
                    break
        
        # 마지막 fallback: article 전체 사용
        if not content_area:
            content_area = article
            logger.warning("콘텐츠 영역을 찾지 못해 article 전체 사용")
        
        # HTML을 마크다운으로 변환
        if content_area:
            # 이미지 URL을 절대 URL로 변환
            for img in content_area.find_all('img'):
                src = img.get('src', '')
                if src and not src.startswith('http'):
                    img['src'] = urljoin(self.base_url, src)
            
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
        """첨부파일 링크 추출 - gnlife5064.kr 사이트 특화"""
        attachments = []
        
        try:
            # 첨부파일 섹션 찾기 - gnlife5064.kr의 구조
            # article 내에서 첨부파일 영역 찾기
            article = soup.find('article')
            if not article:
                return attachments
            
            # 첨부파일 영역을 찾는 여러 방법 시도
            attachment_area = None
            
            # 1. .attachments 클래스 찾기
            attachment_area = article.find('div', class_='attachments')
            if attachment_area:
                logger.debug("attachments 클래스를 통해 첨부파일 영역 발견")
            
            # 2. "첨부파일" 텍스트가 있는 헤더 찾기
            if not attachment_area:
                for h3 in article.find_all('h3'):
                    if '첨부파일' in h3.get_text():
                        attachment_area = h3.parent or h3.find_next_sibling()
                        logger.debug("첨부파일 헤더를 통해 첨부파일 영역 발견")
                        break
            
            # 3. download.php 링크가 있는 영역 찾기
            if not attachment_area:
                download_links = article.find_all('a', href=re.compile(r'download\.php'))
                if download_links:
                    attachment_area = article
                    logger.debug("download.php 링크를 통해 첨부파일 영역 추정")
            
            if not attachment_area:
                logger.debug("첨부파일 영역을 찾을 수 없습니다")
                return attachments
            
            # 첨부파일 링크들 찾기
            file_links = attachment_area.find_all('a', href=re.compile(r'download\.php'))
            
            for link in file_links:
                href = link.get('href', '')
                if not href:
                    continue
                
                file_url = urljoin(self.base_url, href)
                
                # 파일명 추출
                filename = link.get_text(strip=True)
                
                # 파일명이 없으면 href에서 추출 시도
                if not filename:
                    # download.php?bo_table=notice&wr_id=293&no=0 에서 파일명 추출은 어려움
                    filename = f"attachment_{len(attachments) + 1}"
                
                # 파일 크기 추출 (링크 다음 텍스트에서)
                parent = link.parent
                if parent:
                    parent_text = parent.get_text()
                    size_match = re.search(r'\(([^)]+)\)', parent_text)
                    file_size = size_match.group(1) if size_match else ""
                    
                    # 다운로드 횟수 추출
                    download_match = re.search(r'(\d+)회 다운로드', parent_text)
                    download_count = download_match.group(1) if download_match else ""
                else:
                    file_size = ""
                    download_count = ""
                
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
        """파일 다운로드 - gnlife5064.kr 특화 (HTTP 사이트 처리)"""
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
GnlifeScraper = EnhancedGnlifeScraper