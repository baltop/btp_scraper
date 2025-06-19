#!/usr/bin/env python3
"""
CBA (충청북도 중소벤처기업진흥공단) 전용 스크래퍼 - 향상된 버전

사이트: https://www.cba.ne.kr/home/sub.php?menukey=172
특징:
- 표준 HTML 테이블 기반 게시판
- GET 파라미터 페이지네이션 (&page=N)
- 직접 링크 방식 (JavaScript 불필요)
- /base/download/bbs.php 다운로드 패턴
- UTF-8 인코딩
"""

import os
import sys
import re
import time
import logging
from typing import List, Dict, Any
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup
import requests

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.append('/home/baltop/work/bizsupnew/btp_scraper')

from enhanced_base_scraper import StandardTableScraper

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedCBAScraper(StandardTableScraper):
    """CBA 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.cba.ne.kr/home"
        self.list_url = "https://www.cba.ne.kr/home/sub.php?menukey=172"
        
        # CBA 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        
        # 요청 헤더 설정
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # 세션 설정
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - 설정 주입과 Fallback 패턴"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: CBA 특화 로직
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&page={page_num}&scode=00000004"

    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: CBA 특화 로직
        return self._parse_list_fallback(html_content)

    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """CBA 사이트별 특화된 파싱 로직"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 게시판 테이블 찾기
        table = soup.find('table')
        if not table:
            logger.warning("게시판 테이블을 찾을 수 없습니다")
            return announcements
        
        tbody = table.find('tbody') or table
        rows = tbody.find_all('tr')
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 7:  # 번호, 분류, 제목, 작성자, 등록일, 조회, 첨부
                    continue
                
                # 번호 확인 (공지글 제외)
                num_cell = cells[0]
                num_text = num_cell.get_text(strip=True)
                if not num_text.isdigit():
                    continue  # 공지글이나 기타 항목 건너뛰기
                
                # 제목 셀에서 링크와 제목 추출
                title_cell = cells[2]
                link_elem = title_cell.find('a', href=True)
                
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                href = link_elem.get('href')
                
                if not title or not href:
                    continue
                
                # 절대 URL 생성 (CBA 특화: /home/ 경로 필요)
                if href.startswith('sub.php'):
                    detail_url = f"https://www.cba.ne.kr/home/{href}"
                else:
                    detail_url = urljoin(self.base_url, href)
                
                # 분류 정보
                category = cells[1].get_text(strip=True)
                
                # 작성자, 등록일, 조회수
                author = cells[3].get_text(strip=True)
                reg_date = cells[4].get_text(strip=True)
                views = cells[5].get_text(strip=True)
                
                # 첨부파일 정보 (목록에서 바로 확인 가능)
                attach_cell = cells[6]
                has_attachment = bool(attach_cell.find('a', href=True))
                
                announcement = {
                    'number': num_text,
                    'category': category,
                    'title': title,
                    'author': author,
                    'date': reg_date,
                    'views': views,
                    'url': detail_url,
                    'has_attachment': has_attachment
                }
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱: {title}")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements

    def parse_detail_page(self, html_content: str, url: str = None) -> Dict[str, Any]:
        """상세 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용  
        if self.config and self.config.selectors:
            return super().parse_detail_page(html_content, url)
        
        # Fallback: CBA 특화 로직
        return self._parse_detail_fallback(html_content, url)

    def _parse_detail_fallback(self, html_content: str, url: str) -> Dict[str, Any]:
        """CBA 사이트별 특화된 상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 기본 정보 초기화
        result = {
            'title': '',
            'content': '',
            'attachments': [],
            'metadata': {},
            'original_url': url
        }
        
        try:
            # 제목 추출 - CBA 특화 방식
            # 첫 번째 테이블의 첫 번째 행이 제목
            tables = soup.find_all('table')
            if tables:
                first_table = tables[0]
                first_row = first_table.find('tr')
                if first_row:
                    title_cell = first_row.find('td')
                    if title_cell:
                        result['title'] = title_cell.get_text(strip=True)
                        logger.debug(f"제목 추출: {result['title']}")
            
            # 메타데이터 추출 - CBA 특화 방식
            # 첫 번째 테이블의 두 번째 행에 메타데이터가 있음
            if tables and len(tables[0].find_all('tr')) >= 2:
                meta_row = tables[0].find_all('tr')[1]
                meta_cells = meta_row.find_all('td')
                
                # 작성자, 등록일, 조회수 순서로 배치 (총 6개 셀)
                if len(meta_cells) >= 6:
                    result['metadata']['author'] = meta_cells[1].get_text(strip=True)
                    result['metadata']['date'] = meta_cells[3].get_text(strip=True)
                    result['metadata']['views'] = meta_cells[5].get_text(strip=True)
            
            # 첨부파일 추출
            result['attachments'] = self._extract_attachments(soup)
            
            # 본문 내용 추출 - CBA 특화 방식
            # CBA는 대부분 첨부파일로만 내용을 제공하므로 간단한 안내 문구 생성
            attachments = result.get('attachments', [])
            if attachments:
                content_parts = [
                    "본 공고의 상세 내용은 첨부파일을 참조하시기 바랍니다.",
                    "",
                    "**첨부파일:**"
                ]
                for i, attachment in enumerate(attachments, 1):
                    filename = attachment.get('name', f'첨부파일{i}')
                    content_parts.append(f"{i}. {filename}")
                
                result['content'] = '\n'.join(content_parts)
            else:
                result['content'] = "본 공고에 대한 상세 내용을 확인할 수 없습니다."
            
            logger.debug(f"본문 길이: {len(result['content'])} 문자")
            
        except Exception as e:
            logger.error(f"상세 페이지 파싱 중 오류: {e}")
            result['content'] = "파싱 오류로 인해 내용을 추출할 수 없습니다."
        
        return result

    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """첨부파일 추출"""
        attachments = []
        
        try:
            # /base/download/bbs.php 패턴의 다운로드 링크 찾기
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if '/base/download/bbs.php' in href:
                    # 파일명 추출
                    filename = link.get_text(strip=True)
                    if not filename:
                        # 링크 주변 텍스트에서 파일명 찾기
                        parent = link.parent
                        if parent:
                            filename = parent.get_text(strip=True)
                    
                    # 파일 크기 정보 제거
                    filename = self._clean_filename(filename)
                    
                    if filename and href:
                        file_url = urljoin("https://www.cba.ne.kr", href)
                        
                        # URL 파라미터 분석
                        parsed_url = urlparse(href)
                        query_params = parse_qs(parsed_url.query)
                        
                        attachment = {
                            'name': filename,  # 기본 스크래퍼와 호환
                            'filename': filename,  # CBA 호환
                            'url': file_url,
                            'fno': query_params.get('fno', [''])[0],
                            'bid': query_params.get('bid', [''])[0],
                            'did': query_params.get('did', [''])[0]
                        }
                        
                        attachments.append(attachment)
                        logger.debug(f"첨부파일 발견: {filename}")
            
        except Exception as e:
            logger.error(f"첨부파일 추출 중 오류: {e}")
        
        logger.info(f"{len(attachments)}개 첨부파일 발견")
        return attachments

    def _clean_filename(self, filename: str) -> str:
        """파일명 정제 - 불필요한 정보 제거"""
        if not filename:
            return ""
        
        # 파일 크기나 기타 정보 제거 (예: "파일명.pdf (1.2MB)")
        filename = re.sub(r'\s*\([^)]*\)\s*$', '', filename.strip())
        
        # 다운로드 등의 텍스트 제거
        filename = re.sub(r'^\s*(다운로드|download)\s*', '', filename, flags=re.IGNORECASE)
        
        return filename.strip()

    def download_file(self, url: str, save_path: str, attachment_info: dict = None) -> bool:
        """파일 다운로드"""
        try:
            # 디렉토리 생성
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            response = self.session.get(url, stream=True, timeout=self.timeout)
            response.raise_for_status()
            
            # Content-Disposition 헤더에서 파일명 추출 시도
            save_path = self._extract_filename_from_response(response, save_path)
            
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
        """응답 헤더에서 파일명 추출"""
        save_dir = os.path.dirname(default_path)
        
        # Content-Disposition 헤더 확인
        content_disposition = response.headers.get('Content-Disposition', '')
        
        if content_disposition:
            # RFC 5987 형식 처리 (filename*=UTF-8''%ED%95%9C%EA%B8%80.hwp)
            rfc5987_match = re.search(r"filename\*=([^']*)'([^']*)'(.+)", content_disposition)
            if rfc5987_match:
                encoding, lang, filename = rfc5987_match.groups()
                try:
                    from urllib.parse import unquote
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
CBAScraper = EnhancedCBAScraper

if __name__ == "__main__":
    # 간단한 테스트
    scraper = EnhancedCBAScraper()
    output_dir = "output/cba"
    os.makedirs(output_dir, exist_ok=True)
    
    # 1페이지 테스트
    scraper.scrape_pages(max_pages=1, output_base=output_dir)