# -*- coding: utf-8 -*-
"""
Enhanced KOFPI 스크래퍼 - 한국임업진흥원 공지사항
"""

import requests
from bs4 import BeautifulSoup
import os
import re
import logging
from urllib.parse import urljoin, parse_qs, urlparse
from enhanced_base_scraper import StandardTableScraper
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class EnhancedKofpiScraper(StandardTableScraper):
    """KOFPI 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://www.kofpi.or.kr"
        self.list_url = "https://www.kofpi.or.kr/notice/notice_01.do"
        
        # 사이트 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        
        # 폼 데이터 관련
        self.form_data = {}
        
        logger.info("KOFPI 스크래퍼 초기화 완료")
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - JavaScript 폼 전송 방식"""
        if page_num == 1:
            return self.list_url
        else:
            # KOFPI는 POST 방식으로 페이지 이동
            return self.list_url
    
    def _get_page_announcements(self, page_num: int) -> List[Dict[str, Any]]:
        """페이지별 공고 목록 가져오기 - POST 방식 지원"""
        if page_num == 1:
            # 첫 페이지는 GET 방식
            response = self.get_page(self.list_url)
        else:
            # 2페이지부터는 POST 방식으로 폼 전송
            data = {
                'cPage': str(page_num),
                'bb_seq': '',
                'searchKey': 'total',
                'searchValue': ''
            }
            response = self.post_page(self.list_url, data=data)
        
        if not response:
            logger.warning(f"페이지 {page_num} 응답을 가져올 수 없습니다")
            return []
        
        # 페이지가 에러 상태거나 잘못된 경우 감지
        if response.status_code >= 400:
            logger.warning(f"페이지 {page_num} HTTP 에러: {response.status_code}")
            return []
        
        announcements = self.parse_list_page(response.text)
        
        # 마지막 페이지 감지
        if not announcements and page_num > 1:
            logger.info(f"페이지 {page_num}에 공고가 없어 마지막 페이지로 판단됩니다")
        
        return announcements
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - KOFPI 특화"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # KOFPI 테이블 구조 파싱
        table = soup.find('table', class_='table_list')
        if not table:
            logger.warning("table_list 클래스를 가진 테이블을 찾을 수 없습니다")
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
                if len(cells) < 5:  # 번호, 제목, 첨부파일, 조회수, 작성일
                    continue
                
                # 제목 셀에서 링크 찾기
                title_cell = cells[1]  # 두 번째 셀이 제목
                link_elem = title_cell.find('a', onclick=True)
                
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                if not title:
                    continue
                
                # onclick 속성에서 seq 추출
                onclick = link_elem.get('onclick', '')
                seq_match = re.search(r"fnGoView\('(\d+)'\)", onclick)
                if not seq_match:
                    continue
                
                seq = seq_match.group(1)
                detail_url = f"{self.base_url}/notice/notice_01view.do"
                
                # 기본 정보
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'seq': seq  # 상세 페이지 접근용
                }
                
                # 작성일 추출 (5번째 셀)
                if len(cells) >= 5:
                    date_text = cells[4].get_text(strip=True)
                    if date_text:
                        announcement['date'] = date_text
                
                # 조회수 추출 (4번째 셀)
                if len(cells) >= 4:
                    views_text = cells[3].get_text(strip=True)
                    if views_text and views_text.isdigit():
                        announcement['views'] = views_text
                
                # 첨부파일 여부 확인 (3번째 셀)
                if len(cells) >= 3:
                    attachment_cell = cells[2]
                    if attachment_cell.find('img', alt='첨부파일'):
                        announcement['has_attachment'] = True
                    else:
                        announcement['has_attachment'] = False
                
                announcements.append(announcement)
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱 - KOFPI 특화"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        result = {
            'content': '',
            'attachments': []
        }
        
        # 본문 내용 추출
        content_area = soup.find('td', class_='view_cont')
        if content_area:
            # HTML을 마크다운으로 변환
            content_html = str(content_area)
            content_md = self.h.handle(content_html)
            result['content'] = content_md.strip()
            logger.debug(f"본문을 .view_cont 선택자로 찾음")
        else:
            logger.warning("본문 영역을 찾을 수 없습니다")
            result['content'] = "본문을 찾을 수 없습니다."
        
        # 첨부파일 추출
        file_section = soup.find('th', class_='file')
        if file_section:
            file_list = file_section.find('ul', class_='infile_list')
            if file_list:
                file_links = file_list.find_all('a', onclick=True)
                
                for link in file_links:
                    onclick = link.get('onclick', '')
                    # fnNotiDownload('13901') 형태에서 seq 추출
                    seq_match = re.search(r"fnNotiDownload\('(\d+)'\)", onclick)
                    if seq_match:
                        file_seq = seq_match.group(1)
                        file_name = link.get_text(strip=True)
                        file_url = f"{self.base_url}/noti/download.do"
                        
                        result['attachments'].append({
                            'name': file_name,
                            'url': file_url,
                            'seq': file_seq
                        })
                        
                        logger.debug(f"첨부파일 발견: {file_name}")
        
        logger.info(f"상세 페이지 파싱 완료 - 내용 길이: {len(result['content'])}, 첨부파일: {len(result['attachments'])}개")
        return result
    
    def download_file(self, url: str, save_path: str, attachment_info: Dict[str, Any] = None) -> bool:
        """파일 다운로드 - KOFPI 전용 POST 방식"""
        try:
            if not attachment_info or 'seq' not in attachment_info:
                logger.error("첨부파일 seq 정보가 없습니다")
                return False
            
            logger.info(f"파일 다운로드 시작: {attachment_info['name']}")
            
            # POST 데이터로 파일 다운로드
            data = {
                'fileSeq': attachment_info['seq']
            }
            
            response = self.session.post(
                url,
                data=data,
                stream=True,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            
            # 실제 파일명 추출
            actual_filename = self._extract_filename(response, save_path)
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
    
    def get_detail_page(self, announcement: Dict[str, Any]) -> str:
        """상세 페이지 HTML 가져오기 - POST 방식"""
        try:
            data = {
                'cPage': '1',
                'bb_seq': announcement['seq'],
                'searchKey': 'total',
                'searchValue': ''
            }
            
            response = self.post_page(announcement['url'], data=data)
            if response:
                return response.text
            
        except Exception as e:
            logger.error(f"상세 페이지 가져오기 실패: {e}")
        
        return ""
    
    def process_announcement(self, announcement: Dict[str, Any], index: int, output_base: str = 'output'):
        """개별 공고 처리 - KOFPI 특화 버전"""
        logger.info(f"공고 처리 중 {index}: {announcement['title']}")
        
        # 폴더 생성
        folder_title = self.sanitize_filename(announcement['title'])[:50]
        folder_name = f"{index:03d}_{folder_title}"
        folder_path = os.path.join(output_base, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        # 상세 페이지 가져오기 (POST 방식)
        detail_html = self.get_detail_page(announcement)
        if not detail_html:
            logger.error(f"상세 페이지 가져오기 실패: {announcement['title']}")
            return
        
        # 상세 내용 파싱
        try:
            detail = self.parse_detail_page(detail_html)
            logger.info(f"상세 페이지 파싱 완료 - 내용길이: {len(detail['content'])}, 첨부파일: {len(detail['attachments'])}")
        except Exception as e:
            logger.error(f"상세 페이지 파싱 실패: {e}")
            return
        
        # 메타 정보 생성
        meta_info = self._create_meta_info(announcement)
        
        # 본문 저장
        content_path = os.path.join(folder_path, 'content.md')
        with open(content_path, 'w', encoding='utf-8') as f:
            f.write(meta_info + detail['content'])
        
        logger.info(f"내용 저장 완료: {content_path}")
        
        # 첨부파일 다운로드
        self._download_attachments(detail['attachments'], folder_path)
        
        # 처리된 제목으로 추가
        self.add_processed_title(announcement['title'])


# 하위 호환성을 위한 별칭
KofpiScraper = EnhancedKofpiScraper