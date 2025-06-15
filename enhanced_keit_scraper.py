# -*- coding: utf-8 -*-
"""
한국산업기술기획평가원(KEIT) Enhanced 스크래퍼
사이트: https://srome.keit.re.kr/srome/biz/perform/opnnPrpsl/retrieveTaskAnncmListView.do
"""

import requests
from bs4 import BeautifulSoup
import os
import time
import html2text
from urllib.parse import urljoin, parse_qs, urlparse
import re
import json
import logging
from enhanced_base_scraper import StandardTableScraper
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class EnhancedKEITScraper(StandardTableScraper):
    """한국산업기술기획평가원(KEIT) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://srome.keit.re.kr"
        self.list_url = "https://srome.keit.re.kr/srome/biz/perform/opnnPrpsl/retrieveTaskAnncmListView.do?prgmId=XPG201040000&rcveStatus=A"
        
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
        
        # Fallback: KEIT 특화 로직
        # KEIT는 첫 페이지와 다른 페이지가 동일한 URL을 사용
        # JavaScript로 페이지네이션이 처리될 수 있음
        return self.list_url
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: KEIT 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """KEIT 사이트 특화된 파싱 로직"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        logger.info("KEIT 목록 페이지 파싱 시작")
        
        # KEIT는 JavaScript 함수로 상세 페이지 이동
        # f_detail('I13715', '2025') 형태의 onclick 이벤트를 찾기
        onclick_elements = soup.find_all(attrs={'onclick': True})
        
        for element in onclick_elements:
            try:
                onclick = element.get('onclick', '')
                
                # f_detail 함수 호출 패턴 매칭
                detail_match = re.search(r"f_detail\s*\(\s*['\"]([^'\"]+)['\"],\s*['\"](\d{4})['\"]", onclick)
                if not detail_match:
                    continue
                
                ancm_id = detail_match.group(1)
                bsns_year = detail_match.group(2)
                
                # 제목 추출 - 여러 방법 시도
                title = ""
                
                # 1. span.title 찾기
                title_span = element.find('span', class_='title')
                if title_span:
                    title = title_span.get_text(strip=True)
                
                # 2. 요소 내 텍스트에서 추출
                if not title:
                    element_text = element.get_text(strip=True)
                    if '공고' in element_text:
                        title = element_text
                
                # 3. 부모 요소에서 찾기
                if not title and element.parent:
                    parent_text = element.parent.get_text(strip=True)
                    if '공고' in parent_text:
                        title = parent_text
                
                if not title or len(title) < 10:  # 너무 짧은 제목 제외
                    continue
                
                # 상세 페이지 URL 구성
                detail_url = f"{self.base_url}/srome/biz/perform/opnnPrpsl/retrieveTaskAnncmInfoView.do?ancmId={ancm_id}&bsnsYy={bsns_year}"
                
                # 추가 정보 추출
                parent_element = element.parent if element.parent else element
                status = self._extract_status_from_parent(parent_element)
                period = self._extract_period_from_parent(parent_element)
                date = self._extract_date_from_parent(parent_element)
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'status': status,
                    'period': period,
                    'date': date,
                    'ancm_id': ancm_id,
                    'bsns_year': bsns_year
                }
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱: {title[:50]}... - ID: {ancm_id}")
                
            except Exception as e:
                logger.error(f"공고 onclick 파싱 중 오류: {e}")
                continue
        
        logger.info(f"KEIT 목록에서 {len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def _extract_status_from_parent(self, parent) -> str:
        """부모 요소에서 상태 정보 추출"""
        if not parent:
            return ""
        
        # 접수중, 접수마감 등의 상태 찾기
        status_patterns = ['접수중', '접수마감', '접수예정', 'IRIS 공고']
        text = parent.get_text()
        
        for pattern in status_patterns:
            if pattern in text:
                return pattern
        
        return ""
    
    def _extract_period_from_parent(self, parent) -> str:
        """부모 요소에서 접수기간 추출"""
        if not parent:
            return ""
        
        text = parent.get_text()
        
        # 날짜 패턴 찾기 (YYYY-MM-DD HH:MM 형식)
        period_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s*~\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})', text)
        if period_match:
            return f"{period_match.group(1)} ~ {period_match.group(2)}"
        
        return ""
    
    def _extract_date_from_parent(self, parent) -> str:
        """부모 요소에서 등록일 추출"""
        if not parent:
            return ""
        
        text = parent.get_text()
        
        # 등록일 패턴 찾기
        date_match = re.search(r'등록일[:\s]*(\d{4}-\d{2}-\d{2})', text)
        if date_match:
            return date_match.group(1)
        
        return ""
    
    def _extract_status_from_div(self, div) -> str:
        """div에서 상태 정보 추출"""
        return self._extract_status_from_parent(div)
    
    def _extract_period_from_div(self, div) -> str:
        """div에서 접수기간 추출"""
        return self._extract_period_from_parent(div)
    
    def _extract_date_from_div(self, div) -> str:
        """div에서 등록일 추출"""
        return self._extract_date_from_parent(div)
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 내용 추출 - 여러 선택자 시도
        content = ""
        content_selectors = [
            'iframe',  # iframe 내용이 있는 경우
            '.view_content',
            '.content_area', 
            '.board_view',
            '.view_con',
            'div[class*="content"]',
            'div[class*="view"]'
        ]
        
        # iframe이 있는 경우 별도 처리
        iframe = soup.find('iframe')
        if iframe:
            iframe_src = iframe.get('src', '')
            if iframe_src:
                # iframe 내용 가져오기
                iframe_url = urljoin(self.base_url, iframe_src)
                logger.debug(f"iframe 내용 가져오기: {iframe_url}")
                
                try:
                    iframe_response = self.get_page(iframe_url)
                    if iframe_response:
                        iframe_soup = BeautifulSoup(iframe_response.text, 'html.parser')
                        # iframe 내 본문 추출
                        iframe_content = self._extract_iframe_content(iframe_soup)
                        if iframe_content:
                            content = iframe_content
                except Exception as e:
                    logger.error(f"iframe 내용 가져오기 실패: {e}")
        
        # iframe에서 내용을 얻지 못한 경우 일반적인 방법
        if not content:
            for selector in content_selectors:
                content_area = soup.select_one(selector)
                if content_area:
                    # HTML을 마크다운으로 변환
                    content = self.h.handle(str(content_area))
                    logger.debug(f"본문을 {selector} 선택자로 찾음")
                    break
        
        # 기본 추출에 실패한 경우 전체 body에서 추출
        if not content or len(content.strip()) < 100:
            logger.warning("본문 추출에 실패했습니다. 전체 페이지에서 추출을 시도합니다.")
            body = soup.find('body')
            if body:
                # 네비게이션, 헤더, 푸터 등 제거
                for elem in body.find_all(['nav', 'header', 'footer', 'aside', 'script', 'style']):
                    elem.decompose()
                
                content = self.h.handle(str(body))
        
        # 첨부파일 정보 추출
        attachments = self._extract_attachments(soup)
        
        logger.info(f"상세 페이지 파싱 완료 - 내용길이: {len(content)}, 첨부파일: {len(attachments)}개")
        
        return {
            'content': content,
            'attachments': attachments
        }
    
    def _extract_iframe_content(self, iframe_soup: BeautifulSoup) -> str:
        """iframe 내용에서 본문 추출"""
        # iframe 내의 본문 선택자들
        iframe_selectors = [
            'body',
            '.content',
            '#content',
            'div[class*="content"]',
            'div[id*="content"]'
        ]
        
        for selector in iframe_selectors:
            content_area = iframe_soup.select_one(selector)
            if content_area:
                # 불필요한 요소들 제거
                for elem in content_area.find_all(['script', 'style', 'nav', 'header', 'footer']):
                    elem.decompose()
                
                content = self.h.handle(str(content_area))
                if content and len(content.strip()) > 100:
                    logger.debug(f"iframe 본문을 {selector} 선택자로 찾음")
                    return content
        
        return ""
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """첨부파일 정보 추출"""
        attachments = []
        
        # KEIT의 f_itechFileDownload 함수를 사용하는 첨부파일 찾기
        onclick_elements = soup.find_all(attrs={'onclick': True})
        
        for element in onclick_elements:
            try:
                onclick = element.get('onclick', '')
                
                # f_itechFileDownload 함수 패턴 매칭
                download_match = re.search(r"f_itechFileDownload\s*\(\s*['\"]([^'\"]+)['\"],\s*['\"]([^'\"]+)['\"]", onclick)
                if not download_match:
                    continue
                
                param1 = download_match.group(1)  # 첫 번째 파라미터
                param2 = download_match.group(2)  # 두 번째 파라미터
                
                # 파일명 추출
                name = element.get_text(strip=True)
                
                # "다운로드" 텍스트인 경우 부모에서 파일명 찾기
                if name == "다운로드" or len(name) < 5:
                    # 부모 요소에서 파일명 찾기
                    parent = element.parent
                    if parent:
                        # 형제 요소에서 파일명 찾기
                        siblings = parent.find_all(string=True)
                        for sibling in siblings:
                            text = sibling.strip()
                            if text and text != "다운로드" and len(text) > 5:
                                # 파일 확장자가 있는지 확인
                                if any(ext in text.lower() for ext in ['.hwp', '.pdf', '.zip', '.doc', '.xlsx']):
                                    name = text
                                    break
                
                # 여전히 적절한 파일명이 없으면 스킵
                if not name or name == "다운로드" or len(name) < 5:
                    continue
                
                # 다운로드 URL 구성 (KEIT의 실제 다운로드 URL 패턴)
                # 여러 가능한 경로를 시도
                possible_urls = [
                    f"{self.base_url}/common/file/itechFileDownload.do?param1={param1}&param2={param2}",
                    f"{self.base_url}/common/itechFileDownload.do?param1={param1}&param2={param2}",
                    f"{self.base_url}/srome/common/file/itechFileDownload.do?param1={param1}&param2={param2}",
                    f"{self.base_url}/srome/biz/perform/opnnPrpsl/itechFileDownload.do?param1={param1}&param2={param2}"
                ]
                
                file_url = possible_urls[0]  # 첫 번째를 기본으로 사용
                
                attachment = {
                    'name': name,
                    'url': file_url,
                    'param1': param1,
                    'param2': param2,
                    'possible_urls': possible_urls  # 다운로드 실패시 다른 URL 시도용
                }
                
                attachments.append(attachment)
                logger.debug(f"KEIT 첨부파일 발견: {name}")
                
            except Exception as e:
                logger.error(f"첨부파일 추출 중 오류: {e}")
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
    
    def download_file(self, url: str, save_path: str, attachment_info: Dict[str, Any] = None) -> bool:
        """KEIT 특화 파일 다운로드 - 여러 URL 시도"""
        if attachment_info and 'possible_urls' in attachment_info:
            # KEIT의 경우 여러 가능한 URL을 시도
            for i, test_url in enumerate(attachment_info['possible_urls']):
                logger.info(f"다운로드 시도 {i+1}: {test_url}")
                success = super().download_file(test_url, save_path, attachment_info)
                if success:
                    return True
                else:
                    logger.warning(f"다운로드 실패 - 다음 URL 시도: {test_url}")
            
            logger.error(f"모든 다운로드 URL 시도 실패: {attachment_info['name']}")
            return False
        else:
            # 일반적인 다운로드
            return super().download_file(url, save_path, attachment_info)
    
    def _parse_js_download_url(self, onclick_content: str) -> str:
        """JavaScript onclick에서 다운로드 URL 추출"""
        # KEIT의 JavaScript 다운로드 패턴 분석
        patterns = [
            # f_itechFileDownload 패턴
            r"f_itechFileDownload\s*\(\s*['\"]([^'\"]+)['\"],\s*['\"]([^'\"]+)['\"]",
            # 일반적인 패턴들
            r"download\s*\(\s*['\"]([^'\"]+)['\"]",
            r"fileDown\s*\(\s*['\"]([^'\"]+)['\"]",
            r"location\.href\s*=\s*['\"]([^'\"]+)['\"]",
            r"window\.open\s*\(\s*['\"]([^'\"]+)['\"]"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, onclick_content, re.IGNORECASE)
            if match:
                if pattern.startswith("f_itechFileDownload"):
                    # KEIT 특화 처리
                    param1 = match.group(1)
                    param2 = match.group(2)
                    return f"{self.base_url}/common/file/itechFileDownload.do?param1={param1}&param2={param2}"
                else:
                    url_part = match.group(1)
                    if url_part.startswith('http'):
                        return url_part
                    else:
                        return urljoin(self.base_url, url_part)
        
        logger.debug(f"JavaScript 다운로드 URL 파싱 실패: {onclick_content}")
        return ""


# 하위 호환성을 위한 별칭
KEITScraper = EnhancedKEITScraper