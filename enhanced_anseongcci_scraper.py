# -*- coding: utf-8 -*-
"""
안성상공회의소(ANSEONGCCI) 향상된 스크래퍼
- JavaScript 기반 페이지네이션
- 표준 테이블 구조
- 직접 파일 다운로드 링크
"""

import requests
from bs4 import BeautifulSoup
import os
import time
import re
import logging
from urllib.parse import urljoin, quote
from enhanced_base_scraper import StandardTableScraper
import asyncio
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

class EnhancedAnseongCCIScraper(StandardTableScraper):
    """안성상공회의소 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        
        # 기본 설정
        self.base_url = "https://anseongcci.korcham.net"
        self.list_url = "https://anseongcci.korcham.net/front/board/boardContentsListPage.do?boardId=10123&menuId=2962"
        
        # 사이트별 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        
        # 헤더 설정
        self.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.session.headers.update(self.headers)
        
        logger.info("안성상공회의소 스크래퍼 초기화 완료")
        
        # 테스트용 첫 번째 공고만 처리하는 플래그
        self.test_mode = False
        self.max_items_per_page = None
    
    async def get_page_with_playwright(self, url: str) -> str:
        """Playwright를 사용해서 JavaScript 렌더링된 페이지 가져오기"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # 페이지 이동 및 로딩 대기
                await page.goto(url, wait_until='networkidle')
                
                # 게시판 테이블이 로드될 때까지 대기
                try:
                    await page.wait_for_selector('table', timeout=10000)
                except:
                    logger.warning("테이블 로딩 대기 타임아웃")
                
                # 추가 대기 (JavaScript 실행 완료를 위해)
                await page.wait_for_timeout(2000)
                
                # HTML 가져오기
                html_content = await page.content()
                
                await browser.close()
                return html_content
                
        except Exception as e:
            logger.error(f"Playwright로 페이지 가져오기 실패: {e}")
            return ""
    
    def _get_page_announcements(self, page_num: int) -> list:
        """페이지별 공고 목록 가져오기 - Playwright 사용"""
        page_url = self.get_list_url(page_num)
        logger.info(f"페이지 URL: {page_url}")
        
        try:
            # Playwright로 페이지 가져오기
            html_content = asyncio.run(self.get_page_with_playwright(page_url))
            
            if not html_content:
                logger.warning(f"페이지 {page_num} 내용을 가져올 수 없습니다")
                return []
            
            announcements = self.parse_list_page(html_content)
            return announcements
            
        except Exception as e:
            logger.error(f"페이지 {page_num} 가져오기 실패: {e}")
            return []
    
    async def get_detail_page_with_playwright(self, list_url: str, detail_js_url: str) -> str:
        """Playwright를 사용해서 JavaScript 상세 페이지 가져오기"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # 먼저 목록 페이지로 이동
                await page.goto(list_url, wait_until='networkidle')
                
                # 게시판 테이블이 로드될 때까지 대기
                await page.wait_for_selector('table', timeout=10000)
                await page.wait_for_timeout(2000)
                
                # contentsView ID 추출
                id_match = re.search(r"contentsView\('(\d+)'\)", detail_js_url)
                if not id_match:
                    logger.error(f"상세 페이지 ID를 찾을 수 없습니다: {detail_js_url}")
                    await browser.close()
                    return ""
                
                content_id = id_match.group(1)
                
                # contentsView 함수를 실행하는 링크 클릭
                try:
                    # 다양한 방법으로 링크 찾기
                    selectors = [
                        f'a[onclick*="contentsView(\'{content_id}\')"]',
                        f'a[href*="contentsView(\'{content_id}\')"]',
                        f'a:has-text("{content_id}")'
                    ]
                    
                    clicked = False
                    for selector in selectors:
                        try:
                            await page.click(selector, timeout=5000)
                            clicked = True
                            break
                        except:
                            continue
                    
                    if not clicked:
                        # JavaScript 직접 실행
                        await page.evaluate(f'contentsView("{content_id}")')
                        clicked = True
                    
                    # 상세 페이지 로딩 대기
                    try:
                        await page.wait_for_url('**/boardContentsView.do', timeout=10000)
                    except:
                        # URL 변경이 없어도 내용 변경 확인
                        await page.wait_for_selector('table', timeout=5000)
                    
                    await page.wait_for_timeout(2000)
                    
                    # HTML 가져오기
                    html_content = await page.content()
                    
                except Exception as e:
                    logger.error(f"상세 페이지 클릭/로딩 실패: {e}")
                    html_content = ""
                
                await browser.close()
                return html_content
                
        except Exception as e:
            logger.error(f"Playwright로 상세 페이지 가져오기 실패: {e}")
            return ""
    
    def get_detail_page(self, detail_url: str, list_url: str = None) -> str:
        """상세 페이지 가져오기 - JavaScript URL 처리"""
        if detail_url.startswith('javascript:'):
            # JavaScript URL인 경우 Playwright 사용
            if not list_url:
                list_url = self.list_url
            
            return asyncio.run(self.get_detail_page_with_playwright(list_url, detail_url))
        else:
            # 일반 URL인 경우 기존 방식 사용
            response = self.get_page(detail_url)
            return response.text if response else ""
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - JavaScript 기반 페이지네이션"""
        if page_num == 1:
            return self.list_url
        else:
            # 페이지 파라미터 추가
            separator = '&' if '?' in self.list_url else '?'
            return f"{self.list_url}{separator}currentPageNo={page_num}"
    
    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        try:
            # 다양한 방법으로 게시판 테이블 찾기
            table = None
            
            # 방법 1: 일반적인 table 태그
            table = soup.find('table')
            
            # 방법 2: class나 id로 찾기
            if not table:
                table = soup.find('table', {'class': re.compile(r'.*board.*|.*list.*|.*게시.*', re.I)})
            
            # 방법 3: 게시물이 있는 테이블 찾기 (JavaScript로 삽입된 경우)
            if not table:
                # 모든 테이블을 찾아서 게시물이 있는지 확인
                tables = soup.find_all('table')
                for t in tables:
                    text = t.get_text()
                    if any(keyword in text for keyword in ['공지', '제목', '번호', '날짜', '조회']):
                        table = t
                        break
            
            if not table:
                logger.warning("게시판 테이블을 찾을 수 없습니다")
                logger.debug(f"HTML 일부: {html_content[:1000]}")
                return announcements
            
            logger.debug(f"테이블 발견: {table.name if table else 'None'}")
            
            # tbody 찾기 (없으면 table 직접 사용)
            tbody = table.find('tbody')
            if not tbody:
                tbody = table
            
            # 행들 찾기
            rows = tbody.find_all('tr')
            logger.info(f"총 {len(rows)}개 행 발견")
            
            for i, row in enumerate(rows):
                try:
                    cells = row.find_all('td')
                    if len(cells) < 2:  # 최소 필드 확인 (번호, 제목)
                        continue
                    
                    # 안성상공회의소 특별 구조: 첫 번째 셀은 번호, 두 번째 셀은 제목
                    if len(cells) == 2:
                        # 번호와 제목만 있는 경우
                        number_cell = cells[0]
                        title_cell = cells[1]
                    else:
                        # 일반적인 구조
                        title_cell = cells[1] if len(cells) > 1 else cells[0]
                    
                    # 제목 셀에서 링크 찾기
                    link_elem = title_cell.find('a')
                    
                    if not link_elem:
                        # 링크가 없는 경우 제목만 있는 행일 수 있음 (헤더 행)
                        continue
                    
                    title = link_elem.get_text(strip=True)
                    if not title:
                        continue
                    
                    # href 속성 또는 onclick 속성에서 URL 추출
                    href = link_elem.get('href', '')
                    onclick = link_elem.get('onclick', '')
                    
                    detail_url = ""
                    content_id = ""
                    
                    # 방법 1: href 속성에 직접 URL이 있는 경우
                    if href and href != '#' and 'javascript:' not in href:
                        detail_url = urljoin(self.base_url, href)
                    
                    # 방법 2: onclick에서 contentsView 함수 찾기
                    elif onclick:
                        # contentsView('117526') 패턴
                        id_match = re.search(r"contentsView\('(\d+)'\)", onclick)
                        if id_match:
                            content_id = id_match.group(1)
                            # contentsView는 JavaScript 함수이므로 실제 클릭이 필요
                            detail_url = f"javascript:contentsView('{content_id}')"
                        
                        # 다른 JavaScript 함수 패턴들 확인
                        else:
                            # 다양한 패턴 확인
                            patterns = [
                                r"view\('(\d+)'\)",
                                r"goView\('(\d+)'\)",
                                r"boardView\('(\d+)'\)",
                                r"(\d+)"  # 숫자만 있는 경우
                            ]
                            for pattern in patterns:
                                match = re.search(pattern, onclick)
                                if match:
                                    content_id = match.group(1)
                                    detail_url = f"{self.base_url}/front/board/boardContentsView.do?contentsId={content_id}&boardId=10123&menuId=2962"
                                    break
                    
                    # 방법 3: href에 javascript: URL이 있는 경우
                    elif href and 'javascript:' in href:
                        id_match = re.search(r"contentsView\('(\d+)'\)", href)
                        if id_match:
                            content_id = id_match.group(1)
                            # JavaScript 함수이므로 그대로 사용
                            detail_url = href
                    
                    if not detail_url:
                        logger.warning(f"상세 페이지 URL을 찾을 수 없습니다: {title}")
                        logger.debug(f"href: {href}, onclick: {onclick}")
                        # 링크 element 전체 출력
                        logger.debug(f"Link element: {str(link_elem)}")
                        continue
                    
                    # 공지/일반 구분
                    status = ""
                    if len(cells) >= 2:
                        first_cell = cells[0]
                        if first_cell.find('img'):
                            status = "공지"
                        else:
                            status = first_cell.get_text(strip=True)
                    
                    # 날짜 추출 (마지막 셀, 있는 경우)
                    date = ""
                    if len(cells) >= 3:
                        date = cells[-1].get_text(strip=True)
                    
                    announcement = {
                        'title': title,
                        'url': detail_url,
                        'status': status,
                        'date': date,
                        'content_id': content_id
                    }
                    
                    announcements.append(announcement)
                    logger.debug(f"공고 추가: {title}")
                    
                except Exception as e:
                    logger.error(f"행 {i} 파싱 중 오류: {e}")
                    continue
            
            # 테스트 모드에서는 첫 번째 공고만 처리
            if self.test_mode or self.max_items_per_page:
                limit = self.max_items_per_page or 1
                announcements = announcements[:limit]
                logger.info(f"테스트 모드: {len(announcements)}개 공고로 제한")
            
            logger.info(f"총 {len(announcements)}개 공고 파싱 완료")
            return announcements
            
        except Exception as e:
            logger.error(f"목록 페이지 파싱 실패: {e}")
            return announcements
    
    def parse_detail_page(self, html_content: str) -> dict:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        result = {
            'content': '',
            'attachments': []
        }
        
        try:
            # 상세 내용 테이블 찾기
            detail_table = soup.find('table')
            if not detail_table:
                logger.warning("상세 내용 테이블을 찾을 수 없습니다")
                return result
            
            # 제목 추출
            title_row = detail_table.find('tr')
            title = ""
            if title_row:
                title_cell = title_row.find('td')
                if title_cell:
                    title = title_cell.get_text(strip=True)
            
            # 본문 내용 추출 (가장 큰 셀 또는 마지막 row의 큰 셀)
            content_cell = None
            rows = detail_table.find_all('tr')
            
            for row in rows:
                cells = row.find_all('td')
                for cell in cells:
                    cell_text = cell.get_text(strip=True)
                    # 본문으로 보이는 긴 텍스트가 있는 셀 찾기
                    if len(cell_text) > 50 and not cell_text.startswith('첨부파일'):
                        content_cell = cell
                        break
                if content_cell:
                    break
            
            if content_cell:
                # HTML을 마크다운으로 변환
                content_html = str(content_cell)
                result['content'] = self.h.handle(content_html)
            else:
                logger.warning("본문 내용을 찾을 수 없습니다")
            
            # 첨부파일 추출
            result['attachments'] = self._extract_attachments(soup)
            
            logger.info(f"상세 페이지 파싱 완료 - 내용길이: {len(result['content'])}, 첨부파일: {len(result['attachments'])}")
            return result
            
        except Exception as e:
            logger.error(f"상세 페이지 파싱 실패: {e}")
            return result
    
    def _extract_attachments(self, soup: BeautifulSoup) -> list:
        """첨부파일 링크 추출"""
        attachments = []
        
        try:
            # 첨부파일 링크 찾기 - 직접 파일 링크
            file_links = soup.find_all('a', href=re.compile(r'/file/'))
            
            for link in file_links:
                href = link.get('href', '')
                if not href:
                    continue
                
                # 파일 URL 구성
                if href.startswith('/'):
                    file_url = self.base_url + href
                else:
                    file_url = urljoin(self.base_url, href)
                
                # 파일명 추출
                filename = link.get_text(strip=True)
                if not filename:
                    # URL에서 파일명 추출 시도
                    filename = href.split('/')[-1]
                
                attachment = {
                    'url': file_url,
                    'filename': filename
                }
                
                attachments.append(attachment)
                logger.debug(f"첨부파일 발견: {filename}")
            
            logger.info(f"총 {len(attachments)}개 첨부파일 발견")
            return attachments
            
        except Exception as e:
            logger.error(f"첨부파일 추출 실패: {e}")
            return attachments
    
    def download_file(self, url: str, save_path: str, attachment_info: dict = None) -> bool:
        """파일 다운로드 - 안성상공회의소 특화"""
        try:
            logger.info(f"파일 다운로드 시작: {url}")
            
            # 다운로드 헤더 설정
            download_headers = self.headers.copy()
            download_headers['Referer'] = self.base_url
            
            response = self.session.get(
                url, 
                headers=download_headers, 
                stream=True, 
                timeout=self.timeout,
                verify=self.verify_ssl,
                allow_redirects=True
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
    
    def _extract_filename_from_response(self, response: requests.Response, save_dir: str) -> str:
        """응답 헤더에서 실제 파일명 추출"""
        content_disposition = response.headers.get('Content-Disposition', '')
        
        if content_disposition:
            # filename 파라미터 찾기
            filename_match = re.search(r'filename[^;=\n]*=(([\'"]).*?\2|[^;\n]*)', content_disposition)
            if filename_match:
                filename = filename_match.group(1).strip('"\'')
                
                # 인코딩 복구 시도
                for encoding in ['utf-8', 'euc-kr']:
                    try:
                        if encoding == 'utf-8':
                            decoded = filename.encode('latin-1').decode('utf-8')
                        else:
                            decoded = filename.encode('latin-1').decode(encoding)
                        
                        if decoded and not decoded.isspace():
                            clean_filename = self.sanitize_filename(decoded)
                            return os.path.join(save_dir, clean_filename)
                    except:
                        continue
        
        # URL에서 파일명 추출 시도
        from urllib.parse import urlparse, unquote
        parsed_url = urlparse(response.url)
        url_filename = unquote(parsed_url.path.split('/')[-1])
        if url_filename and '.' in url_filename:
            clean_filename = self.sanitize_filename(url_filename)
            return os.path.join(save_dir, clean_filename)
        
        # 기본 파일명 사용
        return os.path.join(save_dir, "download_file")
    
    def process_announcement(self, announcement: dict, index: int, output_base: str = 'output'):
        """개별 공고 처리 - 안성상공회의소 특화 버전"""
        logger.info(f"공고 처리 중 {index}: {announcement['title']}")
        
        # 폴더 생성
        folder_title = self.sanitize_filename(announcement['title'])[:100]
        folder_name = f"{index:03d}_{folder_title}"
        
        if len(folder_name) > 200:
            folder_title = folder_title[:195]
            folder_name = f"{index:03d}_{folder_title}"
        
        folder_path = os.path.join(output_base, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        # 상세 페이지 가져오기 - 안성상공회의소 특화 방식
        try:
            if announcement['url'].startswith('javascript:'):
                # JavaScript URL인 경우
                html_content = self.get_detail_page(announcement['url'], self.get_list_url(1))
            else:
                # 일반 URL인 경우
                response = self.get_page(announcement['url'])
                html_content = response.text if response else ""
            
            if not html_content:
                logger.error(f"상세 페이지 가져오기 실패: {announcement['title']}")
                return
                
        except Exception as e:
            logger.error(f"상세 페이지 가져오기 중 오류: {e}")
            return
        
        # 상세 내용 파싱
        try:
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
        
        # 첨부파일 다운로드
        self._download_attachments(detail['attachments'], folder_path)
        
        # 처리된 제목으로 추가
        self.add_processed_title(announcement['title'])
        
        # 요청 간 대기
        if self.delay_between_requests > 0:
            time.sleep(self.delay_between_requests)


def main():
    """테스트 실행"""
    import sys
    import logging
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('anseongcci_scraper.log', encoding='utf-8')
        ]
    )
    
    scraper = EnhancedAnseongCCIScraper()
    output_dir = "output/anseongcci"
    
    try:
        os.makedirs(output_dir, exist_ok=True)
        success = scraper.scrape_pages(max_pages=3, output_base=output_dir)
        
        if success:
            print("안성상공회의소 스크래핑 완료!")
        else:
            print("안성상공회의소 스크래핑 실패!")
            
    except Exception as e:
        logger.error(f"스크래핑 중 오류 발생: {e}")
        print(f"오류 발생: {e}")


if __name__ == "__main__":
    main()