# -*- coding: utf-8 -*-
"""
중소기업기술정보진흥원(SMTECH) Enhanced 스크래퍼
사이트: https://www.smtech.go.kr/front/ifg/no/notice02_list.do

파일 다운로드 메커니즘 분석 결과:
1. JavaScript 함수: cfn_AtchFileDownload(fileId, context, target)
2. 실제 다운로드 URL: /front/comn/AtchFileDownload.do
3. 대안 URL: /front/comn/fileDownload.do
4. 파라미터: atchFileId (GET/POST 모두 지원)
5. 첨부파일 vs 제출서류 구분 필요
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

class EnhancedSMTECHScraper(StandardTableScraper):
    """중소기업기술정보진흥원(SMTECH) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://www.smtech.go.kr"
        self.list_url = "https://www.smtech.go.kr/front/ifg/no/notice02_list.do"
        
        # 사이트 특화 설정
        self.verify_ssl = False  # SSL 인증서 문제
        self.default_encoding = 'utf-8'
        
        # 분석된 파일 다운로드 URL들 (우선순위 순)
        self.download_endpoints = [
            "/front/comn/AtchFileDownload.do",
            "/front/comn/fileDownload.do"
        ]
        
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
        
        # Fallback: SMTECH 특화 로직
        if page_num == 1:
            return self.list_url
        else:
            # JavaScript pagination이므로 POST 요청 필요할 수 있지만
            # 우선 pageIndex 파라미터로 시도
            return f"{self.list_url}?pageIndex={page_num}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: SMTECH 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """SMTECH 사이트 특화된 파싱 로직"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        logger.info("SMTECH 목록 페이지 파싱 시작")
        
        # SMTECH의 게시판 구조는 table 기반
        # notice02_detail.do 링크를 찾아서 공고 목록 추출
        
        # 테이블에서 공고 행들 찾기
        table = soup.find('table', {'summary': '사업공고 목록'}) or soup.find('table')
        
        if not table:
            logger.warning("사업공고 목록 테이블을 찾을 수 없습니다")
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
                if len(cells) < 6:  # No, 사업명, 제목, 접수기간, 공고일, 상태
                    continue
                
                # 제목 링크 찾기 (notice02_detail.do)
                title_cell = cells[2]  # 제목 컬럼
                title_link = title_cell.find('a', href=lambda x: x and 'notice02_detail.do' in x)
                
                if not title_link:
                    continue
                
                # 기본 정보 추출
                number = cells[0].get_text(strip=True)
                business_name = cells[1].get_text(strip=True)
                title = title_link.get_text(strip=True)
                reception_period = cells[3].get_text(strip=True)
                announcement_date = cells[4].get_text(strip=True)
                status = cells[5].get_text(strip=True)
                
                # URL 구성
                href = title_link.get('href')
                detail_url = urljoin(self.base_url, href)
                
                # URL에서 파라미터 추출
                parsed_url = urlparse(href)
                query_params = parse_qs(parsed_url.query)
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'business_name': business_name,
                    'reception_period': reception_period,
                    'announcement_date': announcement_date,
                    'status': status,
                    'number': number,
                    'ancmId': query_params.get('ancmId', [''])[0],
                    'buclCd': query_params.get('buclCd', [''])[0],
                    'dtlAncmSn': query_params.get('dtlAncmSn', [''])[0],
                    'pageIndex': query_params.get('pageIndex', [''])[0]
                }
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱: {title[:50]}... - 번호: {number}")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"SMTECH 목록에서 {len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 내용 추출 - SMTECH의 상세페이지는 테이블 형태
        content = ""
        
        # 공고 내용이 있는 테이블 찾기
        content_table = soup.find('table', {'summary': '사업공고 목록보기 내용'})
        
        if content_table:
            # '내용' 행에서 실제 공고 내용 추출
            content_rows = content_table.find_all('tr')
            for row in content_rows:
                th = row.find('th')
                if th and '내용' in th.get_text():
                    td = row.find('td')
                    if td:
                        # HTML을 마크다운으로 변환
                        content = self.h.handle(str(td))
                        logger.debug("본문을 '내용' 테이블 셀에서 찾음")
                        break
        
        # 기본 추출에 실패한 경우 대체 방법
        if not content or len(content.strip()) < 50:
            logger.warning("본문 추출에 실패했습니다. 대체 방법을 시도합니다.")
            
            # 텍스트가 많은 td 찾기
            all_tds = soup.find_all('td')
            best_td = None
            max_text_length = 0
            
            for td in all_tds:
                td_text = td.get_text(strip=True)
                if len(td_text) > max_text_length and len(td_text) > 50:
                    # 단순한 메타정보가 아닌지 확인
                    if not any(keyword in td_text for keyword in ['연락처', '시행기관', '접수기간']):
                        max_text_length = len(td_text)
                        best_td = td
            
            if best_td:
                content = self.h.handle(str(best_td))
                logger.info(f"대체 방법으로 본문 추출 완료 (길이: {len(content)})")
        
        # 첨부파일 정보 추출
        attachments = self._extract_attachments(soup)
        
        logger.info(f"상세 페이지 파싱 완료 - 내용길이: {len(content)}, 첨부파일: {len(attachments)}개")
        
        return {
            'content': content,
            'attachments': attachments
        }
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """첨부파일 정보 추출 - 분석된 메커니즘 적용"""
        attachments = []
        
        # SMTECH의 첨부파일은 JavaScript 함수로 다운로드
        # cfn_AtchFileDownload('파일ID','/front','fileDownFrame') 패턴
        
        # JavaScript 다운로드 링크 찾기 (더 포괄적인 검색)
        js_links = soup.find_all('a', href=lambda x: x and 'cfn_AtchFileDownload' in str(x))
        
        for link in js_links:
            try:
                href = link.get('href', '')
                name = link.get_text(strip=True)
                
                if not name or len(name) < 3:
                    continue
                
                # 제출서류 템플릿 필터링 (실제 파일이 아닌 서식 안내)
                if href == "#list" or any(keyword in name for keyword in ['서식', '양식', '템플릿']):
                    logger.debug(f"제출서류 템플릿 건너뜀: {name}")
                    continue
                
                # JavaScript 함수에서 파일 ID 추출
                # cfn_AtchFileDownload('DF2CA1CDD4664BCD3C7294CD7CB7D562','/front','fileDownFrame')
                match = re.search(r"cfn_AtchFileDownload\s*\(\s*['\"]([^'\"]+)['\"]", href)
                if match:
                    file_id = match.group(1)
                    
                    # 분석된 실제 다운로드 URL들
                    download_urls = []
                    for endpoint in self.download_endpoints:
                        download_urls.append(f"{self.base_url}{endpoint}?atchFileId={file_id}")
                    
                    attachment = {
                        'name': name,
                        'url': download_urls[0],  # 기본 URL
                        'download_urls': download_urls,  # 모든 시도할 URL들
                        'file_id': file_id,
                        'download_type': 'javascript'
                    }
                    
                    attachments.append(attachment)
                    logger.debug(f"SMTECH 첨부파일 발견: {name} (ID: {file_id})")
                
            except Exception as e:
                logger.error(f"첨부파일 추출 중 오류: {e}")
                continue
        
        # 직접 링크 방식의 첨부파일도 확인
        direct_links = soup.find_all('a', href=lambda x: x and any(ext in x.lower() for ext in ['.hwp', '.pdf', '.doc', '.zip', '.xlsx']))
        
        for link in direct_links:
            try:
                href = link.get('href')
                name = link.get_text(strip=True)
                
                if not name or len(name) < 3:
                    # 파일명이 없으면 URL에서 추출
                    name = os.path.basename(href)
                
                file_url = urljoin(self.base_url, href)
                
                attachment = {
                    'name': name,
                    'url': file_url,
                    'download_urls': [file_url],
                    'file_id': '',
                    'download_type': 'direct'
                }
                
                attachments.append(attachment)
                logger.debug(f"SMTECH 직접 링크 첨부파일 발견: {name}")
                
            except Exception as e:
                logger.error(f"직접 링크 첨부파일 추출 중 오류: {e}")
                continue
        
        # 중복 제거
        unique_attachments = []
        seen_names = set()
        for att in attachments:
            if att['name'] not in seen_names:
                unique_attachments.append(att)
                seen_names.add(att['name'])
        
        logger.info(f"총 {len(unique_attachments)}개 첨부파일 발견")
        return unique_attachments
    
    def download_file(self, url: str, save_path: str, content_type: str = None) -> bool:
        """파일 다운로드 - SMTECH 특화 처리 (분석된 메커니즘 적용)"""
        try:
            # JavaScript 다운로드인 경우 특별 처리 필요할 수 있음
            if url.startswith('javascript:'):
                logger.warning(f"JavaScript 다운로드는 지원되지 않습니다: {url}")
                return False
            
            # atchFileId 파라미터가 있는 SMTECH 파일 다운로드
            if 'atchFileId=' in url:
                return self._download_smtech_file(url, save_path)
            else:
                # 일반적인 파일 다운로드
                return super().download_file(url, save_path, content_type)
            
        except Exception as e:
            logger.error(f"SMTECH 파일 다운로드 실패 {url}: {e}")
            return False
    
    def _download_smtech_file(self, url: str, save_path: str) -> bool:
        """SMTECH 특화 파일 다운로드 (분석된 다운로드 메커니즘)"""
        # URL에서 파일 ID 추출
        match = re.search(r'atchFileId=([^&]+)', url)
        if not match:
            logger.error(f"파일 ID를 찾을 수 없습니다: {url}")
            return False
        
        file_id = match.group(1)
        logger.info(f"SMTECH 파일 다운로드 시작 (ID: {file_id})")
        
        # 분석된 다운로드 엔드포인트들을 순차적으로 시도
        for endpoint in self.download_endpoints:
            full_url = f"{self.base_url}{endpoint}"
            
            # GET 방식 시도
            try:
                get_url = f"{full_url}?atchFileId={file_id}"
                logger.debug(f"GET 방식 시도: {get_url}")
                
                response = self.session.get(
                    get_url,
                    verify=self.verify_ssl,
                    stream=True,
                    timeout=30
                )
                
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '')
                    # 파일 다운로드 성공 조건
                    if ('application' in content_type or 
                        'attachment' in response.headers.get('Content-Disposition', '')):
                        
                        # 파일명 추출
                        filename = self._extract_filename_from_response(response, save_path)
                        final_save_path = os.path.join(os.path.dirname(save_path), filename)
                        
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
                
            except Exception as e:
                logger.debug(f"GET 방식 실패 {full_url}: {e}")
            
            # POST 방식 시도
            try:
                logger.debug(f"POST 방식 시도: {full_url}")
                
                response = self.session.post(
                    full_url,
                    data={'atchFileId': file_id},
                    verify=self.verify_ssl,
                    stream=True,
                    timeout=30
                )
                
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '')
                    # 파일 다운로드 성공 조건
                    if ('application' in content_type or 
                        'attachment' in response.headers.get('Content-Disposition', '')):
                        
                        # 파일명 추출
                        filename = self._extract_filename_from_response(response, save_path)
                        final_save_path = os.path.join(os.path.dirname(save_path), filename)
                        
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
                
            except Exception as e:
                logger.debug(f"POST 방식 실패 {full_url}: {e}")
        
        logger.error(f"모든 다운로드 방식 실패 (파일 ID: {file_id})")
        return False
    
    def _extract_filename_from_response(self, response: requests.Response, default_path: str) -> str:
        """응답에서 파일명 추출 (분석된 인코딩 처리 적용)"""
        # Content-Disposition 헤더에서 파일명 추출
        content_disposition = response.headers.get('content-disposition', '')
        
        if content_disposition:
            # filename 파라미터 찾기
            filename_match = re.search(r'filename=([^;]+)', content_disposition)
            if filename_match:
                filename = filename_match.group(1).strip().strip('"')
                
                try:
                    # URL 디코딩 (한글 파일명 처리)
                    decoded_filename = unquote(filename)
                    if decoded_filename and not decoded_filename.isspace():
                        clean_filename = self.sanitize_filename(decoded_filename)
                        logger.debug(f"Content-Disposition에서 파일명 추출: {clean_filename}")
                        return clean_filename
                except Exception as e:
                    logger.debug(f"파일명 디코딩 실패: {e}")
        
        # 기본 파일명 사용
        default_filename = os.path.basename(default_path)
        logger.debug(f"기본 파일명 사용: {default_filename}")
        return self.sanitize_filename(default_filename)


# 하위 호환성을 위한 별칭
SMTECHScraper = EnhancedSMTECHScraper