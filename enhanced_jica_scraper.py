# -*- coding: utf-8 -*-
"""
JICA (전주정보문화산업진흥원) 전용 스크래퍼 - 향상된 버전
"""

from enhanced_base_scraper import StandardTableScraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote
import re
import logging
import os

logger = logging.getLogger(__name__)

class EnhancedJicaScraper(StandardTableScraper):
    """JICA 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        
        # 하드코딩된 설정들
        self.base_url = "https://www.jica.or.kr"
        self.list_url = "https://www.jica.or.kr/2025/inner.php?sMenu=A1000"
        
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
        
        # Fallback: JICA 특화 로직 - pno 파라미터 사용
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&pno={page_num}"
    
    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: JICA 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> list:
        """JICA 특화된 목록 파싱 로직"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 테이블 찾기 - JICA는 .ta_bo 클래스 사용
        table = soup.find('table', class_='ta_bo')
        if not table:
            logger.warning("ta_bo 클래스를 가진 테이블을 찾을 수 없습니다")
            return announcements
        
        # tbody 찾기
        tbody = table.find('tbody')
        if not tbody:
            logger.warning("tbody를 찾을 수 없습니다")
            return announcements
        
        logger.info(f"테이블에서 {len(tbody.find_all('tr'))}개 행 발견")
        
        # 각 행 처리
        for row in tbody.find_all('tr'):
            try:
                cells = row.find_all(['td', 'th'])
                if len(cells) < 3:  # 최소 3개 셀 (번호, 상태, 제목)
                    continue
                
                # 제목 셀 (3번째 셀, 인덱스 2)
                title_cell = cells[2]
                
                # 제목 링크 찾기
                link_elem = title_cell.find('a')
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                if not title:
                    continue
                
                # 공지글 이미지 제거
                if 'important.gif' in str(title_cell):
                    # 공지글 이미지가 있는 경우 텍스트만 추출
                    for img in title_cell.find_all('img'):
                        img.decompose()
                    title = link_elem.get_text(strip=True)
                
                # URL 구성
                href = link_elem.get('href', '')
                detail_url = urljoin(self.base_url + "/2025/", href)
                
                announcement = {
                    'title': title,
                    'url': detail_url
                }
                
                # 추가 정보 추출
                try:
                    # 상태 (2번째 셀, 인덱스 1)
                    if len(cells) > 1:
                        status_cell = cells[1]
                        status_span = status_cell.find('span')
                        if status_span:
                            announcement['status'] = status_span.get_text(strip=True)
                    
                    # 접수일 (4번째 셀, 인덱스 3)
                    if len(cells) > 3:
                        date_cell = cells[3]
                        announcement['start_date'] = date_cell.get_text(strip=True)
                    
                    # 마감일 (5번째 셀, 인덱스 4)
                    if len(cells) > 4:
                        end_date_cell = cells[4]
                        announcement['end_date'] = end_date_cell.get_text(strip=True)
                    
                    # D-Day (6번째 셀, 인덱스 5)
                    if len(cells) > 5:
                        dday_cell = cells[5]
                        dday_text = dday_cell.get_text(strip=True)
                        if dday_text != '-':
                            announcement['dday'] = dday_text
                    
                    # 조회수 (7번째 셀, 인덱스 6)
                    if len(cells) > 6:
                        views_cell = cells[6]
                        announcement['views'] = views_cell.get_text(strip=True)
                        
                except Exception as e:
                    logger.debug(f"추가 정보 추출 중 오류 (무시): {e}")
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱: {title}")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> dict:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 내용 추출
        content = self._extract_content(soup)
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup)
        
        return {
            'content': content,
            'attachments': attachments
        }
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """본문 내용 추출"""
        # JICA 사이트의 본문은 특정 영역에 있음
        content_selectors = [
            '.view_con',  # 주요 본문 영역
            '.content',
            '.board_view',
            '#contents'
        ]
        
        content_area = None
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
        if not content_area:
            # 대안: 첨부파일 영역 이전의 div들을 찾아서 본문으로 판단
            file_div = soup.find('div', id='file')
            if file_div:
                # 파일 div 이전의 내용들을 수집
                content_parts = []
                for elem in file_div.find_all_previous():
                    if elem.name in ['div', 'p'] and elem.get_text(strip=True):
                        content_parts.append(elem.get_text(strip=True))
                        if len(content_parts) > 10:  # 너무 많이 수집하지 않도록 제한
                            break
                content_parts.reverse()
                content_text = '\n\n'.join(content_parts[-5:])  # 마지막 5개만
            else:
                # 최종 대안: 모든 텍스트 수집
                all_text = soup.get_text()
                # 불필요한 부분 제거
                lines = [line.strip() for line in all_text.split('\n') if line.strip()]
                # 첫 100라인 정도만 사용
                content_text = '\n'.join(lines[:100])
        else:
            # HTML을 마크다운으로 변환
            content_text = self.h.handle(str(content_area))
            # 과도한 줄바꿈 정리
            content_text = re.sub(r'\n{3,}', '\n\n', content_text)
        
        if not content_text or len(content_text.strip()) < 50:
            content_text = "본문 내용을 추출할 수 없습니다."
            logger.warning("본문 내용 추출 실패")
        
        return content_text.strip()
    
    def _extract_attachments(self, soup: BeautifulSoup) -> list:
        """첨부파일 추출"""
        attachments = []
        
        # JICA 사이트의 첨부파일은 #file div 안에 있음
        file_section = soup.find('div', id='file')
        if not file_section:
            logger.info("첨부파일 섹션을 찾을 수 없습니다")
            return attachments
        
        # 첨부파일 링크들 찾기
        file_links = file_section.find_all('a', href=True)
        
        for link in file_links:
            href = link.get('href', '')
            
            # filedown2.php 형태의 다운로드 링크만 처리
            if 'filedown' in href:
                file_name = link.get_text(strip=True)
                
                # 파일명이 없으면 title 속성에서 추출
                if not file_name:
                    file_name = link.get('title', '')
                
                if file_name:
                    # 완전한 다운로드 URL 구성
                    file_url = urljoin(self.base_url + "/2025/", href)
                    
                    attachments.append({
                        'name': file_name,
                        'url': file_url
                    })
                    
                    logger.info(f"첨부파일 발견: {file_name}")
        
        logger.info(f"총 {len(attachments)}개 첨부파일 발견")
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment_info: dict = None) -> bool:
        """JICA 파일 다운로드 - 특화된 처리"""
        try:
            logger.info(f"파일 다운로드 시작: {url}")
            
            # JICA 사이트 전용 헤더 설정
            download_headers = self.headers.copy()
            download_headers['Referer'] = self.base_url + "/2025/"
            
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
        """JICA 응답에서 파일명 추출"""
        content_disposition = response.headers.get('Content-Disposition', '')
        
        if content_disposition:
            logger.debug(f"Content-Disposition: {content_disposition}")
            
            # RFC 5987 형식 처리 (filename*=UTF-8''filename.ext)
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
            from urllib.parse import urlparse, parse_qs
            parsed_url = urlparse(response.url)
            query_params = parse_qs(parsed_url.query)
            
            # fn2 파라미터에서 파일명 추출
            if 'fn2' in query_params:
                filename = query_params['fn2'][0]
                filename = unquote(filename)
                clean_filename = self.sanitize_filename(filename)
                return os.path.join(save_dir, clean_filename)
            
            # fn1 파라미터에서 파일명 추출
            if 'fn1' in query_params:
                filename = query_params['fn1'][0]
                clean_filename = self.sanitize_filename(filename)
                return os.path.join(save_dir, clean_filename)
                
        except Exception as e:
            logger.debug(f"URL에서 파일명 추출 실패: {e}")
        
        # 기본 파일명 반환
        return os.path.join(save_dir, "attachment.file")

# 하위 호환성을 위한 별칭
JicaScraper = EnhancedJicaScraper