# -*- coding: utf-8 -*-
"""
중소기업일자리경제진흥원(JEPA) Enhanced 스크래퍼
사이트: https://www.jepa.kr/bbs/?b_id=notice&site=new_jepa&mn=426

사이트 분석 결과:
1. 표준 테이블 기반 게시판 구조
2. 페이지네이션: offset=(page-1)*15, page=page_num
3. 직접 링크 방식 파일 다운로드
4. EUC-KR 파일명 인코딩 문제 있음
5. 세션 쿠키 관리 필요
"""

import requests
from bs4 import BeautifulSoup
import os
import time
import html2text
from urllib.parse import urljoin, parse_qs, urlparse, unquote
import re
import json
import logging
from enhanced_base_scraper import StandardTableScraper
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class EnhancedJEPAScraper(StandardTableScraper):
    """중소기업일자리경제진흥원(JEPA) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://www.jepa.kr"
        self.list_url = "https://www.jepa.kr/bbs/?b_id=notice&site=new_jepa&mn=426"
        
        # 사이트 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        
        # 헤더 설정
        self.headers.update({
            'Referer': self.base_url,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        self.session.headers.update(self.headers)
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - 설정 주입과 Fallback 패턴"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: JEPA 특화 로직 (AJAX 엔드포인트 사용)
        if page_num == 1:
            # 첫 페이지는 AJAX 엔드포인트 사용
            return f"{self.base_url}/bbs/bbs_ajax/?b_id=notice&site=new_jepa&mn=426&page=1"
        else:
            # offset = (page - 1) * 15
            offset = (page_num - 1) * 15
            return f"{self.base_url}/bbs/bbs_ajax/?b_id=notice&site=new_jepa&mn=426&type=lists&offset={offset}&page={page_num}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: JEPA 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """JEPA 사이트 특화된 파싱 로직 (AJAX 응답 파싱)"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        logger.info("JEPA 목록 페이지 파싱 시작")
        
        # JEPA의 AJAX 응답 구조: div#board_list table
        board_list_div = soup.find('div', id='board_list')
        if not board_list_div:
            # 대체 방법: class로 찾기
            board_list_div = soup.find('div', class_='board_list')
        
        if not board_list_div:
            logger.warning("board_list div를 찾을 수 없습니다")
            # 일반 테이블 찾기 시도
            table = soup.find('table')
        else:
            table = board_list_div.find('table')
        
        if not table:
            logger.warning("테이블을 찾을 수 없습니다")
            logger.debug(f"HTML 구조 확인: {str(soup)[:500]}...")
            return announcements
        
        tbody = table.find('tbody')
        if not tbody:
            logger.warning("테이블 본문(tbody)을 찾을 수 없습니다")
            return announcements
        
        rows = tbody.find_all('tr')
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 7:  # 번호, 제목, 작성자, 등록일, 첨부, 조회, 진행상태
                    continue
                
                # JEPA AJAX 응답 구조에 맞춘 파싱
                # 번호: td.t_num
                number_cell = cells[0]
                number = number_cell.get_text(strip=True)
                
                # 제목: td.t_title div.title a
                title_cell = cells[1]
                title_div = title_cell.find('div', class_='title')
                if not title_div:
                    title_div = title_cell
                
                title_link = title_div.find('a')
                if not title_link:
                    continue
                
                title = title_link.get_text(strip=True)
                
                # 작성자: td.t_user
                author = cells[2].get_text(strip=True)
                
                # 등록일: td.t_date
                date = cells[3].get_text(strip=True)
                
                # 첨부파일 여부: td.t_file img
                has_attachment = bool(cells[4].find('img'))
                
                # 조회수: td.t_hit
                views = cells[5].get_text(strip=True)
                
                # 진행상태: td 마지막 칸 (span 태그 내부)
                status_cell = cells[6]
                status_span = status_cell.find('span')
                status = status_span.get_text(strip=True) if status_span else status_cell.get_text(strip=True)
                
                # URL 구성 - AJAX 엔드포인트로 변환
                href = title_link.get('href')
                # 기존 링크를 AJAX 엔드포인트로 변환
                if href.startswith('/bbs/?'):
                    # /bbs/?b_id=notice&site=new_jepa&mn=426&type=view&bs_idx=1613
                    # -> /bbs/bbs_ajax/?b_id=notice&site=new_jepa&mn=426&type=view&bs_idx=1613
                    ajax_href = href.replace('/bbs/?', '/bbs/bbs_ajax/?')
                    detail_url = urljoin(self.base_url, ajax_href)
                else:
                    detail_url = urljoin(self.base_url, href)
                
                # URL에서 파라미터 추출
                parsed_url = urlparse(href)
                query_params = parse_qs(parsed_url.query)
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'author': author,
                    'date': date,
                    'views': views,
                    'status': status,
                    'number': number,
                    'has_attachment': has_attachment,
                    'bs_idx': query_params.get('bs_idx', [''])[0],
                    'b_id': query_params.get('b_id', [''])[0],
                    'site': query_params.get('site', [''])[0],
                    'mn': query_params.get('mn', [''])[0]
                }
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱: {title[:50]}... - 번호: {number}")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"JEPA 목록에서 {len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱 (AJAX 응답)"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 내용 추출 - JEPA AJAX 응답 구조
        content = ""
        
        # div.board_view_contents에서 본문 추출
        content_div = soup.find('div', class_='board_view_contents')
        if content_div:
            # HTML을 마크다운으로 변환
            content = self.h.handle(str(content_div))
            logger.debug("본문을 board_view_contents div에서 추출")
        
        # 기본 추출에 실패한 경우 대체 방법들
        if not content or len(content.strip()) < 50:
            logger.warning("본문 추출에 실패했습니다. 대체 방법을 시도합니다.")
            
            # 1. figure 태그들에서 본문 추출
            content_figures = soup.find_all('figure')
            if content_figures:
                # figure 태그들을 HTML로 결합
                content_html = '\n'.join(str(fig) for fig in content_figures)
                # HTML을 마크다운으로 변환
                content = self.h.handle(content_html)
                logger.debug(f"본문을 {len(content_figures)}개 figure 태그에서 추출")
            
            # 2. 여전히 실패하면 div.board_view 전체에서 추출
            if not content or len(content.strip()) < 50:
                board_view = soup.find('div', class_='board_view')
                if board_view:
                    content = self.h.handle(str(board_view))
                    logger.debug("본문을 board_view div 전체에서 추출")
            
            # 3. 최후 수단: 텍스트가 많은 div 찾기
            if not content or len(content.strip()) < 50:
                all_divs = soup.find_all('div')
                best_div = None
                max_text_length = 0
                
                for div in all_divs:
                    div_text = div.get_text(strip=True)
                    if len(div_text) > max_text_length and len(div_text) > 50:
                        # 단순한 메타정보가 아닌지 확인
                        if not any(keyword in div_text for keyword in ['작성자', '작성일', '조회수']):
                            max_text_length = len(div_text)
                            best_div = div
                
                if best_div:
                    content = self.h.handle(str(best_div))
                    logger.info(f"대체 방법으로 본문 추출 완료 (길이: {len(content)})")
        
        # 첨부파일 정보 추출
        attachments = self._extract_attachments(soup)
        
        logger.info(f"상세 페이지 파싱 완료 - 내용길이: {len(content)}, 첨부파일: {len(attachments)}개")
        
        return {
            'content': content,
            'attachments': attachments
        }
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """첨부파일 정보 추출 (AJAX 응답 구조)"""
        attachments = []
        
        # JEPA AJAX 응답의 첨부파일 구조: ul#file_list.file li a
        file_list = soup.find('ul', {'id': 'file_list', 'class': 'file'})
        if file_list:
            file_links = file_list.find_all('a')
        else:
            # 대체 방법: type=download 링크 직접 찾기
            file_links = soup.find_all('a', href=lambda x: x and 'type=download' in x)
        
        for link in file_links:
            try:
                href = link.get('href', '')
                name = link.get_text(strip=True)
                
                if not name or len(name) < 3:
                    continue
                
                # type=download 링크만 처리
                if 'type=download' not in href:
                    continue
                
                # URL 파라미터 추출
                parsed_url = urlparse(href)
                query_params = parse_qs(parsed_url.query)
                
                attachment = {
                    'name': name,
                    'url': href,
                    'download_url': urljoin(self.base_url, href),
                    'bs_idx': query_params.get('bs_idx', [''])[0],
                    'bf_idx': query_params.get('bf_idx', [''])[0],
                    'download_type': 'direct'
                }
                
                attachments.append(attachment)
                logger.debug(f"JEPA 첨부파일 발견: {name}")
                
            except Exception as e:
                logger.error(f"첨부파일 추출 중 오류: {e}")
                continue
        
        logger.info(f"총 {len(attachments)}개 첨부파일 발견")
        return attachments
    
    def download_file(self, url: str, save_path: str, content_type: str = None) -> bool:
        """파일 다운로드 - JEPA 특화 처리"""
        try:
            # JEPA 파일 다운로드 처리
            if 'type=download' in url:
                return self._download_jepa_file(url, save_path)
            else:
                # 일반적인 파일 다운로드
                return super().download_file(url, save_path, content_type)
            
        except Exception as e:
            logger.error(f"JEPA 파일 다운로드 실패 {url}: {e}")
            return False
    
    def _download_jepa_file(self, url: str, save_path: str) -> bool:
        """JEPA 특화 파일 다운로드"""
        try:
            # 절대 URL로 변환
            if not url.startswith('http'):
                full_url = urljoin(self.base_url, url)
            else:
                full_url = url
            
            logger.info(f"JEPA 파일 다운로드 시작: {full_url}")
            
            response = self.session.get(
                full_url,
                verify=self.verify_ssl,
                stream=True,
                timeout=30
            )
            
            if response.status_code == 200:
                # 파일명 추출
                filename = self._extract_filename_from_response(response, save_path)
                if filename:
                    final_save_path = os.path.join(os.path.dirname(save_path), filename)
                else:
                    final_save_path = save_path
                
                # 디렉토리 생성
                os.makedirs(os.path.dirname(final_save_path), exist_ok=True)
                
                # 파일 저장
                with open(final_save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                file_size = os.path.getsize(final_save_path)
                logger.info(f"다운로드 완료: {final_save_path} ({file_size:,} bytes)")
                return True
            else:
                logger.error(f"다운로드 실패 - HTTP {response.status_code}: {full_url}")
                return False
                
        except Exception as e:
            logger.error(f"JEPA 파일 다운로드 중 오류: {e}")
            return False
    
    def _extract_filename_from_response(self, response: requests.Response, default_path: str) -> str:
        """응답에서 파일명 추출 (JEPA EUC-KR 인코딩 처리)"""
        # Content-Disposition 헤더에서 파일명 추출
        content_disposition = response.headers.get('content-disposition', '')
        
        if content_disposition and 'filename=' in content_disposition:
            # filename 파라미터 찾기
            filename_match = re.search(r'filename=([^;]+)', content_disposition)
            if filename_match:
                filename = filename_match.group(1).strip().strip('"')
                
                try:
                    # JEPA는 EUC-KR 인코딩 문제가 있어서 여러 방법 시도
                    # 1. EUC-KR 디코딩 시도
                    decoded_filename = filename.encode('latin-1').decode('euc-kr')
                    if decoded_filename and not decoded_filename.isspace():
                        clean_filename = self.sanitize_filename(decoded_filename)
                        logger.debug(f"EUC-KR 파일명 추출: {clean_filename}")
                        return clean_filename
                except:
                    pass
                
                try:
                    # 2. UTF-8 디코딩 시도
                    decoded_filename = filename.encode('latin-1').decode('utf-8')
                    if decoded_filename and not decoded_filename.isspace():
                        clean_filename = self.sanitize_filename(decoded_filename)
                        logger.debug(f"UTF-8 파일명 추출: {clean_filename}")
                        return clean_filename
                except:
                    pass
                
                try:
                    # 3. URL 디코딩 시도
                    decoded_filename = unquote(filename)
                    if decoded_filename and not decoded_filename.isspace():
                        clean_filename = self.sanitize_filename(decoded_filename)
                        logger.debug(f"URL 디코딩 파일명 추출: {clean_filename}")
                        return clean_filename
                except:
                    pass
                
                # 4. 원본 파일명 사용 (최후 수단)
                clean_filename = self.sanitize_filename(filename)
                logger.debug(f"원본 파일명 사용: {clean_filename}")
                return clean_filename
        
        # 기본 파일명 사용
        default_filename = os.path.basename(default_path)
        logger.debug(f"기본 파일명 사용: {default_filename}")
        return self.sanitize_filename(default_filename)


# 하위 호환성을 위한 별칭
JEPAScraper = EnhancedJEPAScraper