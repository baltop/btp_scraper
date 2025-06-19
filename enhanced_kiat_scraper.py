# -*- coding: utf-8 -*-
"""
Enhanced KIAT Scraper - 한국산업기술진흥원 
URL: https://www.kiat.or.kr/front/board/boardContentsListPage.do?board_id=90&MenuId=b159c9dac684471b87256f1e25404f5e
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import logging
import os
from urllib.parse import urljoin, unquote
from typing import List, Dict, Any
from enhanced_base_scraper import StandardTableScraper

logger = logging.getLogger(__name__)

class EnhancedKiatScraper(StandardTableScraper):
    """KIAT 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        
        # 기본 설정
        self.base_url = "https://www.kiat.or.kr"
        self.list_url = "https://www.kiat.or.kr/front/board/boardContentsListPage.do?board_id=90&MenuId=b159c9dac684471b87256f1e25404f5e"
        self.ajax_url = "https://www.kiat.or.kr/front/board/boardContentsListAjax.do"
        
        # 사이트별 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        
        # 기본 파라미터
        self.base_params = {
            'board_id': '90',
            'MenuId': 'b159c9dac684471b87256f1e25404f5e'
        }
        
        logger.info("Enhanced KIAT 스크래퍼 초기화 완료")
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 AJAX URL 생성"""
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: AJAX URL 사용
        params = self.base_params.copy()
        params['miv_pageNo'] = str(page_num)
        
        param_str = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{self.ajax_url}?{param_str}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - AJAX 응답 처리"""
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: 사이트 특화 파싱
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """KIAT 사이트 특화 목록 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 테이블 찾기 - 여러 선택자 시도
        table = None
        for selector in ['table', '.table', '.board_table']:
            table = soup.select_one(selector)
            if table:
                logger.debug(f"테이블을 {selector} 선택자로 찾음")
                break
        
        if not table:
            logger.warning("테이블을 찾을 수 없습니다")
            return announcements
        
        # 행들 찾기
        rows = table.find_all('tr')
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 3:  # 최소 3개 열 필요
                    continue
                
                # 제목 링크 찾기 (일반적으로 두 번째 열)
                title_cell = None
                link_elem = None
                
                for cell in cells:
                    link_elem = cell.find('a')
                    if link_elem and link_elem.get('href'):
                        title_cell = cell
                        break
                
                if not link_elem:
                    continue
                
                # 제목 추출
                title = link_elem.get_text(strip=True)
                if not title or title.isspace():
                    continue
                
                # JavaScript 링크 패턴 분석
                onclick = link_elem.get('onclick', '')
                href = link_elem.get('href', '')
                
                detail_url = None
                
                # 1. href에서 JavaScript contentsView 함수 패턴 분석
                if href and 'contentsView' in href:
                    # javascript:contentsView('7a688123a8f046cb9990c0d6551ec1a7') 형태
                    match = re.search(r"contentsView\('([^']+)'\)", href)
                    if match:
                        contents_id = match.group(1)
                        # POST 요청을 위한 특별한 URL 형식 사용
                        detail_url = f"POST:{self.base_url}/front/board/boardContentsView.do:{contents_id}"
                        logger.debug(f"JavaScript href 링크 분석: {contents_id}")
                
                # 2. onclick에서 JavaScript contentsView 함수 패턴 분석
                elif onclick and 'contentsView' in onclick:
                    # contentsView('7a688123a8f046cb9990c0d6551ec1a7') 형태
                    match = re.search(r"contentsView\('([^']+)'\)", onclick)
                    if match:
                        contents_id = match.group(1)
                        # POST 요청을 위한 특별한 URL 형식 사용
                        detail_url = f"POST:{self.base_url}/front/board/boardContentsView.do:{contents_id}"
                        logger.debug(f"JavaScript onclick 링크 분석: {contents_id}")
                
                # 3. 일반적인 href 링크
                elif href and href != '#' and href != 'javascript:void(0)' and not href.startswith('javascript:'):
                    detail_url = urljoin(self.base_url, href)
                
                if not detail_url:
                    logger.warning(f"링크를 찾을 수 없습니다: {title}")
                    continue
                
                announcement = {
                    'title': title,
                    'url': detail_url
                }
                
                # 추가 정보 추출 (날짜, 상태 등)
                if len(cells) >= 3:
                    # 날짜 (일반적으로 세 번째 열)
                    date_text = cells[2].get_text(strip=True)
                    if date_text and re.match(r'\d{4}-\d{2}-\d{2}', date_text):
                        announcement['date'] = date_text
                
                if len(cells) >= 4:
                    # 접수기간 (네 번째 열)
                    period_text = cells[3].get_text(strip=True)
                    if period_text:
                        announcement['period'] = period_text
                
                if len(cells) >= 5:
                    # 상태 (다섯 번째 열)
                    status_text = cells[4].get_text(strip=True)
                    if status_text:
                        announcement['status'] = status_text
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱 완료: {title}")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 내용 추출
        content = self._extract_content(soup)
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup)
        
        return {
            'content': content,
            'attachments': attachments
        }
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """본문 내용 추출"""
        # 다양한 선택자 시도
        content_selectors = [
            '.view_content',
            '.board_view',
            '.content_area',
            '.view_area',
            '#content',
            '.table_con'
        ]
        
        content_area = None
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        if not content_area:
            # 테이블 기반 레이아웃 시도
            tables = soup.find_all('table')
            for table in tables:
                if table.find('td') and len(table.get_text(strip=True)) > 100:
                    content_area = table
                    logger.debug("테이블에서 본문 영역 찾음")
                    break
        
        if not content_area:
            logger.warning("본문 영역을 찾을 수 없습니다")
            return "본문을 추출할 수 없습니다."
        
        # HTML을 마크다운으로 변환
        try:
            content_markdown = self.h.handle(str(content_area))
            return content_markdown.strip()
        except Exception as e:
            logger.error(f"마크다운 변환 실패: {e}")
            return content_area.get_text(separator='\n', strip=True)
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """첨부파일 추출"""
        attachments = []
        
        # 첨부파일 영역 찾기
        attachment_areas = []
        
        # 1. 첨부파일 관련 클래스명으로 찾기
        for selector in ['.attach', '.file', '.attachment', '.down']:
            areas = soup.select(selector)
            attachment_areas.extend(areas)
        
        # 2. '첨부파일' 텍스트가 포함된 영역 찾기
        for elem in soup.find_all(string=re.compile(r'첨부파일|다운로드|파일')):
            parent = elem.parent
            if parent:
                attachment_areas.append(parent)
        
        # 3. 모든 링크에서 파일 확장자 패턴 찾기
        file_links = soup.find_all('a', href=re.compile(r'\.(pdf|hwp|doc|docx|xls|xlsx|ppt|pptx|zip|rar)$', re.I))
        for link in file_links:
            attachment_areas.append(link)
        
        for area in attachment_areas:
            try:
                # 링크 찾기
                links = area.find_all('a') if area.name != 'a' else [area]
                
                for link in links:
                    href = link.get('href', '')
                    if not href or href == '#':
                        continue
                    
                    # 파일명 추출
                    file_name = link.get_text(strip=True)
                    if not file_name:
                        # href에서 파일명 추출 시도
                        file_name = href.split('/')[-1]
                    
                    # 파일 확장자 확인
                    if not re.search(r'\.(pdf|hwp|doc|docx|xls|xlsx|ppt|pptx|zip|rar|txt|jpg|jpeg|png|gif)$', file_name, re.I):
                        continue
                    
                    # URL 구성
                    file_url = urljoin(self.base_url, href)
                    
                    attachment = {
                        'name': file_name,
                        'url': file_url
                    }
                    
                    attachments.append(attachment)
                    logger.debug(f"첨부파일 발견: {file_name}")
                
            except Exception as e:
                logger.error(f"첨부파일 추출 오류: {e}")
                continue
        
        # 중복 제거
        unique_attachments = []
        seen_urls = set()
        for att in attachments:
            if att['url'] not in seen_urls:
                unique_attachments.append(att)
                seen_urls.add(att['url'])
        
        logger.info(f"{len(unique_attachments)}개 첨부파일 발견")
        return unique_attachments
    
    def download_file(self, url: str, save_path: str, attachment_info: Dict[str, Any] = None) -> bool:
        """KIAT 사이트 파일 다운로드"""
        try:
            logger.info(f"파일 다운로드 시작: {url}")
            
            # 다운로드 헤더 설정
            download_headers = self.headers.copy()
            download_headers['Referer'] = self.base_url
            
            response = self.session.get(
                url,
                headers=download_headers,
                stream=True,
                timeout=60,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            
            # 파일명 처리
            save_dir = os.path.dirname(save_path)
            actual_filename = self._extract_filename_from_response(response, save_path)
            
            # 파일 저장
            with open(actual_filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(actual_filename)
            logger.info(f"다운로드 완료: {actual_filename} ({file_size:,} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"파일 다운로드 실패 {url}: {e}")
            return False
    
    def _extract_filename_from_response(self, response: requests.Response, default_path: str) -> str:
        """응답에서 파일명 추출 - 한글 처리 강화"""
        import os
        from urllib.parse import unquote
        
        save_dir = os.path.dirname(default_path)
        content_disposition = response.headers.get('Content-Disposition', '')
        
        if content_disposition:
            # RFC 5987 형식 처리
            rfc5987_match = re.search(r"filename\*=([^']*)'([^']*)'(.+)", content_disposition)
            if rfc5987_match:
                encoding, lang, filename = rfc5987_match.groups()
                try:
                    filename = unquote(filename, encoding=encoding or 'utf-8')
                    return os.path.join(save_dir, self.sanitize_filename(filename))
                except:
                    pass
            
            # 일반 filename 처리
            filename_match = re.search(r'filename[^;=\n]*=([\'"]*)(.*?)\1', content_disposition)
            if filename_match:
                filename = filename_match.group(2)
                
                # 다단계 인코딩 시도
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
        
        # 기본 파일명 사용
        return default_path
    
    def process_announcement(self, announcement, index: int, output_base: str = 'output'):
        """KIAT 사이트 특화 공고 처리 - POST 요청 지원"""
        logger.info(f"공고 처리 중 {index}: {announcement['title']}")
        
        # 폴더 생성
        folder_title = self.sanitize_filename(announcement['title'])[:200]
        folder_name = f"{index:03d}_{folder_title}"
        folder_path = os.path.join(output_base, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        # URL이 POST 형식인지 확인
        url = announcement['url']
        if url.startswith('POST:'):
            # POST:URL:contents_id 형식 파싱
            parts = url.split(':')
            if len(parts) >= 3:
                post_url = ':'.join(parts[1:3])  # http://... 부분
                contents_id = parts[3] if len(parts) > 3 else parts[2]
                
                # POST 데이터 준비
                post_data = {
                    'contents_id': contents_id,
                    'board_id': '90',
                    'MenuId': 'b159c9dac684471b87256f1e25404f5e'
                }
                
                # POST 요청 실행
                response = self.post_page(post_url, data=post_data)
                logger.info(f"POST 요청 실행: {post_url} with contents_id={contents_id}")
            else:
                logger.error(f"잘못된 POST URL 형식: {url}")
                return
        else:
            # 일반적인 GET 요청
            response = self.get_page(url)
        
        if not response:
            logger.error(f"상세 페이지 가져오기 실패: {announcement['title']}")
            return
        
        # 상세 내용 파싱
        try:
            detail = self.parse_detail_page(response.text)
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
        
        # 요청 간 대기
        if self.delay_between_requests > 0:
            time.sleep(self.delay_between_requests)


# 하위 호환성을 위한 별칭
KiatScraper = EnhancedKiatScraper