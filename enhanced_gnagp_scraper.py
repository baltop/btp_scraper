# -*- coding: utf-8 -*-
"""
경상남도항노화플랫폼(gnagp.com) Enhanced 스크래퍼
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

class EnhancedGNAGPScraper(StandardTableScraper):
    """경상남도항노화플랫폼(gnagp.com) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "http://www.gnagp.com"
        self.list_url = "http://www.gnagp.com/bbs/board.php?bo_table=sub4_1"
        
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
        """목록 페이지 파싱 - gnagp.com 사이트 특화"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # gnagp.com 사이트의 정확한 테이블 구조 찾기
        table = soup.find('table', summary="게시판 목록입니다.")
        if not table:
            # Fallback: div.tbl_head01.tbl_wrap 내의 테이블
            tbl_wrap = soup.find('div', class_='tbl_head01 tbl_wrap')
            if tbl_wrap:
                table = tbl_wrap.find('table')
                logger.debug("tbl_wrap을 통해 테이블 발견")
        
        if not table:
            # 마지막 fallback: 첫 번째 테이블
            table = soup.find('table')
            logger.debug("첫 번째 테이블을 사용")
        
        if not table:
            logger.warning("테이블을 찾을 수 없습니다")
            return announcements
        
        tbody = table.find('tbody')
        if not tbody:
            tbody = table
        
        # bo_notice 클래스를 가진 행들 찾기 (공지사항 행)
        rows = tbody.find_all('tr', class_='bo_notice')
        if not rows:
            # Fallback: 모든 tr 태그
            rows = tbody.find_all('tr')
            logger.debug("bo_notice 클래스를 찾을 수 없어 모든 tr 사용")
        
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 6:  # 번호, 제목, 작성자, 파일, 날짜, 조회수
                    continue
                
                # 제목 셀에서 링크 찾기 (두 번째 셀: td_subject)
                title_cell = cells[1]
                link_elem = title_cell.find('a')
                
                if not link_elem:
                    continue
                
                raw_title = link_elem.get_text(strip=True)
                if not raw_title:
                    continue
                
                # "공지" 텍스트 제거
                title = re.sub(r'^공지\s*', '', raw_title).strip()
                
                href = link_elem.get('href', '')
                detail_url = urljoin(self.base_url, href)
                
                # 기본 공고 정보
                announcement = {
                    'title': title,
                    'url': detail_url
                }
                
                # 작성자 (세 번째 셀: td_num)
                if len(cells) > 2:
                    author_cell = cells[2]
                    author_elem = author_cell.find('span', class_='sv_member')
                    author = author_elem.get_text(strip=True) if author_elem else cells[2].get_text(strip=True)
                    announcement['author'] = author
                
                # 파일 여부 (네 번째 셀: td_file)
                if len(cells) > 3:
                    file_cell = cells[3]
                    has_files = bool(file_cell.find('i', class_='fa-file-alt'))
                    announcement['has_files'] = has_files
                
                # 날짜 (다섯 번째 셀: td_datetime)
                if len(cells) > 4:
                    date = cells[4].get_text(strip=True)
                    announcement['date'] = date
                
                # 조회수 (여섯 번째 셀: td_view)
                if len(cells) > 5:
                    views = cells[5].get_text(strip=True)
                    announcement['views'] = views
                
                announcements.append(announcement)
                logger.debug(f"공고 추가: {title[:50]}...")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱 - gnagp.com 사이트 특화"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # gnagp.com 사이트의 본문 내용 추출
        # article 태그에서 콘텐츠 찾기
        article = soup.find('article')
        if not article:
            logger.warning("article 태그를 찾을 수 없습니다")
            return {
                'content': "내용을 찾을 수 없습니다.",
                'attachments': []
            }
        
        # 제목 추출
        title_elem = article.find('h2')
        page_title = title_elem.get_text(strip=True) if title_elem else ""
        
        # 본문 영역 찾기
        content_area = None
        
        # "본문" 헤더를 찾고 그 다음 div 사용
        content_header = article.find('h2', string=lambda text: text and '본문' in text)
        if content_header:
            content_area = content_header.find_next_sibling('div')
            logger.debug("본문 헤더를 통해 콘텐츠 영역 발견")
        
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
        """첨부파일 링크 추출 - gnagp.com 사이트 특화"""
        attachments = []
        
        try:
            # 첨부파일 섹션 찾기
            # "첨부파일" 헤더 찾기
            attachment_header = soup.find('h2', string=lambda text: text and '첨부파일' in text)
            if not attachment_header:
                logger.debug("첨부파일 헤더를 찾을 수 없습니다")
                return attachments
            
            # 첨부파일 목록 (ul 태그)
            attachment_list = attachment_header.find_next_sibling('ul')
            if not attachment_list:
                logger.debug("첨부파일 목록을 찾을 수 없습니다")
                return attachments
            
            # 각 첨부파일 링크 처리
            for li in attachment_list.find_all('li'):
                link = li.find('a')
                if not link:
                    continue
                
                href = link.get('href', '')
                if not href:
                    continue
                
                file_url = urljoin(self.base_url, href)
                
                # 파일명 추출 (strong 태그에서)
                strong = link.find('strong')
                filename = strong.get_text(strip=True) if strong else ""
                
                # 파일명이 없으면 링크 전체 텍스트에서 추출
                if not filename:
                    filename = link.get_text(strip=True)
                
                # 파일 크기 추출 (괄호 안의 내용)
                li_text = li.get_text()
                size_match = re.search(r'\(([^)]+)\)', li_text)
                file_size = size_match.group(1) if size_match else ""
                
                # 다운로드 횟수 추출
                download_match = re.search(r'(\d+)회 다운로드', li_text)
                download_count = download_match.group(1) if download_match else ""
                
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
        """파일 다운로드 - gnagp.com 특화 (HTTP 사이트 처리)"""
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
GNAGPScraper = EnhancedGNAGPScraper