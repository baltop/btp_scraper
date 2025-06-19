#!/usr/bin/env python3
"""
KCA (한국방송통신전파진흥원) 스크래퍼 - 향상된 버전

사이트: https://pms.kca.kr:4433/board/boardList.do?sysType=KCA&bbsTc=BBS0001
특징: HTTPS 포트 4433, CSRF 토큰, POST 기반 상세 페이지, iframe 첨부파일
"""

import re
import os
import logging
from typing import List, Dict, Any
from urllib.parse import urljoin, parse_qs, urlparse
from bs4 import BeautifulSoup

from enhanced_base_scraper import StandardTableScraper

logger = logging.getLogger(__name__)

class EnhancedKCAScraper(StandardTableScraper):
    """KCA 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 기본 설정
        self.base_url = "https://pms.kca.kr:4433"
        self.list_url = "https://pms.kca.kr:4433/board/boardList.do?sysType=KCA&bbsTc=BBS0001"
        
        # 사이트별 특화 설정
        self.verify_ssl = False  # 특수 포트로 인한 SSL 검증 비활성화
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 2  # CSRF 토큰 처리를 위해 여유있게 설정
        
        # KCA 특화 설정
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        # CSRF 토큰 저장
        self.csrf_token = None
        
        logger.info("KCA 스크래퍼 초기화 완료")
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: KCA 특화 로직
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&pageNumber={page_num}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: KCA 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """KCA 공고 목록 파싱 (btnBoardView 링크 기반)"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        try:
            # CSRF 토큰 추출 및 저장
            csrf_input = soup.find('input', {'name': '_csrf'})
            if csrf_input:
                self.csrf_token = csrf_input.get('value')
                logger.debug(f"CSRF 토큰 추출: {self.csrf_token[:20]}...")
            
            # btnBoardView 링크들 찾기
            view_links = soup.find_all('a', id=re.compile(r'btnBoardView\d+'))
            logger.info(f"btnBoardView 링크 {len(view_links)}개 발견")
            
            for i, link in enumerate(view_links):
                try:
                    # 링크에서 데이터 속성 추출
                    sys_type = link.get('data-sys-type', 'KCA')
                    bbs_tc = link.get('data-bbs-tc', 'BBS0001')
                    bbs_id = link.get('data-bbs-id')
                    
                    if not bbs_id:
                        logger.debug(f"링크 {i+1}: bbs_id가 없음")
                        continue
                    
                    # 제목 추출 (링크 텍스트 또는 근처 텍스트)
                    title = link.get_text(strip=True)
                    
                    # 제목이 비어있으면 주변에서 찾기
                    if not title or title in ['상세보기', '보기', '클릭']:
                        # 같은 행(tr)에서 제목 찾기
                        parent_row = link.find_parent('tr')
                        if parent_row:
                            cells = parent_row.find_all('td')
                            for cell in cells:
                                cell_text = cell.get_text(strip=True)
                                if cell_text and len(cell_text) > 5 and cell_text not in ['상세보기', '보기']:
                                    title = cell_text
                                    break
                    
                    if not title:
                        logger.debug(f"링크 {i+1}: 제목을 찾을 수 없음")
                        continue
                    
                    # 작성일 추출 (같은 행에서)
                    date = ""
                    parent_row = link.find_parent('tr')
                    if parent_row:
                        cells = parent_row.find_all('td')
                        for cell in cells:
                            cell_text = cell.get_text(strip=True)
                            # 날짜 패턴 찾기 (YYYY-MM-DD 형식)
                            if re.match(r'\d{4}-\d{2}-\d{2}', cell_text):
                                date = cell_text
                                break
                    
                    announcement = {
                        'title': title,
                        'sys_type': sys_type,
                        'bbs_tc': bbs_tc,
                        'bbs_id': bbs_id,
                        'date': date,
                        'url': f"{self.base_url}/board/boardView.do"  # POST 요청용 URL
                    }
                    
                    announcements.append(announcement)
                    logger.debug(f"공고 파싱 완료: {title[:50]}...")
                    
                except Exception as e:
                    logger.warning(f"링크 {i+1} 파싱 중 오류: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"목록 페이지 파싱 중 오류: {e}")
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_detail_page(html_content)
        
        # Fallback: KCA 특화 로직
        return self._parse_detail_fallback(html_content)
    
    def fetch_detail_page(self, announcement: Dict[str, Any]) -> str:
        """KCA 상세 페이지 요청 (POST 방식)"""
        try:
            # POST 데이터 준비
            post_data = {
                'sysType': announcement.get('sys_type', 'KCA'),
                'bbsTc': announcement.get('bbs_tc', 'BBS0001'),
                'bbsId': announcement.get('bbs_id'),
                '_csrf': self.csrf_token or ''
            }
            
            logger.debug(f"POST 요청: {post_data}")
            
            response = self.session.post(
                announcement['url'],
                data=post_data,
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            return response.text
            
        except Exception as e:
            logger.error(f"상세 페이지 요청 실패: {e}")
            return ""
    
    def _parse_detail_fallback(self, html_content: str) -> Dict[str, Any]:
        """KCA 상세 페이지 특화 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 추출을 위한 다양한 선택자 시도
        content_selectors = [
            'h2',  # 제목
            '.board-content',
            '.content-area',
            '.view-content',
            'div[class*="content"]',
            'div[class*="view"]'
        ]
        
        content_parts = []
        
        # 제목 추출
        title_elem = soup.find('h2')
        if title_elem:
            content_parts.append(f"# {title_elem.get_text(strip=True)}")
        
        # 본문 내용 추출
        for selector in content_selectors[1:]:  # 제목 제외
            content_elem = soup.select_one(selector)
            if content_elem:
                text = content_elem.get_text(separator='\n', strip=True)
                if text and len(text) > 50:  # 충분한 내용이 있는 경우
                    content_parts.append(text)
                    logger.debug(f"본문을 {selector} 선택자로 찾음")
                    break
        
        # 본문을 찾지 못한 경우 전체 body에서 추출
        if len(content_parts) <= 1:  # 제목만 있는 경우
            body = soup.find('body')
            if body:
                # 스크립트, 스타일 태그 제거
                for script in body(["script", "style"]):
                    script.decompose()
                
                text = body.get_text(separator='\n', strip=True)
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                
                # 중복 제거 및 필터링
                filtered_lines = []
                for line in lines:
                    if len(line) > 10 and line not in filtered_lines[-5:]:  # 최근 5줄과 중복 체크
                        filtered_lines.append(line)
                
                content_parts.extend(filtered_lines[:50])  # 최대 50줄까지
                logger.warning("본문 영역을 찾지 못해 전체 페이지 텍스트 사용")
        
        content = '\n\n'.join(content_parts)
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup)
        
        return {
            'content': content,
            'attachments': attachments
        }
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """첨부파일 링크 추출 (iframe 기반 시스템 고려)"""
        attachments = []
        
        try:
            # 1. 일반적인 첨부파일 링크 패턴
            download_patterns = [
                'a[href*="download"]',
                'a[href*="file"]',
                'a[href*="attach"]',
                'button[onclick*="download"]',
                'button[onclick*="file"]'
            ]
            
            for pattern in download_patterns:
                links = soup.select(pattern)
                for link in links:
                    href = link.get('href') or link.get('onclick', '')
                    filename = link.get_text(strip=True)
                    
                    if href and filename and len(filename) > 3:
                        if href.startswith('/'):
                            file_url = urljoin(self.base_url, href)
                        else:
                            file_url = href
                        
                        attachments.append({
                            'name': filename,
                            'url': file_url
                        })
                        logger.debug(f"첨부파일 발견: {filename}")
            
            # 2. iframe 내 첨부파일 시스템 체크
            iframes = soup.find_all('iframe')
            for iframe in iframes:
                iframe_src = iframe.get('src')
                if iframe_src and ('file' in iframe_src.lower() or 'attach' in iframe_src.lower()):
                    # iframe 내용을 별도로 요청하여 분석
                    try:
                        if iframe_src.startswith('/'):
                            iframe_url = urljoin(self.base_url, iframe_src)
                        else:
                            iframe_url = iframe_src
                        
                        iframe_response = self.session.get(iframe_url, verify=self.verify_ssl)
                        iframe_soup = BeautifulSoup(iframe_response.text, 'html.parser')
                        
                        # iframe 내에서 다운로드 링크 찾기
                        iframe_links = iframe_soup.find_all('a', href=True)
                        for link in iframe_links:
                            href = link.get('href')
                            filename = link.get_text(strip=True)
                            
                            if filename and any(ext in filename.lower() for ext in ['.pdf', '.hwp', '.doc', '.xls', '.zip']):
                                if href.startswith('/'):
                                    file_url = urljoin(self.base_url, href)
                                else:
                                    file_url = href
                                
                                attachments.append({
                                    'name': filename,
                                    'url': file_url
                                })
                                logger.debug(f"iframe 첨부파일 발견: {filename}")
                        
                    except Exception as e:
                        logger.debug(f"iframe 처리 중 오류: {e}")
            
        except Exception as e:
            logger.error(f"첨부파일 추출 중 오류: {e}")
        
        # 중복 제거
        unique_attachments = []
        seen = set()
        for att in attachments:
            key = (att['name'], att['url'])
            if key not in seen:
                seen.add(key)
                unique_attachments.append(att)
        
        logger.info(f"{len(unique_attachments)}개 첨부파일 발견")
        return unique_attachments
    
    def scrape_announcement(self, announcement: Dict[str, Any], output_dir: str) -> bool:
        """개별 공고 스크래핑 (KCA 특화 버전)"""
        try:
            title = announcement.get('title', 'Unknown')
            logger.info(f"공고 처리 중: {title}")
            
            # KCA 전용 상세 페이지 요청
            html_content = self.fetch_detail_page(announcement)
            if not html_content:
                logger.error(f"상세 페이지 요청 실패: {title}")
                return False
            
            # 상세 페이지 파싱
            detail_data = self.parse_detail_page(html_content)
            
            if not detail_data:
                logger.error(f"상세 페이지 파싱 실패: {title}")
                return False
            
            content = detail_data.get('content', '')
            attachments = detail_data.get('attachments', [])
            
            logger.info(f"상세 페이지 파싱 완료 - 내용길이: {len(content)}, 첨부파일: {len(attachments)}")
            
            # 파일 저장
            safe_title = self.sanitize_filename(title)
            announcement_dir = os.path.join(output_dir, safe_title)
            os.makedirs(announcement_dir, exist_ok=True)
            
            # 내용 저장
            content_file = os.path.join(announcement_dir, 'content.md')
            
            # 메타데이터 추가
            full_content = f"# {title}\n\n"
            if announcement.get('date'):
                full_content += f"**작성일**: {announcement['date']}\n"
            full_content += f"**원본 URL**: {announcement['url']}\n"
            full_content += f"**게시글 ID**: {announcement.get('bbs_id', 'N/A')}\n\n"
            full_content += "---\n"
            full_content += content
            
            with open(content_file, 'w', encoding='utf-8') as f:
                f.write(full_content)
            
            logger.info(f"내용 저장 완료: {content_file}")
            
            # 첨부파일 다운로드
            if attachments:
                attachments_dir = os.path.join(announcement_dir, 'attachments')
                os.makedirs(attachments_dir, exist_ok=True)
                
                logger.info(f"{len(attachments)}개 첨부파일 다운로드 시작")
                
                for i, attachment in enumerate(attachments, 1):
                    try:
                        filename = attachment.get('name', f'attachment_{i}')
                        file_url = attachment['url']
                        
                        logger.info(f"  첨부파일 {i}: {filename}")
                        logger.info(f"파일 다운로드 시작: {file_url}")
                        
                        if self.download_file(file_url, attachments_dir, filename):
                            logger.info(f"다운로드 완료: {filename}")
                        else:
                            logger.warning(f"다운로드 실패: {filename}")
                            
                    except Exception as e:
                        logger.error(f"첨부파일 {i} 처리 중 오류: {e}")
            else:
                logger.info("첨부파일이 없습니다")
            
            return True
            
        except Exception as e:
            logger.error(f"공고 스크래핑 중 오류: {e}")
            return False

# 하위 호환성을 위한 별칭
KCAScraper = EnhancedKCAScraper

if __name__ == "__main__":
    # 간단한 테스트
    scraper = EnhancedKCAScraper()
    print(f"KCA 스크래퍼 초기화 완료")
    print(f"기본 URL: {scraper.list_url}")
    print(f"1페이지 URL: {scraper.get_list_url(1)}")
    print(f"2페이지 URL: {scraper.get_list_url(2)}")
    print(f"SSL 검증: {scraper.verify_ssl}")  # False여야 함