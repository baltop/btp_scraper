"""
경북신용보증재단(GBSINBO) 전용 스크래퍼 - 향상된 버전

사이트 특성:
- URL: https://gbsinbo.co.kr/page/10054/10007.tc
- 시스템: 커스텀 JSP 기반 게시판
- 페이지네이션: JavaScript 함수 방식 (boardList.pageMove)
- 목록 구조: table.com_table.board 클래스
- 링크 패턴: JavaScript onclick="boardList.view('id')" 방식
- 상세 페이지: GET 파라미터 (boardNo, boardMngNo)
- 첨부파일: fileDown 클래스, readFile.tc 패턴
- 인코딩: UTF-8
"""

import os
import re
import logging
import time
from urllib.parse import urljoin, unquote, urlparse, parse_qs
from bs4 import BeautifulSoup
from enhanced_base_scraper import StandardTableScraper
import asyncio
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

class EnhancedGbsinboScraper(StandardTableScraper):
    """GBSINBO 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (fallback용)
        self.base_url = "https://gbsinbo.co.kr"
        self.list_url = "https://gbsinbo.co.kr/page/10054/10007.tc"
        
        # 사이트별 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 2
        
        # 요청 헤더 설정
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - JavaScript POST 방식"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if hasattr(self, 'config') and self.config and hasattr(self.config, 'pagination'):
            return super().get_list_url(page_num)
        
        # Fallback: GBSINBO 특화 로직
        if page_num == 1:
            return self.list_url
        else:
            # JavaScript 함수를 POST 요청으로 변환
            return f"{self.list_url}?pageIndex={page_num}"
    
    def _get_page_announcements(self, page_num: int) -> list:
        """페이지별 공고 목록 가져오기 - POST 요청 처리"""
        
        if page_num == 1:
            # 첫 페이지는 직접 접근
            response = self.get_page(self.list_url)
        else:
            # 페이지 이동을 위한 POST 요청
            post_data = {
                'pageIndex': str(page_num),
                'searchCondition': '1',
                'searchKeyword': '',
                'boardMngNo': '3'
            }
            response = self.post_page(self.list_url, data=post_data)
        
        if not response:
            logger.warning(f"페이지 {page_num} 응답을 가져올 수 없습니다")
            return []
        
        # 페이지가 에러 상태거나 잘못된 경우 감지
        if response.status_code >= 400:
            logger.warning(f"페이지 {page_num} HTTP 에러: {response.status_code}")
            return []
        
        announcements = self.parse_list_page(response.text)
        
        # 추가 마지막 페이지 감지 로직
        if not announcements and page_num > 1:
            logger.info(f"페이지 {page_num}에 공고가 없어 마지막 페이지로 판단됩니다")
        
        return announcements
    
    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱"""
        # 설정 기반 파싱이 가능하면 사용
        if hasattr(self, 'config') and self.config and hasattr(self.config, 'selectors'):
            return super().parse_list_page(html_content)
        
        # Fallback: 사이트 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> list:
        """GBSINBO 특화된 목록 파싱 로직"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # table.com_table.board 클래스를 가진 테이블 찾기
        table = soup.find('table', class_='com_table board')
        if not table:
            logger.warning("com_table board 클래스를 가진 테이블을 찾을 수 없습니다")
            return announcements
        
        tbody = table.find('tbody') or table
        rows = tbody.find_all('tr')
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 5:  # 최소 5개 셀 (번호, 제목, 작성자, 조회수, 작성일)
                    continue
                
                # onclick 이벤트에서 ID 추출
                onclick_attr = None
                for cell in cells:
                    onclick = cell.get('onclick')
                    if onclick and 'boardList.view' in onclick:
                        onclick_attr = onclick
                        break
                
                if not onclick_attr:
                    continue
                
                # ID 추출
                id_match = re.search(r"boardList\.view\('(\d+)'\)", onclick_attr)
                if not id_match:
                    continue
                
                board_id = id_match.group(1)
                
                # 제목 (보통 두 번째 셀)
                title = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                
                # 작성자 (보통 세 번째 셀)
                author = cells[2].get_text(strip=True) if len(cells) > 2 else "경북신용보증재단"
                
                # 조회수 (보통 네 번째 셀)  
                views = cells[3].get_text(strip=True) if len(cells) > 3 else "0"
                
                # 작성일 (보통 다섯 번째 셀)
                date = cells[4].get_text(strip=True) if len(cells) > 4 else ""
                
                if not title:
                    continue
                
                # 상세 페이지 URL 구성
                detail_url = f"{self.base_url}/page/10054/10007.tc?boardNo={board_id}&boardMngNo=3&importUrl=%2Fboard%2Fview.tc"
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'author': author,
                    'date': date,
                    'views': views,
                    'board_id': board_id
                }
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱: {title}")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str, url: str = None) -> dict:
        """상세 페이지 파싱 - Playwright로 동적 로딩 처리"""
        
        # JavaScript로 동적 로딩되는 사이트이므로 Playwright 사용
        if url and '?' in url:
            # URL에서 boardNo 추출
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            board_no = query_params.get('boardNo', [None])[0]
            
            if board_no:
                logger.info(f"Playwright로 동적 상세 페이지 로딩: boardNo={board_no}")
                return asyncio.run(self._parse_detail_with_playwright(board_no))
        
        # 일반적인 파싱 (fallback)
        return self._parse_detail_fallback(html_content)
    
    async def _parse_detail_with_playwright(self, board_no: str) -> dict:
        """Playwright를 사용한 동적 상세 페이지 파싱"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # 목록 페이지 먼저 로드
                await page.goto(self.list_url, wait_until='networkidle')
                
                # JavaScript 함수로 상세 페이지 로드
                await page.evaluate(f"boardList.view('{board_no}')")
                
                # 상세 페이지 로드 대기
                await page.wait_for_selector('.board_view', timeout=10000)
                
                # 페이지 내용 가져오기
                html_content = await page.content()
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # 제목 추출 - 목록에서 가져온 제목 사용
                title = f"boardNo_{board_no}"  # 기본값
                
                # 본문 추출
                content = ""
                content_area = soup.find('div', class_='board_view')
                if content_area:
                    # 실제 본문 내용 찾기
                    text_elements = content_area.find_all(['td', 'div', 'p'])
                    for elem in text_elements:
                        text = elem.get_text(strip=True)
                        if ('붙임' in text and '참조' in text) or (len(text) > 10 and len(text) < 500):
                            if '붙임파일' in text or '참조' in text:
                                content = f"<p>{text}</p>"
                                logger.debug("본문 텍스트 추출 성공")
                                break
                    
                    if not content:
                        # 전체 board_view 영역 사용
                        content = str(content_area)
                        logger.debug("board_view 전체 영역 사용")
                
                if not content:
                    content = "<p>붙임파일 참조바랍니다.</p>"
                    logger.debug("기본 본문 사용")
                
                # 첨부파일 추출
                attachments = []
                file_links = soup.find_all('a', class_='fileDown')
                logger.info(f"{len(file_links)}개의 첨부파일 발견 (Playwright)")
                
                for link in file_links:
                    try:
                        href = link.get('href', '')
                        if not href:
                            continue
                        
                        file_url = urljoin(self.base_url, href)
                        filename = link.get_text(strip=True)
                        
                        # 파일명에서 크기 정보 제거
                        filename = re.sub(r'\s*\[[^\]]+\]$', '', filename)
                        
                        if filename:
                            attachment = {
                                'filename': filename,
                                'url': file_url
                            }
                            attachments.append(attachment)
                            logger.debug(f"첨부파일 (Playwright): {filename}")
                        
                    except Exception as e:
                        logger.error(f"첨부파일 파싱 중 오류 (Playwright): {e}")
                        continue
                
                return {
                    'title': title,
                    'content': content,
                    'attachments': attachments,
                    'links': []
                }
                
            except Exception as e:
                logger.error(f"Playwright 상세 페이지 파싱 실패: {e}")
                return {
                    'title': f"boardNo_{board_no}",
                    'content': "<p>동적 페이지 로딩 실패</p>",
                    'attachments': [],
                    'links': []
                }
            finally:
                await browser.close()
    
    def _parse_detail_fallback(self, html_content: str) -> dict:
        """일반적인 상세 페이지 파싱 (fallback)"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        title = ""
        content = "<p>본문 내용을 추출할 수 없습니다.</p>"
        attachments = self._extract_attachments(soup)
        
        return {
            'title': title,
            'content': content,
            'attachments': attachments,
            'links': []
        }
    
    def _extract_attachments(self, soup: BeautifulSoup) -> list:
        """첨부파일 정보 추출"""
        attachments = []
        
        # fileDown 클래스를 가진 링크들 찾기
        file_links = soup.find_all('a', class_='fileDown')
        logger.info(f"{len(file_links)}개의 첨부파일 발견")
        
        for link in file_links:
            try:
                href = link.get('href', '')
                if not href:
                    continue
                
                file_url = urljoin(self.base_url, href)
                
                # 파일명 추출
                filename = link.get_text(strip=True)
                
                # 파일명에서 크기 정보 제거
                filename = re.sub(r'\s*\[[^\]]+\]$', '', filename)
                
                if filename:
                    attachment = {
                        'filename': filename,
                        'url': file_url
                    }
                    attachments.append(attachment)
                    logger.debug(f"첨부파일: {filename}")
                
            except Exception as e:
                logger.error(f"첨부파일 파싱 중 오류: {e}")
                continue
        
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment: dict = None) -> bool:
        """파일 다운로드"""
        try:
            # Referer 헤더 추가 (보안 강화)
            download_headers = self.headers.copy()
            download_headers['Referer'] = self.base_url
            
            response = self.session.get(
                url, 
                headers=download_headers,
                stream=True, 
                verify=self.verify_ssl, 
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # 파일 크기 확인
            total_size = int(response.headers.get('content-length', 0))
            
            with open(save_path, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
            
            file_size = os.path.getsize(save_path)
            logger.info(f"다운로드 완료: {save_path} ({file_size:,} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"파일 다운로드 실패 {url}: {e}")
            if os.path.exists(save_path):
                os.remove(save_path)
            return False

# 하위 호환성을 위한 별칭
GbsinboScraper = EnhancedGbsinboScraper