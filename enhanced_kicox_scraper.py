# -*- coding: utf-8 -*-
"""
KICOX 전용 Enhanced 스크래퍼
사이트: https://www.kicox.or.kr/user/bbs/BD_selectBbsList.do?q_bbsCode=1016
특징: SSL 인증서 문제, 표준 테이블 구조, 파일 다운로드 UUID 방식
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

class EnhancedKicoxScraper(StandardTableScraper):
    """KICOX 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (fallback용) - HTTPS로 다시 시도 (Playwright용)
        self.base_url = "https://www.kicox.or.kr"
        self.list_url = "https://www.kicox.or.kr/user/bbs/BD_selectBbsList.do?q_bbsCode=1016"
        
        # 사이트 특화 설정
        self.verify_ssl = False  # SSL 인증서 문제
        self.default_encoding = 'utf-8'
        self.timeout = 60
        
        # KICOX 특화 헤더
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en;q=0.6',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # SSL 설정 추가
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # 연결 어댑터 설정 (SSL 문제 해결)
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=1
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def get_page(self, url: str, **kwargs):
        """KICOX 특화 페이지 가져오기 - Playwright로 SSL 문제 해결"""
        try:
            # 먼저 Playwright로 시도
            html_content = self._get_page_with_playwright(url)
            if html_content:
                # 가짜 Response 객체 생성
                class FakeResponse:
                    def __init__(self, text):
                        self.text = text
                        self.status_code = 200
                        self.encoding = 'utf-8'
                
                return FakeResponse(html_content)
        except Exception as e:
            logger.debug(f"Playwright 시도 실패, requests로 fallback: {e}")
        
        # 부모 클래스의 기본 방식으로 fallback
        return super().get_page(url, **kwargs)
    
    def _get_page_with_playwright(self, url: str):
        """Playwright로 페이지 가져오기 (SSL 문제 해결)"""
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    ignore_https_errors=True,  # SSL 에러 무시
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = context.new_page()
                
                # 페이지 로드
                response = page.goto(url, timeout=30000, wait_until='networkidle')
                if response and response.status < 400:
                    # 테이블이 로드될 때까지 대기
                    try:
                        page.wait_for_selector('table', timeout=10000)
                    except:
                        pass  # 테이블이 없어도 계속 진행
                    
                    html_content = page.content()
                    browser.close()
                    logger.info(f"Playwright로 페이지 로드 성공: {url}")
                    return html_content
                else:
                    browser.close()
                    return None
                    
        except ImportError:
            logger.warning("Playwright가 설치되지 않았습니다. pip install playwright 실행 후 playwright install 필요")
            return None
        except Exception as e:
            logger.debug(f"Playwright 페이지 로드 실패: {e}")
            return None
        
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - GET 파라미터 기반"""
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: q_currPage 파라미터 사용
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&q_bbscttSn=&q_currPage={page_num}&q_order=&q_clCode=&q_searchKeyTy=sj___1002&q_searchVal=&"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - 테이블 기반"""
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """KICOX 특화 목록 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 특정 테이블 구조 찾기 (caption에 "공지사항 정보"가 포함된 테이블)
        tables = soup.find_all('table')
        main_table = None
        
        for table in tables:
            caption = table.find('caption')
            if caption and '공지사항' in caption.get_text():
                main_table = table
                logger.debug("공지사항 테이블 발견")
                break
        
        # 못 찾으면 tbody가 있는 테이블 중에서 찾기
        if not main_table:
            for table in tables:
                tbody = table.find('tbody')
                if tbody:
                    rows = tbody.find_all('tr')
                    if len(rows) > 0:
                        # subject 클래스가 있는지 확인
                        for row in rows:
                            if row.find('td', class_='subject'):
                                main_table = table
                                logger.debug("subject 클래스 기반으로 테이블 발견")
                                break
                        if main_table:
                            break
        
        if not main_table:
            logger.warning("공고 목록 테이블을 찾을 수 없습니다")
            return announcements
        
        tbody = main_table.find('tbody')
        if not tbody:
            logger.warning("tbody를 찾을 수 없습니다")
            return announcements
        
        rows = tbody.find_all('tr')
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 3:  # 번호, 제목, 등록일 최소 3개 컬럼
                    continue
                
                # 제목 셀 찾기 (class="subject"가 있는 td)
                title_cell = row.find('td', class_='subject')
                if not title_cell:
                    # subject 클래스가 없으면 두 번째 셀 시도
                    if len(cells) > 1:
                        title_cell = cells[1]
                    else:
                        continue
                
                link_elem = title_cell.find('a')
                if not link_elem:
                    logger.debug("링크를 찾을 수 없는 행 건너뛰기")
                    continue
                
                title = link_elem.get_text(strip=True)
                href = link_elem.get('href', '')
                
                if not title or not href:
                    continue
                
                # 상세 페이지 URL 구성
                detail_url = urljoin(self.base_url, href)
                
                # 등록일 추출 - 날짜 형식의 텍스트가 있는 셀 찾기
                date = ""
                for cell in cells:
                    cell_text = cell.get_text(strip=True)
                    # 날짜 패턴 확인 (YYYY-MM-DD 형식)
                    import re
                    if re.match(r'\d{4}-\d{2}-\d{2}', cell_text):
                        date = cell_text
                        break
                
                # 첨부파일 여부 확인 - icon-file.png 이미지가 있는지 확인
                has_attachment = False
                for cell in cells:
                    file_img = cell.find('img', src=lambda x: x and 'icon-file.png' in x)
                    if file_img:
                        has_attachment = True
                        break
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'date': date,
                    'has_attachment': has_attachment,
                    'href': href  # 원본 href 보존
                }
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱: {title[:50]}...")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱"""
        if self.config and self.config.selectors:
            return super().parse_detail_page(html_content)
        
        return self._parse_detail_fallback(html_content)
    
    def _parse_detail_fallback(self, html_content: str) -> Dict[str, Any]:
        """KICOX 특화 상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 추출 시도
        content_area = None
        content_selectors = [
            '.view_area',
            '.content_area',
            '.board_view',
            '.view_content',
            '#content',
            '.content'
        ]
        
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        if not content_area:
            # 대안: 메인 콘텐츠 영역 찾기
            # KICOX는 div 구조가 복잡할 수 있으므로 다양한 방법 시도
            for div in soup.find_all('div'):
                div_text = div.get_text(strip=True)
                # 충분한 길이의 텍스트가 있는 div 찾기
                if len(div_text) > 100 and 'script' not in div.get('class', []):
                    content_area = div
                    logger.debug("텍스트 길이 기반으로 본문 영역 추정")
                    break
            
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
        title_selectors = ['h1', 'h2', 'h3', '.title', '.subject', '.view_title']
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = title_elem.get_text(strip=True)
                if title:
                    break
        
        # URL은 베이스 클래스에서 처리되므로 현재 URL 반환
        current_url = self.base_url + "/user/bbs/BD_selectBbs.do"
        
        return {
            'title': title,
            'content': content_markdown,
            'attachments': attachments,
            'url': current_url
        }
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """첨부파일 추출 - KICOX 특화"""
        attachments = []
        
        try:
            # KICOX 파일 다운로드 패턴: /component/file/ND_fileDownload.do?q_fileSn=XXX&q_fileId=UUID
            file_links = soup.find_all('a', href=lambda x: x and 'ND_fileDownload.do' in x)
            
            for link in file_links:
                href = link.get('href', '')
                if not href:
                    continue
                
                # 파일명 추출 - 링크 텍스트에서
                filename = link.get_text(strip=True)
                
                # 파일명이 없거나 너무 짧으면 href에서 파라미터 추출해서 임시 이름 생성
                if not filename or len(filename) < 3 or '다운로드' in filename:
                    # q_fileSn 파라미터에서 ID 추출
                    import re
                    sn_match = re.search(r'q_fileSn=(\d+)', href)
                    if sn_match:
                        file_sn = sn_match.group(1)
                        filename = f"attachment_{file_sn}"
                    else:
                        filename = f"attachment_{len(attachments) + 1}"
                
                # 확장자 추가 (주변 텍스트에서 확장자 정보 찾기)
                parent_text = ""
                parent = link.find_parent(['td', 'div', 'span'])
                if parent:
                    parent_text = parent.get_text()
                
                # 확장자 패턴 찾기
                for ext in ['.pdf', '.hwp', '.hwpx', '.doc', '.docx', '.zip', '.xlsx']:
                    if ext in parent_text.lower() and not filename.lower().endswith(ext):
                        filename += ext
                        break
                
                # URL 완성
                file_url = urljoin(self.base_url, href)
                
                attachments.append({
                    'name': filename,  # 베이스 클래스 호환성
                    'filename': filename,
                    'url': file_url,
                    'type': 'kicox_download'
                })
                
                logger.debug(f"첨부파일 발견: {filename}")
            
            # 추가 패턴: 일반적인 다운로드 링크들
            general_patterns = [
                'a[href*="fileDown"]',
                'a[href*="download"]',
                'a[href*=".pdf"]',
                'a[href*=".hwp"]',
                'a[href*=".zip"]',
                'a[href*=".doc"]'
            ]
            
            seen_urls = set(att['url'] for att in attachments)
            
            for pattern in general_patterns:
                links = soup.select(pattern)
                for link in links:
                    href = link.get('href', '')
                    if href and urljoin(self.base_url, href) not in seen_urls and 'javascript:' not in href:
                        text = link.get_text(strip=True)
                        if text and len(text) > 2:
                            file_url = urljoin(self.base_url, href)
                            attachments.append({
                                'name': text,  # 베이스 클래스 호환성
                                'filename': text,
                                'url': file_url,
                                'type': 'general_download'
                            })
                            seen_urls.add(file_url)
            
            logger.info(f"{len(attachments)}개 첨부파일 발견")
            for att in attachments:
                logger.debug(f"- {att['filename']} ({att['type']})")
            
        except Exception as e:
            logger.error(f"첨부파일 추출 중 오류: {e}")
        
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment: dict = None) -> bool:
        """첨부파일 다운로드 - KICOX 특화 (SSL 문제로 Playwright 사용)"""
        logger.info(f"파일 다운로드 시작: {url}")
        
        # 먼저 Playwright로 다운로드 시도
        logger.info("Playwright로 다운로드 시도 중...")
        success = self._download_with_playwright(url, save_path)
        if success:
            logger.info("Playwright 다운로드 성공!")
            return True
        
        # Playwright 실패 시 일반 requests로 시도
        logger.warning("Playwright 다운로드 실패, requests로 fallback 시도")
        
        try:
            # KICOX 파일 다운로드 헤더 설정
            download_headers = self.session.headers.copy()
            download_headers.update({
                'Referer': self.base_url + '/user/bbs/BD_selectBbsList.do',
                'Accept': 'application/pdf,application/zip,application/octet-stream,*/*',
            })
            
            response = self.session.get(
                url,
                headers=download_headers,
                timeout=self.timeout,
                verify=self.verify_ssl,  # False due to SSL issues
                stream=True  # 대용량 파일 지원
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
                        # 다양한 인코딩 시도
                        for encoding in ['utf-8', 'euc-kr', 'cp949']:
                            try:
                                if encoding == 'utf-8':
                                    decoded_filename = header_filename.encode('latin-1').decode('utf-8')
                                else:
                                    decoded_filename = header_filename.encode('latin-1').decode(encoding)
                                
                                if decoded_filename and len(decoded_filename) > 2:
                                    # 헤더의 파일명을 사용하여 저장 경로 업데이트
                                    save_dir = os.path.dirname(save_path)
                                    save_path = os.path.join(save_dir, self.sanitize_filename(decoded_filename))
                                    break
                            except:
                                continue
                    except:
                        pass
            
            # 스트리밍 다운로드로 메모리 효율성 확보
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(save_path)
            logger.info(f"requests 다운로드 완료: {save_path} ({file_size:,} bytes)")
            
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
    
    def _download_with_playwright(self, url: str, save_path: str) -> bool:
        """Playwright로 파일 다운로드 (SSL 문제 해결) - 개선된 버전"""
        try:
            from playwright.sync_api import sync_playwright
            
            logger.info(f"Playwright 초기화 중...")
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    ignore_https_errors=True,
                    accept_downloads=True,
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = context.new_page()
                
                try:
                    logger.info(f"Playwright로 URL 접근 중: {url}")
                    
                    # 다운로드 이벤트 감지
                    download_info = {}
                    
                    def handle_download(download):
                        download_info['download'] = download
                        logger.info(f"다운로드 이벤트 감지: {download.suggested_filename}")
                    
                    page.on("download", handle_download)
                    
                    # 다운로드 URL로 이동 - 단순히 load로 시도
                    try:
                        response = page.goto(url, timeout=30000, wait_until='load')
                        logger.info(f"페이지 로드 완료: {response.status if response else 'No response'}")
                        
                        # 다운로드 이벤트 대기
                        page.wait_for_timeout(3000)  # 3초 대기
                        
                        if 'download' in download_info:
                            download = download_info['download']
                            logger.info(f"다운로드 객체 획득: {download.suggested_filename}")
                            
                            # 다운로드된 파일을 지정된 경로로 저장
                            try:
                                download.save_as(save_path)
                                logger.info(f"파일 저장 시도: {save_path}")
                                
                                # 파일이 실제로 저장되었는지 확인
                                if os.path.exists(save_path):
                                    file_size = os.path.getsize(save_path)
                                    logger.info(f"Playwright 다운로드 완료: {save_path} ({file_size:,} bytes)")
                                    
                                    browser.close()
                                    return True
                                else:
                                    logger.warning(f"파일이 저장되지 않음: {save_path}")
                            except Exception as save_err:
                                logger.error(f"파일 저장 오류: {save_err}")
                                
                                # 다운로드 패스에서 직접 복사 시도
                                try:
                                    import shutil
                                    download_path = download.path()
                                    if download_path and os.path.exists(download_path):
                                        shutil.copy2(download_path, save_path)
                                        file_size = os.path.getsize(save_path)
                                        logger.info(f"Playwright 직접 복사 완료: {save_path} ({file_size:,} bytes)")
                                        browser.close()
                                        return True
                                except Exception as copy_err:
                                    logger.error(f"직접 복사도 실패: {copy_err}")
                        else:
                            # 다운로드 이벤트가 없으면 직접 응답 바디 시도
                            logger.info("다운로드 이벤트 없음, 직접 응답 시도")
                            if response and response.status < 400:
                                # 응답 바디를 직접 가져오기
                                content = response.body()
                                
                                if content and len(content) > 100:
                                    logger.info(f"응답 바디 크기: {len(content)} bytes")
                                    
                                    # 파일 저장
                                    with open(save_path, 'wb') as f:
                                        f.write(content)
                                    
                                    file_size = os.path.getsize(save_path)
                                    logger.info(f"Playwright 직접 다운로드 완료: {save_path} ({file_size:,} bytes)")
                                    
                                    # Content-Disposition 헤더에서 실제 파일명 추출 시도
                                    content_disposition = response.headers.get('content-disposition', '')
                                    if content_disposition:
                                        logger.info(f"Content-Disposition: {content_disposition}")
                                        actual_filename = self._extract_filename_from_header(content_disposition, save_path)
                                        if actual_filename != save_path:
                                            # 실제 파일명으로 리네임
                                            try:
                                                os.rename(save_path, actual_filename)
                                                logger.info(f"파일명 수정: {os.path.basename(actual_filename)}")
                                                save_path = actual_filename
                                            except Exception as rename_err:
                                                logger.warning(f"파일명 변경 실패: {rename_err}")
                                    
                                    browser.close()
                                    return True
                                else:
                                    logger.warning("응답 바디가 비어있거나 너무 작음")
                            else:
                                logger.warning(f"HTTP 오류: {response.status if response else 'No response'}")
                        
                    except Exception as goto_err:
                        logger.warning(f"페이지 이동 실패: {goto_err}")
                        # goto 실패 시에도 다운로드 이벤트가 있을 수 있으므로 체크
                        page.wait_for_timeout(3000)  # 다운로드 이벤트 대기
                        
                        if 'download' in download_info:
                            download = download_info['download']
                            logger.info(f"goto 실패하지만 다운로드 이벤트 있음: {download.suggested_filename}")
                            
                            try:
                                download.save_as(save_path)
                                if os.path.exists(save_path):
                                    file_size = os.path.getsize(save_path)
                                    logger.info(f"Playwright 다운로드 완료 (goto 실패하지만 다운로드 성공): {save_path} ({file_size:,} bytes)")
                                    browser.close()
                                    return True
                            except Exception as save_err:
                                logger.error(f"goto 실패 후 저장 오류: {save_err}")
                                try:
                                    import shutil
                                    download_path = download.path()
                                    if download_path and os.path.exists(download_path):
                                        shutil.copy2(download_path, save_path)
                                        file_size = os.path.getsize(save_path)
                                        logger.info(f"Playwright 직접 복사 완료 (goto 실패): {save_path} ({file_size:,} bytes)")
                                        browser.close()
                                        return True
                                except Exception as copy_err:
                                    logger.error(f"goto 실패 후 직접 복사도 실패: {copy_err}")
                        
                except Exception as e:
                    logger.error(f"Playwright 다운로드 중 오류: {e}")
                    import traceback
                    logger.debug(traceback.format_exc())
                finally:
                    try:
                        browser.close()
                    except:
                        pass
                    
                return False
                    
        except ImportError:
            logger.warning("Playwright 모듈이 없음")
            return False
        except Exception as e:
            logger.error(f"Playwright 다운로드 실패: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    def _extract_filename_from_header(self, content_disposition: str, default_path: str) -> str:
        """Content-Disposition 헤더에서 파일명 추출"""
        import re
        from urllib.parse import unquote
        
        save_dir = os.path.dirname(default_path)
        
        # RFC 5987 형식 우선 시도
        rfc5987_match = re.search(r"filename\*=([^']*)'([^']*)'(.+)", content_disposition)
        if rfc5987_match:
            encoding, lang, filename = rfc5987_match.groups()
            try:
                filename = unquote(filename, encoding=encoding or 'utf-8')
                return os.path.join(save_dir, self.sanitize_filename(filename))
            except:
                pass
        
        # 일반적인 filename 파라미터 시도
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
        
        return default_path


# 하위 호환성을 위한 별칭
KicoxScraper = EnhancedKicoxScraper