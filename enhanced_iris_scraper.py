# -*- coding: utf-8 -*-
"""
IRIS (국가과학기술연구회) Enhanced 스크래퍼 - Spring Framework + JSON API 기반
URL: https://www.iris.go.kr/contents/retrieveBsnsAncmBtinSituListView.do
"""

import requests
from bs4 import BeautifulSoup
import re
import logging
import os
import json
import base64
from urllib.parse import urljoin, parse_qs, urlparse, unquote
from enhanced_base_scraper import StandardTableScraper
import time
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class EnhancedIrisScraper(StandardTableScraper):
    """국가과학기술연구회(IRIS) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        
        # 브라우저 환경 모방 헤더 설정
        self.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
        })
        self.session.headers.update(self.headers)
        
        # IRIS 사이트 설정
        self.base_url = "https://www.iris.go.kr"
        self.list_url = "https://www.iris.go.kr/contents/retrieveBsnsAncmBtinSituListView.do"
        self.list_api_url = "https://www.iris.go.kr/contents/retrieveBsnsAncmBtinSituList.do"
        self.detail_url = "https://www.iris.go.kr/contents/retrieveBsnsAncmView.do"
        self.download_url = "https://www.iris.go.kr/contents/downloadBsnsAncmAtchFile.do"
        
        # 사이트 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 2
        
        # 세션 데이터 캐시
        self._session_initialized = False
        
    def _initialize_session(self):
        """브라우저 환경 모방 세션 초기화"""
        if self._session_initialized:
            return True
            
        try:
            logger.info("IRIS 브라우저 세션 초기화 중...")
            
            # 1단계: 메인 페이지 방문으로 세션 수립
            response = self.session.get(self.base_url, timeout=self.timeout, verify=False)
            logger.info(f"메인 페이지 접근: {response.status_code}")
            
            # 2단계: 목록 페이지 방문
            response = self.session.get(self.list_url, timeout=self.timeout, verify=False)
            response.raise_for_status()
            logger.info(f"목록 페이지 접근: {response.status_code}")
            
            # 세션 쿠키 확인
            jsessionid = None
            for cookie in self.session.cookies:
                if cookie.name == 'JSESSIONID':
                    jsessionid = cookie.value
                    break
            
            if jsessionid:
                logger.info(f"JSESSIONID 획득: {jsessionid[:10]}...")
            else:
                logger.warning("JSESSIONID를 찾을 수 없음")
            
            self._session_initialized = True
            logger.info("IRIS 브라우저 세션 초기화 완료")
            return True
            
        except Exception as e:
            logger.error(f"세션 초기화 실패: {e}")
            return False
    
    def get_page_data(self, page_num: int) -> dict:
        """POST 요청으로 페이지 데이터 가져오기"""
        if not self._initialize_session():
            return None
            
        try:
            # IRIS POST 요청 데이터
            post_data = {
                'pageIndex': str(page_num),
                'pageUnit': '10',
                'searchKeyword': '',
                'searchCondition': '',
                'searchBgnDe': '',
                'searchEndDe': '',
                'searchMethType': 'all'
            }
            
            logger.info(f"IRIS {page_num}페이지 JSON API 요청")
            
            # AJAX 요청 헤더 설정
            ajax_headers = {
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': self.list_url,
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin'
            }
            
            response = self.session.post(
                self.list_api_url,
                data=post_data,
                headers=ajax_headers,
                timeout=self.timeout,
                verify=False
            )
            response.raise_for_status()
            
            # JSON 응답 파싱 시도
            try:
                json_data = response.json()
                return {
                    'type': 'json',
                    'data': json_data,
                    'status_code': response.status_code
                }
            except:
                # HTML 응답인 경우
                return {
                    'type': 'html',
                    'content': response.text,
                    'status_code': response.status_code
                }
            
        except Exception as e:
            logger.error(f"{page_num}페이지 데이터 가져오기 실패: {e}")
            return None
    
    def parse_list_page(self, page_data: dict) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - JSON 우선, HTML 폴백"""
        announcements = []
        
        if not page_data:
            return announcements
        
        if page_data.get('type') == 'json':
            # JSON API 응답 파싱
            announcements = self.parse_json_response(page_data['data'])
        else:
            # HTML 응답 파싱
            announcements = self.parse_html_response(page_data.get('content', ''))
        
        logger.info(f"{len(announcements)}개 IRIS 공고 파싱 완료")
        return announcements
    
    def parse_json_response(self, json_data: dict) -> List[Dict[str, Any]]:
        """JSON API 응답 파싱"""
        announcements = []
        
        try:
            # IRIS JSON 구조 분석
            items = []
            if 'resultList' in json_data:
                items = json_data['resultList']
            elif 'list' in json_data:
                items = json_data['list']
            elif 'data' in json_data:
                items = json_data['data']
            elif isinstance(json_data, list):
                items = json_data
            else:
                logger.info(f"JSON 구조: {list(json_data.keys())}")
                # 중첩된 구조 탐색
                for key, value in json_data.items():
                    if isinstance(value, list) and len(value) > 0:
                        items = value
                        logger.info(f"'{key}' 키에서 목록 발견: {len(items)}개")
                        break
            
            if not items:
                logger.warning("JSON에서 공고 목록을 찾을 수 없습니다")
                return announcements
            
            logger.info(f"JSON에서 {len(items)}개 공고 발견")
            
            for item in items:
                try:
                    # IRIS JSON 구조 디버깅
                    logger.debug(f"항목 키들: {list(item.keys())}")
                    
                    # 제목 추출 (IRIS 특화 필드명)
                    title_fields = ['ancmTl', 'title', 'ancmTitle', 'ancmNm', 'subjectNm', 'subject', 'name', 'bsnsNm', 'ancmSj']
                    title = None
                    for field in title_fields:
                        if field in item and item[field]:
                            title = str(item[field]).strip()
                            logger.debug(f"제목 필드 '{field}'에서 발견: {title}")
                            break
                    
                    if not title:
                        logger.debug(f"제목을 찾을 수 없음. 사용 가능한 키: {list(item.keys())}")
                        continue
                    
                    # 공고 ID 추출 (IRIS 특화 필드명)
                    id_fields = ['ancmId', 'ancmNo', 'id', 'seq', 'idx', 'no', 'bsnsAncmId']
                    announcement_id = None
                    for field in id_fields:
                        if field in item and item[field]:
                            announcement_id = str(item[field])
                            logger.debug(f"ID 필드 '{field}'에서 발견: {announcement_id}")
                            break
                    
                    if not announcement_id:
                        logger.debug(f"ID를 찾을 수 없음. 사용 가능한 키: {list(item.keys())}")
                        continue
                    
                    announcement = {
                        'title': title,
                        'id': announcement_id,
                        'url': self.detail_url
                    }
                    
                    # 추가 메타 정보 (IRIS 특화 필드명)
                    date_fields = ['ancmDe', 'regDt', 'ancmBgnDt', 'createDt', 'regDate']
                    for field in date_fields:
                        if field in item and item[field]:
                            announcement['date'] = str(item[field])
                            break
                    
                    # 공고 번호
                    if 'ancmNo' in item and item['ancmNo']:
                        announcement['announcement_no'] = str(item['ancmNo'])
                    
                    # 소관기관
                    if 'sorgnNm' in item and item['sorgnNm']:
                        announcement['institution'] = str(item['sorgnNm'])
                    
                    # 부처 구분
                    if 'blngGovdSeNm' in item and item['blngGovdSeNm']:
                        announcement['department'] = str(item['blngGovdSeNm'])
                    
                    # 공고 상태
                    if 'rcveSttSeNmLst' in item and item['rcveSttSeNmLst']:
                        announcement['status'] = str(item['rcveSttSeNmLst'])
                    
                    announcements.append(announcement)
                    logger.debug(f"JSON 공고 파싱: {title[:50]}...")
                    
                except Exception as e:
                    logger.debug(f"JSON 항목 파싱 중 오류: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"JSON 응답 파싱 실패: {e}")
        
        return announcements
    
    def parse_html_response(self, html_content: str) -> List[Dict[str, Any]]:
        """HTML 응답 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # IRIS HTML 구조 분석
        list_selectors = [
            'ul.list li',
            'div.list-wrap .list-item',
            'ul.board-list li',
            'div.board-list .item',
            'table tbody tr',
            '.content-area ul li',
            'ul li',
            '.announcement-list .item'
        ]
        
        items = []
        for selector in list_selectors:
            items = soup.select(selector)
            if len(items) > 0:
                logger.debug(f"IRIS HTML 목록을 {selector} 선택자로 찾음: {len(items)}개")
                break
        
        if not items:
            logger.warning("IRIS HTML 목록 항목을 찾을 수 없습니다")
            return self._fallback_parse_links(soup)
        
        for item in items:
            try:
                # 제목 링크 찾기
                title_elem = item.find('a') or item.find('h3') or item.find('h4')
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                if not title or len(title) < 3:
                    continue
                
                # 공고 ID 추출
                announcement_id = None
                onclick = title_elem.get('onclick', '')
                href = title_elem.get('href', '')
                
                # JavaScript 함수에서 ID 추출
                if onclick:
                    id_patterns = [
                        r"retrieveBsnsAncmView\('([^']+)'\)",
                        r"goDetail\('([^']+)'\)",
                        r"viewDetail\('([^']+)'\)",
                        r"'([^']+)'"
                    ]
                    
                    for pattern in id_patterns:
                        match = re.search(pattern, onclick)
                        if match:
                            announcement_id = match.group(1)
                            break
                
                if not announcement_id and href:
                    id_match = re.search(r'[?&]id=([^&]+)', href)
                    if id_match:
                        announcement_id = id_match.group(1)
                
                if not announcement_id:
                    continue
                
                announcement = {
                    'title': title,
                    'id': announcement_id,
                    'url': self.detail_url
                }
                
                # 메타 정보 추출
                self._extract_meta_info_from_item(item, announcement)
                
                announcements.append(announcement)
                logger.debug(f"HTML 공고 파싱: {title[:50]}...")
                
            except Exception as e:
                logger.debug(f"HTML 항목 파싱 중 오류: {e}")
                continue
        
        return announcements
    
    def _fallback_parse_links(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """대안 파싱: JavaScript 함수 호출 링크 찾기"""
        announcements = []
        
        js_links = soup.find_all('a', onclick=re.compile(r'retrieveBsnsAncmView|goDetail|viewDetail'))
        logger.info(f"JavaScript 링크 {len(js_links)}개 발견 (HTML 대안 방법)")
        
        for link in js_links:
            try:
                title = link.get_text(strip=True)
                if not title or len(title) < 3:
                    continue
                
                onclick = link.get('onclick', '')
                id_match = re.search(r"'([^']+)'", onclick)
                if id_match:
                    announcement_id = id_match.group(1)
                    
                    announcement = {
                        'title': title,
                        'id': announcement_id,
                        'url': self.detail_url
                    }
                    
                    announcements.append(announcement)
                    
            except Exception as e:
                logger.debug(f"링크 파싱 중 오류: {e}")
                continue
        
        return announcements
    
    def _extract_meta_info_from_item(self, item, announcement: Dict[str, Any]):
        """HTML 항목에서 메타 정보 추출"""
        try:
            item_text = item.get_text()
            
            # 날짜 패턴 추출
            date_patterns = [
                r'(\d{4}-\d{2}-\d{2})',
                r'(\d{4}\.\d{2}\.\d{2})',
                r'(\d{4}/\d{2}/\d{2})'
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, item_text)
                if match:
                    announcement['date'] = match.group(1)
                    break
            
            # 상태 정보 추출
            if '모집중' in item_text:
                announcement['status'] = '모집중'
            elif '마감' in item_text:
                announcement['status'] = '마감'
            elif '종료' in item_text:
                announcement['status'] = '종료'
                
        except Exception as e:
            logger.debug(f"메타 정보 추출 중 오류: {e}")
    
    def get_detail_content(self, announcement: Dict[str, Any]) -> Dict[str, Any]:
        """POST 요청으로 상세 페이지 데이터 가져오기"""
        try:
            announcement_id = announcement.get('id')
            if not announcement_id:
                logger.error("공고 ID가 없습니다")
                return {'content': '', 'attachments': []}
            
            post_data = {
                'ancmId': announcement_id,
                'pageIndex': '1'
            }
            
            logger.info(f"상세 페이지 요청: {announcement_id}")
            
            # 상세 페이지 요청 헤더
            detail_headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': self.list_url,
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1'
            }
            
            response = self.session.post(
                self.detail_url,
                data=post_data,
                headers=detail_headers,
                timeout=self.timeout,
                verify=False
            )
            response.raise_for_status()
            
            return self.parse_detail_page(response.text)
            
        except Exception as e:
            logger.error(f"상세 페이지 가져오기 실패: {e}")
            return {'content': '', 'attachments': []}
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        result = {
            'content': '',
            'attachments': []
        }
        
        try:
            # 본문 내용 추출
            content_text = self._extract_content(soup)
            result['content'] = content_text
            
            # 첨부파일 추출
            attachments = self._extract_attachments(soup)
            result['attachments'] = attachments
            
            logger.info(f"IRIS 상세 페이지 파싱 완료 - 내용: {len(content_text)}자, 첨부파일: {len(attachments)}개")
            
        except Exception as e:
            logger.error(f"IRIS 상세 페이지 파싱 실패: {e}")
        
        return result
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """본문 내용 추출"""
        content_parts = []
        
        # IRIS 본문 영역 찾기
        content_selectors = [
            '.content-area',
            '.view-content',
            '.detail-content', 
            '.board-content',
            'article',
            '.post-content',
            '#content'
        ]
        
        main_content = None
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        if main_content:
            # HTML을 마크다운으로 변환
            content_html = str(main_content)
            markdown_content = self.h.handle(content_html)
            content_parts.append(markdown_content)
        else:
            # 폴백: 의미있는 텍스트 블록 추출
            for tag in soup.find_all(['script', 'style', 'nav', 'header', 'footer']):
                tag.decompose()
            
            text_blocks = []
            for element in soup.find_all(['p', 'div', 'section']):
                text = element.get_text(strip=True)
                if text and len(text) > 30:
                    text_blocks.append(text)
            
            if text_blocks:
                content_parts.extend(text_blocks[:10])
        
        return '\n\n'.join(content_parts)
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """첨부파일 추출"""
        attachments = []
        
        try:
            # href 속성에서 JavaScript 함수 호출 찾기 (IRIS는 href에 JavaScript 사용)
            all_links = soup.find_all('a')
            
            for link in all_links:
                try:
                    href = link.get('href', '')
                    onclick = link.get('onclick', '')
                    file_name = link.get_text(strip=True)
                    
                    # href나 onclick에서 JavaScript 함수 찾기
                    js_content = href + ' ' + onclick
                    
                    # JavaScript 함수에서 파라미터 추출
                    param_patterns = [
                        r"f_bsnsAncm_downloadAtchFile\('([^']+)','([^']+)','([^']+)'\s*,\s*'([^']+)'\)",
                        r"downloadAtchFile\('([^']+)','([^']+)','([^']+)','([^']+)'\)",
                        r"download\('([^']+)'\)"
                    ]
                    
                    download_params = None
                    for pattern in param_patterns:
                        match = re.search(pattern, js_content)
                        if match:
                            download_params = match.groups()
                            break
                    
                    if download_params and file_name:
                        # 파일 확장자 확인
                        if any(ext in file_name.lower() for ext in ['.pdf', '.hwp', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.ppt', '.pptx']):
                            attachment = {
                                'name': file_name,
                                'url': self.download_url,
                                'params': download_params,
                                'type': 'javascript',
                                'file_group_id': download_params[0] if len(download_params) > 0 else '',
                                'file_detail_id': download_params[1] if len(download_params) > 1 else '',
                                'file_size': download_params[3] if len(download_params) > 3 else ''
                            }
                            attachments.append(attachment)
                            logger.debug(f"첨부파일 발견: {file_name}")
                
                except Exception as e:
                    logger.debug(f"첨부파일 링크 처리 중 오류: {e}")
                    continue
            
            logger.info(f"{len(attachments)}개 첨부파일 발견")
            
        except Exception as e:
            logger.error(f"첨부파일 추출 중 오류: {e}")
        
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment_info: Dict[str, Any] = None) -> bool:
        """파일 다운로드 - IRIS JavaScript 함수 파라미터 사용"""
        try:
            if attachment_info and attachment_info.get('type') == 'javascript':
                # IRIS 첨부파일 다운로드 시도
                params = attachment_info.get('params', [])
                if len(params) >= 2:
                    file_group_id = params[0]  # atchFileId
                    file_detail_id = params[1]  # fileSn
                    
                    logger.info(f"IRIS 파일 다운로드 시도: {attachment_info.get('name', 'unknown')}")
                    
                    # POST 데이터 구성
                    download_data = {
                        'atchFileId': file_group_id,
                        'fileSn': file_detail_id
                    }
                    
                    # 브라우저 환경과 동일한 헤더로 GET 요청 시도
                    # IRIS는 실제로 downloadBsnsAncmAtchFile.do를 GET으로 호출
                    download_url_with_params = f"{self.download_url}?atchFileId={file_group_id}&fileSn={file_detail_id}"
                    
                    download_headers = {
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Referer': f"{self.detail_url}",
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'same-origin',
                        'Sec-Fetch-User': '?1',
                        'Upgrade-Insecure-Requests': '1',
                        'Cache-Control': 'max-age=0'
                    }
                    
                    try:
                        logger.info(f"IRIS 파일 다운로드 시도 (GET 방식): {attachment_info.get('name')}")
                        logger.info(f"다운로드 URL: {download_url_with_params}")
                        
                        response = self.session.get(
                            download_url_with_params,
                            headers=download_headers,
                            stream=True,
                            timeout=120,
                            verify=False
                        )
                        
                        logger.info(f"응답 상태: {response.status_code}")
                        logger.info(f"Content-Type: {response.headers.get('Content-Type', 'unknown')}")
                        logger.info(f"Content-Length: {response.headers.get('Content-Length', 'unknown')}")
                        
                        if response.status_code == 200:
                            content_type = response.headers.get('Content-Type', '')
                            content_length = response.headers.get('Content-Length', '0')
                            content_disposition = response.headers.get('Content-Disposition', '')
                            
                            # 파일인지 확인 (더 엄격한 기준)
                            is_file = False
                            if content_disposition and 'attachment' in content_disposition:
                                is_file = True
                            elif ('application' in content_type or 
                                  'hwp' in content_type or 
                                  'pdf' in content_type or
                                  'zip' in content_type or
                                  'msword' in content_type or
                                  'excel' in content_type or
                                  'octet-stream' in content_type):
                                is_file = True
                            elif content_length.isdigit() and int(content_length) > 1000:
                                is_file = True
                            
                            if is_file:
                                # 파일 저장
                                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                                with open(save_path, 'wb') as f:
                                    for chunk in response.iter_content(chunk_size=8192):
                                        if chunk:
                                            f.write(chunk)
                                
                                file_size = os.path.getsize(save_path)
                                if file_size > 0:
                                    logger.info(f"다운로드 성공: {save_path} ({file_size:,} bytes)")
                                    return True
                                else:
                                    logger.warning("다운로드된 파일이 비어있음")
                                    os.remove(save_path)
                            else:
                                # HTML 응답인 경우 에러 메시지 확인
                                response_text = response.text[:500]
                                if 'error' in response_text.lower() or 'exception' in response_text.lower():
                                    logger.warning(f"서버 에러 응답: {response_text}")
                                else:
                                    logger.warning(f"HTML 응답 (파일 아님): {response_text}")
                        else:
                            logger.warning(f"다운로드 실패 (HTTP {response.status_code}): {response.text[:200]}")
                            
                    except Exception as e:
                        logger.warning(f"다운로드 중 예외 발생: {e}")
                        return False
                    
                    # 모든 시도 실패 시 메타데이터만 저장
                    logger.warning("모든 다운로드 시도 실패, 메타데이터만 저장")
                    return False
                else:
                    logger.warning("다운로드 파라미터가 부족합니다")
                    return False
            
            # 직접 링크 다운로드 시도
            response = self.session.get(url, stream=True, timeout=120)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(save_path)
            logger.info(f"다운로드 완료: {save_path} ({file_size:,} bytes)")
            return True
            
        except Exception as e:
            logger.warning(f"파일 다운로드 실패: {e}")
            return False
    
    def scrape_pages(self, max_pages: int = 3, output_base: str = "output") -> bool:
        """페이지 스크래핑 실행"""
        try:
            if not self._initialize_session():
                logger.error("세션 초기화 실패")
                return False
            
            total_processed = 0
            
            for page_num in range(1, max_pages + 1):
                logger.info(f"\n=== IRIS {page_num}페이지 처리 시작 ===")
                
                # 페이지 데이터 가져오기
                page_data = self.get_page_data(page_num)
                if not page_data:
                    logger.error(f"{page_num}페이지 데이터 가져오기 실패")
                    break
                
                # 목록 파싱
                announcements = self.parse_list_page(page_data)
                if not announcements:
                    logger.warning(f"{page_num}페이지에 공고가 없습니다")
                    break
                
                logger.info(f"{len(announcements)}개 공고 발견")
                
                # 각 공고 처리
                for i, announcement in enumerate(announcements):
                    try:
                        title = announcement.get('title', f'공고_{page_num}_{i+1}')
                        logger.info(f"처리 중: {title}")
                        
                        # 상세 내용 가져오기
                        detail_data = self.get_detail_content(announcement)
                        
                        # 폴더 생성 및 저장
                        safe_title = self.sanitize_filename(title)
                        folder_name = f"{total_processed + 1:03d}_{safe_title}"
                        announcement_dir = os.path.join(output_base, folder_name)
                        os.makedirs(announcement_dir, exist_ok=True)
                        
                        # content.md 파일 생성
                        content_md = f"# {title}\n\n"
                        content_md += f"**공고 ID**: {announcement.get('id', '')}\n"
                        content_md += f"**날짜**: {announcement.get('date', '')}\n"
                        content_md += f"**상태**: {announcement.get('status', '')}\n"
                        content_md += f"**기관**: {announcement.get('institution', '')}\n"
                        content_md += f"**원본 URL**: POST {self.detail_url}\n\n"
                        content_md += "---\n\n"
                        content_md += detail_data.get('content', '')
                        
                        content_file = os.path.join(announcement_dir, 'content.md')
                        with open(content_file, 'w', encoding='utf-8') as f:
                            f.write(content_md)
                        
                        # 첨부파일 다운로드 시도
                        attachments = detail_data.get('attachments', [])
                        downloaded_files = 0
                        if attachments:
                            attachments_dir = os.path.join(announcement_dir, 'attachments')
                            os.makedirs(attachments_dir, exist_ok=True)
                            
                            # 실제 파일 다운로드 시도
                            attachments_info = []
                            for i, attachment in enumerate(attachments):
                                file_name = attachment.get('name', f'attachment_{i+1}')
                                safe_file_name = self.sanitize_filename(file_name)
                                file_path = os.path.join(attachments_dir, safe_file_name)
                                
                                # 파일 다운로드 시도
                                download_success = self.download_file(
                                    attachment.get('url', ''),
                                    file_path,
                                    attachment
                                )
                                
                                if download_success:
                                    downloaded_files += 1
                                    logger.info(f"파일 다운로드 성공: {safe_file_name}")
                                else:
                                    # 다운로드 실패 시 메타데이터 저장
                                    info = f"파일명: {attachment.get('name', 'unknown')}\n"
                                    info += f"다운로드 URL: {attachment.get('url', '')}\n"
                                    info += f"타입: {attachment.get('type', '')}\n"
                                    if attachment.get('params'):
                                        info += f"파라미터: {attachment.get('params')}\n"
                                    if attachment.get('file_size'):
                                        info += f"파일 크기: {attachment.get('file_size')} bytes\n"
                                    info += "다운로드 상태: 실패 (보안 제한)\n"
                                    info += "---\n"
                                    attachments_info.append(info)
                            
                            # 실패한 첨부파일 정보를 텍스트로 저장
                            if attachments_info:
                                attachments_file = os.path.join(attachments_dir, 'failed_attachments_info.txt')
                                with open(attachments_file, 'w', encoding='utf-8') as f:
                                    f.write('\n'.join(attachments_info))
                            
                            logger.info(f"첨부파일 처리 완료: {downloaded_files}/{len(attachments)}개 다운로드 성공")
                        
                        total_processed += 1
                        logger.info(f"처리 완료: {title} (첨부파일 정보: {len(attachments)}개)")
                        
                        time.sleep(self.delay_between_requests)
                        
                    except Exception as e:
                        logger.error(f"공고 처리 중 오류: {e}")
                        continue
                
                logger.info(f"{page_num}페이지 처리 완료")
                time.sleep(3)
            
            logger.info(f"\n=== IRIS 스크래핑 완료: 총 {total_processed}개 공고 처리 ===")
            return True
            
        except Exception as e:
            logger.error(f"스크래핑 중 오류 발생: {e}")
            return False


# 하위 호환성을 위한 별칭
IrisScraper = EnhancedIrisScraper