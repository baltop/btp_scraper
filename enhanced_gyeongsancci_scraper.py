#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GYEONGSANCCI (경산상공회의소) 전용 향상된 스크래퍼
JSP/Spring 기반 사이트, JavaScript 함수 기반 페이지네이션
"""

import os
import logging
import re
import asyncio
from typing import Dict, List, Any
from urllib.parse import urljoin, unquote
from bs4 import BeautifulSoup
import requests

from enhanced_base_scraper import StandardTableScraper

logger = logging.getLogger(__name__)

class EnhancedGYEONGSANCCIScraper(StandardTableScraper):
    """GYEONGSANCCI 전용 스크래퍼 - Playwright 기반"""
    
    def __init__(self):
        super().__init__()
        
        # GYEONGSANCCI 사이트 기본 정보
        self.base_url = "http://gyeongsancci.korcham.net"
        self.list_url = "http://gyeongsancci.korcham.net/front/board/boardContentsListPage.do?boardId=10334&menuId=1905"
        
        # GYEONGSANCCI 특화 설정
        self.verify_ssl = True  # HTTP 사이트이므로 SSL 검증 불필요하지만 기본값 유지
        self.default_encoding = 'utf-8'  # UTF-8 인코딩 사용
        self.timeout = 30
        self.delay_between_requests = 2
        
        # Playwright 관련 설정
        self.use_playwright = True
        self.browser = None
        self.page = None
        
        logger.info("GYEONGSANCCI 스크래퍼 초기화 완료")
    
    async def initialize_browser(self):
        """Playwright 브라우저 초기화"""
        try:
            from playwright.async_api import async_playwright
            
            if self.browser is None:
                self.playwright = await async_playwright().start()
                self.browser = await self.playwright.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )
                self.context = await self.browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                )
                self.page = await self.context.new_page()
                
                # 타임아웃 설정
                self.page.set_default_timeout(30000)
                
            logger.info("Playwright 브라우저 초기화 완료")
            return True
            
        except ImportError:
            logger.error("Playwright가 설치되지 않았습니다. 'pip install playwright'로 설치해주세요")
            return False
        except Exception as e:
            logger.error(f"브라우저 초기화 실패: {e}")
            return False
    
    async def cleanup_browser(self):
        """브라우저 정리"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
            
            self.page = None
            self.context = None
            self.browser = None
            
            logger.info("브라우저 정리 완료")
        except Exception as e:
            logger.error(f"브라우저 정리 중 오류: {e}")
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 목록 URL 생성 - JavaScript 함수 기반이므로 기본 URL 반환"""
        return self.list_url
    
    async def navigate_to_page(self, page_num: int) -> str:
        """Playwright로 특정 페이지로 이동"""
        try:
            if page_num == 1:
                # 첫 페이지는 기본 URL로 이동
                await self.page.goto(self.list_url, wait_until='networkidle')
                
                # AJAX 로딩 완료 대기 - .contents_detail 영역이 로드될 때까지
                await self.page.wait_for_selector('.contents_detail', timeout=10000)
                await asyncio.sleep(2)  # 추가 안정화 대기
            else:
                # JavaScript 함수로 페이지 이동
                await self.page.evaluate(f"go_Page({page_num})")
                
                # AJAX 완료 대기
                await asyncio.sleep(3)  # AJAX 로딩 대기
                
                # 새로운 콘텐츠 로딩 확인
                await self.page.wait_for_function(
                    "document.querySelector('.contents_detail') && document.querySelector('.contents_detail').innerHTML.length > 100",
                    timeout=10000
                )
            
            # 최종 안정화 대기
            await asyncio.sleep(1)
            
            # HTML 내용 반환
            html_content = await self.page.content()
            return html_content
            
        except Exception as e:
            logger.error(f"페이지 {page_num} 이동 실패: {e}")
            return ""
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - JSP/Spring 테이블 구조"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        try:
            # 게시판 테이블 찾기 - contents_detail 영역 내에서
            contents_detail = soup.find(class_='contents_detail')
            if not contents_detail:
                logger.warning("contents_detail 영역을 찾을 수 없습니다")
                return announcements
            
            # 테이블 찾기
            table = contents_detail.find('table', {'summary': '게시판 리스트 화면'})
            if not table:
                # 대체 테이블 찾기
                table = contents_detail.find('table')
                if not table:
                    logger.warning("게시판 테이블을 찾을 수 없습니다")
                    return announcements
            
            tbody = table.find('tbody')
            if not tbody:
                tbody = table
            
            rows = tbody.find_all('tr')
            logger.info(f"총 {len(rows)}개 행 발견")
            
            for row in rows:
                try:
                    cells = row.find_all('td')
                    if len(cells) < 3:  # 최소 3개 컬럼 필요 (번호, 제목, 작성일)
                        continue
                    
                    # 번호 또는 공지 확인
                    number_cell = cells[0]
                    number_text = number_cell.get_text(strip=True)
                    
                    # 공지사항 체크 (이미지나 텍스트로)
                    is_notice = bool(number_cell.find('img', {'alt': '공지'})) or '공지' in number_text
                    
                    # 제목 링크 찾기 (두 번째 컬럼)
                    title_cell = cells[1]
                    link_elem = title_cell.find('a')
                    
                    if not link_elem:
                        continue
                    
                    title = link_elem.get_text(strip=True)
                    if not title:
                        continue
                    
                    # JavaScript 함수에서 게시물 ID 추출 (href 속성에서)
                    href = link_elem.get('href', '')
                    content_id_match = re.search(r"contentsView\('(\d+)'\)", href)
                    
                    if not content_id_match:
                        # onclick 속성에서도 시도
                        onclick = link_elem.get('onclick', '')
                        content_id_match = re.search(r"contentsView\('(\d+)'\)", onclick)
                    
                    if not content_id_match:
                        logger.warning(f"게시물 ID를 찾을 수 없습니다. href: {href}, onclick: {onclick}")
                        continue
                    
                    content_id = content_id_match.group(1)
                    
                    # 상세 URL 구성 (실제로는 JavaScript로 이동하지만 추정)
                    detail_url = f"{self.base_url}/front/board/boardContentsView.do"
                    
                    # 기본 공고 정보
                    announcement = {
                        'title': title,
                        'url': detail_url,
                        'content_id': content_id,
                        'number': number_text,
                        'is_notice': is_notice
                    }
                    
                    # 작성일 (세 번째 컬럼)
                    if len(cells) > 2:
                        date_text = cells[2].get_text(strip=True)
                        if date_text:
                            announcement['date'] = date_text
                    
                    announcements.append(announcement)
                    logger.debug(f"공고 파싱 완료: {title}")
                    
                except Exception as e:
                    logger.error(f"행 파싱 중 오류: {e}")
                    continue
            
            logger.info(f"총 {len(announcements)}개 공고 파싱 완료")
            return announcements
            
        except Exception as e:
            logger.error(f"목록 페이지 파싱 실패: {e}")
            return announcements
    
    async def get_detail_page_content(self, content_id: str) -> str:
        """Playwright로 상세 페이지 내용 가져오기"""
        try:
            # JavaScript 함수로 상세 페이지 이동
            await self.page.evaluate(f"contentsView('{content_id}')")
            
            # 페이지 로딩 대기 - URL 변경이나 새 콘텐츠 로딩 확인
            try:
                # URL이 변경되거나 새 콘텐츠가 로드될 때까지 대기
                await self.page.wait_for_load_state('networkidle', timeout=10000)
            except:
                # 타임아웃 시에도 계속 진행
                pass
            
            # 페이지 로딩 후 잠시 대기
            await asyncio.sleep(2)
            
            # HTML 내용 반환
            html_content = await self.page.content()
            return html_content
            
        except Exception as e:
            logger.error(f"상세 페이지 {content_id} 가져오기 실패: {e}")
            return ""
    
    def parse_detail_page(self, html_content: str, detail_url: str = None) -> Dict[str, Any]:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 기본 결과 구조
        result = {
            'content': '',
            'attachments': []
        }
        
        try:
            # 본문 내용 추출
            content_selectors = [
                '.board_view .contents',  # 일반적인 게시판 내용
                '.contents',
                '.content',
                'div.view_content',
                'td.content',
                'div[class*="content"]',
                '.contents_detail .contents'  # 경산상공회의소 특화
            ]
            
            content_elem = None
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    logger.debug(f"본문을 찾았습니다: {selector}")
                    break
            
            # 본문을 찾지 못한 경우 가장 긴 텍스트가 있는 영역 찾기
            if not content_elem:
                # 테이블에서 내용이 긴 td 찾기
                all_tds = soup.find_all('td')
                if all_tds:
                    content_elem = max(all_tds, key=lambda td: len(td.get_text(strip=True)))
                    if content_elem and len(content_elem.get_text(strip=True)) > 50:
                        logger.debug("가장 긴 텍스트의 td를 본문으로 사용")
                    else:
                        content_elem = None
            
            if content_elem:
                # HTML을 마크다운으로 변환
                content_html = str(content_elem)
                result['content'] = self.h.handle(content_html).strip()
                logger.info(f"본문 추출 완료 (길이: {len(result['content'])})")
            else:
                logger.warning("본문을 찾을 수 없습니다")
                result['content'] = "본문을 추출할 수 없습니다."
            
            # 첨부파일 추출
            result['attachments'] = self._extract_attachments(soup)
            
            return result
            
        except Exception as e:
            logger.error(f"상세 페이지 파싱 실패: {e}")
            result['content'] = f"상세 페이지 파싱 중 오류가 발생했습니다: {str(e)}"
            return result
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """첨부파일 추출"""
        attachments = []
        
        try:
            # 첨부파일 섹션 찾기
            attachment_patterns = [
                ('th', '첨부파일'),  # 테이블 기반
                ('td', '첨부파일'),
                ('.attach', None),
                ('.file', None),
                ('.attachment', None)
            ]
            
            attachment_section = None
            for tag, text in attachment_patterns:
                if text:
                    elements = soup.find_all(tag, string=lambda s: s and text in s)
                    if elements:
                        # 해당 th/td의 다음 형제 또는 부모의 다음 형제에서 파일 링크 찾기
                        for elem in elements:
                            next_td = elem.find_next_sibling('td')
                            if next_td:
                                attachment_section = next_td
                                break
                            # 부모 tr의 다음 tr에서 찾기
                            parent_tr = elem.find_parent('tr')
                            if parent_tr:
                                next_tr = parent_tr.find_next_sibling('tr')
                                if next_tr:
                                    attachment_section = next_tr
                                    break
                else:
                    attachment_section = soup.select_one(tag)
                
                if attachment_section:
                    break
            
            if attachment_section:
                # 첨부파일 링크 찾기
                file_links = attachment_section.find_all('a', href=True)
                for link in file_links:
                    href = link.get('href', '')
                    if href and ('/file/' in href or href.endswith(('.hwp', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip'))):
                        file_url = urljoin(self.base_url, href)
                        filename = link.get_text(strip=True)
                        
                        if not filename:
                            # href에서 파일명 추출
                            filename = href.split('/')[-1]
                            try:
                                filename = unquote(filename)
                            except:
                                pass
                        
                        if filename:
                            attachment = {
                                'url': file_url,
                                'filename': filename
                            }
                            attachments.append(attachment)
                            logger.debug(f"첨부파일 발견: {filename}")
            
            # 전체 페이지에서 파일 링크 패턴 검색 (보완)
            file_link_patterns = [
                r'/file/dext5uploaddata/[^"\s]+',
                r'/upload/[^"\s]+\.(?:hwp|pdf|doc|docx|xls|xlsx|ppt|pptx|zip)'
            ]
            
            page_text = str(soup)
            for pattern in file_link_patterns:
                matches = re.findall(pattern, page_text)
                for match in matches:
                    file_url = urljoin(self.base_url, match)
                    filename = match.split('/')[-1]
                    try:
                        filename = unquote(filename)
                        # 경산상공회의소 특수 처리: __를 공백으로 치환
                        filename = filename.replace('__', ' ')
                    except:
                        pass
                    
                    # 중복 체크
                    if not any(att['url'] == file_url for att in attachments):
                        attachment = {
                            'url': file_url,
                            'filename': filename
                        }
                        attachments.append(attachment)
                        logger.debug(f"패턴으로 첨부파일 발견: {filename}")
            
            logger.info(f"총 {len(attachments)}개 첨부파일 발견")
            return attachments
            
        except Exception as e:
            logger.error(f"첨부파일 추출 중 오류: {e}")
            return attachments
    
    def sanitize_filename(self, filename: str) -> str:
        """파일명 정리 - 경산상공회의소 특화"""
        # 기본 정리 수행
        filename = super().sanitize_filename(filename)
        
        # 경산상공회의소 특수 처리: __를 공백으로 치환
        filename = filename.replace('__', ' ')
        
        # 연속된 공백 정리
        filename = re.sub(r'\s+', ' ', filename)
        
        return filename.strip()
    
    async def process_announcement_async(self, announcement: Dict[str, Any], index: int, output_base: str = 'output'):
        """개별 공고 처리 - 비동기 버전"""
        logger.info(f"공고 처리 중 {index}: {announcement['title']}")
        
        # 폴더 생성
        folder_title = self.sanitize_filename(announcement['title'])[:100]
        folder_name = f"{index:03d}_{folder_title}"
        
        if len(folder_name) > 200:
            folder_title = folder_title[:195]
            folder_name = f"{index:03d}_{folder_title}"
        
        folder_path = os.path.join(output_base, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        # 상세 페이지 내용 가져오기 (Playwright 사용)
        content_id = announcement.get('content_id', '')
        if not content_id:
            logger.error(f"게시물 ID가 없습니다: {announcement['title']}")
            return
        
        html_content = await self.get_detail_page_content(content_id)
        if not html_content:
            logger.error(f"상세 페이지 가져오기 실패: {announcement['title']}")
            return
        
        # 상세 내용 파싱
        try:
            detail = self.parse_detail_page(html_content, announcement['url'])
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
        
        # 첨부파일 다운로드 (requests 사용)
        self._download_attachments(detail['attachments'], folder_path)
        
        # 처리된 제목으로 추가
        self.add_processed_title(announcement['title'])
        
        # 요청 간 대기
        if self.delay_between_requests > 0:
            await asyncio.sleep(self.delay_between_requests)
    
    async def scrape_pages_async(self, max_pages: int = 3, output_base: str = 'output'):
        """비동기 스크래핑 메인 함수"""
        logger.info(f"GYEONGSANCCI 스크래핑 시작: 최대 {max_pages}페이지")
        
        # Playwright 초기화
        if not await self.initialize_browser():
            logger.error("브라우저 초기화 실패")
            return False
        
        try:
            # 처리된 제목 목록 로드
            self.load_processed_titles(output_base)
            
            announcement_count = 0
            processed_count = 0
            
            for page_num in range(1, max_pages + 1):
                logger.info(f"페이지 {page_num} 처리 중")
                
                try:
                    # 페이지 이동 및 HTML 가져오기
                    html_content = await self.navigate_to_page(page_num)
                    if not html_content:
                        logger.warning(f"페이지 {page_num} 내용을 가져올 수 없습니다")
                        break
                    
                    # 목록 파싱
                    announcements = self.parse_list_page(html_content)
                    
                    if not announcements:
                        logger.warning(f"페이지 {page_num}에 공고가 없습니다")
                        if page_num == 1:
                            logger.error("첫 페이지에 공고가 없습니다. 사이트 구조를 확인해주세요.")
                        break
                    
                    logger.info(f"페이지 {page_num}에서 {len(announcements)}개 공고 발견")
                    
                    # 새로운 공고만 필터링
                    new_announcements, should_stop = self.filter_new_announcements(announcements)
                    
                    if should_stop:
                        logger.info(f"중복 공고 {self.duplicate_threshold}개 연속 발견으로 조기 종료")
                        break
                    
                    if not new_announcements and page_num > 1:
                        logger.info("새로운 공고가 없어 스크래핑 조기 종료")
                        break
                    
                    # 각 공고 처리
                    for ann in new_announcements:
                        announcement_count += 1
                        processed_count += 1
                        await self.process_announcement_async(ann, announcement_count, output_base)
                    
                    # 페이지 간 대기
                    if page_num < max_pages and self.delay_between_pages > 0:
                        await asyncio.sleep(self.delay_between_pages)
                    
                except Exception as e:
                    logger.error(f"페이지 {page_num} 처리 중 오류: {e}")
                    break
            
            # 처리된 제목 목록 저장
            self.save_processed_titles()
            
            logger.info(f"스크래핑 완료: 총 {processed_count}개 새로운 공고 처리")
            return True
            
        finally:
            # 브라우저 정리
            await self.cleanup_browser()
    
    def scrape_pages(self, max_pages: int = 3, output_base: str = 'output'):
        """동기 래퍼 함수"""
        return asyncio.run(self.scrape_pages_async(max_pages, output_base))