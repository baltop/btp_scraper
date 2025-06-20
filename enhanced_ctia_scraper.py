"""
충남콘텐츠진흥원(CTIA) 전용 스크래퍼 - 향상된 버전
사이트: https://www.ctia.kr/bbs/board.php?bo_table=bnt
"""
import os
import re
import time
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote
from enhanced_base_scraper import StandardTableScraper

logger = logging.getLogger(__name__)

class EnhancedCTIAScraper(StandardTableScraper):
    """CTIA 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://www.ctia.kr"
        self.list_url = "https://www.ctia.kr/bbs/board.php?bo_table=bnt"
        
        # 사이트 특화 설정
        self.verify_ssl = False  # SSL 인증서 문제가 있을 수 있음
        self.default_encoding = 'utf-8'  
        self.timeout = 30
        self.delay_between_requests = 1
        
        # 그누보드 특화 헤더
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: 그누보드 기본 페이지네이션 방식
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&page={page_num}"
    
    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: CTIA 사이트 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> list:
        """CTIA 사이트별 특화된 파싱 로직"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 그누보드 기본 구조: .board_list ul li
        board_list = soup.find('div', class_='board_list')
        if not board_list:
            logger.warning("board_list div를 찾을 수 없습니다")
            return announcements
        
        ul_element = board_list.find('ul')
        if not ul_element:
            logger.warning("board_list 안의 ul 요소를 찾을 수 없습니다")
            return announcements
        
        rows = ul_element.find_all('li')
        logger.info(f"목록에서 {len(rows)}개 항목 발견")
        
        for row in rows:
            try:
                # 제목과 링크 추출
                subject_div = row.find('div', class_='bo_subject')
                if not subject_div:
                    continue
                
                link_elem = subject_div.find('a', class_='bo_subject')
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                href = link_elem.get('href', '')
                
                if not title or not href:
                    continue
                
                detail_url = urljoin(self.base_url, href)
                
                # 날짜 추출
                date_span = row.find('span', class_='bo_date')
                date = ''
                if date_span:
                    date = date_span.get_text(strip=True).replace('🕒', '').strip()
                
                # 첨부파일 여부 확인 (다운로드 아이콘 존재)
                has_attachment = bool(link_elem.find('i', class_='fa-download'))
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'date': date,
                    'has_attachment': has_attachment
                }
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱 완료: {title}")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str, url: str = "") -> dict:
        """상세 페이지 파싱"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.content_selectors:
            return super().parse_detail_page(html_content, url)
        
        # Fallback: CTIA 사이트 특화 로직
        return self._parse_detail_fallback(html_content, url)
    
    def _parse_detail_fallback(self, html_content: str, url: str = "") -> dict:
        """CTIA 사이트별 특화된 상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 제목 추출 - 그누보드 기본 구조
        title = ""
        title_elem = soup.find('h1', id='bo_v_title')
        if title_elem:
            title = title_elem.get_text(strip=True)
        else:
            # title 태그에서 추출
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True).split('|')[0].strip()
        
        # 본문 내용 추출 - 여러 선택자 시도
        content = ""
        content_selectors = [
            '#bo_v_con',      # 그누보드 표준 본문 영역
            '.bo_v_con',      # 클래스 형태
            '#bo_v_atc',      # 다른 그누보드 버전
            '.view_content',  # 일반적인 본문 클래스
        ]
        
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                content = content_area.get_text(separator='\n', strip=True)
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        if not content:
            # 본문을 찾지 못한 경우 전체 텍스트에서 추출
            body = soup.find('body')
            if body:
                content = body.get_text(separator='\n', strip=True)
                logger.warning("본문 영역을 찾지 못해 body 전체에서 추출")
        
        # 첨부파일 정보 추출
        attachments = self._extract_attachments(soup)
        
        return {
            'title': title,
            'content': content,
            'attachments': attachments,
            'url': url
        }
    
    def _extract_attachments(self, soup: BeautifulSoup) -> list:
        """첨부파일 정보 추출"""
        attachments = []
        
        # 그누보드 표준 첨부파일 섹션
        file_section = soup.find('section', id='bo_v_file')
        if not file_section:
            return attachments
        
        file_links = file_section.find_all('a', class_='view_file_download')
        
        for link in file_links:
            try:
                href = link.get('href', '')
                if not href:
                    continue
                
                # 파일명 추출 - strong 태그 안의 텍스트
                strong_elem = link.find('strong')
                if strong_elem:
                    filename = strong_elem.get_text(strip=True)
                else:
                    filename = link.get_text(strip=True)
                
                # 파일 크기 추출 (괄호 안의 숫자)
                file_size = ""
                link_text = link.get_text()
                size_match = re.search(r'\(([^)]+)\)', link_text)
                if size_match:
                    file_size = size_match.group(1)
                
                file_url = urljoin(self.base_url, href)
                
                attachments.append({
                    'name': filename,  # enhanced_base_scraper가 'name' 키를 사용
                    'filename': filename,
                    'url': file_url,
                    'size': file_size
                })
                
                logger.debug(f"첨부파일 발견: {filename} ({file_size})")
                
            except Exception as e:
                logger.error(f"첨부파일 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(attachments)}개 첨부파일 발견")
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment: dict = None) -> bool:
        """파일 다운로드 - 그누보드 특화"""
        try:
            # 그누보드 다운로드는 Referer 헤더가 중요할 수 있음
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
            
            # 스트리밍 다운로드
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(save_path)
            logger.info(f"다운로드 완료: {save_path} ({file_size:,} bytes)")
            
            # 잠시 대기 (서버 부하 방지)
            time.sleep(self.delay_between_requests)
            
            return True
            
        except Exception as e:
            logger.error(f"파일 다운로드 실패 {url}: {e}")
            return False

# 하위 호환성을 위한 별칭
CTIAScraper = EnhancedCTIAScraper