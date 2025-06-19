# -*- coding: utf-8 -*-
"""
한국콘텐츠진흥원(KOCCA) 전용 스크래퍼 - 향상된 버전
"""

import re
import os
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
from enhanced_base_scraper import StandardTableScraper
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class EnhancedKOCCAScraper(StandardTableScraper):
    """한국콘텐츠진흥원(KOCCA) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://www.kocca.kr"
        self.list_url = "https://www.kocca.kr/kocca/pims/list.do?menuNo=204104"
        self.pms_base_url = "https://pms.kocca.kr"  # 첨부파일 서버
        
        # 사이트 특화 설정
        self.verify_ssl = True
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
        # KOCCA 특화 페이지네이션 파라미터
        return f"{self.list_url}&pageIndex={page_num}&category=&search=&searchWrd=&recptSt="
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: 사이트 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """KOCCA 특화된 파싱 로직 - 표준 HTML 테이블 기반"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # KOCCA는 표준 테이블 구조
        table = soup.find('table')
        
        if not table:
            logger.warning("테이블을 찾을 수 없습니다")
            return announcements
        
        tbody = table.find('tbody')
        if not tbody:
            tbody = table
        
        rows = tbody.find_all('tr')
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 5:  # 구분, 제목, 공고일, 접수기간, 조회
                    continue
                
                # 각 셀 정보 추출 (KOCCA 실제 구조)
                category_cell = cells[0]  # 구분 (모집공모, 자유공고)
                title_cell = cells[1]  # 제목 (링크 포함)
                notice_date_cell = cells[2]  # 공고일
                period_cell = cells[3]  # 접수기간
                views_cell = cells[4]  # 조회수
                
                # 제목 링크 찾기
                title_link = title_cell.find('a')
                if not title_link:
                    continue
                
                # 제목과 URL 추출
                title = title_link.get_text(strip=True)
                href = title_link.get('href', '')
                
                if not href or not title:
                    continue
                
                # 상세 페이지 URL 생성
                detail_url = urljoin(self.base_url, href)
                
                # 카테고리 추출
                category = category_cell.get_text(strip=True)
                
                # 첨부파일 여부 확인 (JavaScript 함수가 있는지)
                has_attachment = False
                onclick_attr = title_link.get('onclick', '')
                if 'openNoticeFileList' in onclick_attr:
                    has_attachment = True
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'category': category,
                    'has_attachment': has_attachment
                }
                
                # 추가 정보 추출
                try:
                    # 공고일
                    notice_date = notice_date_cell.get_text(strip=True)
                    if notice_date:
                        announcement['notice_date'] = notice_date
                    
                    # 접수기간
                    period = period_cell.get_text(strip=True)
                    if period:
                        announcement['period'] = period
                    
                    # 조회수
                    views = views_cell.get_text(strip=True)
                    if views and views.isdigit():
                        announcement['views'] = int(views)
                    
                    # intcNo 추출 (첨부파일 다운로드에 필요)
                    if href:
                        parsed_url = urlparse(href)
                        query_params = parse_qs(parsed_url.query)
                        intc_no = query_params.get('intcNo', [None])[0]
                        if intc_no:
                            announcement['intc_no'] = intc_no
                            
                except Exception as e:
                    logger.warning(f"추가 정보 추출 중 오류: {e}")
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱 완료: {title[:50]}...")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str, url: str = None) -> Dict[str, Any]:
        """상세 페이지 파싱 - KOCCA 구조 기반"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        result = {
            'content': '',
            'attachments': []
        }
        
        # URL에서 intcNo 추출 (첨부파일 다운로드에 필요)
        intc_no = None
        if url:
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            intc_no = query_params.get('intcNo', [None])[0]
            logger.debug(f"URL에서 intcNo 추출: {intc_no}")
        
        # KOCCA 특화: 본문 영역 찾기
        content_parts = []
        
        # 상세 페이지의 본문 영역 찾기
        content_selectors = [
            '.view_area',
            '.content_area',
            '.board_view',
            '#content',
            '.detail_content'
        ]
        
        content_found = False
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                try:
                    # HTML to Markdown 변환
                    content_md = self.h.handle(str(content_elem))
                    content_parts.append(content_md)
                    content_found = True
                    logger.debug(f"{selector} 선택자로 본문 추출 완료")
                    break
                except Exception as e:
                    logger.error(f"HTML to Markdown 변환 실패: {e}")
                    content_parts.append(content_elem.get_text(separator='\n', strip=True))
                    content_found = True
                    break
        
        # 본문이 없으면 전체 페이지에서 추출
        if not content_found:
            logger.warning("본문 영역을 찾을 수 없어 전체 페이지에서 추출")
            # 불필요한 요소들 제거
            for tag in soup(['script', 'style', 'nav', 'header', 'footer', '.navigation', '.sidebar']):
                tag.decompose()
            
            # 메인 콘텐츠 영역 찾기
            main_content = soup.find('div', class_='content') or soup.find('div', id='content')
            if main_content:
                content_parts.append(main_content.get_text(separator='\n', strip=True))
            else:
                content_parts.append(soup.get_text(separator='\n', strip=True))
        
        result['content'] = '\n\n---\n\n'.join(content_parts)
        
        # 첨부파일 찾기 (intcNo 전달)
        result['attachments'] = self._extract_attachments(soup, intc_no)
        
        logger.info(f"상세 페이지 파싱 완료 - 내용길이: {len(result['content'])}, 첨부파일: {len(result['attachments'])}")
        return result
    
    def _extract_attachments(self, soup: BeautifulSoup, intc_no: str = None) -> List[Dict[str, Any]]:
        """첨부파일 추출 - KOCCA 구조 기반 (JavaScript 팝업 처리)"""
        attachments = []
        
        # KOCCA의 첨부파일은 JavaScript 함수로 팝업 창에서 처리됨
        # "공고관련자료확인" 링크에서 openNoticeFileList2() 함수의 파라미터 찾기
        file_key = None
        
        # 1. onclick 속성에서 찾기
        file_links = soup.find_all('a', onclick=re.compile(r'openNoticeFileList2'))
        for link in file_links:
            onclick_text = link.get('onclick', '')
            match = re.search(r"openNoticeFileList2\(['\"]([^'\"]+)['\"]\)", onclick_text)
            if match:
                file_key = match.group(1)
                logger.debug(f"onclick 속성에서 첨부파일 키 발견: {file_key}")
                break
        
        # 2. href 속성에서 찾기 (백업)
        if not file_key:
            file_links = soup.find_all('a', href=re.compile(r'openNoticeFileList2'))
            for link in file_links:
                href_text = link.get('href', '')
                match = re.search(r"openNoticeFileList2\(['\"]([^'\"]+)['\"]\)", href_text)
                if match:
                    file_key = match.group(1)
                    logger.debug(f"href 속성에서 첨부파일 키 발견: {file_key}")
                    break
        
        # 3. script 태그에서 찾기 (백업)
        if not file_key:
            script_tags = soup.find_all('script')
            for script in script_tags:
                script_text = script.get_text()
                match = re.search(r"openNoticeFileList2\(['\"]([^'\"]+)['\"]\)", script_text)
                if match:
                    file_key = match.group(1)
                    logger.debug(f"script 태그에서 첨부파일 키 발견: {file_key}")
                    break
        
        if not file_key:
            logger.warning("첨부파일 키를 찾을 수 없습니다")
            return attachments
        
        try:
            # 첨부파일 목록 페이지 요청 (실제 KOCCA 구조 기반)
            file_list_url = f"{self.pms_base_url}/pblanc/pblancPopupViewPage.do"
            file_list_params = {
                'pblancId': file_key
            }
            
            logger.debug(f"첨부파일 목록 요청: {file_list_url}?pblancId={file_key}")
            
            file_response = self.session.get(
                file_list_url,
                params=file_list_params,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            file_response.raise_for_status()
            
            # 첨부파일 목록 파싱
            file_soup = BeautifulSoup(file_response.text, 'html.parser')
            
            # 파일 목록 테이블에서 파일 정보 추출
            file_table = file_soup.find('table', class_=lambda x: x and 'file' in x.lower() if x else False) or \
                        file_soup.find('table', string=re.compile('파일첨부'))
            
            if not file_table:
                # 테이블이 명시적으로 없으면 전체 페이지에서 파일 링크 찾기
                file_table = file_soup
            
            # 숨겨진 attachFileId 필드에서 실제 파일 ID 찾기
            attach_file_id = None
            hidden_inputs = file_soup.find_all('input', type='hidden')
            for inp in hidden_inputs:
                name = inp.get('name', '')
                if 'attfile' in name.lower() or 'attach' in name.lower():
                    attach_file_id = inp.get('value', '')
                    logger.debug(f"숨겨진 필드에서 attachFileId 발견: {attach_file_id}")
                    break
            
            # attachFileId를 사용해 실제 파일 목록 API 호출
            if attach_file_id:
                try:
                    file_api_url = f"{self.pms_base_url}/file/innorix/fileList.do"
                    file_api_data = {'attachFileId': attach_file_id}
                    
                    logger.debug(f"파일 목록 API 호출: {file_api_url} with {file_api_data}")
                    
                    api_response = self.session.post(
                        file_api_url,
                        data=file_api_data,
                        timeout=self.timeout,
                        verify=self.verify_ssl
                    )
                    
                    if api_response.status_code == 200:
                        try:
                            api_data = api_response.json()
                            if isinstance(api_data, list):
                                for file_info in api_data:
                                    file_name = file_info.get('fileName', file_info.get('fileNm', ''))
                                    download_key = file_info.get('dwnldUk', file_info.get('fileId', ''))
                                    file_size = file_info.get('fileSize', file_info.get('fileSz', ''))
                                    
                                    if file_name and download_key:
                                        file_url = f"{self.pms_base_url}/file/innorix/download.do?dwnldUk={download_key}"
                                        
                                        attachment = {
                                            'name': file_name,
                                            'url': file_url,
                                            'download_key': download_key,
                                            'attach_file_id': attach_file_id,
                                            'type': 'api_download'
                                        }
                                        
                                        if file_size:
                                            attachment['size'] = str(file_size)
                                        
                                        attachments.append(attachment)
                                        logger.debug(f"API에서 첨부파일 발견: {file_name} (key: {download_key})")
                            
                            elif isinstance(api_data, dict) and api_data.get('fileList'):
                                # 다른 JSON 구조인 경우
                                for file_info in api_data['fileList']:
                                    file_name = file_info.get('fileName', file_info.get('fileNm', ''))
                                    download_key = file_info.get('dwnldUk', file_info.get('fileId', ''))
                                    
                                    if file_name and download_key:
                                        file_url = f"{self.pms_base_url}/file/innorix/download.do?dwnldUk={download_key}"
                                        
                                        attachment = {
                                            'name': file_name,
                                            'url': file_url,
                                            'download_key': download_key,
                                            'attach_file_id': attach_file_id,
                                            'type': 'api_download'
                                        }
                                        
                                        attachments.append(attachment)
                                        logger.debug(f"API에서 첨부파일 발견: {file_name}")
                        
                        except Exception as json_error:
                            logger.debug(f"JSON 파싱 실패: {json_error}")
                            # HTML 응답인 경우도 있을 수 있음
                    
                    else:
                        logger.debug(f"API 응답 상태: {api_response.status_code}")
                
                except Exception as e:
                    logger.debug(f"API 호출 실패: {e}")
                    
            else:
                logger.debug("attachFileId를 찾을 수 없음")
            
            # attachFileId를 사용해 패턴 기반으로 다운로드 키 추정 (실험적)
            if not attachments and attach_file_id:
                logger.debug("패턴 기반 다운로드 키 추정 시도")
                potential_keys = self._generate_potential_download_keys(attach_file_id)
                
                for potential_key in potential_keys:
                    try:
                        test_url = f"{self.pms_base_url}/file/innorix/download.do?dwnldUk={potential_key}"
                        # HEAD가 지원되지 않으므로 GET으로 테스트 (stream=True로 부분 다운로드)
                        test_response = self.session.get(test_url, stream=True, timeout=10)
                        
                        if test_response.status_code == 200:
                            # 실제 파일명 추출
                            content_disp = test_response.headers.get('Content-Disposition', '')
                            file_name = 'attachment'
                            
                            if content_disp:
                                filename_match = re.search(r'filename[^;=\n]*=([\'"]*)(.*?)\1', content_disp)
                                if filename_match:
                                    file_name = filename_match.group(2)
                                    # URL 디코딩
                                    try:
                                        from urllib.parse import unquote
                                        file_name = unquote(file_name)
                                    except:
                                        pass
                            
                            attachment = {
                                'name': file_name,
                                'url': test_url,
                                'download_key': potential_key,
                                'attach_file_id': attach_file_id,
                                'type': 'pattern_match'
                            }
                            
                            file_size = test_response.headers.get('Content-Length')
                            if file_size:
                                attachment['size'] = f"{int(file_size):,} bytes"
                            
                            # 스트림 연결 닫기 (다운로드용 새 연결을 위해)
                            test_response.close()
                            
                            attachments.append(attachment)
                            logger.debug(f"패턴 매칭으로 첨부파일 발견: {file_name} (key: {potential_key})")
                            break  # 첫 번째 성공한 키만 사용
                    
                    except Exception as e:
                        continue  # 다음 키 시도
            
            # API로 파일을 찾지 못한 경우 HTML에서 직접 파싱
            if not attachments:
                logger.debug("API 방식 실패, HTML 파싱으로 첨부파일 추출 시도")
                
                # 파일 테이블 찾기 - 더 구체적으로 찾기
                tables = file_soup.find_all('table')
                file_table = None
                
                for table in tables:
                    # 테이블 내용에서 "파일명" 또는 "첨부" 키워드가 있는 테이블 찾기
                    table_text = table.get_text()
                    if '파일명' in table_text or '첨부' in table_text or 'KB' in table_text or 'MB' in table_text:
                        file_table = table
                        break
                
                if file_table:
                    logger.debug("파일 테이블 발견, 파싱 시도")
                    file_rows = file_table.find_all('tr')
                    
                    for row in file_rows:
                        cells = row.find_all('td')
                        if len(cells) >= 2:  # 최소 파일명과 용량 컬럼이 있어야 함
                            file_link = row.find('a')
                            if file_link:
                                file_name = file_link.get_text(strip=True)
                                
                                # 헤더나 빈 값 제외
                                if file_name and file_name not in ['순번', '파일명', '용량', '구분', '일반']:
                                    # 파일 크기 정보 추출
                                    size_text = ''
                                    for cell in cells:
                                        cell_text = cell.get_text(strip=True)
                                        if re.search(r'\d+\.?\d*\s*[KMG]?B', cell_text):
                                            size_text = cell_text
                                            break
                                    
                                    attachment = {
                                        'name': file_name,
                                        'url': f"{self.pms_base_url}/file/download_placeholder",
                                        'file_key': file_key,
                                        'type': 'html_extract',
                                        'needs_processing': True
                                    }
                                    
                                    if size_text:
                                        attachment['size'] = size_text
                                    
                                    attachments.append(attachment)
                                    logger.debug(f"HTML에서 첨부파일 발견: {file_name} ({size_text})")
                else:
                    logger.debug("파일 테이블을 찾을 수 없음")
                    
                    # 테이블이 없어도 링크에서 파일을 찾는 시도
                    all_links = file_soup.find_all('a')
                    for link in all_links:
                        link_text = link.get_text(strip=True)
                        # 파일 확장자가 있는 링크 찾기
                        if re.search(r'\.(hwp|pdf|doc|docx|xls|xlsx|zip|rar)$', link_text, re.IGNORECASE):
                            attachment = {
                                'name': link_text,
                                'url': f"{self.pms_base_url}/file/download_placeholder",
                                'file_key': file_key,
                                'type': 'link_extract',
                                'needs_processing': True
                            }
                            attachments.append(attachment)
                            logger.debug(f"링크에서 첨부파일 발견: {link_text}")
            
        except Exception as e:
            logger.error(f"첨부파일 목록 가져오기 실패: {e}")
            
            # 최후의 수단: 원본 상세 페이지에서 첨부파일 링크 직접 찾기
            try:
                attachment_links = soup.find_all('a', string=re.compile(r'첨부|다운로드|파일'))
                for link in attachment_links:
                    link_text = link.get_text(strip=True)
                    if link_text and '첨부' in link_text:
                        attachment = {
                            'name': link_text,
                            'url': f"{self.pms_base_url}/file/download_placeholder",
                            'file_key': file_key,
                            'type': 'fallback',
                            'needs_processing': True
                        }
                        attachments.append(attachment)
                        logger.debug(f"fallback으로 첨부파일 발견: {link_text}")
            except Exception as e2:
                logger.error(f"fallback 첨부파일 추출도 실패: {e2}")
        
        logger.info(f"총 {len(attachments)}개 첨부파일 발견 (intcNo: {intc_no})")
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment_info: dict = None) -> bool:
        """KOCCA 특화 파일 다운로드 - 팝업 서버 처리"""
        try:
            logger.info(f"파일 다운로드 시작: {url}")
            
            # 플레이스홀더 URL인 경우 실제 다운로드 URL 찾기
            if 'download_placeholder' in url and attachment_info:
                if attachment_info.get('needs_processing'):
                    # 파일키를 사용해서 실제 다운로드 URL 찾기
                    file_key = attachment_info.get('file_key')
                    file_name = attachment_info.get('name', '')
                    
                    if file_key:
                        # 첨부파일 목록 페이지에서 실제 다운로드 URL 추출
                        try:
                            real_url = self._get_real_download_url(file_key, file_name)
                            if real_url:
                                url = real_url
                                logger.debug(f"실제 다운로드 URL 획득: {url}")
                            else:
                                logger.warning(f"실제 다운로드 URL을 찾을 수 없음: {file_name}")
                                return False
                        except Exception as e:
                            logger.error(f"실제 다운로드 URL 획득 실패: {e}")
                            return False
            
            # KOCCA의 팝업 서버 다운로드 처리
            download_headers = self.headers.copy()
            download_headers['Referer'] = self.pms_base_url
            
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
    
    def _get_real_download_url(self, file_key: str, file_name: str) -> str:
        """파일키와 파일명을 이용해 실제 다운로드 URL 찾기"""
        try:
            # 첨부파일 목록 페이지 재접속
            file_list_url = f"{self.pms_base_url}/pblanc/pblancPopupViewPage.do"
            file_list_params = {'pblancId': file_key}
            
            response = self.session.get(file_list_url, params=file_list_params)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # API 방식으로 다운로드 키 찾기
            try:
                file_api_url = f"{self.pms_base_url}/file/innorix/fileList.do"
                file_api_data = {'attachFileId': file_key}
                
                api_response = self.session.post(file_api_url, data=file_api_data)
                
                if api_response.status_code == 200:
                    api_data = api_response.json()
                    if isinstance(api_data, list):
                        for file_info in api_data:
                            api_file_name = file_info.get('fileName', file_info.get('fileNm', ''))
                            download_key = file_info.get('fileId', file_info.get('dwnldUk', ''))
                            
                            if api_file_name == file_name and download_key:
                                return f"{self.pms_base_url}/file/innorix/download.do?dwnldUk={download_key}"
            except:
                pass
            
            # HTML에서 다운로드 링크 패턴 찾기 (백업)
            file_links = soup.find_all('a')
            for link in file_links:
                if link.get_text(strip=True) == file_name:
                    onclick = link.get('onclick', '')
                    if 'download' in onclick.lower():
                        # onclick에서 다운로드 키 추출 시도
                        key_match = re.search(r"download[^'\"]*['\"']([^'\"]+)['\"]", onclick)
                        if key_match:
                            download_key = key_match.group(1)
                            return f"{self.pms_base_url}/file/innorix/download.do?dwnldUk={download_key}"
            
            return None
            
        except Exception as e:
            logger.error(f"실제 다운로드 URL 찾기 실패: {e}")
            return None
    
    def _generate_potential_download_keys(self, attach_file_id: str) -> List[str]:
        """attachFileId에서 가능한 다운로드 키들을 생성"""
        potential_keys = []
        
        if not attach_file_id:
            return potential_keys
        
        # 패턴 1: U000을 V000으로 변경 (관찰된 패턴)
        if attach_file_id.endswith('U000'):
            key1 = attach_file_id.replace('U000', 'V000')
            potential_keys.append(key1)
        
        # 패턴 2: 마지막 문자 변경 시도 (U -> V, E -> F 등)
        if len(attach_file_id) > 0:
            last_char = attach_file_id[-4]  # 끝에서 4번째 문자
            if last_char == 'U':
                key2 = attach_file_id[:-4] + 'V' + attach_file_id[-3:]
                potential_keys.append(key2)
            elif last_char == 'E':
                key3 = attach_file_id[:-4] + 'F' + attach_file_id[-3:]
                potential_keys.append(key3)
        
        # 패턴 3: 그대로 사용
        potential_keys.append(attach_file_id)
        
        # 패턴 4: 다른 일반적인 변환 시도
        transformations = [
            ('NVU000', 'NVV000'),
            ('RNE000', 'RNF000'),
            ('000', '001'),
            ('000', '999')
        ]
        
        for old_pattern, new_pattern in transformations:
            if old_pattern in attach_file_id:
                key = attach_file_id.replace(old_pattern, new_pattern)
                potential_keys.append(key)
        
        # 중복 제거
        unique_keys = []
        for key in potential_keys:
            if key not in unique_keys:
                unique_keys.append(key)
        
        return unique_keys


# 하위 호환성을 위한 별칭
KOCCAScraper = EnhancedKOCCAScraper