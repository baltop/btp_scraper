# -*- coding: utf-8 -*-
"""
경기도시장상권진흥원(gmr.or.kr) Enhanced 스크래퍼
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

class EnhancedGMRScraper(StandardTableScraper):
    """경기도시장상권진흥원(gmr.or.kr) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://gmr.or.kr"
        self.list_url = "https://gmr.or.kr/base/board/list?boardManagementNo=1&menuLevel=2&menuNo=14"
        
        # 사이트 특화 설정
        self.verify_ssl = True  # HTTPS 사이트
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
        """페이지별 URL 생성 - GET 파라미터 방식"""
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.base_url}/base/board/list?boardManagementNo=1&page={page_num}&menuLevel=2&menuNo=14"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - gmr.or.kr 사이트 특화"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # gmr.or.kr 사이트의 테이블 구조 분석
        table_container = soup.find('div', class_='basicTable2 notice-type')
        if not table_container:
            logger.warning("basicTable2 notice-type 컨테이너를 찾을 수 없습니다")
            return announcements
        
        table = table_container.find('table')
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
                if len(cells) < 2:  # 제목, 날짜 최소 필요
                    continue
                
                # 제목 셀에서 링크 찾기 (첫 번째 셀)
                title_cell = cells[0]
                link_elem = title_cell.find('a')
                
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                if not title:
                    continue
                
                href = link_elem.get('href', '')
                detail_url = urljoin(self.base_url, href)
                
                # 날짜 정보 추출 (두 번째 셀)
                date_cell = cells[1] if len(cells) > 1 else None
                date = date_cell.get_text(strip=True) if date_cell else ''
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'date': date
                }
                
                announcements.append(announcement)
                logger.debug(f"공고 추가: {title[:50]}...")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱 - gmr.or.kr 사이트 특화"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # gmr.or.kr 사이트의 본문 내용 추출
        content_selectors = [
            '.noticeView__cont',
            '.noticeView .content',
            '.notice_content',
            '.board_content',
            '.content',
            'div[class*="content"]',
            'div[class*="view"]'
        ]
        
        content_area = None
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        # Fallback: 텍스트가 많은 div 찾기
        if not content_area:
            for div in soup.find_all('div'):
                text = div.get_text(strip=True)
                if len(text) > 100 and '첨부파일' not in text and '목록' not in text:
                    content_area = div
                    logger.debug("텍스트 길이 기반으로 본문 영역 추정")
                    break
        
        # 마지막 fallback: body 전체에서 추출
        if not content_area:
            content_area = soup.find('body') or soup
            logger.warning("본문 영역을 찾지 못해 전체 페이지에서 추출")
        
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
        """첨부파일 링크 추출 - gmr.or.kr 사이트 특화"""
        attachments = []
        
        try:
            # 첨부파일 섹션 찾기
            attachment_selectors = [
                '.noticeView__file',
                '.noticeView__file__list',
                '.file_list',
                '.attach_list',
                'div[class*="file"]',
                'div[class*="attach"]'
            ]
            
            attachment_area = None
            for selector in attachment_selectors:
                attachment_area = soup.select_one(selector)
                if attachment_area:
                    logger.debug(f"첨부파일 영역을 {selector} 선택자로 찾음")
                    break
            
            # 첨부파일 영역이 없으면 전체에서 파일 링크 찾기
            if not attachment_area:
                attachment_area = soup
            
            # 파일 다운로드 링크 찾기
            file_links = []
            
            # 특정 클래스의 링크들 먼저 확인
            for class_name in ['noticeView__file__list__down', 'file_down', 'attach_down']:
                links = attachment_area.find_all('a', class_=class_name)
                file_links.extend(links)
            
            # 일반적인 다운로드 링크 패턴도 확인
            if not file_links:
                all_links = attachment_area.find_all('a', href=True)
                for link in all_links:
                    href = link.get('href', '')
                    if any(pattern in href.lower() for pattern in ['download', 'file', 'attach', 'storage']):
                        file_links.append(link)
            
            for link in file_links:
                href = link.get('href', '')
                filename = link.get_text(strip=True)
                
                # 파일 아이콘이나 다른 요소 때문에 파일명이 없는 경우 대체 방법 시도
                if not filename:
                    filename = link.get('title', '') or link.get('alt', '')
                
                # 상위 요소에서 파일명 찾기
                if not filename:
                    parent = link.parent
                    if parent:
                        filename = parent.get_text(strip=True)
                
                if filename and href:
                    # URL 정리
                    if href.startswith('/'):
                        file_url = urljoin(self.base_url, href)
                    else:
                        file_url = href
                    
                    attachment = {
                        'filename': filename,
                        'url': file_url
                    }
                    
                    attachments.append(attachment)
                    logger.info(f"첨부파일 발견: {filename}")
            
        except Exception as e:
            logger.error(f"첨부파일 추출 중 오류: {e}")
        
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment_info: Dict[str, Any] = None) -> bool:
        """파일 다운로드 - gmr.or.kr 특화 (한글 파일명 처리)"""
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
            # RFC 5987 형식 우선 처리 (filename*=UTF-8''%ED%95%9C%EA%B8%80.pdf)
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
GMRScraper = EnhancedGMRScraper