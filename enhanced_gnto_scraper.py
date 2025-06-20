# -*- coding: utf-8 -*-
"""
경남관광재단(gnto.or.kr) Enhanced 스크래퍼
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
import base64

logger = logging.getLogger(__name__)

class EnhancedGNTOScraper(StandardTableScraper):
    """경남관광재단(gnto.or.kr) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://gnto.or.kr"
        self.list_url = "https://gnto.or.kr/sub04/sub01_01.php"
        
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
        """페이지별 URL 생성 - GNTO 특화 (bbsData 파라미터 포함)"""
        if page_num == 1:
            return self.list_url
        else:
            # 기본 bbsData는 bm85Mjc3|| (보통 총 공고 수 관련)
            # 실제로는 각 페이지마다 다른 값이지만 기본값으로 시작
            return f"{self.list_url}?code=040101&page={page_num}&bbsData=bm89Mjc3||&search=&searchstring=&gubunx="
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - GNTO 리스트 구조 특화"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # GNTO 사이트의 정확한 리스트 구조 찾기
        # .boardType01 .board_ul 구조 사용
        board_container = soup.select_one('.boardType01 .board_ul')
        if not board_container:
            # Fallback: 일반적인 ul 찾기
            board_container = soup.find('ul', class_='board_ul')
            if board_container:
                logger.debug("board_ul 클래스를 통해 리스트 컨테이너 발견")
            
        if not board_container:
            # 마지막 fallback: 첫 번째 ul
            board_container = soup.find('ul')
            if board_container:
                logger.debug("첫 번째 ul을 리스트 컨테이너로 사용")
        
        if not board_container:
            logger.warning("리스트 컨테이너를 찾을 수 없습니다")
            return announcements
        
        # 모든 li 항목 찾기
        list_items = board_container.find_all('li')
        logger.info(f"리스트에서 {len(list_items)}개 항목 발견")
        
        for item in list_items:
            try:
                # 헤더 행 스킵 (title_li 클래스나 링크가 없는 항목)
                if 'title_li' in item.get('class', []):
                    continue
                
                # h5 > a 구조에서 링크 찾기
                link_elem = item.select_one('h5 a')
                if not link_elem:
                    continue
                
                href = link_elem.get('href', '')
                if not href:
                    continue
                
                # 상대 URL을 절대 URL로 변환
                if href.startswith('/'):
                    detail_url = self.base_url + href
                else:
                    detail_url = urljoin(self.base_url, href)
                
                # 제목 추출 - .title span에서 가져오기
                title_elem = link_elem.select_one('.title')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                else:
                    # Fallback: span들에서 두 번째 span (첫 번째는 "공지")
                    title_spans = link_elem.find_all('span')
                    if len(title_spans) >= 2:
                        title = title_spans[1].get_text(strip=True)
                    else:
                        # 마지막 fallback: 전체 링크 텍스트에서 "공지" 제거
                        full_text = link_elem.get_text(strip=True)
                        title = re.sub(r'^공지\s*', '', full_text).strip()
                
                if not title:
                    continue
                
                # 기본 공고 정보
                announcement = {
                    'title': title,
                    'url': detail_url
                }
                
                # bbsData 파라미터 추출 (상세 페이지 접근용)
                bbs_data_match = re.search(r'bbsData=([^&]+)', href)
                if bbs_data_match:
                    announcement['bbs_data'] = bbs_data_match.group(1)
                
                # 공고 번호 추출 (URL에서)
                no_match = re.search(r'no=(\d+)', href)
                if no_match:
                    announcement['no'] = no_match.group(1)
                
                # 작성자 및 날짜 정보 추출 (.boardInfo에서)
                board_info = item.select_one('.boardInfo')
                if board_info:
                    # 날짜 추출
                    date_elem = board_info.select_one('.date')
                    if date_elem:
                        announcement['date'] = date_elem.get_text(strip=True)
                    
                    # 작성자 추출
                    author_elem = board_info.select_one('.name')
                    if author_elem:
                        announcement['author'] = author_elem.get_text(strip=True)
                else:
                    # Fallback: h5 다음 div에서 span들 찾기
                    info_div = item.select_one('h5 + div')
                    if info_div:
                        info_spans = info_div.find_all('span')
                        if len(info_spans) >= 2:
                            announcement['author'] = info_spans[0].get_text(strip=True)
                            announcement['date'] = info_spans[1].get_text(strip=True)
                
                announcements.append(announcement)
                logger.debug(f"공고 추가: {title[:50]}...")
                
            except Exception as e:
                logger.error(f"리스트 항목 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱 - GNTO 사이트 특화"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # GNTO 사이트의 상세 페이지 구조에서 본문 추출
        content_area = None
        
        # 제목 찾기
        title_elem = soup.find('h4')
        page_title = title_elem.get_text(strip=True) if title_elem else ""
        
        # 본문 영역 찾기 - 여러 방법 시도
        # 1. 메인 콘텐츠 영역 찾기
        main_content = soup.find('div', class_='content')
        if main_content:
            content_area = main_content
            logger.debug("content 클래스를 통해 본문 영역 발견")
        
        # 2. Fallback: 제목 다음의 div들 중 충분한 텍스트가 있는 것 찾기
        if not content_area and title_elem:
            next_divs = title_elem.find_all_next('div')
            for div in next_divs:
                text = div.get_text(strip=True)
                if len(text) > 100:  # 충분한 텍스트가 있는 div
                    content_area = div
                    logger.debug("텍스트 길이 기반으로 본문 영역 추정")
                    break
        
        # 3. 마지막 fallback: body 전체에서 본문 추정
        if not content_area:
            # 첨부파일 섹션 제외하고 본문 영역 찾기
            body = soup.find('body')
            if body:
                # 첨부파일 관련 요소들 제거
                for elem in body.find_all(text=re.compile(r'첨부파일')):
                    if elem.parent:
                        elem.parent.extract()
                
                content_area = body
                logger.warning("body 전체를 본문 영역으로 사용")
        
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
        """첨부파일 링크 추출 - GNTO 사이트 특화"""
        attachments = []
        
        try:
            # 첨부파일 섹션 찾기
            # "첨부파일" 텍스트가 있는 요소 찾기
            attachment_section = None
            
            # 1. p 태그에서 "첨부파일" 텍스트 찾기
            for p in soup.find_all('p'):
                if '첨부파일' in p.get_text():
                    attachment_section = p.parent or p.find_next_sibling()
                    logger.debug("첨부파일 섹션을 p 태그에서 발견")
                    break
            
            # 2. div에서 "첨부파일" 텍스트 찾기
            if not attachment_section:
                for div in soup.find_all('div'):
                    if '첨부파일' in div.get_text():
                        attachment_section = div
                        logger.debug("첨부파일 섹션을 div 태그에서 발견")
                        break
            
            # 3. Fallback: bbs_download.php 링크가 있는 모든 영역
            if not attachment_section:
                download_links = soup.find_all('a', href=re.compile(r'bbs_download\.php'))
                if download_links:
                    attachment_section = soup
                    logger.debug("bbs_download.php 링크를 통해 첨부파일 영역 추정")
            
            if not attachment_section:
                logger.debug("첨부파일 섹션을 찾을 수 없습니다")
                return attachments
            
            # 첨부파일 링크들 찾기
            file_links = attachment_section.find_all('a', href=re.compile(r'bbs_download\.php'))
            
            for link in file_links:
                href = link.get('href', '')
                if not href:
                    continue
                
                file_url = urljoin(self.base_url, href)
                
                # 파일명 추출
                filename = link.get_text(strip=True)
                
                # 파일명이 없으면 URL에서 추출 시도
                if not filename:
                    # URL 파라미터에서 파일명 추출은 어려우므로 기본 이름 사용
                    filename = f"attachment_{len(attachments) + 1}"
                
                # URL에서 공고 번호와 파일 번호 추출
                no_match = re.search(r'no=(\d+)', href)
                dn_match = re.search(r'dn=(\d+)', href)
                fn_match = re.search(r'fn=(\d+)', href)
                
                file_no = no_match.group(1) if no_match else ""
                download_no = dn_match.group(1) if dn_match else ""
                file_index = fn_match.group(1) if fn_match else ""
                
                if filename:
                    attachment = {
                        'filename': filename,
                        'url': file_url,
                        'file_no': file_no,
                        'download_no': download_no,
                        'file_index': file_index
                    }
                    
                    attachments.append(attachment)
                    logger.info(f"첨부파일 발견: {filename}")
            
        except Exception as e:
            logger.error(f"첨부파일 추출 중 오류: {e}")
        
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment_info: Dict[str, Any] = None) -> bool:
        """파일 다운로드 - GNTO 특화 (HTTPS 사이트, 한글 파일명 처리)"""
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
GNTOScraper = EnhancedGNTOScraper