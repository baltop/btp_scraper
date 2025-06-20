# -*- coding: utf-8 -*-
"""
CBF (춘천바이오산업진흥원) 전용 스크래퍼 - 향상된 버전
"""

from enhanced_base_scraper import StandardTableScraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote, parse_qs, urlparse
import re
import logging
import os
import json
import requests

logger = logging.getLogger(__name__)

class EnhancedCbfScraper(StandardTableScraper):
    """CBF 전용 스크래퍼 - 향상된 버전 (표준 HTML 테이블 기반)"""
    
    def __init__(self):
        super().__init__()
        
        # 하드코딩된 설정들
        self.base_url = "http://www.cbf.or.kr"
        self.list_url = "http://www.cbf.or.kr/twb_bbs/bbs_list.php?bcd=01_05_01_00_00"
        
        # 사이트 특화 설정
        self.verify_ssl = False  # HTTP 사이트
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        self.delay_between_pages = 2
        
        # CBF 사이트는 groupid 파라미터가 필요함
        self.groupid = 1
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - CBF 특화"""
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&pg={page_num}"
    
    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱 - CBF 특화"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # CBF의 게시판 테이블 찾기
        table = soup.find('table', class_='table_basic')
        if not table:
            logger.error("table_basic 클래스를 가진 테이블을 찾을 수 없습니다")
            return announcements
        
        tbody = table.find('tbody')
        if not tbody:
            logger.error("tbody를 찾을 수 없습니다")
            return announcements
        
        logger.info(f"테이블에서 {len(tbody.find_all('tr'))}개 행 발견")
        
        for row in tbody.find_all('tr'):
            try:
                cells = row.find_all('td')
                if len(cells) < 6:  # 번호, 제목, 글쓴이, 파일, 날짜, 조회수
                    logger.debug(f"셀 개수 부족: {len(cells)}")
                    continue
                
                # 제목 셀 (두 번째 칼럼)
                title_cell = cells[1]
                link_elem = title_cell.find('a')
                
                if not link_elem:
                    logger.debug("제목 링크를 찾을 수 없습니다")
                    continue
                
                title = link_elem.get_text(strip=True)
                if not title:
                    logger.debug("제목이 비어있습니다")
                    continue
                
                # URL 추출 및 절대 URL 생성
                href = link_elem.get('href', '')
                if href.startswith('bbs_read.php'):
                    detail_url = urljoin("http://www.cbf.or.kr/twb_bbs/", href)
                else:
                    detail_url = urljoin(self.base_url, href)
                
                # 기타 정보 추출
                number_text = cells[0].get_text(strip=True)  # 번호
                writer = cells[2].get_text(strip=True)       # 글쓴이
                date = cells[4].get_text(strip=True)         # 날짜
                hits = cells[5].get_text(strip=True)         # 조회수
                
                # 첨부파일 여부 확인 (파일 칼럼의 이미지 개수)
                file_cell = cells[3]
                file_count = len(file_cell.find_all('img'))
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'number': number_text,
                    'writer': writer,
                    'date': date,
                    'hits': hits,
                    'file_count': file_count
                }
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱: {title}")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str, url: str = None) -> dict:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 내용 추출
        content = self._extract_content(soup)
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup, url)
        
        return {
            'content': content,
            'attachments': attachments
        }
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """본문 내용 추출"""
        # CBF 상세 페이지의 본문 영역 찾기
        content_selectors = [
            '.context',
            '.content',
            '.board_content',
            '#board_content',
            '.view_content'
        ]
        
        content_area = None
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        if not content_area:
            # 대안: 첨부파일 영역 이후의 context div 찾기
            file_wrap = soup.find('div', class_='file_wrap')
            if file_wrap:
                context_div = file_wrap.find_next_sibling('div', class_='context')
                if context_div:
                    content_area = context_div
                    logger.debug("file_wrap 이후 context div를 본문으로 사용")
        
        if not content_area:
            # 마지막 대안: 전체에서 context 클래스 찾기
            context_divs = soup.find_all('div', class_='context')
            if context_divs:
                content_area = context_divs[-1]  # 마지막 context div 사용
                logger.debug("마지막 context div를 본문으로 사용")
        
        if not content_area:
            content_text = "본문 내용을 추출할 수 없습니다."
            logger.warning("본문 내용 추출 실패")
        else:
            # HTML을 마크다운으로 변환
            content_text = self.h.handle(str(content_area))
            # 과도한 줄바꿈 정리
            content_text = re.sub(r'\n{3,}', '\n\n', content_text)
        
        if not content_text or len(content_text.strip()) < 20:
            content_text = "본문 내용을 추출할 수 없습니다."
            logger.warning("본문 내용이 너무 짧습니다")
        
        return content_text.strip()
    
    def _extract_attachments(self, soup: BeautifulSoup, url: str = None) -> list:
        """첨부파일 추출 - CBF 특화 JavaScript 방식"""
        attachments = []
        
        # file_wrap 영역에서 첨부파일 링크 찾기
        file_wrap = soup.find('div', class_='file_wrap')
        if not file_wrap:
            logger.info("첨부파일 영역을 찾을 수 없습니다")
            return attachments
        
        # JavaScript 다운로드 링크 찾기: opendownload('01_05_01_00_00', 4732, 0)
        download_links = file_wrap.find_all('a', href=True)
        
        for link in download_links:
            href = link.get('href', '')
            if 'opendownload' in href:
                try:
                    # JavaScript 함수에서 파라미터 추출
                    match = re.search(r"opendownload\('([^']+)',\s*(\d+),\s*(\d+)\)", href)
                    if match:
                        bcd = match.group(1)
                        bn = match.group(2)
                        num = match.group(3)
                        
                        # 파일명 추출
                        filename = link.get_text(strip=True)
                        if not filename:
                            filename = f"attachment_{num}"
                        
                        # 다운로드 URL 구성
                        download_url = f"{self.base_url}/twb_bbs/bbs_download.php?bcd={bcd}&bn={bn}&num={num}"
                        
                        attachments.append({
                            'name': filename,
                            'url': download_url,
                            'bcd': bcd,
                            'bn': bn,
                            'num': num
                        })
                        logger.info(f"첨부파일 발견: {filename}")
                        
                except Exception as e:
                    logger.error(f"첨부파일 링크 파싱 중 오류: {e}")
                    continue
        
        logger.info(f"총 {len(attachments)}개 첨부파일 발견")
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment_info: dict = None) -> bool:
        """CBF 파일 다운로드 - 특화된 처리"""
        try:
            logger.info(f"파일 다운로드 시작: {url}")
            
            # CBF 사이트 전용 헤더 설정
            download_headers = {
                'User-Agent': self.headers['User-Agent'],
                'Referer': self.base_url + "/twb_bbs/"
            }
            
            response = self.session.get(
                url, 
                headers=download_headers, 
                stream=True, 
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            
            # 실제 파일명 추출 시도
            save_dir = os.path.dirname(save_path)
            actual_filename = self._extract_filename_from_response(response, save_dir)
            
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
    
    def _extract_filename_from_response(self, response, save_dir):
        """CBF 응답에서 파일명 추출"""
        content_disposition = response.headers.get('Content-Disposition', '')
        
        if content_disposition:
            logger.debug(f"Content-Disposition: {content_disposition}")
            
            # RFC 5987 형식 처리
            rfc5987_match = re.search(r"filename\*=([^']*)'([^']*)'(.+)", content_disposition)
            if rfc5987_match:
                encoding = rfc5987_match.group(1) or 'utf-8'
                filename = rfc5987_match.group(3)
                try:
                    filename = unquote(filename, encoding=encoding)
                    clean_filename = self.sanitize_filename(filename)
                    return os.path.join(save_dir, clean_filename)
                except Exception as e:
                    logger.debug(f"RFC 5987 파일명 처리 실패: {e}")
            
            # 일반적인 filename 파라미터 처리
            filename_match = re.search(r'filename[^;=\n]*=(([\'"]).*?\2|[^;\n]*)', content_disposition)
            if filename_match:
                filename = filename_match.group(1).strip('"\'')
                
                # 다양한 인코딩 시도
                for encoding in ['utf-8', 'euc-kr', 'cp949']:
                    try:
                        if encoding == 'utf-8':
                            decoded = filename.encode('latin-1').decode('utf-8')
                        else:
                            decoded = filename.encode('latin-1').decode(encoding)
                        
                        if decoded and not decoded.isspace():
                            clean_filename = self.sanitize_filename(decoded.replace('+', ' '))
                            return os.path.join(save_dir, clean_filename)
                    except Exception as e:
                        logger.debug(f"{encoding} 인코딩 시도 실패: {e}")
                        continue
        
        # URL에서 파일명 추출 시도
        try:
            parsed_url = urlparse(response.url)
            path_filename = os.path.basename(parsed_url.path)
            if path_filename and '.' in path_filename:
                clean_filename = self.sanitize_filename(path_filename)
                return os.path.join(save_dir, clean_filename)
        except Exception as e:
            logger.debug(f"URL에서 파일명 추출 실패: {e}")
        
        # 기본 파일명 반환
        return os.path.join(save_dir, "attachment.file")

# 하위 호환성을 위한 별칭
CbfScraper = EnhancedCbfScraper