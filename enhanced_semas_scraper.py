#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEMAS (중소기업유통센터) 전용 스크래퍼 - 향상된 버전

표준 테이블 기반 게시판 스크래핑
"""

import os
import re
import time
import logging
from urllib.parse import urljoin, urlparse, parse_qs, unquote
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup

from enhanced_base_scraper import StandardTableScraper

logger = logging.getLogger(__name__)


class EnhancedSEMASScraper(StandardTableScraper):
    """SEMAS 전용 스크래퍼 - 표준 테이블 기반"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://semas.or.kr"
        self.list_url = "https://semas.or.kr/web/board/webBoardList.kmdc?bCd=1&pNm=BOA0101"
        
        # SEMAS 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 2  # 정중한 스크래핑
        
        logger.info("SEMAS 스크래퍼 초기화 완료")

    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성"""
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&page={page_num}"

    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱"""
        announcements = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 게시판 테이블 찾기
            table = soup.find('table')
            if not table:
                logger.error("게시판 테이블을 찾을 수 없습니다")
                return []
            
            # tbody 찾기
            tbody = table.find('tbody')
            if not tbody:
                tbody = table  # tbody가 없는 경우 table 직접 사용
            
            rows = tbody.find_all('tr')
            
            for row in rows:
                try:
                    cells = row.find_all('td')
                    if len(cells) < 5:
                        continue
                    
                    # 번호 (첫 번째 셀)
                    number_text = cells[0].get_text(strip=True)
                    if not number_text.isdigit():
                        continue  # 공지사항 등 숫자가 아닌 행 건너뛰기
                    
                    # 제목 및 링크 (두 번째 셀)
                    title_cell = cells[1]
                    title_link = title_cell.find('a')
                    if not title_link:
                        continue
                    
                    title = title_link.get_text(strip=True)
                    href = title_link.get('href', '')
                    
                    if not href:
                        continue
                    
                    # 상세 페이지 URL 구성
                    detail_url = urljoin(self.base_url + '/web/board/', href)
                    
                    # 첨부파일 여부 (세 번째 셀)
                    file_cell = cells[2]
                    has_attachment = bool(file_cell.find('img'))
                    
                    # 등록일 (네 번째 셀)
                    date = cells[3].get_text(strip=True)
                    
                    # 조회수 (다섯 번째 셀)
                    views = cells[4].get_text(strip=True)
                    
                    announcement = {
                        'title': title,
                        'url': detail_url,
                        'number': number_text,
                        'date': date,
                        'views': views,
                        'has_attachment': has_attachment
                    }
                    
                    announcements.append(announcement)
                    
                except Exception as e:
                    logger.error(f"공고 파싱 실패: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"목록 페이지 파싱 실패: {e}")
        
        return announcements

    def parse_detail_page(self, html_content: str, detail_url: str = None) -> dict:
        """상세 페이지 파싱"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 제목 추출
            title = ""
            title_elem = soup.find('td', class_='title')
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            # 본문 내용 추출
            content = ""
            content_elem = soup.find('td', class_='cont')
            if content_elem:
                # HTML 태그 제거하고 텍스트만 추출
                content = self.h.handle(str(content_elem)).strip()
            
            # 메타 정보 추출
            meta_info = {}
            
            # 테이블에서 등록일, 조회수 등 추출
            info_rows = soup.find_all('tr')
            for row in info_rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    for i in range(0, len(cells)-1, 2):
                        key_cell = cells[i]
                        value_cell = cells[i+1]
                        
                        key = key_cell.get_text(strip=True)
                        value = value_cell.get_text(strip=True)
                        
                        if key and value and key not in ['제목', '내용']:
                            meta_info[key] = value
            
            # 첨부파일 추출
            attachments = self._extract_attachments(soup)
            
            detail_data = {
                'title': title,
                'content': content,
                'meta_info': meta_info,
                'attachments': attachments,
                'original_url': detail_url
            }
            
            return detail_data
            
        except Exception as e:
            logger.error(f"상세 페이지 파싱 실패: {e}")
            return {}

    def _extract_attachments(self, soup: BeautifulSoup) -> list:
        """첨부파일 정보 추출"""
        attachments = []
        
        try:
            # 다운로드 링크 찾기
            download_links = soup.find_all('a', href=re.compile(r'/common/download\.kmdc'))
            
            for link in download_links:
                try:
                    href = link.get('href', '')
                    filename = link.get_text(strip=True)
                    
                    if not href or not filename:
                        continue
                    
                    # 전체 URL 구성
                    file_url = urljoin(self.base_url, href)
                    
                    attachment = {
                        'filename': filename,
                        'url': file_url,
                        'original_filename': filename
                    }
                    
                    attachments.append(attachment)
                    
                except Exception as e:
                    logger.error(f"첨부파일 파싱 실패: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"첨부파일 추출 실패: {e}")
        
        return attachments

    def download_file(self, file_url: str, file_path: str, attachment: dict = None) -> str:
        """파일 다운로드"""
        try:
            # file_path는 이미 완전한 경로로 전달됨
            # 디렉토리 생성
            save_dir = os.path.dirname(file_path)
            os.makedirs(save_dir, exist_ok=True)
            
            # 파일 다운로드
            response = self.session.get(
                file_url,
                verify=self.verify_ssl,
                stream=True,
                timeout=60
            )
            
            if response.status_code == 200:
                # Content-Disposition 헤더에서 파일명 추출 시도
                content_disposition = response.headers.get('Content-Disposition', '')
                if content_disposition:
                    extracted_filename = self._extract_filename_from_response(response, save_dir)
                    if extracted_filename and extracted_filename != file_path:
                        file_path = extracted_filename
                
                # 파일 저장
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                file_size = os.path.getsize(file_path)
                if file_size > 0:
                    logger.info(f"파일 다운로드 성공: {os.path.basename(file_path)} ({file_size:,} bytes)")
                    return file_path
                else:
                    os.remove(file_path)
                    logger.error("파일 크기가 0입니다")
                    return None
            else:
                logger.error(f"파일 다운로드 실패: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"파일 다운로드 중 오류: {e}")
            return None

    def _extract_filename_from_response(self, response, save_dir):
        """HTTP 응답에서 파일명 추출"""
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
                            decoded = filename.encode('latin-1').decode('utf-8')
                        else:
                            decoded = filename.encode('latin-1').decode(encoding)
                        
                        if decoded and not decoded.isspace():
                            clean_filename = self.sanitize_filename(decoded.replace('+', ' '))
                            return os.path.join(save_dir, clean_filename)
                    except:
                        continue
        
        return None


def main():
    """테스트 실행"""
    scraper = EnhancedSEMASScraper()
    output_dir = "output/semas"
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        scraper.scrape_pages(max_pages=1, output_base=output_dir)
    except Exception as e:
        print(f"스크래핑 실패: {e}")


if __name__ == "__main__":
    main()