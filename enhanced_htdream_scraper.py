# -*- coding: utf-8 -*-
"""
HT Dream 전용 Enhanced 스크래퍼
사이트: https://www.htdream.kr/main/pubAmt/PubAmtList.do
특징: POST 기반 상세 페이지 접근, JavaScript 함수 기반 네비게이션
"""

from enhanced_base_scraper import StandardTableScraper
from bs4 import BeautifulSoup
import requests
import os
import re
import time
import logging
from urllib.parse import urljoin
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class EnhancedHtdreamScraper(StandardTableScraper):
    """HT Dream 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (fallback용)
        self.base_url = "https://www.htdream.kr"
        self.list_url = "https://www.htdream.kr/main/pubAmt/PubAmtList.do?searchCondition="
        
        # 사이트 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 60
        
        # HT Dream 특화 헤더
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en;q=0.6',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - GET 파라미터 기반"""
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: pageIndex 파라미터 사용
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&pageIndex={page_num}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - 테이블 기반"""
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """HT Dream 특화 목록 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 테이블 찾기
        table = soup.find('table', class_='board')
        if not table:
            logger.warning("board 클래스 테이블을 찾을 수 없습니다")
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
                if len(cells) < 6:  # 사업년도, 공지여부, 공고명, 공고기간, 신청기간, 조회수
                    continue
                
                # 공지사항 행 건너뛰기
                if 'notify' in row.get('class', []):
                    remark_span = row.find('span', class_='remark')
                    if remark_span and '공지' in remark_span.get_text():
                        logger.debug("공지사항 행 건너뛰기")
                        continue
                
                # 공고명 셀에서 링크 추출
                title_cell = cells[2]  # 세 번째 셀이 공고명
                link_elem = title_cell.find('a')
                
                if not link_elem:
                    logger.debug("링크를 찾을 수 없는 행 건너뛰기")
                    continue
                
                title = link_elem.get_text(strip=True)
                onclick = link_elem.get('onclick', '')
                
                # fn_select2('8727', 'Y') 패턴에서 파라미터 추출
                onclick_match = re.search(r"fn_select2\('([^']+)',\s*'([^']+)'\)", onclick)
                if not onclick_match:
                    logger.debug(f"onclick 패턴 매칭 실패: {onclick}")
                    continue
                
                pban_id = onclick_match.group(1)
                pban_open_yn = onclick_match.group(2)
                
                # 추가 정보 추출
                year = cells[0].get_text(strip=True)
                notice_period = cells[3].get_text(strip=True) if len(cells) > 3 else ""
                apply_period = cells[4].get_text(strip=True) if len(cells) > 4 else ""
                view_count = cells[5].get_text(strip=True) if len(cells) > 5 else ""
                
                # 상세 페이지 URL 생성 (POST 방식이지만 참조용)
                detail_url = f"{self.base_url}/main/pubAmt/addPubAmtView2.do?pbanId={pban_id}&pbanOpenYn={pban_open_yn}"
                
                announcement = {
                    'title': title,
                    'url': detail_url,  # 베이스 클래스에서 필요
                    'pban_id': pban_id,
                    'pban_open_yn': pban_open_yn,
                    'year': year,
                    'notice_period': notice_period,
                    'apply_period': apply_period,
                    'view_count': view_count,
                    'detail_url_params': {
                        'pban_id': pban_id,
                        'pban_open_yn': pban_open_yn
                    }
                }
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱: {title[:50]}...")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def fetch_detail_page(self, announcement: Dict[str, Any]) -> str:
        """상세 페이지 가져오기 - POST 요청"""
        try:
            # POST 데이터 준비
            post_data = {
                'pbanId': announcement['pban_id'],
                'pbanOpenYn': announcement['pban_open_yn'],
                'actionMode': 'view',
                'pageIndex': '1',
                'searchCtgrDsncCd1': 'on',
                'searchPmiDsncCd': '',
                'searchKeyword2': '',
                'searchKeyword3': '',
                'searchCondition': ''
            }
            
            detail_url = f"{self.base_url}/main/pubAmt/addPubAmtView2.do"
            
            logger.debug(f"상세 페이지 POST 요청: {detail_url}")
            logger.debug(f"POST 데이터: {post_data}")
            
            response = self.session.post(
                detail_url,
                data=post_data,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            
            if self.default_encoding != 'auto':
                response.encoding = self.default_encoding
            
            return response.text
            
        except Exception as e:
            logger.error(f"상세 페이지 가져오기 실패: {e}")
            return ""
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱"""
        if self.config and self.config.selectors:
            return super().parse_detail_page(html_content)
        
        return self._parse_detail_fallback(html_content)
    
    def _parse_detail_fallback(self, html_content: str) -> Dict[str, Any]:
        """HT Dream 특화 상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 추출 시도
        content_area = None
        content_selectors = [
            '.table_con',
            '.view_con', 
            '.board_view',
            '.content_area',
            '#content'
        ]
        
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        if not content_area:
            # 대안: 메인 콘텐츠 영역 찾기
            content_area = soup.find('div', class_='content')
            if not content_area:
                content_area = soup.find('div', id='content')
            if not content_area:
                # 최후 수단: body 전체
                content_area = soup.find('body')
                logger.warning("특정 본문 영역을 찾지 못해 body 전체 사용")
        
        # 본문을 마크다운으로 변환
        if content_area:
            # 불필요한 요소 제거
            for unwanted in content_area.find_all(['script', 'style', 'nav', 'header', 'footer']):
                unwanted.decompose()
            
            content_html = str(content_area)
            content_markdown = self.h.handle(content_html)
        else:
            content_markdown = "본문을 찾을 수 없습니다."
            logger.warning("본문 영역을 찾을 수 없음")
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup)
        
        # 제목 추출 시도
        title = ""
        title_selectors = ['h1', 'h2', '.title', '.subject', '.view_title']
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = title_elem.get_text(strip=True)
                if title:
                    break
        
        # URL은 베이스 클래스에서 처리되므로 현재 URL 반환
        current_url = self.base_url + "/main/pubAmt/addPubAmtView2.do"
        
        return {
            'title': title,
            'content': content_markdown,
            'attachments': attachments,
            'url': current_url
        }
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """첨부파일 추출 - HT Dream 특화"""
        attachments = []
        
        try:
            # HT Dream 특화: 첨부파일 목록 테이블에서 추출
            # 패턴: <th>첨부파일 목록</th> 이후의 tr들
            attachment_rows = []
            
            # 첨부파일 목록 헤더 찾기
            file_headers = soup.find_all('th', string=lambda text: text and '첨부파일' in text)
            for header in file_headers:
                # 해당 테이블의 모든 행 탐색
                table = header.find_parent('table')
                if table:
                    rows = table.find_all('tr')
                    for row in rows:
                        # FileCryptDown3.do 링크가 있는 행 찾기
                        crypto_links = row.find_all('a', href=lambda x: x and 'FileCryptDown3.do' in x)
                        if crypto_links:
                            attachment_rows.extend(crypto_links)
            
            # 직접 FileCryptDown3.do 링크 검색 (추가 보완)
            crypto_links = soup.find_all('a', href=lambda x: x and 'FileCryptDown3.do' in x)
            attachment_rows.extend(crypto_links)
            
            # 중복 제거
            seen_urls = set()
            for link in attachment_rows:
                href = link.get('href', '')
                if href and href not in seen_urls:
                    seen_urls.add(href)
                    
                    # 파일명 추출
                    filename = link.get_text(strip=True)
                    
                    # 파일명이 "파일다운로드" 같은 버튼 텍스트인 경우 제외
                    if not filename or '파일다운로드' in filename or len(filename) < 3:
                        # 이전 텍스트 노드에서 파일명 찾기
                        parent_td = link.find_parent('td')
                        if parent_td:
                            # td 내의 모든 텍스트에서 파일명 추출
                            td_text = parent_td.get_text(strip=True)
                            # 파일다운로드 버튼 텍스트 제거
                            filename = td_text.replace('파일다운로드', '').strip()
                            # 파일 크기 정보 제거 (예: (786KB))
                            filename = re.sub(r'\([^)]*\)', '', filename).strip()
                    
                    if filename and len(filename) > 2:
                        file_url = urljoin(self.base_url, href)
                        attachments.append({
                            'name': filename,  # 베이스 클래스 호환성
                            'filename': filename,
                            'url': file_url,
                            'type': 'crypto_download'
                        })
                        logger.debug(f"첨부파일 발견: {filename}")
            
            # 추가 패턴: 일반적인 다운로드 링크들
            general_patterns = [
                'a[href*="FileDown"]',
                'a[href*="download"]',
                'a[href*=".pdf"]',
                'a[href*=".hwp"]',
                'a[href*=".zip"]',
                'a[href*=".doc"]'
            ]
            
            for pattern in general_patterns:
                links = soup.select(pattern)
                for link in links:
                    href = link.get('href', '')
                    if href and href not in seen_urls and 'javascript:' not in href:
                        seen_urls.add(href)
                        text = link.get_text(strip=True)
                        if text and len(text) > 2 and '파일다운로드' not in text:
                            file_url = urljoin(self.base_url, href)
                            attachments.append({
                                'name': text,  # 베이스 클래스 호환성
                                'filename': text,
                                'url': file_url,
                                'type': 'general_download'
                            })
            
            logger.info(f"{len(attachments)}개 첨부파일 발견")
            for att in attachments:
                logger.debug(f"- {att['filename']} ({att['type']})")
            
        except Exception as e:
            logger.error(f"첨부파일 추출 중 오류: {e}")
        
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment: dict = None) -> bool:
        """첨부파일 다운로드 - HT Dream 특화 (암호화된 링크 지원)"""
        try:
            logger.debug(f"파일 다운로드 시작: {url}")
            
            # HT Dream의 암호화된 다운로드 링크 처리
            if 'FileCryptDown3.do' in url:
                # ARIA256 암호화된 파라미터를 그대로 사용
                response = self.session.get(
                    url,
                    timeout=self.timeout,
                    verify=self.verify_ssl,
                    stream=True,  # 대용량 파일 지원
                    headers={
                        'Referer': self.base_url + '/main/pubAmt/addPubAmtView2.do',
                        'Accept': 'application/pdf,application/zip,application/octet-stream,*/*',
                    }
                )
            else:
                # 일반 다운로드 링크
                response = self.session.get(
                    url,
                    timeout=self.timeout,
                    verify=self.verify_ssl,
                    stream=True
                )
            
            response.raise_for_status()
            
            # 파일명이 응답 헤더에 있는지 확인
            content_disposition = response.headers.get('Content-Disposition', '')
            if content_disposition and 'filename' in content_disposition:
                # 응답 헤더에서 파일명 추출 시도
                filename_match = re.search(r'filename[^;=\n]*=([\'"]*)(.*?)\1', content_disposition)
                if filename_match:
                    header_filename = filename_match.group(2)
                    # 한글 파일명 디코딩 시도
                    try:
                        decoded_filename = header_filename.encode('latin-1').decode('utf-8')
                        if decoded_filename and len(decoded_filename) > 2:
                            # 헤더의 파일명을 사용하여 저장 경로 업데이트
                            save_dir = os.path.dirname(save_path)
                            save_path = os.path.join(save_dir, self.sanitize_filename(decoded_filename))
                    except:
                        pass
            
            # 스트리밍 다운로드로 메모리 효율성 확보
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(save_path)
            logger.info(f"다운로드 완료: {save_path} ({file_size:,} bytes)")
            
            return True
            
        except Exception as e:
            logger.error(f"파일 다운로드 실패 {url}: {e}")
            # 실패한 파일 삭제
            if os.path.exists(save_path):
                try:
                    os.remove(save_path)
                except:
                    pass
            return False


# 하위 호환성을 위한 별칭
HtdreamScraper = EnhancedHtdreamScraper