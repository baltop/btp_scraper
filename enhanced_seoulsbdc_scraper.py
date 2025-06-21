#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEOULSBDC (서울시중소기업지원센터) 전용 스크래퍼 - 향상된 버전

Playwright 브라우저 자동화를 통한 WebSquare 프레임워크 기반 사이트 스크래핑
"""

import os
import re
import time
import json
import hashlib
import logging
from urllib.parse import urljoin
from typing import List, Dict, Any
from pathlib import Path
import requests
from playwright.sync_api import sync_playwright, Browser, Page

from enhanced_base_scraper import EnhancedBaseScraper

logger = logging.getLogger(__name__)


class EnhancedSEOULSBDCScraper(EnhancedBaseScraper):
    """SEOULSBDC 전용 스크래퍼 - Playwright 기반"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.seoulsbdc.or.kr"
        self.list_url = "https://www.seoulsbdc.or.kr/sb/main.do"
        
        # SEOULSBDC 특화 설정
        self.verify_ssl = False
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 2
        
        # Playwright 관련
        self.browser = None
        self.page = None
        self.playwright = None
        
        logger.info("SEOULSBDC 스크래퍼 초기화 완료")

    def _initialize_browser(self):
        """Playwright 브라우저 초기화"""
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-web-security']
            )
            self.page = self.browser.new_page()
            
            # 기본 설정
            self.page.set_default_timeout(30000)
            self.page.set_viewport_size({"width": 1920, "height": 1080})
            
            logger.info("Playwright 브라우저 초기화 완료")
            return True
            
        except Exception as e:
            logger.error(f"브라우저 초기화 실패: {e}")
            return False

    def _navigate_to_board(self):
        """공지사항 게시판으로 네비게이션"""
        try:
            # 1. 메인 페이지 접근
            logger.info("메인 페이지 접근 중...")
            self.page.goto(self.base_url)
            self.page.wait_for_load_state('networkidle')
            time.sleep(2)
            
            # 2. 팝업 제거 (JavaScript 사용)
            try:
                self.page.evaluate("""
                    // 모든 팝업, 모달 숨기기
                    document.querySelectorAll('.modal, .popup, .overlay').forEach(el => {
                        el.style.display = 'none';
                        el.remove();
                    });
                    // z-index가 높은 요소들 숨기기
                    document.querySelectorAll('*').forEach(el => {
                        const zIndex = window.getComputedStyle(el).zIndex;
                        if (zIndex && parseInt(zIndex) > 100) {
                            el.style.display = 'none';
                        }
                    });
                """)
                logger.info("팝업 제거 완료")
            except:
                pass
            
            # 3. 직접 공지사항 페이지로 이동
            logger.info("공지사항 페이지로 직접 이동 중...")
            self.page.evaluate("location.href='/sb/main.do'")
            self.page.wait_for_load_state('networkidle')
            time.sleep(2)
            
            # 테이블 확인
            tables = self.page.query_selector_all('table')
            if len(tables) > 0:
                logger.info(f"게시판 테이블 발견: {len(tables)}개")
                return True
            else:
                logger.error("게시판 테이블을 찾을 수 없습니다")
                return False
                
        except Exception as e:
            logger.error(f"게시판 네비게이션 실패: {e}")
            return False

    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 반환 (Playwright에서는 사용하지 않음)"""
        return self.list_url

    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 (Playwright에서는 직접 사용하지 않음)"""
        # 이 메서드는 추상 클래스 요구사항으로 구현하지만 실제로는 _parse_page_announcements 사용
        return []

    def _get_page_announcements(self, page_num: int) -> List[Dict[str, Any]]:
        """특정 페이지의 공고 목록 수집 (Playwright 사용)"""
        try:
            if not self.browser:
                if not self._initialize_browser():
                    return []
                if not self._navigate_to_board():
                    return []
            
            # 페이지 이동 (1페이지가 아닌 경우)
            if page_num > 1:
                self._navigate_to_page(page_num)
            
            # 페이지 로드 대기
            self.page.wait_for_load_state('networkidle')
            time.sleep(2)
            
            # 공고 목록 파싱
            announcements = self._parse_page_announcements()
            logger.info(f"{page_num}페이지에서 {len(announcements)}개 공고 수집")
            
            return announcements
            
        except Exception as e:
            logger.error(f"{page_num}페이지 공고 수집 실패: {e}")
            return []

    def _navigate_to_page(self, page_num: int):
        """특정 페이지로 이동"""
        try:
            # 페이지네이션 버튼 찾기
            page_button = self.page.query_selector(f'a[onclick*="fn_page({page_num})"]')
            if page_button:
                page_button.click()
                self.page.wait_for_load_state('networkidle')
                time.sleep(2)
                logger.info(f"{page_num}페이지로 이동 완료")
            else:
                logger.warning(f"{page_num}페이지 버튼을 찾을 수 없습니다")
                
        except Exception as e:
            logger.error(f"{page_num}페이지 이동 실패: {e}")

    def _parse_page_announcements(self) -> List[Dict[str, Any]]:
        """현재 페이지의 공고 목록 파싱"""
        announcements = []
        
        try:
            # 테이블 행 찾기
            rows = self.page.query_selector_all('tbody tr')
            
            for i, row in enumerate(rows):
                try:
                    cells = row.query_selector_all('td')
                    if len(cells) < 5:
                        continue
                    
                    # 번호
                    number_text = cells[0].inner_text().strip()
                    
                    # 제목 및 링크
                    title_cell = cells[1]
                    title_link = title_cell.query_selector('a')
                    if not title_link:
                        continue
                        
                    title = title_link.inner_text().strip()
                    onclick = title_link.get_attribute('onclick') or ""
                    
                    # 작성자
                    author = cells[2].inner_text().strip()
                    
                    # 작성일
                    date = cells[3].inner_text().strip()
                    
                    # 조회수
                    views = cells[4].inner_text().strip()
                    
                    # 첨부파일 여부
                    has_attachment = bool(cells[5].query_selector('img'))
                    
                    # onclick에서 파라미터 추출
                    seq_match = re.search(r"'([^']+)'", onclick)
                    if not seq_match:
                        continue
                        
                    seq = seq_match.group(1)
                    
                    announcement = {
                        'title': title,
                        'url': f"detail#{seq}",  # 상세 페이지 식별자
                        'author': author,
                        'date': date,
                        'views': views,
                        'has_attachment': has_attachment,
                        'seq': seq,
                        'number': number_text
                    }
                    
                    announcements.append(announcement)
                    
                except Exception as e:
                    logger.error(f"공고 파싱 실패 (행 {i}): {e}")
                    continue
            
        except Exception as e:
            logger.error(f"페이지 파싱 실패: {e}")
        
        return announcements

    def parse_detail_page(self, html_content: str, detail_url: str = None) -> dict:
        """상세 페이지 파싱 (모달 팝업 처리)"""
        try:
            if not detail_url or not detail_url.startswith('detail#'):
                logger.error("잘못된 상세 페이지 URL")
                return {}
            
            seq = detail_url.split('#')[1]
            
            # 상세 페이지 모달 열기
            logger.info(f"상세 페이지 모달 열기: {seq}")
            
            # JavaScript 함수 호출로 모달 열기
            self.page.evaluate(f"fn_detail('{seq}')")
            
            # 모달 로드 대기
            time.sleep(3)
            
            # 모달 내용 파싱
            detail_data = self._parse_modal_content()
            
            # 모달 닫기
            try:
                close_button = self.page.query_selector('.modal-close, .popup-close, button:has-text("닫기")')
                if close_button:
                    close_button.click()
                    time.sleep(1)
            except:
                pass
            
            return detail_data
            
        except Exception as e:
            logger.error(f"상세 페이지 파싱 실패: {e}")
            return {}

    def _parse_modal_content(self) -> dict:
        """모달 팝업 내용 파싱"""
        try:
            # 모달이 나타날 때까지 대기
            modal = self.page.wait_for_selector('.modal, .popup, .detail-popup', timeout=5000)
            if not modal:
                logger.error("모달을 찾을 수 없습니다")
                return {}
            
            # 제목
            title = ""
            title_elem = modal.query_selector('.title, .subject, h3, h4')
            if title_elem:
                title = title_elem.inner_text().strip()
            
            # 메타 정보 테이블에서 정보 추출
            meta_info = {}
            meta_rows = modal.query_selector_all('table tr, .info-table tr')
            for row in meta_rows:
                cells = row.query_selector_all('td, th')
                if len(cells) >= 2:
                    key = cells[0].inner_text().strip()
                    value = cells[1].inner_text().strip()
                    meta_info[key] = value
            
            # 본문 내용
            content = ""
            content_elem = modal.query_selector('.content, .detail-content, .view-content')
            if content_elem:
                content = content_elem.inner_text().strip()
            
            # 첨부파일 링크 추출
            attachments = self._extract_modal_attachments(modal)
            
            detail_data = {
                'title': title,
                'content': content,
                'meta_info': meta_info,
                'attachments': attachments
            }
            
            return detail_data
            
        except Exception as e:
            logger.error(f"모달 내용 파싱 실패: {e}")
            return {}

    def _extract_modal_attachments(self, modal) -> list:
        """모달에서 첨부파일 정보 추출"""
        attachments = []
        
        try:
            # 첨부파일 링크 찾기
            file_links = modal.query_selector_all('a[href*="downloadFile"], a[onclick*="download"]')
            
            for link in file_links:
                try:
                    href = link.get_attribute('href')
                    onclick = link.get_attribute('onclick')
                    text = link.inner_text().strip()
                    
                    file_url = ""
                    filename = text
                    
                    if href and 'downloadFile' in href:
                        file_url = href
                    elif onclick:
                        # onclick에서 파일 ID 추출
                        file_id_match = re.search(r"'([^']+)'", onclick)
                        if file_id_match:
                            file_id = file_id_match.group(1)
                            file_url = f"/cm/downloadFile/{file_id}.do"
                    
                    if file_url:
                        attachment = {
                            'filename': filename,
                            'url': urljoin(self.base_url, file_url),
                            'original_filename': filename
                        }
                        attachments.append(attachment)
                        
                except Exception as e:
                    logger.error(f"첨부파일 추출 실패: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"첨부파일 목록 추출 실패: {e}")
        
        return attachments

    def download_file(self, file_url: str, save_dir: str, original_filename: str = None) -> str:
        """파일 다운로드 (브라우저 세션 사용)"""
        try:
            # 파일명 정리
            if original_filename:
                filename = self.sanitize_filename(original_filename)
            else:
                filename = f"attachment_{int(time.time())}"
            
            file_path = os.path.join(save_dir, filename)
            
            # 브라우저 쿠키 추출
            cookies = self.page.context.cookies()
            cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
            
            # requests 세션으로 다운로드
            response = self.session.get(
                file_url,
                cookies=cookie_dict,
                verify=self.verify_ssl,
                stream=True,
                timeout=60
            )
            
            if response.status_code == 200:
                # 파일명 재추출 시도
                content_disposition = response.headers.get('Content-Disposition', '')
                if content_disposition:
                    extracted_filename = self._extract_filename_from_response(response, save_dir)
                    if extracted_filename and extracted_filename != file_path:
                        file_path = extracted_filename
                
                # 파일 저장
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                file_size = os.path.getsize(file_path)
                if file_size > 0:
                    logger.info(f"파일 다운로드 성공: {os.path.basename(file_path)} ({file_size:,} bytes)")
                    return file_path
                else:
                    os.remove(file_path)
                    logger.error("파일 크기가 0입니다")
                    return None
            else:
                logger.error(f"파일 다운로드 실패: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"파일 다운로드 중 오류: {e}")
            return None

    def cleanup_browser(self):
        """브라우저 리소스 정리"""
        try:
            if self.page:
                self.page.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            logger.info("브라우저 리소스 정리 완료")
        except Exception as e:
            logger.error(f"브라우저 정리 실패: {e}")

    def scrape_pages(self, max_pages: int = 3, output_base: str = 'output'):
        """페이지 스크래핑 실행"""
        try:
            return super().scrape_pages(max_pages, output_base)
        finally:
            # 항상 브라우저 정리
            self.cleanup_browser()


def main():
    """테스트 실행"""
    scraper = EnhancedSEOULSBDCScraper()
    output_dir = "output/seoulsbdc"
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        scraper.scrape_pages(max_pages=1, output_base=output_dir)
    except Exception as e:
        print(f"스크래핑 실패: {e}")
    finally:
        scraper.cleanup_browser()


if __name__ == "__main__":
    main()