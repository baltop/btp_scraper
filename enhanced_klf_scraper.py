# -*- coding: utf-8 -*-
"""
한국고용노동교육원(KLF) 전용 스크래퍼 - 향상된 버전
WordPress + WPDM 기반 사이트
"""

from enhanced_base_scraper import StandardTableScraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote, unquote
import re
import logging
import time
import requests

logger = logging.getLogger(__name__)

class EnhancedKlfScraper(StandardTableScraper):
    """한국고용노동교육원(KLF) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://klf.or.kr"
        self.list_url = "https://klf.or.kr/story/notice/business-announcement/"
        
        # 사이트 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        self.delay_between_pages = 2
        
        # WordPress 특화 헤더
        self.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - 설정 주입과 Fallback 패턴"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: WordPress 페이지네이션 방식
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}page/{page_num}/"
    
    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: 사이트 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> list:
        """KLF WordPress 사이트별 특화된 파싱 로직"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # KLF 특화: nectar-post-grid-item 찾기
        items = soup.find_all('div', class_='nectar-post-grid-item')
        
        if not items:
            logger.warning("nectar-post-grid-item을 찾을 수 없습니다")
            # 대체 방법: article 태그나 다른 구조 시도
            items = soup.find_all('article')
            if not items:
                logger.warning("기본 article 태그도 찾을 수 없습니다")
                return announcements
        
        logger.info(f"WordPress 그리드에서 {len(items)}개 공고 발견")
        
        for item in items:
            try:
                # 제목과 링크 찾기 - h3 > a 패턴
                title_elem = item.find('h3')
                if not title_elem:
                    # 대체 방법: a 태그 직접 찾기
                    title_elem = item.find('a')
                
                if not title_elem:
                    logger.debug("제목 요소를 찾을 수 없는 아이템 스킵")
                    continue
                
                # 링크 찾기
                if title_elem.name == 'a':
                    link_elem = title_elem
                else:
                    link_elem = title_elem.find('a')
                
                if not link_elem:
                    logger.debug("링크가 없는 아이템 스킵")
                    continue
                
                title = link_elem.get_text(strip=True)
                if not title:
                    logger.debug("제목이 비어있는 아이템 스킵")
                    continue
                
                # URL 구성
                href = link_elem.get('href', '')
                if not href:
                    logger.debug("href가 없는 링크 스킵")
                    continue
                
                # WordPress 특화: 절대 경로 처리
                detail_url = urljoin(self.base_url, href)
                
                announcement = {
                    'title': title,
                    'url': detail_url
                }
                
                # 날짜 정보 추출 시도
                try:
                    # 날짜 패턴 찾기 (YYYY-MM-DD 또는 YYYY.MM.DD)
                    date_patterns = [
                        r'\d{4}-\d{2}-\d{2}',
                        r'\d{4}\.\d{2}\.\d{2}',
                        r'\d{4}/\d{2}/\d{2}'
                    ]
                    
                    item_text = item.get_text()
                    for pattern in date_patterns:
                        date_match = re.search(pattern, item_text)
                        if date_match:
                            announcement['date'] = date_match.group()
                            break
                    
                    # WordPress 메타 정보에서 날짜 찾기
                    meta_elem = item.find(['time', 'span'], class_=re.compile(r'date|time'))
                    if meta_elem and not announcement.get('date'):
                        meta_text = meta_elem.get_text(strip=True)
                        for pattern in date_patterns:
                            if re.search(pattern, meta_text):
                                announcement['date'] = meta_text
                                break
                
                except Exception as e:
                    logger.debug(f"날짜 추출 실패: {e}")
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱 성공: {title[:50]}...")
                
            except Exception as e:
                logger.error(f"공고 아이템 파싱 중 오류: {e}")
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
        content_parts = []
        
        # WordPress 특화: 제목 추출
        title_elem = soup.find('h1')
        if not title_elem:
            title_elem = soup.find('h2')
        
        if title_elem:
            content_parts.append(f"# {title_elem.get_text(strip=True)}")
            content_parts.append("")
        
        # WordPress 메타 정보 추출
        # 날짜, 카테고리 등의 메타 정보
        meta_selectors = [
            '.post-meta',
            '.entry-meta', 
            '.meta-info',
            'time',
            '.breadcrumb'
        ]
        
        for selector in meta_selectors:
            meta_elems = soup.select(selector)
            for elem in meta_elems:
                meta_text = elem.get_text(strip=True)
                if meta_text and len(meta_text) < 200:  # 메타 정보는 보통 짧음
                    content_parts.append(f"**{meta_text}**")
        
        if content_parts and len(content_parts) > 1:
            content_parts.append("")
            content_parts.append("---")
            content_parts.append("")
        
        # WordPress 본문 내용 추출
        # 1. WordPress 표준 선택자들 시도
        content_selectors = [
            '.entry-content',
            '.post-content',
            '.content',
            '.wpb_text_column',
            '.vc_column-inner',
            'article .content',
            '.single-post-content'
        ]
        
        main_content_found = False
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                # HTML을 Markdown으로 변환
                content_html = str(content_elem)
                markdown_content = self.h.handle(content_html)
                if markdown_content.strip():
                    content_parts.append(markdown_content)
                    main_content_found = True
                    break
        
        # 2. 대체 방법: p 태그들로 본문 구성
        if not main_content_found:
            logger.warning("표준 본문 선택자로 내용을 찾지 못해 p 태그 검색")
            paragraphs = soup.find_all('p')
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 20:  # 의미있는 길이의 텍스트만
                    content_parts.append(text)
                    content_parts.append("")
        
        # 3. 최종 대체 방법: 긴 텍스트 영역 찾기
        if len(content_parts) <= 3:  # 제목과 메타 정보만 있는 경우
            logger.warning("표준 방법으로 본문을 찾지 못해 대체 방법 시도")
            all_elements = soup.find_all(['div', 'section', 'article'])
            for elem in all_elements:
                text = elem.get_text(strip=True)
                if len(text) > 200:  # 200자 이상인 경우 본문으로 간주
                    logger.debug(f"긴 텍스트 영역을 본문으로 사용: {len(text)}자")
                    content_parts.append(self.h.handle(str(elem)))
                    break
        
        if not content_parts:
            logger.warning("본문 내용을 찾을 수 없습니다")
            return "본문 내용을 추출할 수 없습니다."
        
        return "\n\n".join(content_parts)
    
    def _extract_attachments(self, soup: BeautifulSoup) -> list:
        """WPDM 첨부파일 추출"""
        attachments = []
        
        logger.debug("=== WPDM 첨부파일 추출 시작 ===")
        
        # WPDM (WordPress Download Manager) 패턴 찾기
        # 1. 표준 WPDM 구조
        wpdm_items = soup.find_all('div', class_='media')
        
        for item in wpdm_items:
            try:
                # 파일명 추출
                title_elem = item.find('h3', class_='package-title')
                if not title_elem:
                    title_elem = item.find(['h3', 'h4', 'h5'])
                
                if not title_elem:
                    logger.debug("WPDM 아이템에서 제목을 찾을 수 없음")
                    continue
                
                filename = title_elem.get_text(strip=True)
                if not filename:
                    logger.debug("파일명이 비어있음")
                    continue
                
                # 다운로드 링크 찾기
                download_link = item.find('a', class_='wpdm-download-link')
                if not download_link:
                    # 대체 방법: data-downloadurl이 있는 링크 찾기
                    download_link = item.find('a', attrs={'data-downloadurl': True})
                
                if not download_link:
                    # 더 넓은 범위에서 다운로드 링크 찾기
                    download_link = item.find('a', href=re.compile(r'/download/'))
                
                if not download_link:
                    logger.debug(f"다운로드 링크를 찾을 수 없음: {filename}")
                    continue
                
                # URL 추출
                download_url = download_link.get('data-downloadurl')
                if not download_url:
                    download_url = download_link.get('href')
                
                if not download_url:
                    logger.debug("다운로드 URL을 찾을 수 없음")
                    continue
                
                # 절대 URL로 변환
                file_url = urljoin(self.base_url, download_url)
                
                attachment = {
                    'filename': filename,
                    'url': file_url
                }
                
                # 파일 크기 정보 추출 시도
                try:
                    size_elem = item.find(class_=re.compile(r'size|file-size|text-muted'))
                    if size_elem:
                        size_text = size_elem.get_text(strip=True)
                        if re.search(r'\d+\s*(KB|MB|GB|bytes)', size_text, re.IGNORECASE):
                            attachment['size'] = size_text
                except Exception as e:
                    logger.debug(f"파일 크기 추출 실패: {e}")
                
                attachments.append(attachment)
                logger.debug(f"WPDM 첨부파일 발견: {filename}")
                
            except Exception as e:
                logger.error(f"WPDM 아이템 처리 중 오류: {e}")
                continue
        
        # 2. 대체 방법: 일반적인 다운로드 링크 찾기
        if not attachments:
            logger.debug("WPDM 방식으로 첨부파일을 찾지 못해 일반 링크 검색")
            
            # 다운로드 관련 링크 패턴
            download_patterns = [
                r'/download/',
                r'\.zip',
                r'\.pdf',
                r'\.hwp',
                r'\.doc',
                r'\.xlsx',
                r'wpdmdl='
            ]
            
            for pattern in download_patterns:
                links = soup.find_all('a', href=re.compile(pattern))
                for link in links:
                    href = link.get('href', '')
                    filename = link.get_text(strip=True)
                    
                    if filename and href:
                        file_url = urljoin(self.base_url, href)
                        attachment = {
                            'filename': filename,
                            'url': file_url
                        }
                        attachments.append(attachment)
                        logger.debug(f"일반 다운로드 링크 발견: {filename}")
        
        logger.debug("=== WPDM 첨부파일 추출 완료 ===")
        logger.info(f"{len(attachments)}개 첨부파일 발견")
        return attachments
    
    def download_file(self, url: str, save_path: str, save_dir: str = None) -> bool:
        """WordPress/WPDM 파일 다운로드 (세션 처리 강화)"""
        try:
            logger.debug(f"WPDM 파일 다운로드 시작: {url}")
            
            # WordPress/WPDM는 세션 기반 다운로드를 사용할 수 있음
            # 먼저 다운로드 페이지에 접근하여 세션 설정
            if 'wpdmdl=' in url:
                # WPDM 다운로드 링크의 경우 사전 접근
                response = self.session.get(url, verify=self.verify_ssl, allow_redirects=True)
                
                # 리디렉션된 경우 최종 URL 사용
                if response.history:
                    final_url = response.url
                    logger.debug(f"리디렉션 감지, 최종 URL: {final_url}")
                else:
                    final_url = url
            else:
                final_url = url
            
            # 실제 파일 다운로드
            response = self.session.get(final_url, stream=True, verify=self.verify_ssl, timeout=120)
            response.raise_for_status()
            
            # 파일 크기 확인
            total_size = int(response.headers.get('content-length', 0))
            
            with open(save_path, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # 대용량 파일의 경우 진행률 로깅
                        if total_size > 1024*1024 and downloaded % (1024*1024) < 8192:  # 1MB 단위
                            progress = (downloaded / total_size) * 100 if total_size > 0 else 0
                            logger.debug(f"다운로드 진행률: {progress:.1f}%")
            
            file_size = downloaded
            logger.info(f"다운로드 완료: {save_path} ({file_size:,} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"파일 다운로드 실패 {url}: {e}")
            return False

# 하위 호환성을 위한 별칭
KlfScraper = EnhancedKlfScraper