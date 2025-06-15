# -*- coding: utf-8 -*-
"""
대구경북디자인진흥원(DGDP) Enhanced 스크래퍼
표준 테이블 기반 게시판, 직접 링크 다운로드 방식
"""

import re
import logging
import os
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from enhanced_base_scraper import AjaxAPIScraper
import json

logger = logging.getLogger(__name__)

class EnhancedDGDPScraper(AjaxAPIScraper):
    """DGDP 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        
        # 하드코딩된 설정들 (Fallback용)
        self.base_url = "https://dgdp.or.kr"
        self.list_url = "https://dgdp.or.kr/notice/public"
        
        # 사이트 특화 설정
        self.verify_ssl = False  # DGDP 사이트 SSL 인증서 문제
        self.default_encoding = 'utf-8'
        
        # AJAX API 설정
        self.api_url = "https://dgdp.or.kr/notice/public"
        self.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest'
        })
        
        # 중복 체크 활성화
        self.enable_duplicate_check = True
        self.duplicate_threshold = 3
    
    def get_list_url(self, page_num: int) -> str:
        """API URL 반환"""
        return self.api_url
    
    def _get_page_announcements(self, page_num: int) -> list:
        """AJAX API를 통한 공고 목록 가져오기"""
        logger.info(f"페이지 {page_num} API 호출 중")
        
        # API 요청 데이터 구성
        request_data = {
            "searchCategory": "",      # 카테고리 (전체)
            "searchCategorySub": "",   # 하위카테고리 (전체)
            "searchValue": "",         # 검색어
            "searchType": "all",       # 검색타입
            "pageIndex": page_num,     # 현재 페이지 (1부터 시작)
            "pageUnit": 10,            # 페이지당 항목 수
            "pageSize": 5              # 페이지네이션 크기
        }
        
        try:
            # JSON으로 POST 요청
            response = self.session.post(
                self.api_url,
                json=request_data,
                headers=self.headers,
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                logger.error(f"API 요청 실패: HTTP {response.status_code}")
                return []
            
            # JSON 응답 파싱
            json_data = response.json()
            return self.parse_api_response(json_data, page_num)
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}")
            return []
        except Exception as e:
            logger.error(f"API 호출 중 오류: {e}")
            return []
    
    def parse_api_response(self, json_data: dict, page_num: int) -> list:
        """API 응답에서 공고 목록 파싱"""
        announcements = []
        
        try:
            data = json_data.get('data', {})
            data_list = data.get('dataList', [])
            total_count = data.get('totalCount', 0)
            
            logger.info(f"API 응답: 총 {total_count}개 공고 중 {len(data_list)}개 수신")
            
            for item in data_list:
                # 외부 링크인 경우 스킵
                if item.get('linkYn') == 'Y':
                    logger.debug(f"외부 링크 공고 스킵: {item.get('title', '')}")
                    continue
                
                announcement = {
                    'title': item.get('title', '').strip(),
                    'url': f"{self.base_url}/notice/public/{item.get('id', '')}",
                    'id': item.get('id', ''),
                    'category': item.get('category', ''),
                    'status': self._determine_status(item),
                    'period': f"{item.get('stDt', '')} ~ {item.get('edDt', '')}",
                    'date': item.get('regDt', ''),
                    'views': str(item.get('views', 0))
                }
                
                if announcement['title'] and announcement['id']:
                    announcements.append(announcement)
            
            logger.info(f"{len(announcements)}개 유효한 공고 파싱 완료")
            return announcements
            
        except Exception as e:
            logger.error(f"API 응답 파싱 중 오류: {e}")
            return []
    
    def _determine_status(self, item: dict) -> str:
        """공고 상태 결정"""
        from datetime import datetime, date
        
        try:
            ed_dt = item.get('edDt', '')
            if ed_dt:
                end_date = datetime.strptime(ed_dt, '%Y-%m-%d').date()
                today = date.today()
                
                if end_date < today:
                    return '종료'
                else:
                    return '진행중'
        except:
            pass
        
        return '진행중'  # 기본값
    
    def parse_list_page(self, data) -> list:
        """하위 호환성을 위한 메소드"""
        # API 방식에서는 사용되지 않음
        return []
    
    
    def parse_detail_page(self, html_content: str) -> dict:
        """상세 페이지 파싱 - DGDP API 방식"""
        # DGDP는 SPA이므로 HTML 파싱 대신 API 호출 시도
        return self._parse_detail_fallback(html_content)
    
    def _parse_detail_fallback(self, html_content: str) -> dict:
        """HTML에서 JavaScript 데이터 추출 또는 기본 파싱"""
        # 방법 1: HTML 내 JavaScript에서 JSON 데이터 추출 시도
        detail_data = self._extract_js_data(html_content)
        if detail_data:
            return detail_data
        
        # 방법 2: 기본 HTML 파싱
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 추출
        content = self._extract_content(soup)
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup)
        
        return {
            'content': content,
            'attachments': attachments
        }
    
    def _extract_js_data(self, html_content: str) -> dict:
        """HTML 내 JavaScript에서 공고 데이터 추출"""
        try:
            # JavaScript 변수에서 공고 상세 정보 찾기
            patterns = [
                # DGDP 특화 패턴들
                r'const\s+publicDetail\s*=\s*({.*?});',
                r'var\s+publicDetail\s*=\s*({.*?});',
                r'publicDetail\s*=\s*({.*?});',
                r'noticeDetail\s*=\s*({.*?});',
                r'detail\s*=\s*({.*?});',
                # 일반적인 패턴들
                r'data\s*:\s*({.*?})',
                r'notice\s*:\s*({.*?})',
                r'announcement\s*:\s*({.*?})'
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, html_content, re.DOTALL)
                for match in matches:
                    json_str = match.group(1)
                    # 복잡한 객체 구조도 처리할 수 있도록 확장
                    try:
                        # 기본 JSON 파싱 시도
                        data = json.loads(json_str)
                        
                        # 유효한 공고 데이터인지 확인
                        if self._is_valid_notice_data(data):
                            logger.info(f"JavaScript에서 공고 데이터 추출 성공: {pattern}")
                            return self._parse_js_detail_data(data)
                    except json.JSONDecodeError:
                        continue
            
            # 대안: 파일 정보만 별도로 추출
            file_data = self._extract_file_data(html_content)
            if file_data:
                logger.info("JavaScript에서 파일 데이터만 추출 성공")
                return {
                    'content': "본문 내용을 추출할 수 없습니다.",
                    'attachments': file_data
                }
            
            logger.debug("JavaScript에서 공고 데이터를 찾을 수 없음")
            return None
            
        except Exception as e:
            logger.error(f"JavaScript 데이터 추출 중 오류: {e}")
            return None
    
    def _is_valid_notice_data(self, data: dict) -> bool:
        """유효한 공고 데이터인지 확인"""
        # 기본 필드가 있는지 확인
        required_fields = ['title', 'contents', 'id']
        optional_fields = ['attachFiles', 'files', 'fileList']
        
        # 필수 필드 중 하나라도 있으면 유효
        has_required = any(field in data for field in required_fields)
        # 또는 첨부파일 정보가 있으면 유효
        has_files = any(field in data for field in optional_fields)
        
        return has_required or has_files
    
    def _extract_file_data(self, html_content: str) -> list:
        """HTML에서 파일 정보만 별도로 추출"""
        attachments = []
        
        try:
            # 파일 정보 패턴들
            file_patterns = [
                r'fileUploadId[\'"]?\s*:\s*(\d+).*?fileNm[\'"]?\s*:\s*[\'"]([^\'\"]+)[\'"].*?fileUuid[\'"]?\s*:\s*[\'"]([^\'\"]+)[\'"]',
                r'fileName[\'"]?\s*:\s*[\'"]([^\'\"]+)[\'"].*?fileUuid[\'"]?\s*:\s*[\'"]([^\'\"]+)[\'"]',
                r'name[\'"]?\s*:\s*[\'"]([^\'\"]+)[\'"].*?uuid[\'"]?\s*:\s*[\'"]([^\'\"]+)[\'"]'
            ]
            
            for pattern in file_patterns:
                matches = re.finditer(pattern, html_content, re.DOTALL | re.IGNORECASE)
                for match in matches:
                    if len(match.groups()) >= 3:  # fileUploadId, fileName, fileUuid
                        file_name = match.group(2)
                        file_uuid = match.group(3)
                    elif len(match.groups()) >= 2:  # fileName, fileUuid
                        file_name = match.group(1)
                        file_uuid = match.group(2)
                    else:
                        continue
                    
                    if file_name and file_uuid and len(file_uuid) > 10:  # UUID는 보통 길다
                        file_url = f"{self.base_url}/file/download/board/{file_uuid}"
                        
                        attachments.append({
                            'name': file_name,
                            'url': file_url,
                            'uuid': file_uuid
                        })
                        logger.debug(f"파일 정보 추출: {file_name}")
            
            return attachments
            
        except Exception as e:
            logger.error(f"파일 데이터 추출 중 오류: {e}")
            return []
    
    def _parse_js_detail_data(self, data: dict) -> dict:
        """JavaScript에서 추출한 데이터 파싱"""
        try:
            # 본문 내용 추출
            content_parts = []
            
            # 제목 추가
            title = data.get('title', '')
            if title:
                content_parts.append(f"# {title}\n")
            
            # 본문 HTML을 마크다운으로 변환
            contents = data.get('contents', '')
            if contents:
                markdown_content = self.h.handle(contents)
                content_parts.append(markdown_content)
            else:
                content_parts.append("본문 내용이 없습니다.")
            
            # 첨부파일 정보 추출
            attachments = []
            attach_files = data.get('attachFiles', [])
            
            for file_info in attach_files:
                file_uuid = file_info.get('fileUuid', '')
                file_name = file_info.get('fileName', '')
                
                if file_uuid and file_name:
                    # DGDP 파일 다운로드 URL 패턴
                    file_url = f"{self.base_url}/download/board/{file_uuid}"
                    
                    attachments.append({
                        'name': file_name,
                        'url': file_url,
                        'uuid': file_uuid,
                        'size': file_info.get('fileSize', ''),
                        'type': file_info.get('fileType', '')
                    })
                    logger.debug(f"JavaScript 첨부파일: {file_name}")
            
            logger.info(f"JavaScript 데이터 파싱 완료 - 내용길이: {len(''.join(content_parts))}, 첨부파일: {len(attachments)}개")
            
            return {
                'content': '\n\n'.join(content_parts),
                'attachments': attachments
            }
            
        except Exception as e:
            logger.error(f"JavaScript 데이터 파싱 중 오류: {e}")
            return {
                'content': "데이터 파싱 실패",
                'attachments': []
            }
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """본문 내용 추출"""
        content_parts = []
        
        # 제목 추출 - 다양한 선택자 시도
        title_selectors = [
            'h1',
            'h2',
            '.title',
            '.notice-title',
            '.page-title',
            '[class*="title"]'
        ]
        
        title_elem = None
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                logger.debug(f"제목을 {selector} 선택자로 찾음")
                break
        
        if title_elem:
            title = title_elem.get_text(strip=True)
            if title:
                content_parts.append(f"# {title}\n")
        
        # 본문 영역 찾기 - 다양한 선택자 시도
        content_selectors = [
            '.content-area',
            '.view-content',
            '.board-view',
            '.notice-content',
            '.detail-content',
            'main section',
            'article',
            '.content',
            '[class*="content"]',
            '.view-area',
            '.board-content'
        ]
        
        content_area = None
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        if content_area:
            # HTML to Markdown 변환
            content_html = str(content_area)
            markdown_content = self.h.handle(content_html)
            content_parts.append(markdown_content)
        else:
            # 대체: 본문으로 추정되는 모든 p, div 태그에서 텍스트 추출
            body_text = []
            for elem in soup.find_all(['p', 'div'], string=True):
                text = elem.get_text(strip=True)
                if text and len(text) > 20:  # 충분히 긴 텍스트만
                    body_text.append(text)
            
            if body_text:
                content_parts.extend(body_text)
                logger.debug(f"{len(body_text)}개 텍스트 블록으로 본문 구성")
            else:
                content_parts.append("본문 내용을 추출할 수 없습니다.")
        
        return "\n\n".join(content_parts) if content_parts else "내용을 추출할 수 없습니다."
    
    def _extract_attachments(self, soup: BeautifulSoup) -> list:
        """첨부파일 정보 추출"""
        attachments = []
        
        # 첨부파일 섹션 찾기 방법들
        attachment_sections = []
        
        # 방법 1: "첨부파일" 텍스트가 있는 섹션 찾기
        for elem in soup.find_all(text=re.compile(r'첨부파일|첨부|다운로드', re.IGNORECASE)):
            parent = elem.parent
            # 상위로 올라가면서 링크가 있는 컨테이너 찾기
            for _ in range(5):  # 최대 5단계까지
                if parent and parent.name not in ['html', 'body']:
                    links = parent.find_all('a', href=True)
                    if links:
                        attachment_sections.append(parent)
                        break
                    parent = parent.parent
                else:
                    break
        
        # 방법 2: 다운로드 관련 클래스나 ID 찾기
        download_selectors = [
            '[class*="attach"]',
            '[class*="download"]',
            '[class*="file"]',
            '[id*="attach"]',
            '[id*="download"]',
            '[id*="file"]'
        ]
        
        for selector in download_selectors:
            elements = soup.select(selector)
            for elem in elements:
                if elem.find_all('a', href=True):
                    attachment_sections.append(elem)
        
        # 방법 3: 전체 페이지에서 파일 확장자가 있는 링크 찾기
        if not attachment_sections:
            attachment_sections.append(soup)  # 전체 페이지 검색
        
        # 중복 제거
        unique_sections = []
        for section in attachment_sections:
            if section not in unique_sections:
                unique_sections.append(section)
        
        logger.debug(f"{len(unique_sections)}개 첨부파일 섹션에서 검색 중")
        
        # 각 섹션에서 첨부파일 링크 찾기
        for section in unique_sections:
            section_attachments = self._find_attachment_links(section)
            for att in section_attachments:
                # 중복 제거
                if not any(existing['url'] == att['url'] for existing in attachments):
                    attachments.append(att)
        
        logger.info(f"{len(attachments)}개 첨부파일 발견")
        return attachments
    
    def _find_attachment_links(self, section: BeautifulSoup) -> list:
        """섹션 내에서 첨부파일 링크 찾기"""
        section_attachments = []
        
        # 직접 링크 방식
        for link in section.find_all('a', href=True):
            href = link.get('href', '').strip()
            if not href:
                continue
            
            # 파일 확장자 패턴 확인
            file_extensions = ['.pdf', '.hwp', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.txt', '.ppt', '.pptx']
            is_file_link = any(ext in href.lower() for ext in file_extensions)
            
            # download 관련 URL 패턴 확인
            is_download_link = any(pattern in href.lower() for pattern in ['download', 'file', 'attach'])
            
            if is_file_link or is_download_link:
                file_url = urljoin(self.base_url, href)
                
                # 파일명 추출
                file_text = link.get_text(strip=True)
                filename = self._extract_filename_from_text(file_text)
                
                if not filename:
                    # href에서 파일명 추출 시도
                    filename = self._extract_filename_from_url(href)
                
                if filename:
                    section_attachments.append({
                        'name': filename,
                        'url': file_url
                    })
                    logger.debug(f"직접 링크 첨부파일: {filename}")
        
        # JavaScript 다운로드 방식
        for elem in section.find_all(onclick=True):
            onclick = elem.get('onclick', '')
            
            if any(pattern in onclick.lower() for pattern in ['download', 'file']):
                file_text = elem.get_text(strip=True)
                filename = self._extract_filename_from_text(file_text)
                
                if filename:
                    file_url = self._construct_download_url(onclick)
                    if file_url:
                        section_attachments.append({
                            'name': filename,
                            'url': file_url
                        })
                        logger.debug(f"JavaScript 첨부파일: {filename}")
        
        return section_attachments
    
    def _extract_filename_from_text(self, text: str) -> str:
        """텍스트에서 파일명 추출"""
        if not text:
            return ""
        
        # 파일명 패턴 찾기: "파일명.확장자(크기)" 또는 "파일명.확장자"
        filename_patterns = [
            r'([^()]+\.[a-zA-Z0-9]+)\s*\([^)]*\)',  # "파일명.확장자(크기)"
            r'([^()]+\.[a-zA-Z0-9]+)',              # "파일명.확장자"
        ]
        
        for pattern in filename_patterns:
            match = re.search(pattern, text)
            if match:
                filename = match.group(1).strip()
                if filename:
                    return filename
        
        # 패턴이 안 맞으면 전체 텍스트에서 파일 확장자가 있는지 확인
        file_extensions = ['pdf', 'hwp', 'doc', 'docx', 'xls', 'xlsx', 'zip', 'txt', 'ppt', 'pptx']
        for ext in file_extensions:
            if f'.{ext}' in text.lower():
                return text.strip()
        
        return ""
    
    def _extract_filename_from_url(self, url: str) -> str:
        """URL에서 파일명 추출"""
        if not url:
            return ""
        
        # URL에서 파일명 부분 추출
        from urllib.parse import urlparse, unquote
        
        try:
            parsed = urlparse(url)
            path = parsed.path
            
            # URL 디코딩
            path = unquote(path)
            
            # 파일명 추출
            filename = path.split('/')[-1]
            
            # 파일 확장자가 있는지 확인
            if '.' in filename and len(filename.split('.')[-1]) <= 5:
                return filename
            
        except Exception:
            pass
        
        return ""
    
    def _construct_download_url(self, onclick: str) -> str:
        """onclick 속성에서 다운로드 URL 구성"""
        # 일반적인 패턴들 시도
        patterns = [
            r"download\s*\(\s*['\"]([^'\"]+)['\"]",  # download('file_id')
            r"location\.href\s*=\s*['\"]([^'\"]+)['\"]",  # location.href='url'
            r"window\.open\s*\(\s*['\"]([^'\"]+)['\"]",  # window.open('url')
            r"downloadFile\s*\(\s*['\"]([^'\"]+)['\"]",  # downloadFile('file_id')
        ]
        
        for pattern in patterns:
            match = re.search(pattern, onclick)
            if match:
                url_part = match.group(1)
                return urljoin(self.base_url, url_part)
        
        return ""
    
    def _get_detail_from_api(self, announcement_id: str) -> dict:
        """API를 통한 공고 상세 정보 가져오기"""
        try:
            # API 엔드포인트 시도
            api_urls = [
                f"{self.base_url}/api/notice/public/{announcement_id}",
                f"{self.base_url}/notice/public/api/{announcement_id}",
                f"{self.base_url}/api/board/public/{announcement_id}"
            ]
            
            for api_url in api_urls:
                try:
                    logger.debug(f"API 호출 시도: {api_url}")
                    response = self.session.get(
                        api_url,
                        headers={
                            **self.headers,
                            'Accept': 'application/json',
                            'X-Requested-With': 'XMLHttpRequest'
                        },
                        verify=self.verify_ssl,
                        timeout=self.timeout
                    )
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            logger.info(f"API에서 공고 상세 정보 획득: {api_url}")
                            return self._parse_api_detail_data(data)
                        except json.JSONDecodeError:
                            continue
                except Exception as e:
                    logger.debug(f"API 호출 실패 {api_url}: {e}")
                    continue
            
            logger.debug("모든 API 엔드포인트 시도 실패")
            return None
            
        except Exception as e:
            logger.error(f"API 상세 정보 가져오기 중 오류: {e}")
            return None
    
    def _parse_api_detail_data(self, data: dict) -> dict:
        """API 응답 데이터 파싱"""
        try:
            # 데이터 구조에 따라 유연하게 처리
            detail_info = data
            if 'data' in data:
                detail_info = data['data']
            
            # 본문 내용 추출
            content_parts = []
            
            # 제목 추가
            title = detail_info.get('title', '')
            if title:
                content_parts.append(f"# {title}\n")
            
            # 본문 HTML을 마크다운으로 변환
            contents = detail_info.get('contents', '') or detail_info.get('content', '')
            if contents:
                markdown_content = self.h.handle(contents)
                content_parts.append(markdown_content)
            else:
                content_parts.append("본문 내용이 없습니다.")
            
            # 첨부파일 정보 추출
            attachments = []
            attach_files = detail_info.get('attachFiles', []) or detail_info.get('files', [])
            
            for file_info in attach_files:
                file_uuid = file_info.get('fileUuid', '') or file_info.get('uuid', '')
                file_name = file_info.get('fileName', '') or file_info.get('name', '')
                
                if file_uuid and file_name:
                    # DGDP 파일 다운로드 URL 패턴들 시도
                    download_urls = [
                        f"{self.base_url}/download/board/{file_uuid}",
                        f"{self.base_url}/file/download/board/{file_uuid}",
                        f"{self.base_url}/api/file/download/{file_uuid}"
                    ]
                    
                    attachments.append({
                        'name': file_name,
                        'url': download_urls[0],  # 첫 번째 URL 사용
                        'uuid': file_uuid,
                        'size': file_info.get('fileSize', ''),
                        'type': file_info.get('fileType', '')
                    })
                    logger.debug(f"API 첨부파일: {file_name}")
            
            logger.info(f"API 데이터 파싱 완료 - 내용길이: {len(''.join(content_parts))}, 첨부파일: {len(attachments)}개")
            
            return {
                'content': '\n\n'.join(content_parts),
                'attachments': attachments
            }
            
        except Exception as e:
            logger.error(f"API 데이터 파싱 중 오류: {e}")
            return None
    
    def process_announcement(self, announcement: dict, index: int, output_base: str = 'output'):
        """개별 공고 처리 - DGDP 특화 버전"""
        logger.info(f"공고 처리 중 {index}: {announcement['title']}")
        
        # 폴더 생성
        folder_title = self.sanitize_filename(announcement['title'])[:50]
        folder_name = f"{index:03d}_{folder_title}"
        folder_path = os.path.join(output_base, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        # 방법 1: API 직접 호출 시도
        announcement_id = announcement.get('id', '')
        detail = None
        
        if announcement_id:
            detail = self._get_detail_from_api(announcement_id)
        
        # 방법 2: HTML 페이지 파싱
        if not detail:
            response = self.get_page(announcement['url'])
            if not response:
                logger.error(f"상세 페이지 가져오기 실패: {announcement['title']}")
                return
            
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
DGDPScraper = EnhancedDGDPScraper