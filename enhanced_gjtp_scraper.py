# -*- coding: utf-8 -*-
"""
광주테크노파크(GJTP) 전용 스크래퍼 - 향상된 버전
"""

import re
import os
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
from enhanced_base_scraper import StandardTableScraper
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class EnhancedGJTPScraper(StandardTableScraper):
    """광주테크노파크(GJTP) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://www.gjtp.or.kr"
        self.list_url = "https://www.gjtp.or.kr/home/business.cs"
        
        # 사이트 특화 설정
        self.verify_ssl = False  # SSL 인증서 문제로 비활성화
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        self.delay_between_pages = 2
        
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - 설정 주입과 Fallback 패턴"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: 사이트 특화 로직
        # GJTP 특화 페이지네이션 파라미터
        return f"{self.list_url}?searchKeyword=&pageUnit=30&pageIndex={page_num}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: 사이트 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """GJTP 특화된 파싱 로직 - 표준 HTML 테이블 기반"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # GJTP는 표준 테이블 구조
        table = soup.find('table')
        
        if not table:
            logger.warning("테이블을 찾을 수 없습니다")
            return announcements
        
        # tbody 또는 테이블 직접 검색
        tbody = table.find('tbody')
        if not tbody:
            tbody = table
        
        # 모든 tr 태그 찾기 (헤더 행 제외)
        rows = tbody.find_all('tr')
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for row_idx, row in enumerate(rows):
            try:
                # thead 내부의 실제 헤더 행만 건너뛰기 (th scope="col"이 있는 경우)
                th_col = row.find('th', scope='col')
                if th_col:
                    logger.debug(f"컬럼 헤더 행 {row_idx} 건너뛰기")
                    continue
                
                # 모든 셀 찾기 (th, td 모두 포함)
                cells = row.find_all(['th', 'td'])
                logger.debug(f"행 {row_idx}: {len(cells)}개 셀 발견")
                
                if len(cells) < 2:  # 최소한 번호와 제목은 있어야 함
                    logger.debug(f"행 {row_idx}: 셀 수 부족 ({len(cells)}개)")
                    continue
                
                # 셀 정보 디버깅
                for i, cell in enumerate(cells):
                    cell_text = cell.get_text(strip=True)[:30]
                    cell_tag = cell.name
                    cell_scope = cell.get('scope', '')
                    logger.debug(f"  셀 {i} ({cell_tag} scope='{cell_scope}'): {cell_text}")
                
                # 첫 번째 셀이 번호인지 확인 (th scope="row" 또는 td)
                first_cell_text = cells[0].get_text(strip=True)
                if not first_cell_text.isdigit():
                    logger.debug(f"행 {row_idx}: 첫 번째 셀이 번호가 아님 ({first_cell_text})")
                    continue
                
                # 제목 셀 찾기 (보통 두 번째 셀)
                title_cell = cells[1] if len(cells) > 1 else None
                if not title_cell:
                    logger.debug(f"행 {row_idx}: 제목 셀이 없음")
                    continue
                
                # 제목 링크 찾기
                title_link = title_cell.find('a')
                if not title_link:
                    logger.debug(f"행 {row_idx}: 링크가 없음")
                    continue
                
                # 제목과 URL 추출
                title = title_link.get_text(strip=True)
                href = title_link.get('href', '')
                
                if not href or not title:
                    logger.debug(f"행 {row_idx}: 제목 또는 URL이 비어있음")
                    continue
                
                # 상세 페이지 URL 생성 (상대 URL)
                detail_url = urljoin(self.list_url, href)
                logger.debug(f"상세 URL 생성: {href} -> {detail_url}")
                
                # 첨부파일 여부 확인 (제목에 첨부파일 아이콘이나 텍스트가 있는지)
                has_attachment = False
                # 패턴 1: Font Awesome 아이콘
                if title_cell.find('i', class_='fa-paperclip') or title_cell.find('i', class_='fa-file'):
                    has_attachment = True
                # 패턴 2: 이미지 아이콘
                elif title_cell.find('img', alt=re.compile(r'첨부|파일')):
                    has_attachment = True
                # 패턴 3: 텍스트 패턴
                elif re.search(r'첨부|파일|hwp|pdf|doc|xls', title, re.IGNORECASE):
                    has_attachment = True
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'category': '',  # GJTP는 카테고리 구분 없음
                    'has_attachment': has_attachment
                }
                
                # 추가 정보 추출 (GJTP 실제 구조에 맞춤)
                try:
                    # 번호 (첫 번째 셀)
                    num_text = cells[0].get_text(strip=True)
                    if num_text and num_text.isdigit():
                        announcement['number'] = int(num_text)
                    
                    # 셀이 5개 이상인 경우 (th + 4개 td)
                    if len(cells) >= 5:
                        # 공고/접수기간 (3번째 셀)
                        period = cells[2].get_text(strip=True)
                        if period:
                            # 줄바꿈 제거
                            period = period.replace('\n', ' ').replace('\r', ' ')
                            period = ' '.join(period.split())  # 연속 공백 제거
                            announcement['period'] = period
                        
                        # 담당자 (4번째 셀)
                        manager = cells[3].get_text(strip=True)
                        if manager:
                            announcement['manager'] = manager
                        
                        # 조회수 (5번째 셀)
                        views = cells[4].get_text(strip=True)
                        if views and views.isdigit():
                            announcement['views'] = int(views)
                    
                    # 접수상태 (마지막 셀)
                    if len(cells) >= 6:
                        status = cells[5].get_text(strip=True)
                        if status:
                            announcement['status'] = status
                        
                except Exception as e:
                    logger.warning(f"추가 정보 추출 중 오류: {e}")
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱 완료: {title[:50]}...")
                
            except Exception as e:
                logger.error(f"행 {row_idx} 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str, url: str = None) -> Dict[str, Any]:
        """상세 페이지 파싱 - GJTP 구조 기반"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        result = {
            'content': '',
            'attachments': []
        }
        
        # URL에서 bsnssId 추출 (첨부파일 다운로드에 필요)
        bsnss_id = None
        if url:
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            bsnss_id = query_params.get('bsnssId', [None])[0]
            logger.debug(f"URL에서 bsnssId 추출: {bsnss_id}")
        
        # GJTP 특화: 본문 영역 찾기
        # 전체 페이지에서 테이블들을 찾아 본문 구성
        content_parts = []
        
        # 기본 정보 테이블들
        tables = soup.find_all('table')
        
        for table in tables:
            # 네비게이션이나 불필요한 테이블 제외
            if table.find('a', href=re.compile(r'pageIndex|business\.cs')):
                continue
            
            # 테이블이 본문 정보를 담고 있는지 확인
            table_text = table.get_text(strip=True)
            if any(keyword in table_text for keyword in ['지원규모', '접수기간', '사업기간', '사업목적', '사업내용', '지원대상']):
                try:
                    # 테이블을 마크다운으로 변환
                    table_md = self.h.handle(str(table))
                    content_parts.append(table_md)
                    logger.debug("테이블을 본문으로 추가")
                except Exception as e:
                    logger.error(f"테이블 마크다운 변환 실패: {e}")
                    content_parts.append(table.get_text(separator='\n', strip=True))
        
        # 본문이 없으면 전체 페이지에서 추출
        if not content_parts:
            logger.warning("본문 테이블을 찾을 수 없어 전체 페이지에서 추출")
            # 불필요한 요소들 제거
            for tag in soup(['script', 'style', 'nav', 'header', 'footer', '.navigation', '.sidebar']):
                tag.decompose()
            
            # 메인 콘텐츠 영역 찾기
            main_content = soup.find('div', id='contents') or soup.find('div', class_='contents')
            if main_content:
                content_parts.append(main_content.get_text(separator='\n', strip=True))
            else:
                content_parts.append(soup.get_text(separator='\n', strip=True))
        
        result['content'] = '\n\n---\n\n'.join(content_parts)
        
        # 첨부파일 찾기 (bsnssId 전달)
        result['attachments'] = self._extract_attachments(soup, bsnss_id)
        
        logger.info(f"상세 페이지 파싱 완료 - 내용길이: {len(result['content'])}, 첨부파일: {len(result['attachments'])}")
        return result
    
    def _extract_attachments(self, soup: BeautifulSoup, bsnss_id: str = None) -> List[Dict[str, Any]]:
        """첨부파일 추출 - GJTP 구조 기반"""
        attachments = []
        
        if not bsnss_id:
            logger.warning("bsnssId가 없어 첨부파일 다운로드 URL을 생성할 수 없습니다")
            return attachments
        
        # GJTP 첨부파일 패턴: 다운로드 링크 직접 찾기
        download_links = soup.find_all('a', href=re.compile(r'act=download'))
        
        for idx, link in enumerate(download_links):
            try:
                href = link.get('href', '')
                file_name = link.get_text(strip=True)
                
                if not file_name:
                    file_name = f"attachment_{idx}"
                
                # 상대 URL을 절대 URL로 변환
                file_url = urljoin(self.base_url + '/home/business.cs', href)
                
                # URL에서 fileSn 추출
                parsed_url = urlparse(file_url)
                query_params = parse_qs(parsed_url.query)
                file_sn = query_params.get('fileSn', [str(idx)])[0]
                
                attachment = {
                    'name': file_name,
                    'url': file_url,
                    'bsnss_id': bsnss_id,
                    'file_sn': file_sn,
                    'type': 'get_download'  # GET 요청임을 표시
                }
                
                attachments.append(attachment)
                logger.debug(f"첨부파일 발견: {file_name} (bsnssId: {bsnss_id}, fileSn: {file_sn})")
                
            except Exception as e:
                logger.error(f"첨부파일 추출 중 오류: {e}")
                continue
        
        # Fallback: 파일 확장자가 포함된 링크 찾기
        if not attachments:
            logger.debug("직접 다운로드 링크를 찾지 못해 파일 확장자 기반 검색")
            
            file_links = soup.find_all('a', text=re.compile(r'\.(pdf|hwp|doc|docx|xls|xlsx|ppt|pptx|zip|rar)$', re.IGNORECASE))
            for idx, link in enumerate(file_links):
                href = link.get('href', '')
                if href:
                    file_name = link.get_text(strip=True)
                    file_url = urljoin(self.base_url, href)
                    
                    attachment = {
                        'name': file_name,
                        'url': file_url,
                        'bsnss_id': bsnss_id,
                        'file_sn': str(idx),
                        'type': 'direct_link'
                    }
                    
                    attachments.append(attachment)
                    logger.debug(f"Fallback 첨부파일 발견: {file_name}")
        
        logger.info(f"총 {len(attachments)}개 첨부파일 발견 (bsnssId: {bsnss_id})")
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment_info: dict = None) -> bool:
        """GJTP 특화 파일 다운로드 - GET 요청 처리"""
        try:
            logger.info(f"파일 다운로드 시작: {url}")
            
            # GJTP의 GET 다운로드 처리
            download_headers = self.headers.copy()
            download_headers['Referer'] = self.base_url
            
            response = self.session.get(
                url,
                headers=download_headers,
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


# 하위 호환성을 위한 별칭
GJTPScraper = EnhancedGJTPScraper