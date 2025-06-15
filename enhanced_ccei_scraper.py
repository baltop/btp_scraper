# -*- coding: utf-8 -*-
"""
Enhanced CCEI 스크래퍼 - AJAX/JSON API 기반
충북창조경제혁신센터 전용 스크래퍼 (Enhanced 아키텍처)
ccei_scraper_improved.py 기반 리팩토링
"""

from enhanced_base_scraper import AjaxAPIScraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import re
import os
import logging

logger = logging.getLogger(__name__)

class EnhancedCCEIScraper(AjaxAPIScraper):
    """충북창조경제혁신센터 전용 스크래퍼 - Enhanced 버전"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://ccei.creativekorea.or.kr"
        self.list_url = "https://ccei.creativekorea.or.kr/chungbuk/custom/notice_list.do"
        self.api_url = "https://ccei.creativekorea.or.kr/chungbuk/custom/noticeList.json"
        self._list_data_cache = {}  # improved.py와 동일한 네이밍
        
    def get_list_url(self, page_num: int) -> str:
        """API URL 반환"""
        return self.api_url
        
    def get_list_data(self, page_num: int) -> dict:
        """AJAX로 목록 데이터 가져오기 - improved.py 방식"""
        data = {
            'pn': str(page_num),
            'boardGubun': '',
            'keyword': '',
            'title': ''
        }
        
        response = self.post_page(self.api_url, data=data)
        if response and response.status_code == 200:
            try:
                json_data = response.json()
                # Cache the data for file information
                if json_data and 'result' in json_data:
                    items = json_data.get('result', {}).get('list', [])
                    for item in items:
                        seq = str(item.get('SEQ', ''))
                        if seq:
                            self._list_data_cache[seq] = item
                return json_data
            except Exception as e:
                logger.error(f"JSON 파싱 실패: {e}")
                return None
        return None
        
    def _get_page_announcements(self, page_num: int) -> list:
        """목록 데이터 가져오기 - 캐싱 포함"""
        logger.info(f"페이지 {page_num} API 호출: {self.api_url}")
        
        json_data = self.get_list_data(page_num)
        if not json_data:
            logger.error(f"API 호출 실패: 페이지 {page_num}")
            return []
        
        announcements = self.parse_api_response(json_data, page_num)
        
        # CCEI API 특화: 빈 결과나 totalCnt를 확인하여 마지막 페이지 감지
        if not announcements and page_num > 1:
            result = json_data.get('result', {})
            total_count = result.get('totalCnt', 0)
            current_count = len(result.get('list', []))
            
            if total_count == 0 or current_count == 0:
                logger.info(f"CCEI API 페이지 {page_num}: 총 {total_count}개, 현재 페이지 {current_count}개 - 마지막 페이지")
            else:
                logger.info(f"CCEI API 페이지 {page_num}: 공고가 없어 마지막 페이지로 판단됩니다")
        
        return announcements
        
    def parse_api_response(self, json_data: dict, page_num: int) -> list:
        """API 응답 파싱"""
        announcements = []
        
        if 'result' not in json_data:
            logger.warning("API 응답에 result 필드가 없습니다")
            return announcements
            
        result = json_data.get('result', {})
        items = result.get('list', [])
        
        logger.info(f"페이지 {page_num}에서 {len(items)}개 공고 발견")
        
        for item in items:
            try:
                # 제목
                title = item.get('TITLE', '').strip()
                if not title:
                    continue
                
                # SEQ로 상세 URL 구성
                seq = item.get('SEQ', '')
                if seq:
                    detail_url = f"{self.base_url}/chungbuk/custom/notice_view.do?no={seq}"
                else:
                    continue
                
                # 기타 정보
                organization = item.get('COUNTRY_NM', '통합')
                date = item.get('REG_DATE', '')
                views = item.get('HIT', '0')
                has_file = item.get('FILE', '') != ''
                is_recommend = item.get('RECOMMEND_WHETHER', '') == 'Y'
                
                # 리스트 캐시에 저장 (파일 다운로드용) - 이미 get_list_data에서 처리됨
                
                announcements.append({
                    'title': title,
                    'url': detail_url,
                    'organization': organization,
                    'date': date,
                    'views': views,
                    'has_file': has_file,
                    'is_recommend': is_recommend,
                    'seq': seq,
                    'file_data': item.get('FILE', '')  # improved.py와 동일한 필드명
                })
                
            except Exception as e:
                logger.error(f"공고 항목 파싱 중 오류: {e}")
                continue
                
        return announcements
        
    def parse_list_page(self, html_content) -> list:
        """목록 페이지 파싱 - API 응답 처리용"""
        # API 응답인 경우 json_data를 그대로 전달
        if isinstance(html_content, dict):
            return self.parse_api_response(html_content, 1)
        
        # 혹시 HTML이 전달된 경우 기본 처리
        return []
        
    def parse_detail_page(self, html_content: str, url: str = None) -> dict:
        """상세 페이지 파싱 - improved.py 방식"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract SEQ from the page URL if provided
        seq = None
        if url:
            match = re.search(r'no=(\d+)', url)
            if match:
                seq = match.group(1)
        
        # If not found in URL, try to extract from the page
        if not seq:
            # Try to find in JavaScript or hidden fields
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    match = re.search(r'var\s+seq\s*=\s*["\']?(\d+)["\']?', script.string)
                    if match:
                        seq = match.group(1)
                        break
        
        # 본문 내용 찾기
        content_area = self._find_content_area(soup)
        
        # 첨부파일 찾기 - CCEI는 list API에서 파일 정보를 가져와야 함
        attachments = []
        
        # Get file data from cache if we have the SEQ
        if seq and seq in self._list_data_cache:
            item_data = self._list_data_cache[seq]
            file_data = item_data.get('FILE', '')
            
            if file_data:
                file_uuids = file_data.split(',')
                logger.info(f"Found {len(file_uuids)} files from cached data for SEQ {seq}")
                
                # For each UUID, create download URL
                for i, uuid in enumerate(file_uuids):
                    if uuid.strip():
                        file_url = f"{self.base_url}/chungbuk/json/common/fileDown.download?uuid={uuid.strip()}"
                        # We don't have filename info here, so we'll get it during download
                        attachments.append({
                            'name': f'attachment_{i+1}',  # Placeholder name
                            'url': file_url,
                            'uuid': uuid.strip()
                        })
        
        # 본문을 마크다운으로 변환
        content_md = ""
        if content_area:
            content_md = self.h.handle(str(content_area))
        else:
            # 전체 페이지에서 헤더/푸터 제외하고 추출 시도
            main_content = soup.find('div', class_='content_wrap') or soup.find('div', id='content')
            if main_content:
                content_md = self.h.handle(str(main_content))
                
        return {
            'content': content_md,
            'attachments': attachments,
            'seq': seq
        }
    
    def _find_content_area(self, soup):
        """본문 영역 찾기 - improved.py 기반"""
        # 가능한 본문 선택자들
        content_selectors = [
            'div.view_cont',
            'div.board_view',
            'div.view_content',
            'div.content',
            'td.content',
            'div.view_body',
            'div.board_content',
            'div.bbs_content',
            'div.vw_article'  # CCEI specific
        ]
        
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                logger.debug(f"본문 영역 발견: {selector}")
                return content_area
                
        # 테이블 구조에서 본문 찾기
        view_table = soup.find('table', class_=['view', 'board_view'])
        if view_table:
            for tr in view_table.find_all('tr'):
                th = tr.find('th')
                if th and '내용' in th.get_text():
                    content_area = tr.find('td')
                    if content_area:
                        logger.debug("테이블 구조에서 본문 발견")
                        return content_area
                        
        return None
    
    # 기존 첨부파일 관련 메서드들은 parse_detail_page에서 직접 처리하므로 제거
    
    def download_file(self, url: str, save_path: str, attachment_info: dict = None) -> bool:
        """파일 다운로드 - CCEI 특화 처리 (improved.py 기반)"""
        try:
            logger.info(f"Downloading from: {url}")
            response = self.session.get(url, stream=True, verify=self.verify_ssl)
            response.raise_for_status()
            
            # Extract filename from Content-Disposition header
            content_disp = response.headers.get('Content-Disposition', '')
            filename = None
            
            if content_disp:
                # Extract filename from header
                match = re.search(r'filename="([^"]+)"', content_disp)
                if match:
                    raw_filename = match.group(1)
                    # Decode filename (CCEI uses ISO-8859-1 encoding)
                    try:
                        filename = raw_filename.encode('iso-8859-1').decode('utf-8')
                    except:
                        filename = raw_filename
            
            # If we got a proper filename, update the save path
            if filename and filename != save_path:
                # Keep the directory but use the actual filename
                save_dir = os.path.dirname(save_path)
                save_path = os.path.join(save_dir, filename)
                logger.info(f"Using actual filename: {filename}")
            
            # Download the file
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"Successfully downloaded: {save_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading file from {url}: {e}")
            return False
    
    def process_announcement(self, announcement: dict, index: int, output_base: str = 'output'):
        """개별 공고 처리 - CCEI 특화 (improved.py 기반)"""
        logger.info(f"Processing announcement {index}: {announcement['title']}")
        
        # 폴더 생성
        folder_title = self.sanitize_filename(announcement['title'])[:50]
        folder_name = f"{index:03d}_{folder_title}"
        folder_path = os.path.join(output_base, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        # 상세 페이지 가져오기
        response = self.get_page(announcement['url'])
        if not response:
            logger.error(f"상세 페이지 가져오기 실패: {announcement['title']}")
            return
            
        # 상세 내용 파싱 - URL 전달
        try:
            detail = self.parse_detail_page(response.text, announcement['url'])
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
        if detail['attachments']:
            attachments_path = os.path.join(folder_path, 'attachments')
            os.makedirs(attachments_path, exist_ok=True)
            
            for attachment in detail['attachments']:
                # For CCEI, use the UUID as temporary filename
                temp_filename = attachment.get('uuid', attachment['name'])
                if not temp_filename.endswith(('.hwp', '.pdf', '.docx', '.xlsx', '.zip')):
                    temp_filename += '.download'  # Add extension for safety
                    
                file_path = os.path.join(attachments_path, temp_filename)
                
                if self.download_file(attachment['url'], file_path):
                    # File will be renamed by download_file method
                    logger.info(f"Downloaded: {attachment['name']}")
                else:
                    logger.warning(f"Failed to download: {attachment['name']}")
        else:
            logger.info("No attachments found")
        
        # 처리된 제목으로 추가
        self.add_processed_title(announcement['title'])