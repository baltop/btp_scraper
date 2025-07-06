# -*- coding: utf-8 -*-
"""
YWBIC (영월군 비즈니스 인큐베이터 센터) Enhanced Scraper
"""

import requests
from bs4 import BeautifulSoup
import os
import time
import html2text
from urllib.parse import urljoin, urlparse, unquote
import re
import json
import logging
import chardet
from typing import Dict, List, Any, Optional, Union
import hashlib
from datetime import datetime
from enhanced_base_scraper import StandardTableScraper

logger = logging.getLogger(__name__)

class EnhancedYwbicScraper(StandardTableScraper):
    """YWBIC (영월군 비즈니스 인큐베이터 센터) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        
        # 기본 설정
        self.base_url = "https://ywbic.kr"
        self.list_url = "https://ywbic.kr/ywbic/bbs_list.php?code=sub01a&keyvalue=sub01"
        
        # YWBIC 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        
        # 헤더 설정 - 더 상세한 브라우저 헤더
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Cache-Control': 'max-age=0',
        })
        
        logger.info("YWBIC Enhanced Scraper 초기화 완료")

    def get_list_url(self, page_num: int = 1) -> str:
        """페이지별 목록 URL 생성"""
        if page_num == 1:
            return self.list_url
        else:
            # YWBIC는 startPage 파라미터로 페이지네이션 처리
            # 페이지당 15개씩 표시되므로 (page_num - 1) * 15
            start_page = (page_num - 1) * 15
            import base64
            # Base64 인코딩된 파라미터 생성
            params = f"startPage={start_page}&code=sub01a&table=cs_bbs_data&search_item=&search_order=&url=sub01a&keyvalue=sub01"
            encoded_params = base64.b64encode(params.encode('utf-8')).decode('utf-8')
            return f"https://ywbic.kr/ywbic/bbs_list.php?bbs_data={encoded_params}||"

    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - YWBIC 구조에 맞춤"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 테이블에서 공고 목록 찾기
        table = soup.find('table', class_='table-hover')
        if not table:
            logger.warning("공고 목록 테이블을 찾을 수 없습니다")
            return announcements
        
        tbody = table.find('tbody')
        if not tbody:
            logger.warning("tbody를 찾을 수 없습니다")
            return announcements
        
        rows = tbody.find_all('tr')
        logger.info(f"총 {len(rows)}개의 행을 발견했습니다")
        
        for i, row in enumerate(rows):
            try:
                cells = row.find_all('td')
                if len(cells) < 5:  # 번호, 제목, 작성자, 등록일, 조회 (최소 5개)
                    continue
                
                # 번호 (첫 번째 셀) - 공지 이미지 처리
                number_cell = cells[0]
                number = number_cell.get_text(strip=True)
                
                # 공지 이미지 확인
                notice_img = number_cell.find('img', src=re.compile(r'ani_arrow\.gif'))
                is_notice = notice_img is not None
                
                if is_notice:
                    number = "공지"
                elif not number:
                    number = f"row_{i}"
                
                # 제목 (두 번째 셀)
                title_cell = cells[1]
                link_elem = title_cell.find('a')
                
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                href = link_elem.get('href', '')
                
                # 상세 URL 생성
                if href.startswith('bbs_view.php'):
                    # URL 끝의 || 제거
                    clean_href = href.rstrip('|')
                    detail_url = urljoin(self.base_url, f"/ywbic/{clean_href}")
                else:
                    detail_url = urljoin(self.base_url, href)
                
                # 작성자 (세 번째 셀)
                author = cells[2].get_text(strip=True)
                
                # 등록일 (네 번째 셀)
                date = cells[3].get_text(strip=True)
                
                # 조회수 (다섯 번째 셀)
                views = cells[4].get_text(strip=True)
                
                # HOT 이미지 확인
                hot_img = title_cell.find('img', src=re.compile(r'hit3\.gif'))
                is_hot = hot_img is not None
                
                announcement = {
                    'number': number,
                    'title': title,
                    'author': author,
                    'date': date,
                    'views': views,
                    'url': detail_url,
                    'is_notice': is_notice,
                    'is_hot': is_hot,
                    'attachments': []
                }
                
                announcements.append(announcement)
                logger.info(f"공고 추가: [{number}] {title}")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류 발생: {e}")
                continue
        
        logger.info(f"총 {len(announcements)}개의 공고를 파싱했습니다")
        return announcements

    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱 - YWBIC 구조에 맞춤"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 제목 추출
        title_row = soup.find('tr', style=re.compile(r'border-top:2px solid'))
        title = ""
        if title_row:
            title_text = title_row.get_text(strip=True)
            if "제 목 :" in title_text:
                title = title_text.replace("제 목 :", "").strip()
        
        # 메타 정보 추출
        meta_info = {}
        meta_rows = soup.find_all('tr')
        for row in meta_rows:
            cells = row.find_all(['th', 'td'])
            if len(cells) >= 2:
                for i in range(0, len(cells)-1, 2):
                    key = cells[i].get_text(strip=True)
                    value = cells[i+1].get_text(strip=True)
                    meta_info[key] = value
        
        # 본문 내용 추출
        content_cell = soup.find('td', class_='img_td')
        if not content_cell:
            # img_td 클래스가 없는 경우 다른 방법으로 찾기
            content_rows = soup.find_all('tr')
            for row in content_rows:
                cells = row.find_all('td')
                if len(cells) == 1 and cells[0].get('colspan') == '4':
                    content_cell = cells[0]
                    break
        
        content = ""
        if content_cell:
            # 링크와 이미지 정보 포함하여 마크다운으로 변환
            content = self.h.handle(str(content_cell))
            content = content.strip()
        
        # 내용이 비어있다면 다른 방법들 시도
        if not content:
            # 방법 1: 본문이 있을만한 셀 찾기 (긴 텍스트가 있는 td)
            all_tds = soup.find_all('td')
            for td in all_tds:
                td_text = td.get_text(strip=True)
                # 충분히 긴 텍스트이고, 메타정보가 아닌 것
                if (len(td_text) > 100 and 
                    not any(keyword in td_text for keyword in ['작성자', '등록일', '조회', '파일', '자료 미등록'])):
                    content = self.h.handle(str(td))
                    content = content.strip()
                    break
        
        # 여전히 내용이 없다면 전체 테이블에서 추출
        if not content:
            main_table = soup.find('table', class_='table')
            if main_table:
                # 테이블의 마지막 행이 보통 본문
                rows = main_table.find_all('tr')
                if len(rows) > 3:  # 최소 4행 이상인 경우
                    last_row = rows[-1]
                    last_cell = last_row.find('td')
                    if last_cell:
                        cell_text = last_cell.get_text(strip=True)
                        if len(cell_text) > 50:  # 충분한 내용이 있다면
                            content = self.h.handle(str(last_cell))
                            content = content.strip()
        
        # 첨부파일 정보 추출
        attachments = self._extract_attachments(soup)
        
        return {
            'title': title,
            'content': content,
            'meta_info': meta_info,
            'attachments': attachments
        }

    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """첨부파일 정보 추출"""
        attachments = []
        
        # 방법 1: 다운로드 링크 직접 찾기 (bbs_download.php 포함)
        download_links = soup.find_all('a', href=re.compile(r'bbs_download\.php'))
        for link in download_links:
            href = link.get('href', '')
            filename = link.get_text(strip=True)
            
            if href and filename:
                if href.startswith('http'):
                    file_url = href
                else:
                    # YWBIC의 상대 경로를 절대 경로로 변환
                    file_url = urljoin(f"{self.base_url}/ywbic/", href)
                
                attachments.append({
                    'filename': filename,
                    'url': file_url,
                    'size': 'Unknown'
                })
                logger.info(f"첨부파일 발견: {filename} -> {file_url}")
        
        # 방법 2: 파일 확장자로 링크 찾기
        if not attachments:
            file_extension_links = soup.find_all('a', string=re.compile(r'\.(hwp|pdf|doc|docx|xls|xlsx|ppt|pptx|zip|rar)$', re.IGNORECASE))
            for link in file_extension_links:
                href = link.get('href', '')
                filename = link.get_text(strip=True)
                
                if href and filename:
                    if href.startswith('http'):
                        file_url = href
                    else:
                        file_url = urljoin(self.base_url, href)
                    
                    attachments.append({
                        'filename': filename,
                        'url': file_url,
                        'size': 'Unknown'
                    })
        
        # 방법 3: 파일 섹션에서 찾기 (기존 방법)
        if not attachments:
            file_row = soup.find('tr', string=re.compile(r'파일'))
            if not file_row:
                file_row = soup.find('th', string='파일')
                if file_row:
                    file_row = file_row.find_parent('tr')
            
            if file_row:
                file_cell = file_row.find('td')
                if file_cell:
                    file_text = file_cell.get_text(strip=True)
                    if "자료 미등록" not in file_text:
                        # 다운로드 링크 찾기
                        cell_links = file_cell.find_all('a')
                        for link in cell_links:
                            href = link.get('href', '')
                            filename = link.get_text(strip=True)
                            
                            if href and filename:
                                if href.startswith('http'):
                                    file_url = href
                                else:
                                    file_url = urljoin(self.base_url, href)
                                
                                attachments.append({
                                    'filename': filename,
                                    'url': file_url,
                                    'size': 'Unknown'
                                })
        
        return attachments

    def download_file(self, file_url: str, file_path_or_filename: str, attachment_or_save_dir=None) -> Optional[str]:
        """파일 다운로드 - Enhanced Base Scraper 호환"""
        try:
            # Enhanced Base Scraper 호출 방식 처리
            if attachment_or_save_dir is not None and isinstance(attachment_or_save_dir, dict):
                # Enhanced Base Scraper 방식: (url, full_file_path, attachment_dict)
                file_path = file_path_or_filename
                attachment = attachment_or_save_dir
                filename = attachment.get('filename', os.path.basename(file_path))
            else:
                # 기존 방식: (url, filename, save_dir)
                filename = file_path_or_filename
                save_dir = attachment_or_save_dir or "."
                file_path = os.path.join(save_dir, filename)
            
            # YWBIC 다운로드에 필요한 헤더 추가
            headers = {
                'Referer': self.list_url,
                'User-Agent': self.session.headers.get('User-Agent')
            }
            
            response = self.session.get(file_url, stream=True, timeout=self.timeout, 
                                      headers=headers, allow_redirects=True, verify=False)
            response.raise_for_status()
            
            # Content-Disposition 헤더에서 파일명 추출 시도
            content_disposition = response.headers.get('Content-Disposition', '')
            extracted_filename = None
            
            if content_disposition:
                # 다양한 파일명 인코딩 처리
                import re
                filename_match = re.search(r'filename[^;=\n]*=(.*)', content_disposition)
                if filename_match:
                    extracted_filename = filename_match.group(1).strip('\'"')
                    try:
                        # EUC-KR이나 UTF-8 디코딩 시도
                        extracted_filename = extracted_filename.encode('latin-1').decode('utf-8')
                    except:
                        try:
                            extracted_filename = extracted_filename.encode('latin-1').decode('euc-kr')
                        except:
                            extracted_filename = None
            
            # 최종 파일명 결정
            if extracted_filename:
                final_filename = self.sanitize_filename(extracted_filename)
                # 추출된 파일명으로 경로 업데이트
                if attachment_or_save_dir is not None and isinstance(attachment_or_save_dir, dict):
                    # Enhanced Base Scraper 방식
                    file_path = os.path.join(os.path.dirname(file_path), final_filename)
                else:
                    # 기존 방식
                    file_path = os.path.join(os.path.dirname(file_path), final_filename)
            
            # 디렉토리 생성
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 파일 저장
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(file_path)
            logger.info(f"파일 다운로드 완료: {os.path.basename(file_path)} ({file_size:,} bytes)")
            
            # Enhanced Base Scraper는 성공시 True 반환 기대
            if attachment_or_save_dir is not None and isinstance(attachment_or_save_dir, dict):
                return True
            else:
                return file_path
            
        except Exception as e:
            logger.error(f"파일 다운로드 실패 ({file_url}): {e}")
            # 디버깅을 위해 응답 상태 코드도 로그
            try:
                test_response = self.session.head(file_url, timeout=10, verify=False)
                logger.error(f"테스트 응답 상태: {test_response.status_code}")
            except:
                logger.error("테스트 요청도 실패")
            return None

    def sanitize_filename(self, filename: str) -> str:
        """파일명 정리 - 한글 및 특수문자 처리"""
        if not filename:
            return ""
        
        # HTML 엔티티 디코딩
        filename = html2text.html2text(filename).strip()
        
        # 금지된 문자들 제거
        forbidden_chars = '<>:"/\\|?*'
        for char in forbidden_chars:
            filename = filename.replace(char, '_')
        
        # 연속된 공백과 점 정리
        filename = re.sub(r'\s+', ' ', filename)
        filename = re.sub(r'\.+', '.', filename)
        filename = filename.strip('. ')
        
        # 파일명 길이 제한
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[:200-len(ext)] + ext
        
        return filename

def main():
    """테스트 실행"""
    print("YWBIC Enhanced Scraper 테스트 시작")
    
    scraper = EnhancedYwbicScraper()
    output_dir = "output/ywbic"
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        scraper.scrape_pages(max_pages=3, output_base=output_dir)
        print("스크래핑 완료!")
    except Exception as e:
        print(f"스크래핑 중 오류 발생: {e}")

if __name__ == "__main__":
    main()