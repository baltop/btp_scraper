# -*- coding: utf-8 -*-
"""
KITECH 전용 Enhanced 스크래퍼
사이트: https://www.kitech.re.kr/research/page1-1.php
특징: EUC-KR 인코딩, JavaScript 기반 상세 페이지 접근, 표준 테이블 구조
"""

from enhanced_base_scraper import StandardTableScraper
from bs4 import BeautifulSoup
import requests
import os
import re
import time
import logging
from urllib.parse import urljoin
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class EnhancedKitechScraper(StandardTableScraper):
    """KITECH 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (fallback용)
        self.base_url = "https://www.kitech.re.kr"
        self.list_url = "https://www.kitech.re.kr/research/page1-1.php"
        
        # 사이트 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'euc-kr'  # KITECH는 EUC-KR 사용
        self.timeout = 30
        
        # KITECH 특화 헤더
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en;q=0.6',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def get_page(self, url: str, **kwargs):
        """KITECH 특화 페이지 가져오기 - EUC-KR 인코딩 처리"""
        response = super().get_page(url, **kwargs)
        if response:
            response.encoding = self.default_encoding  # EUC-KR 강제 설정
        return response
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - GET 파라미터 기반"""
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: KITECH는 page 파라미터 사용
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}?page={page_num}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - 테이블 기반"""
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """KITECH 특화 목록 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 메인 테이블 찾기 - KITECH는 단일 테이블 구조
        table = soup.find('table')
        if not table:
            logger.warning("공고 목록 테이블을 찾을 수 없습니다")
            return announcements
        
        tbody = table.find('tbody')
        if not tbody:
            logger.warning("tbody를 찾을 수 없습니다")
            return announcements
        
        rows = tbody.find_all('tr')
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 4:  # 번호, 제목, 첨부, 등록일 최소 4개 컬럼
                    continue
                
                # KITECH 테이블 구조: [번호] [제목] [첨부] [등록일]
                num_cell = cells[0]
                title_cell = cells[1]
                attach_cell = cells[2]
                date_cell = cells[3]
                
                # 제목 및 링크 추출 - href로 JavaScript 함수 확인
                link_elem = title_cell.find('a')
                if not link_elem:
                    logger.debug("링크를 찾을 수 없는 행 건너뛰기")
                    continue
                
                title = link_elem.get_text(strip=True)
                href = link_elem.get('href', '')
                
                if not title or not href:
                    continue
                
                # JavaScript 함수에서 ID 추출: javascript:goDetail(682)
                detail_id = None
                if 'javascript:goDetail' in href:
                    detail_match = re.search(r'goDetail\((\d+)\)', href)
                    if detail_match:
                        detail_id = detail_match.group(1)
                    else:
                        logger.debug(f"상세 ID를 추출할 수 없음: {href}")
                        continue
                else:
                    logger.debug(f"goDetail이 아닌 링크: {href}")
                    continue
                
                # 상세 페이지 URL 구성 (추정)
                detail_url = f"{self.base_url}/research/page1-2.php?idx={detail_id}"
                
                # 등록일 추출
                date = date_cell.get_text(strip=True)
                
                # 첨부파일 여부 확인
                has_attachment = bool(attach_cell.find('img') or attach_cell.get_text(strip=True))
                
                # 번호 추출
                num = num_cell.get_text(strip=True)
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'date': date,
                    'has_attachment': has_attachment,
                    'detail_id': detail_id,
                    'num': num
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
        """KITECH 특화 상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 추출 시도
        content_area = None
        content_selectors = [
            '.view_content',
            '.content_area', 
            '.board_view',
            '.view_area',
            '#content',
            '.content'
        ]
        
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        if not content_area:
            # 대안: 테이블 내 본문 찾기
            tables = soup.find_all('table')
            for table in tables:
                # 충분한 텍스트가 있는 테이블 찾기
                table_text = table.get_text(strip=True)
                if len(table_text) > 200:
                    content_area = table
                    logger.debug("테이블 기반으로 본문 영역 추정")
                    break
            
            if not content_area:
                # 최후 수단: body 전체
                content_area = soup.find('body')
                logger.warning("특정 본문 영역을 찾지 못해 body 전체 사용")
        
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
            'url': self.base_url + "/research/page1-2.php"
        }
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """첨부파일 추출 - KITECH 특화"""
        attachments = []
        
        try:
            # KITECH 특화 파일 다운로드 패턴
            # KITECH는 /upload_files/download.php 패턴 사용
            download_links = soup.find_all('a', href=lambda x: x and 'download.php' in x)
            
            seen_urls = set()
            
            for link in download_links:
                href = link.get('href', '')
                if not href:
                    continue
                
                file_url = urljoin(self.base_url, href)
                if file_url in seen_urls:
                    continue
                
                # URL에서 filename 파라미터 추출
                filename = "attachment"
                if 'filename=' in href:
                    # URL 디코딩하여 파일명 추출
                    from urllib.parse import unquote, parse_qs, urlparse
                    try:
                        parsed = urlparse(href)
                        params = parse_qs(parsed.query)
                        if 'filename' in params:
                            encoded_filename = params['filename'][0]
                            # EUC-KR로 디코딩 시도
                            try:
                                # URL 인코딩된 EUC-KR을 디코딩
                                decoded = unquote(encoded_filename, encoding='euc-kr')
                                if decoded and len(decoded) > 2:
                                    filename = decoded
                            except:
                                # fallback으로 그대로 사용
                                filename = encoded_filename
                    except Exception as e:
                        logger.debug(f"파일명 디코딩 실패: {e}")
                
                # 파일 확장자 확인
                if not any(ext in filename.lower() for ext in ['.pdf', '.hwp', '.doc', '.zip', '.xlsx']):
                    # filepath에서 확장자 추출 시도
                    if 'filepath=' in href:
                        try:
                            parsed = urlparse(href)
                            params = parse_qs(parsed.query)
                            if 'filepath' in params:
                                filepath = params['filepath'][0]
                                file_ext = os.path.splitext(filepath)[1]
                                if file_ext:
                                    filename += file_ext
                        except:
                            pass
                
                attachments.append({
                    'name': filename,
                    'filename': filename,
                    'url': file_url,
                    'type': 'kitech_download'
                })
                seen_urls.add(file_url)
                logger.debug(f"KITECH 첨부파일 발견: {filename}")
            
            # 추가 패턴: 일반적인 다운로드 링크들도 확인
            general_patterns = [
                'a[href*=".pdf"]',
                'a[href*=".hwp"]',
                'a[href*=".zip"]',
                'a[href*=".doc"]'
            ]
            
            for pattern in general_patterns:
                links = soup.select(pattern)
                for link in links:
                    href = link.get('href', '')
                    if href and 'javascript:' not in href and 'download.php' not in href:
                        file_url = urljoin(self.base_url, href)
                        if file_url not in seen_urls:
                            filename = link.get_text(strip=True) or os.path.basename(href)
                            if filename and len(filename) > 2:
                                attachments.append({
                                    'name': filename,
                                    'filename': filename,
                                    'url': file_url,
                                    'type': 'direct_link'
                                })
                                seen_urls.add(file_url)
                    
            
            # 2. 테이블 내 첨부파일 정보 찾기
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    for cell in cells:
                        cell_text = cell.get_text().lower()
                        if any(word in cell_text for word in ['첨부', '파일', 'attachment', 'file']):
                            # 셀 내의 링크 찾기
                            cell_links = cell.find_all('a')
                            for link in cell_links:
                                href = link.get('href', '')
                                if href and 'javascript:' not in href:
                                    file_url = urljoin(self.base_url, href)
                                    if file_url not in seen_urls:
                                        filename = link.get_text(strip=True) or os.path.basename(href)
                                        attachments.append({
                                            'name': filename,
                                            'filename': filename,
                                            'url': file_url,
                                            'type': 'table_attachment'
                                        })
                                        seen_urls.add(file_url)
            
            logger.info(f"{len(attachments)}개 첨부파일 발견")
            for att in attachments:
                logger.debug(f"- {att['filename']} ({att['type']})")
            
        except Exception as e:
            logger.error(f"첨부파일 추출 중 오류: {e}")
        
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment: dict = None) -> bool:
        """첨부파일 다운로드 - KITECH 특화"""
        logger.info(f"파일 다운로드 시작: {url}")
        
        try:
            # KITECH 파일 다운로드 헤더 설정
            download_headers = self.session.headers.copy()
            download_headers.update({
                'Referer': self.list_url,
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
            
            # 파일명이 응답 헤더에 있는지 확인
            content_disposition = response.headers.get('Content-Disposition', '')
            if content_disposition and 'filename' in content_disposition:
                # 응답 헤더에서 파일명 추출 시도
                filename_match = re.search(r'filename[^;=\n]*=([\'"]*)(.*?)\1', content_disposition)
                if filename_match:
                    header_filename = filename_match.group(2)
                    # 한글 파일명 디코딩 시도
                    try:
                        # EUC-KR 또는 UTF-8 디코딩 시도
                        for encoding in ['euc-kr', 'utf-8', 'cp949']:
                            try:
                                if encoding == 'utf-8':
                                    decoded_filename = header_filename.encode('latin-1').decode('utf-8')
                                else:
                                    decoded_filename = header_filename.encode('latin-1').decode(encoding)
                                
                                if decoded_filename and len(decoded_filename) > 2:
                                    # 헤더의 파일명을 사용하여 저장 경로 업데이트
                                    save_dir = os.path.dirname(save_path)
                                    save_path = os.path.join(save_dir, self.sanitize_filename(decoded_filename))
                                    break
                            except:
                                continue
                    except:
                        pass
            
            # 스트리밍 다운로드로 메모리 효율성 확보
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(save_path)
            logger.info(f"다운로드 완료: {save_path} ({file_size:,} bytes)")
            
            return True
            
        except Exception as e:
            logger.error(f"파일 다운로드 실패 {url}: {e}")
            # 실패한 파일 삭제
            if os.path.exists(save_path):
                try:
                    os.remove(save_path)
                except:
                    pass
            return False


# 하위 호환성을 위한 별칭
KitechScraper = EnhancedKitechScraper