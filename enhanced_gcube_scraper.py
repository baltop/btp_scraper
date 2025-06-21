#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GCUBE 전용 향상된 스크래퍼
Classic ASP 기반 사이트, EUC-KR 인코딩, 표준 테이블 구조
"""

import os
import logging
import re
from typing import Dict, List, Any
from urllib.parse import urljoin, unquote
from bs4 import BeautifulSoup

from enhanced_base_scraper import StandardTableScraper

logger = logging.getLogger(__name__)

class EnhancedGCUBEScraper(StandardTableScraper):
    """GCUBE 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        
        # GCUBE 사이트 기본 정보
        self.base_url = "https://gcube.or.kr:1021"
        self.list_url = "https://gcube.or.kr:1021/home/sub1/sub1.asp"
        
        # GCUBE 특화 설정
        self.verify_ssl = False  # SSL 인증서 문제로 비활성화
        self.default_encoding = 'euc-kr'  # EUC-KR 인코딩 사용
        self.timeout = 60  # 응답이 느릴 수 있어 타임아웃 증가
        self.delay_between_requests = 2  # 서버 부하 방지
        
        # User-Agent 설정 (필수)
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        self.session.headers.update(self.headers)
        
        logger.info("GCUBE 스크래퍼 초기화 완료")
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 목록 URL 생성"""
        if page_num == 1:
            return self.list_url
        else:
            # GET 파라미터: ?bseq=3&cat=-1&sk=&sv=&yy=all&page=N
            return f"{self.list_url}?bseq=3&cat=-1&sk=&sv=&yy=all&page={page_num}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - 표준 테이블 구조"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        try:
            # 테이블 찾기
            table = soup.find('table')
            if not table:
                logger.warning("테이블을 찾을 수 없습니다")
                return announcements
            
            # tbody 찾기 (있으면 사용, 없으면 table 직접 사용)
            tbody = table.find('tbody') or table
            rows = tbody.find_all('tr')
            
            logger.info(f"총 {len(rows)}개 행 발견")
            
            for row in rows:
                try:
                    cells = row.find_all('td')
                    if len(cells) < 4:  # 최소 4개 컬럼 필요
                        continue
                    
                    # 번호 컬럼 체크 (숫자가 아니면 헤더나 공지사항)
                    number_text = cells[0].get_text(strip=True)
                    if not number_text.isdigit():
                        continue
                    
                    # 제목 링크 찾기 (보통 두 번째 컬럼)
                    title_cell = cells[1]
                    link_elem = title_cell.find('a')
                    
                    if not link_elem:
                        continue
                    
                    title = link_elem.get_text(strip=True)
                    if not title:
                        continue
                    
                    # 상세 URL 구성
                    href = link_elem.get('href', '')
                    detail_url = urljoin(self.base_url, href)
                    
                    # 기본 공고 정보
                    announcement = {
                        'title': title,
                        'url': detail_url,
                        'number': number_text
                    }
                    
                    # 첨부파일 존재 여부 (이미지 아이콘으로 표시)
                    if len(cells) > 2:
                        attach_cell = cells[2]
                        has_attachment = bool(attach_cell.find('img'))
                        announcement['has_attachment'] = has_attachment
                    
                    # 작성일 (세 번째 또는 네 번째 컬럼)
                    if len(cells) > 3:
                        date_text = cells[3].get_text(strip=True)
                        if date_text:
                            announcement['date'] = date_text
                    
                    # 조회수 (있으면)
                    if len(cells) > 4:
                        views_text = cells[4].get_text(strip=True)
                        if views_text.isdigit():
                            announcement['views'] = views_text
                    
                    announcements.append(announcement)
                    logger.debug(f"공고 파싱 완료: {title}")
                    
                except Exception as e:
                    logger.error(f"행 파싱 중 오류: {e}")
                    continue
            
            logger.info(f"총 {len(announcements)}개 공고 파싱 완료")
            return announcements
            
        except Exception as e:
            logger.error(f"목록 페이지 파싱 실패: {e}")
            return announcements
    
    def parse_detail_page(self, html_content: str, detail_url: str = None) -> Dict[str, Any]:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 기본 결과 구조
        result = {
            'content': '',
            'attachments': []
        }
        
        try:
            # 본문 내용 추출 - 다양한 패턴 시도
            content_selectors = [
                'td.cont',  # 일반적인 패턴
                'td[class*="cont"]',
                '.content',
                '.board_content',
                'div.content',
                'td[height="300"]',  # 높이가 설정된 내용 셀
                'td[valign="top"]'   # 상단 정렬된 내용 셀
            ]
            
            content_elem = None
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    logger.debug(f"본문을 찾았습니다: {selector}")
                    break
            
            # 본문을 찾지 못한 경우 가장 긴 텍스트가 있는 td 찾기
            if not content_elem:
                all_tds = soup.find_all('td')
                content_elem = max(all_tds, key=lambda td: len(td.get_text(strip=True)), default=None)
                if content_elem:
                    logger.debug("가장 긴 텍스트의 td를 본문으로 사용")
            
            if content_elem:
                # HTML을 마크다운으로 변환
                content_html = str(content_elem)
                result['content'] = self.h.handle(content_html).strip()
                logger.info(f"본문 추출 완료 (길이: {len(result['content'])})")
            else:
                logger.warning("본문을 찾을 수 없습니다")
                result['content'] = "본문을 추출할 수 없습니다."
            
            # 첨부파일 추출
            result['attachments'] = self._extract_attachments(soup)
            
            return result
            
        except Exception as e:
            logger.error(f"상세 페이지 파싱 실패: {e}")
            result['content'] = f"상세 페이지 파싱 중 오류가 발생했습니다: {str(e)}"
            return result
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """첨부파일 추출"""
        attachments = []
        
        try:
            # 다운로드 링크 패턴들
            download_patterns = [
                r'/gears/lib/download\.ashx/gears_pds/board/\d+/[^"\']+',  # 직접 다운로드 링크
                r'onclick="download\([\'"]([^\'"]+)[\'"]\)',  # JavaScript 다운로드 함수
                r'href="([^"]*download[^"]*)"'  # 일반적인 다운로드 링크
            ]
            
            # article-info 영역에서 파일 링크 찾기
            info_divs = soup.find_all('div', class_='article-info')
            for info_div in info_divs:
                file_links = info_div.find_all('a', href=True)
                for link in file_links:
                    href = link.get('href', '')
                    if 'download' in href.lower():
                        file_url = urljoin(self.base_url, href)
                        filename = link.get_text(strip=True) or "첨부파일"
                        
                        attachment = {
                            'url': file_url,
                            'filename': filename
                        }
                        attachments.append(attachment)
                        logger.debug(f"첨부파일 발견: {filename}")
            
            # 전체 페이지에서 다운로드 링크 패턴 검색
            page_text = str(soup)
            for pattern in download_patterns:
                matches = re.findall(pattern, page_text)
                for match in matches:
                    if isinstance(match, tuple):
                        file_url = match[0]
                    else:
                        file_url = match
                    
                    # 상대 URL을 절대 URL로 변환
                    if not file_url.startswith('http'):
                        file_url = urljoin(self.base_url, file_url)
                    
                    # 파일명 추출
                    filename = file_url.split('/')[-1]
                    if filename:
                        try:
                            filename = unquote(filename)
                        except:
                            pass
                    else:
                        filename = "첨부파일"
                    
                    attachment = {
                        'url': file_url,
                        'filename': filename
                    }
                    
                    # 중복 체크
                    if not any(att['url'] == file_url for att in attachments):
                        attachments.append(attachment)
                        logger.debug(f"패턴으로 첨부파일 발견: {filename}")
            
            logger.info(f"총 {len(attachments)}개 첨부파일 발견")
            return attachments
            
        except Exception as e:
            logger.error(f"첨부파일 추출 중 오류: {e}")
            return attachments
    
    def download_file(self, file_url: str, file_path: str, attachment: dict = None) -> str:
        """파일 다운로드 - EUC-KR 파일명 처리"""
        try:
            logger.info(f"파일 다운로드 시작: {file_url}")
            
            # 저장 디렉토리 생성
            save_dir = os.path.dirname(file_path)
            os.makedirs(save_dir, exist_ok=True)
            
            # 다운로드 헤더 설정
            download_headers = self.headers.copy()
            download_headers['Referer'] = self.base_url
            
            response = self.session.get(
                file_url,
                headers=download_headers,
                stream=True,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            
            # Content-Disposition에서 실제 파일명 추출
            actual_filename = self._extract_filename_from_response(response, file_path)
            
            # 파일 저장
            with open(actual_filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # 파일 크기 확인
            file_size = os.path.getsize(actual_filename)
            if file_size == 0:
                os.remove(actual_filename)
                logger.warning(f"빈 파일 삭제: {actual_filename}")
                return ""
            
            logger.info(f"다운로드 완료: {actual_filename} ({file_size:,} bytes)")
            return actual_filename
            
        except Exception as e:
            logger.error(f"파일 다운로드 실패 {file_url}: {e}")
            return ""
    
    def _extract_filename_from_response(self, response, default_path):
        """응답에서 실제 파일명 추출 - EUC-KR 특화"""
        content_disposition = response.headers.get('Content-Disposition', '')
        save_dir = os.path.dirname(default_path)
        
        if content_disposition:
            # RFC 5987 형식 우선 시도
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
                
                # EUC-KR 인코딩 시도 (GCUBE는 EUC-KR 사용)
                for encoding in ['euc-kr', 'cp949', 'utf-8']:
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