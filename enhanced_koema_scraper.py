# -*- coding: utf-8 -*-
"""
한국에너지공단 조합(KOEMA) 스크래퍼 - 향상된 아키텍처
onclick 기반 URL 추출과 특수 첨부파일 처리
"""

from enhanced_base_scraper import StandardTableScraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import logging
import os

logger = logging.getLogger(__name__)

class EnhancedKOEMAScraper(StandardTableScraper):
    """한국에너지공단 조합 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://www.koema.or.kr"
        self.list_url = "https://www.koema.or.kr/koema/report/total_notice.html"
        
        # KOEMA 특화 설정
        self.verify_ssl = True  # SSL 인증서 검증 사용
        self.default_encoding = 'utf-8'
        
        # KOEMA 특화 헤더 설정
        self.headers.update({
            'Referer': self.base_url,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate'
        })
        self.session.headers.update(self.headers)
    
    def get_list_url(self, page_num: int) -> str:
        """페이지 번호에 따른 목록 URL 반환"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: 기존 KOEMA 특화 로직
        if page_num == 1:
            return self.list_url
        else:
            # 일반적인 페이지네이션 패턴
            separator = '&' if '?' in self.list_url else '?'
            return f"{self.list_url}{separator}page={page_num}"
    
    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: 기존 KOEMA 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> list:
        """기존 방식의 목록 파싱 (Fallback)"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # KOEMA의 게시판 테이블 구조
        tbody = soup.select_one('tbody.bbs_list')
        if not tbody:
            logger.warning("tbody.bbs_list를 찾을 수 없습니다")
            return announcements
        
        logger.info("KOEMA 게시판 리스트 발견")
        
        # 테이블의 행들 찾기
        rows = tbody.select('tr')
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for i, row in enumerate(rows):
            try:
                # KOEMA는 onclick 속성에 URL이 있음
                onclick = row.get('onclick', '')
                if not onclick or 'board_view.html' not in onclick:
                    continue
                
                # onclick="location.href='/koema/report/board_view.html?idx=78340&page=1&sword=&category=all'"
                # 정규표현식으로 URL 추출
                url_match = re.search(r"location\.href='([^']+)'", onclick)
                if not url_match:
                    continue
                
                relative_url = url_match.group(1)
                detail_url = urljoin(self.base_url, relative_url)
                
                # 테이블 셀들 파싱
                cells = row.select('td')
                if len(cells) < 5:
                    continue
                
                # 순서: 번호, 제목, 작성자, 작성일, 조회수
                num = cells[0].get_text(strip=True)
                title = cells[1].get_text(strip=True)
                writer = cells[2].get_text(strip=True)
                date = cells[3].get_text(strip=True)
                views = cells[4].get_text(strip=True)
                
                if not title or len(title) < 3:
                    continue
                
                announcement = {
                    'num': num,
                    'title': title,
                    'writer': writer,
                    'date': date,
                    'views': views,
                    'url': detail_url
                }
                
                announcements.append(announcement)
                logger.debug(f"공고 추가: {title}")
                
            except Exception as e:
                logger.error(f"행 {i} 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> dict:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        result = {
            'content': '',
            'attachments': []
        }
        
        try:
            # 본문 추출
            content = self._extract_content(soup)
            result['content'] = content
            
            # 첨부파일 추출
            attachments = self._extract_attachments(soup)
            result['attachments'] = attachments
            
            logger.debug(f"상세 페이지 파싱 완료 - 내용: {len(content)}자, 첨부파일: {len(attachments)}개")
            
        except Exception as e:
            logger.error(f"상세 페이지 파싱 중 오류: {e}")
        
        return result
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """본문 내용 추출 - KOEMA 특화"""
        content_area = None
        
        # KOEMA의 다양한 본문 컨테이너 시도
        content_selectors = [
            'td.EditView',
            'div.view-content',
            'div.board-view-content', 
            'div.content',
            'td[class*="content"]',
            'td[style*="height:400px"]'  # KOEMA 특화
        ]
        
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        if not content_area:
            # 대체 방법: 가장 큰 텍스트 블록 찾기
            all_elements = soup.find_all(['div', 'td'])
            if all_elements:
                content_area = max(all_elements, key=lambda x: len(x.get_text()))
                logger.debug("본문을 최대 텍스트 블록으로 추정")
        
        if content_area:
            # 불필요한 요소들 제거
            for unwanted in content_area.select('script, style, nav, header, footer, .navigation, .menu'):
                unwanted.decompose()
            
            # HTML을 마크다운으로 변환
            content_html = str(content_area)
            content_text = self.h.handle(content_html)
            
            # 빈 줄 정리
            content_lines = [line.strip() for line in content_text.split('\n')]
            content_lines = [line for line in content_lines if line]
            return '\n\n'.join(content_lines)
        else:
            logger.warning("본문 내용을 찾을 수 없습니다")
            logger.debug(f"HTML 길이: {len(str(soup))}")
            return ""
    
    def _extract_attachments(self, soup: BeautifulSoup) -> list:
        """첨부파일 목록 추출 - KOEMA 특화"""
        attachments = []
        
        # KOEMA의 첨부파일 패턴: "첨부화일" 텍스트가 있는 행들
        attach_rows = []
        for td in soup.find_all('td'):
            if td.get_text(strip=True) == '첨부화일':
                # 같은 행의 다음 셀들에서 파일 정보 찾기
                parent_row = td.find_parent('tr')
                if parent_row:
                    attach_rows.append(parent_row)
        
        logger.debug(f"첨부파일 행 {len(attach_rows)}개 발견")
        
        # 파일명 패턴들
        file_patterns = [
            r'([^&\s]+\.(pdf|hwp|doc|docx|xls|xlsx|ppt|pptx|zip|rar|txt))',
            r'([가-힣a-zA-Z0-9\s\(\)_-]+\.(pdf|hwp|doc|docx|xls|xlsx|ppt|pptx|zip|rar|txt))'
        ]
        
        for row in attach_rows:
            try:
                # _pds_down.html 링크 찾기
                download_link = row.select_one('a[href*="_pds_down.html"]')
                if not download_link:
                    continue
                
                download_url = download_link.get('href', '')
                if not download_url:
                    continue
                
                # 파일명 추출 - 링크 앞의 텍스트에서 찾기
                row_text = row.get_text()
                
                file_name = None
                for pattern in file_patterns:
                    match = re.search(pattern, row_text, re.IGNORECASE)
                    if match:
                        file_name = match.group(1).strip()
                        break
                
                # 파일명을 찾지 못한 경우 셀 내용에서 추출 시도
                if not file_name:
                    cells = row.select('td')
                    for cell in cells:
                        cell_text = cell.get_text(strip=True)
                        if ('.' in cell_text and 
                            any(ext in cell_text.lower() for ext in ['.pdf', '.hwp', '.doc', '.xls', '.ppt', '.zip'])):
                            # 파일명으로 추정되는 부분 추출
                            parts = cell_text.split()
                            for part in parts:
                                if '.' in part and any(ext in part.lower() for ext in ['.pdf', '.hwp', '.doc', '.xls', '.ppt', '.zip']):
                                    file_name = part.strip('&nbsp;').strip()
                                    break
                            if file_name:
                                break
                
                if not file_name:
                    file_name = f"첨부파일_{len(attachments) + 1}"
                
                # 절대 URL 생성
                full_download_url = urljoin(self.base_url, download_url)
                
                # 중복 체크
                if not any(att['url'] == full_download_url for att in attachments):
                    attachments.append({
                        'name': file_name,
                        'url': full_download_url
                    })
                    logger.debug(f"첨부파일 추가: {file_name}")
                
            except Exception as e:
                logger.error(f"첨부파일 행 파싱 중 오류: {e}")
                continue
        
        # 보완: 직접 _pds_down.html 링크 찾기
        if not attachments:
            download_links = soup.select('a[href*="_pds_down.html"]')
            logger.debug(f"직접 다운로드 링크 {len(download_links)}개 발견")
            
            for i, link in enumerate(download_links):
                href = link.get('href', '')
                if not href:
                    continue
                
                # 링크 주변 텍스트에서 파일명 찾기
                parent = link.find_parent(['td', 'tr'])
                file_name = f"첨부파일_{i+1}"
                
                if parent:
                    parent_text = parent.get_text()
                    # 파일명 패턴 찾기
                    for pattern in file_patterns:
                        match = re.search(pattern, parent_text, re.IGNORECASE)
                        if match:
                            file_name = match.group(1).strip()
                            break
                
                full_url = urljoin(self.base_url, href)
                
                # 중복 체크
                if not any(att['url'] == full_url for att in attachments):
                    attachments.append({
                        'name': file_name,
                        'url': full_url
                    })
                    logger.debug(f"추가 첨부파일 추가: {file_name}")
        
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment_info: dict = None) -> bool:
        """파일 다운로드 - KOEMA 맞춤형"""
        try:
            logger.info(f"파일 다운로드 시작: {url}")
            
            # KOEMA 특화 헤더 설정
            headers = self.headers.copy()
            headers['Referer'] = self.base_url
            
            response = self.session.get(
                url, 
                headers=headers, 
                stream=True, 
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # 실제 파일명 추출 (기본 구현 사용)
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


# 하위 호환성을 위한 별칭
KOEMAScraper = EnhancedKOEMAScraper