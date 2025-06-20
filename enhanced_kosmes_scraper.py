#!/usr/bin/env python3
"""
KOSMES (중소벤처기업진흥공단) Enhanced Scraper
사이트: https://www.kosmes.or.kr/nsh/SH/NTS/SHNTS001M0.do
"""

import os
import re
import time
import logging
from urllib.parse import urljoin, unquote
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import requests
from playwright.sync_api import sync_playwright

# 상위 디렉토리의 enhanced_base_scraper 모듈 import
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from enhanced_base_scraper import StandardTableScraper

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedKosmesScraper(StandardTableScraper):
    """KOSMES 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 기본 설정
        self.base_url = "https://www.kosmes.or.kr"
        self.list_url = "https://www.kosmes.or.kr/nsh/SH/NTS/SHNTS001M0.do"
        
        # 사이트별 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 2
        
        # 헤더 설정
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # 세션 설정
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # JavaScript 필요 여부 플래그
        self.requires_javascript = True
        
    def fetch_page_with_playwright(self, url: str, page_num: int = 1) -> str:
        """Playwright를 사용하여 동적 페이지 로딩"""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # 페이지 이동
                logger.info(f"Playwright로 페이지 {page_num} 로딩 중: {url}")
                page.goto(url, wait_until="networkidle")
                
                # 페이지 번호가 1이 아닌 경우 해당 페이지로 이동
                if page_num > 1:
                    logger.info(f"페이지 {page_num}로 이동 중")
                    # goPage JavaScript 함수 호출
                    page.evaluate(f"goPage({page_num})")
                    
                    # 테이블 로딩 대기
                    page.wait_for_selector('table tbody tr', timeout=30000)
                    time.sleep(2)  # 추가 대기
                
                # 동적 컨텐츠 로딩 대기
                try:
                    if 'SHNTS001F0.do' in url:  # 상세페이지인 경우
                        # TTU_TXT div 또는 downFile div가 로딩될 때까지 대기
                        page.wait_for_selector('#TTU_TXT, #downFile1', timeout=10000)
                        time.sleep(3)  # JavaScript 실행 완료 대기
                    else:  # 목록페이지인 경우
                        page.wait_for_selector('table tbody tr', timeout=10000)
                except:
                    logger.warning("동적 컨텐츠 로딩 대기 중 타임아웃")
                
                # HTML 내용 가져오기
                html_content = page.content()
                browser.close()
                
                logger.info(f"Playwright로 페이지 로딩 완료: {len(html_content)} 문자")
                return html_content
                
        except Exception as e:
            logger.error(f"Playwright 페이지 로딩 실패: {e}")
            # 대체 방법으로 일반 requests 사용
            return self._fetch_with_requests(url)
    
    def _fetch_with_requests(self, url: str) -> str:
        """requests를 사용한 일반적인 페이지 로딩"""
        try:
            response = self.session.get(url, timeout=self.timeout, verify=self.verify_ssl)
            response.raise_for_status()
            
            if response.encoding is None:
                response.encoding = self.default_encoding
                
            return response.text
        except Exception as e:
            logger.error(f"requests 페이지 로딩 실패: {e}")
            return ""
    
    def _get_page_announcements(self, page_num: int) -> List[Dict[str, Any]]:
        """페이지별 공고 목록 가져오기 - Playwright 사용"""
        logger.info(f"_get_page_announcements 호출됨: page_num={page_num}")
        
        if self.requires_javascript:
            # Playwright로 동적 페이지 로딩
            page_url = self.get_list_url(page_num)
            html_content = self.fetch_page_with_playwright(page_url, page_num)
            
            if not html_content:
                logger.warning(f"페이지 {page_num} HTML 내용을 가져올 수 없습니다")
                return []
            
            # 파싱 수행
            announcements = self.parse_list_page(html_content)
            return announcements
        else:
            # 부모 클래스의 기본 구현 사용
            return super()._get_page_announcements(page_num)
        
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: KOSMES 특화 로직
        # JavaScript 기반 페이지네이션이므로 모든 페이지에 동일한 URL 사용
        return self.list_url
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: KOSMES 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """KOSMES 특화된 목록 파싱"""
        announcements = []
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 테이블 찾기
        table = soup.find('table')
        if not table:
            logger.warning("공고 테이블을 찾을 수 없습니다")
            return announcements
            
        tbody = table.find('tbody')
        if not tbody:
            logger.warning("테이블 tbody를 찾을 수 없습니다")
            return announcements
            
        rows = tbody.find_all('tr')
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 4:  # 번호, 구분, 제목, 등록일
                    continue
                
                # 번호
                number = cells[0].get_text(strip=True)
                
                # 구분
                category = cells[1].get_text(strip=True)
                
                # 제목과 링크
                title_cell = cells[2]
                link_elem = title_cell.find('a')
                
                if not link_elem:
                    continue
                    
                title = link_elem.get_text(strip=True)
                
                # href 속성 확인 후 JavaScript 함수 확인
                href = link_elem.get('href', '')
                onclick = link_elem.get('onclick', '')
                
                seq_no = None
                detail_url = None
                
                # href가 JavaScript 함수인 경우
                if href and href != 'javascript:void(0)' and href.startswith('javascript:'):
                    # JavaScript에서 seqNo 추출
                    seq_no_match = re.search(r'fn_detail\([\'"]?(\d+)[\'"]?\)', href)
                    if seq_no_match:
                        seq_no = seq_no_match.group(1)
                
                # onclick에서 seqNo 추출
                if not seq_no and onclick:
                    seq_no_match = re.search(r'fn_detail\([\'"]?(\d+)[\'"]?\)', onclick)
                    if seq_no_match:
                        seq_no = seq_no_match.group(1)
                
                # 직접 링크인 경우
                if not seq_no and href and not href.startswith('javascript:'):
                    detail_url = urljoin(self.base_url, href)
                    # URL에서 seqNo 추출 시도
                    seq_no_match = re.search(r'seqNo=(\d+)', detail_url)
                    if seq_no_match:
                        seq_no = seq_no_match.group(1)
                
                if not detail_url and seq_no:
                    detail_url = f"{self.base_url}/nsh/SH/NTS/SHNTS001F0.do?seqNo={seq_no}&nowPage=1&searchG=titleCon&searchT="
                
                if not detail_url:
                    logger.debug(f"상세 페이지 URL을 찾을 수 없습니다: {title}")
                    continue
                
                # 등록일
                date = cells[3].get_text(strip=True)
                
                announcement = {
                    'number': number,
                    'category': category,
                    'title': title,
                    'url': detail_url,
                    'date': date,
                    'seq_no': seq_no
                }
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱 완료: {title}")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱"""
        # 설정이 있으면 부모 클래스 구현 사용
        if self.config and self.config.selectors:
            return super().parse_detail_page(html_content)
        
        # Fallback: KOSMES 특화 로직
        # URL은 HTML에서 추출하거나 기본값 사용
        return self._parse_detail_fallback(html_content, self.base_url)
    
    def _parse_detail_fallback(self, html_content: str, announcement_url: str) -> Dict[str, Any]:
        """KOSMES 특화된 상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 제목 추출 - 테이블의 첫 번째 행에서
        title = ""
        title_cell = soup.find('td')
        if title_cell:
            title = title_cell.get_text(strip=True)
        
        # 본문 추출 - TTU_TXT ID를 가진 div에서
        content = ""
        content_div = soup.find('div', id='TTU_TXT')
        if content_div:
            content = content_div.get_text(separator='\n', strip=True)
            logger.debug("본문을 TTU_TXT div에서 찾음")
        else:
            # 대체 방법: detailInfo div에서 본문 부분 추출
            detail_div = soup.find('div', id='detailInfo')
            if detail_div:
                # 테이블 이후의 텍스트 추출
                table = detail_div.find('table')
                if table:
                    # 테이블 다음의 모든 텍스트
                    content_parts = []
                    for sibling in table.next_siblings:
                        if hasattr(sibling, 'get_text'):
                            text = sibling.get_text(strip=True)
                            if text and len(text) > 10:  # 의미있는 텍스트만
                                content_parts.append(text)
                        elif isinstance(sibling, str) and sibling.strip():
                            content_parts.append(sibling.strip())
                    content = '\n'.join(content_parts)
                    logger.debug("본문을 detailInfo 테이블 이후에서 찾음")
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup)
        
        result = {
            'title': title,
            'content': content,
            'attachments': attachments,
            'url': announcement_url
        }
        
        logger.info(f"상세 페이지 파싱 완료: {title}")
        return result
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """첨부파일 정보 추출"""
        attachments = []
        
        # 첨부파일 링크 찾기 - lfn_fileDown JavaScript onclick 패턴
        attachment_links = soup.find_all('a', onclick=re.compile(r'lfn_fileDown'))
        
        for link in attachment_links:
            try:
                onclick = link.get('onclick', '')
                filename = link.get_text(strip=True)
                
                # lfn_fileDown() 함수에서 파라미터 추출
                # 예: lfn_fileDown('fileMskTxt', 'fileName', 'upload')
                params_match = re.search(r"lfn_fileDown\s*\(\s*['\"]([^'\"]*)['\"],\s*['\"]([^'\"]*)['\"],\s*['\"]([^'\"]*)['\"]", onclick)
                if params_match:
                    file_msk_txt, file_name, upload_type = params_match.groups()
                    
                    # 다운로드 URL 구성 (KOSMES 특화)
                    download_url = f"{self.base_url}/nsh/cmm/fms/FileDown.do?fileMskTxt={file_msk_txt}&fileName={file_name}"
                    
                    attachment = {
                        'filename': file_name or filename,
                        'url': download_url,
                        'file_msk_txt': file_msk_txt,
                        'upload_type': upload_type
                    }
                    
                    attachments.append(attachment)
                    logger.debug(f"첨부파일 발견: {attachment['filename']}")
                
            except Exception as e:
                logger.error(f"첨부파일 추출 중 오류: {e}")
                continue
        
        # downFile1, downFile2, downFile3 div에서도 찾기
        for i in range(1, 4):
            div_id = f'downFile{i}'
            download_div = soup.find('div', id=div_id)
            if download_div and download_div.get('style') != 'display: none;':
                link = download_div.find('a', onclick=re.compile(r'lfn_fileDown'))
                if link:
                    try:
                        onclick = link.get('onclick', '')
                        filename = link.get_text(strip=True)
                        
                        params_match = re.search(r"lfn_fileDown\s*\(\s*['\"]([^'\"]*)['\"],\s*['\"]([^'\"]*)['\"],\s*['\"]([^'\"]*)['\"]", onclick)
                        if params_match:
                            file_msk_txt, file_name, upload_type = params_match.groups()
                            
                            download_url = f"{self.base_url}/nsh/cmm/fms/FileDown.do?fileMskTxt={file_msk_txt}&fileName={file_name}"
                            
                            # 중복 체크
                            if not any(att['filename'] == file_name for att in attachments):
                                attachment = {
                                    'filename': file_name or filename,
                                    'url': download_url,
                                    'file_msk_txt': file_msk_txt,
                                    'upload_type': upload_type
                                }
                                
                                attachments.append(attachment)
                                logger.debug(f"첨부파일 발견 (div {div_id}): {attachment['filename']}")
                    
                    except Exception as e:
                        logger.error(f"첨부파일 추출 중 오류 (div {div_id}): {e}")
                        continue
        
        logger.info(f"{len(attachments)}개 첨부파일 발견")
        return attachments
    
    def download_file(self, url: str, save_path: str, filename: str = None) -> bool:
        """파일 다운로드"""
        try:
            response = self.session.get(url, stream=True, timeout=60, verify=self.verify_ssl)
            response.raise_for_status()
            
            # 파일명 처리
            if not filename:
                filename = self._extract_filename_from_response(response, save_path)
            else:
                filename = os.path.join(os.path.dirname(save_path), self.sanitize_filename(filename))
            
            # 디렉토리 생성
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            # 파일 다운로드
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(filename)
            logger.info(f"다운로드 완료: {os.path.basename(filename)} ({file_size:,} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"파일 다운로드 실패 {url}: {e}")
            return False
    
    def _extract_filename_from_response(self, response: requests.Response, default_path: str) -> str:
        """Response에서 파일명 추출 - 향상된 한글 처리"""
        save_dir = os.path.dirname(default_path)
        
        content_disposition = response.headers.get('Content-Disposition', '')
        
        if content_disposition:
            # RFC 5987 형식 우선 처리 (filename*=UTF-8''%ED%95%9C%EA%B8%80.hwp)
            rfc5987_match = re.search(r"filename\*=([^']*)'([^']*)'(.+)", content_disposition)
            if rfc5987_match:
                encoding, lang, filename = rfc5987_match.groups()
                try:
                    filename = unquote(filename, encoding=encoding or 'utf-8')
                    return os.path.join(save_dir, self.sanitize_filename(filename))
                except:
                    pass
            
            # 일반 filename 파라미터 처리
            filename_match = re.search(r'filename[^;=\n]*=([\'"]*)(.*?)\1', content_disposition)
            if filename_match:
                filename = filename_match.group(2)
                
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
                    except:
                        continue
        
        # 기본 파일명 사용
        return default_path
    
    def process_announcement(self, announcement: Dict[str, Any], index: int, output_base: str = 'output'):
        """개별 공고 처리 - Playwright 사용하여 상세 페이지 로딩"""
        logger.info(f"공고 처리 중 {index}: {announcement['title']}")
        
        # 폴더 생성
        folder_title = self.sanitize_filename(announcement['title'])[:100]
        folder_name = f"{index:03d}_{folder_title}"
        
        if len(folder_name) > 200:
            folder_title = folder_title[:195]
            folder_name = f"{index:03d}_{folder_title}"
        
        folder_path = os.path.join(output_base, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        # 상세 페이지 가져오기 - Playwright 사용
        try:
            if self.requires_javascript:
                html_content = self.fetch_page_with_playwright(announcement['url'], 1)
            else:
                response = self.get_page(announcement['url'])
                if response:
                    html_content = response.text
                else:
                    logger.error(f"상세 페이지 가져오기 실패: {announcement['title']}")
                    return
            
            if not html_content:
                logger.error(f"상세 페이지 내용이 비어있음: {announcement['title']}")
                return
                
            # 상세 페이지 파싱
            detail = self.parse_detail_page(html_content)
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
        
        # 첨부파일 처리
        if detail['attachments']:
            attachments_dir = os.path.join(folder_path, 'attachments')
            os.makedirs(attachments_dir, exist_ok=True)
            
            for i, attachment in enumerate(detail['attachments']):
                try:
                    filename = attachment.get('filename', f'attachment_{i+1}')
                    save_path = os.path.join(attachments_dir, filename)
                    
                    if self.download_file(attachment['url'], save_path, filename):
                        logger.info(f"첨부파일 다운로드 완료: {filename}")
                    else:
                        logger.warning(f"첨부파일 다운로드 실패: {filename}")
                        
                except Exception as e:
                    logger.error(f"첨부파일 처리 중 오류: {e}")
                    continue
        else:
            logger.info("첨부파일이 없습니다")
        
        # 처리된 제목 추가
        self.add_processed_title(announcement['title'])
    
    def _create_meta_info(self, announcement: Dict[str, Any]) -> str:
        """메타 정보 생성"""
        meta_info = f"# {announcement['title']}\n\n"
        
        if announcement.get('date'):
            meta_info += f"**등록일**: {announcement['date']}\n\n"
        
        if announcement.get('category'):
            meta_info += f"**구분**: {announcement['category']}\n\n"
        
        if announcement.get('url'):
            meta_info += f"**원본 URL**: {announcement['url']}\n\n"
        
        meta_info += "---\n\n"
        return meta_info

# 하위 호환성을 위한 별칭
KosmesScraper = EnhancedKosmesScraper

if __name__ == "__main__":
    scraper = EnhancedKosmesScraper()
    output_dir = "output/kosmes"
    os.makedirs(output_dir, exist_ok=True)
    scraper.scrape_pages(max_pages=3, output_base=output_dir)