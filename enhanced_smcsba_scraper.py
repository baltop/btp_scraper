# -*- coding: utf-8 -*-
"""
SMCSBA (서울산업진흥원 글로벌마케팅센터) 전용 스크래퍼 - 향상된 버전
"""

from enhanced_base_scraper import AjaxAPIScraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote, parse_qs, urlparse
import re
import logging
import os
import json
import requests

logger = logging.getLogger(__name__)

class EnhancedSmcsbaScraper(AjaxAPIScraper):
    """SMCSBA 전용 스크래퍼 - 향상된 버전 (AJAX API 기반)"""
    
    def __init__(self):
        super().__init__()
        
        # 하드코딩된 설정들
        self.base_url = "https://smc.sba.kr"
        self.list_url = "https://smc.sba.kr/Pages/Information/Notice.aspx"
        self.api_url = "https://smc.sba.kr/Services/OnegateNoticeService.svc/GetNoticeinfo"
        self.detail_base_url = "https://smc.sba.kr/Pages/Information/NoticeDetail.aspx"
        
        # 사이트 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        self.delay_between_pages = 2
        
        # API 특화 헤더
        self.headers.update({
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest'
        })
        
        # 캐시된 전체 목록 (API에서 한 번에 모든 데이터를 가져옴)
        self.cached_announcements = None
        self.items_per_page = 10
    
    def get_list_url(self, page_num: int) -> str:
        """API URL 반환 - 페이지네이션은 클라이언트 사이드에서 처리"""
        return self.api_url
    
    def parse_list_page(self, api_data) -> list:
        """API 응답 파싱"""
        # API 데이터가 이미 파싱된 JSON인 경우
        if isinstance(api_data, dict):
            return self._parse_api_response(api_data)
        
        # 문자열인 경우 JSON 파싱
        try:
            data = json.loads(api_data)
            return self._parse_api_response(data)
        except:
            logger.error("API 응답 파싱 실패")
            return []
    
    def _get_page_announcements(self, page_num: int) -> list:
        """API를 통한 공고 목록 가져오기 - 페이지별 처리"""
        
        # 첫 번째 페이지에서 전체 데이터를 캐시
        if self.cached_announcements is None:
            logger.info("API에서 전체 공고 목록 가져오는 중...")
            
            # API 요청 데이터
            payload = {
                "new_name": "",
                "new_p_businesscategory": ""
            }
            
            try:
                response = self.session.post(
                    self.api_url,
                    data=json.dumps(payload),
                    headers=self.headers,
                    verify=self.verify_ssl,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                api_data = response.json()
                if api_data.get('result'):
                    self.cached_announcements = self._parse_api_response(api_data)
                    logger.info(f"총 {len(self.cached_announcements)}개 공고 캐시 완료")
                else:
                    logger.error("API 응답에서 result가 False")
                    return []
                    
            except Exception as e:
                logger.error(f"API 요청 실패: {e}")
                return []
        
        # 페이지별로 데이터 반환
        if not self.cached_announcements:
            return []
        
        start_idx = (page_num - 1) * self.items_per_page
        end_idx = start_idx + self.items_per_page
        
        page_announcements = self.cached_announcements[start_idx:end_idx]
        logger.info(f"페이지 {page_num}: {len(page_announcements)}개 공고 반환")
        
        return page_announcements
    
    def _parse_api_response(self, api_data: dict) -> list:
        """API 응답을 공고 목록으로 변환"""
        announcements = []
        
        if not api_data.get('result'):
            logger.warning("API 응답에서 result가 False")
            return announcements
        
        notice_list = api_data.get('list', [])
        logger.info(f"API에서 {len(notice_list)}개 공고 발견")
        
        for item in notice_list:
            try:
                # 필수 필드 확인
                if not item.get('new_name') or not item.get('new_onegate_noticeid'):
                    continue
                
                announcement = {
                    'title': item.get('new_name', '').strip(),
                    'url': f"{self.detail_base_url}?ID={item.get('new_onegate_noticeid')}",
                    'notice_id': item.get('new_onegate_noticeid'),
                    'category': item.get('new_p_businesscategoryname', ''),
                    'author': item.get('ownerIdName', ''),
                    'created_date': item.get('createdOn', ''),
                    'row_num': item.get('rownum', 0)
                }
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱: {announcement['title']}")
                
            except Exception as e:
                logger.error(f"공고 항목 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str, url: str = None) -> dict:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 내용 추출
        content = self._extract_content(soup)
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup, url)
        
        return {
            'content': content,
            'attachments': attachments
        }
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """본문 내용 추출"""
        # SMCSBA 상세 페이지의 본문 영역 찾기
        content_selectors = [
            '.con_data',  # 주요 본문 영역
            '.content',
            '.view_content',
            '#content',
            '.board_view'
        ]
        
        content_area = None
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        if not content_area:
            # 대안: body에서 스크립트와 스타일 제거 후 텍스트 추출
            body = soup.find('body')
            if body:
                # 스크립트, 스타일, 네비게이션 등 제거
                for elem in body.find_all(['script', 'style', 'nav', 'header', 'footer']):
                    elem.decompose()
                content_text = body.get_text()
                # 과도한 공백 정리
                lines = [line.strip() for line in content_text.split('\n') if line.strip()]
                content_text = '\n'.join(lines)
            else:
                content_text = "본문 내용을 추출할 수 없습니다."
        else:
            # HTML을 마크다운으로 변환
            content_text = self.h.handle(str(content_area))
            # 과도한 줄바꿈 정리
            content_text = re.sub(r'\n{3,}', '\n\n', content_text)
        
        if not content_text or len(content_text.strip()) < 50:
            content_text = "본문 내용을 추출할 수 없습니다."
            logger.warning("본문 내용 추출 실패")
        
        return content_text.strip()
    
    def _extract_attachments(self, soup: BeautifulSoup, url: str = None) -> list:
        """첨부파일 추출 - SMCSBA 특화 API 기반"""
        attachments = []
        
        # url에서 공고 ID 추출
        if not url:
            logger.warning("상세 페이지 URL이 없어 첨부파일을 가져올 수 없습니다")
            return attachments
        
        try:
            # URL에서 ID 파라미터 추출
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            record_id = query_params.get('ID', [None])[0]
            
            if not record_id:
                logger.warning("공고 ID를 찾을 수 없습니다")
                return attachments
            
            # 첨부파일 API 호출
            attachments = self._fetch_attachments_from_api(record_id)
            
        except Exception as e:
            logger.error(f"첨부파일 추출 중 오류: {e}")
            # 기존 HTML 파싱 방식으로 fallback
            attachments = self._extract_attachments_from_html(soup)
        
        logger.info(f"총 {len(attachments)}개 첨부파일 발견")
        return attachments
    
    def _fetch_attachments_from_api(self, record_id: str) -> list:
        """SMCSBA 첨부파일 API에서 첨부파일 정보 가져오기"""
        attachments = []
        
        try:
            # 첨부파일 API 엔드포인트
            attachment_api_url = "https://smc.sba.kr/Services/CommonService.svc/GetEntityAttachment"
            
            # API 요청 데이터
            payload = {
                "recordid": record_id
            }
            
            response = self.session.post(
                attachment_api_url,
                data=json.dumps(payload),
                headers=self.headers,
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            api_data = response.json()
            if api_data.get('result'):
                file_list = api_data.get('list', [])
                logger.info(f"첨부파일 API에서 {len(file_list)}개 파일 발견")
                
                for file_info in file_list:
                    try:
                        filename = file_info.get('filename', '')
                        virtualpath = file_info.get('virtualpath', '')
                        
                        if filename and virtualpath:
                            # virtualpath를 실제 다운로드 URL로 변환
                            file_url = self._build_download_url(virtualpath)
                            
                            attachments.append({
                                'name': filename,
                                'url': file_url,
                                'virtualpath': virtualpath
                            })
                            logger.info(f"첨부파일 API에서 발견: {filename}")
                        
                    except Exception as e:
                        logger.error(f"첨부파일 정보 처리 중 오류: {e}")
                        continue
            else:
                logger.info("첨부파일 API 응답에서 result가 False - 첨부파일 없음")
                
        except Exception as e:
            logger.error(f"첨부파일 API 호출 실패: {e}")
        
        return attachments
    
    def _build_download_url(self, virtualpath: str) -> str:
        """virtualpath를 실제 다운로드 URL로 변환"""
        # SMCSBA의 경우 virtualpath가 이미 전체 URL일 수 있음
        if virtualpath.startswith('http'):
            return virtualpath
        elif virtualpath.startswith('/'):
            return self.base_url + virtualpath
        else:
            # 상대 경로인 경우 AttachFiles 경로로 구성
            return f"{self.base_url}/AttachFiles/{virtualpath}"
    
    def _extract_attachments_from_html(self, soup: BeautifulSoup) -> list:
        """HTML에서 첨부파일 추출 - Fallback 방식"""
        attachments = []
        
        # 기존 HTML 파싱 방식
        attachment_selectors = [
            'a[href*="AttachFiles"]',  # AttachFiles 경로
            'a[href*="download"]',     # download 링크
            'a[href*=".pdf"]',         # PDF 직접 링크
            'a[href*=".hwp"]',         # HWP 직접 링크
            'a[href*=".doc"]',         # DOC 직접 링크
            'a[href*=".xls"]',         # Excel 직접 링크
            'a[href*=".zip"]'          # ZIP 파일
        ]
        
        # 개인정보처리방침 링크 제외
        exclude_patterns = [
            '개인정보처리방침',
            'privacy',
            'policy'
        ]
        
        for selector in attachment_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href', '')
                if not href:
                    continue
                
                # 파일명 추출
                file_name = link.get_text(strip=True)
                if not file_name:
                    file_name = link.get('title', '')
                
                # 개인정보처리방침 등 시스템 링크 제외
                if any(exclude in file_name for exclude in exclude_patterns):
                    continue
                
                # href가 상대 경로인 경우 절대 URL로 변환
                if href.startswith('/'):
                    file_url = self.base_url + href
                elif href.startswith('http'):
                    file_url = href
                else:
                    file_url = urljoin(self.base_url, href)
                
                # 파일명이 없으면 URL에서 추출
                if not file_name:
                    parsed_url = urlparse(file_url)
                    file_name = os.path.basename(parsed_url.path)
                    if not file_name:
                        file_name = f"attachment_{len(attachments) + 1}"
                
                # 중복 제거
                if not any(att['url'] == file_url for att in attachments):
                    attachments.append({
                        'name': file_name,
                        'url': file_url
                    })
                    logger.info(f"HTML에서 첨부파일 발견: {file_name}")
        
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment_info: dict = None) -> bool:
        """SMCSBA 파일 다운로드 - 특화된 처리"""
        try:
            logger.info(f"파일 다운로드 시작: {url}")
            
            # SMCSBA 사이트 전용 헤더 설정
            download_headers = {
                'User-Agent': self.headers['User-Agent'],
                'Referer': self.base_url + "/Pages/Information/Notice.aspx"
            }
            
            response = self.session.get(
                url, 
                headers=download_headers, 
                stream=True, 
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            
            # 실제 파일명 추출 시도
            save_dir = os.path.dirname(save_path)
            actual_filename = self._extract_filename_from_response(response, save_dir)
            
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
    
    def _extract_filename_from_response(self, response, save_dir):
        """SMCSBA 응답에서 파일명 추출"""
        content_disposition = response.headers.get('Content-Disposition', '')
        
        if content_disposition:
            logger.debug(f"Content-Disposition: {content_disposition}")
            
            # RFC 5987 형식 처리
            rfc5987_match = re.search(r"filename\*=([^']*)'([^']*)'(.+)", content_disposition)
            if rfc5987_match:
                encoding = rfc5987_match.group(1) or 'utf-8'
                filename = rfc5987_match.group(3)
                try:
                    filename = unquote(filename, encoding=encoding)
                    clean_filename = self.sanitize_filename(filename)
                    return os.path.join(save_dir, clean_filename)
                except Exception as e:
                    logger.debug(f"RFC 5987 파일명 처리 실패: {e}")
            
            # 일반적인 filename 파라미터 처리
            filename_match = re.search(r'filename[^;=\n]*=(([\'"]).*?\2|[^;\n]*)', content_disposition)
            if filename_match:
                filename = filename_match.group(1).strip('"\'')
                
                # 다양한 인코딩 시도
                for encoding in ['utf-8', 'euc-kr', 'cp949']:
                    try:
                        if encoding == 'utf-8':
                            decoded = filename.encode('latin-1').decode('utf-8')
                        else:
                            decoded = filename.encode('latin-1').decode(encoding)
                        
                        if decoded and not decoded.isspace():
                            clean_filename = self.sanitize_filename(decoded.replace('+', ' '))
                            return os.path.join(save_dir, clean_filename)
                    except Exception as e:
                        logger.debug(f"{encoding} 인코딩 시도 실패: {e}")
                        continue
        
        # URL에서 파일명 추출 시도
        try:
            parsed_url = urlparse(response.url)
            path_filename = os.path.basename(parsed_url.path)
            if path_filename and '.' in path_filename:
                clean_filename = self.sanitize_filename(path_filename)
                return os.path.join(save_dir, clean_filename)
        except Exception as e:
            logger.debug(f"URL에서 파일명 추출 실패: {e}")
        
        # 기본 파일명 반환
        return os.path.join(save_dir, "attachment.file")

# 하위 호환성을 위한 별칭
SmcsbaScraper = EnhancedSmcsbaScraper