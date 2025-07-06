#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import time
from urllib.parse import urljoin, unquote
from enhanced_base_scraper import StandardTableScraper
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import logging
import requests

logger = logging.getLogger(__name__)

class EnhancedWinScraperPlaywright(StandardTableScraper):
    """윈윈사회적경제지원센터 전용 스크래퍼 - Playwright 버전"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.win-win.or.kr"
        self.list_url = "https://www.win-win.or.kr/kr/board/notice/boardList.do"
        
        # WIN 사이트별 특화 설정
        self.verify_ssl = False
        self.default_encoding = 'utf-8'
        self.timeout = 60
        self.delay_between_requests = 2
        
        # Playwright 설정
        self.playwright = None
        self.browser = None
        self.page = None
        
        # 세션 설정 (파일 다운로드용)
        self.session.verify = self.verify_ssl
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        })
        
        logger.info("Enhanced WIN 스크래퍼 (Playwright) 초기화 완료")

    def _init_playwright(self):
        """Playwright 초기화"""
        if not self.playwright:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=True)
            self.page = self.browser.new_page()
            
            # SSL 에러 무시
            self.page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })

    def _close_playwright(self):
        """Playwright 정리"""
        if self.page:
            self.page.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def get_list_url(self, page_num: int) -> str:
        """페이지네이션 URL 생성"""
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}?pageIndex={page_num}"

    def _navigate_to_page(self, page_num: int) -> bool:
        """특정 페이지로 이동"""
        try:
            if page_num == 1:
                self.page.goto(self.list_url, timeout=30000)
            else:
                # JavaScript로 페이지네이션 클릭
                pagination_script = f"fnLinkPage({page_num})"
                self.page.evaluate(pagination_script)
                time.sleep(2)  # 페이지 로드 대기
            
            return True
        except Exception as e:
            logger.error(f"페이지 {page_num} 이동 실패: {e}")
            return False

    def parse_list_page_playwright(self) -> list:
        """Playwright로 목록 페이지 파싱"""
        announcements = []
        
        try:
            # ul.bbs_table.notice 구조 찾기
            notice_list = self.page.locator('ul.bbs_table.notice')
            if not notice_list.count():
                logger.warning("공지사항 목록을 찾을 수 없습니다")
                return announcements
            
            items = notice_list.locator('li')
            item_count = items.count()
            logger.info(f"총 {item_count}개 항목 발견")
            
            for i in range(item_count):
                try:
                    # 헤더 행 제외
                    if i == 0:
                        continue
                    
                    item = items.nth(i)
                    
                    # 링크 찾기
                    link = item.locator('a')
                    if not link.count():
                        continue
                    
                    title = link.inner_text().strip()
                    
                    # 링크 클릭해서 상세 페이지 URL 얻기
                    # href가 #none이므로 onclick 이벤트로 처리
                    try:
                        # 새 탭에서 열기
                        with self.page.expect_popup() as popup_info:
                            link.click()
                        popup = popup_info.value
                        detail_url = popup.url
                        popup.close()
                    except:
                        # 직접 클릭이 안되면 JavaScript 실행
                        onclick = link.get_attribute('onclick')
                        if onclick and 'javascript:' in onclick:
                            # onclick에서 실제 링크 추출 시도
                            detail_url = self.list_url  # 기본값
                        else:
                            continue
                    
                    # 현재 페이지 URL 기반으로 상세 URL 구성
                    current_url = self.page.url
                    if 'pageIndex=' in current_url:
                        page_index = re.search(r'pageIndex=(\d+)', current_url)
                        page_index = page_index.group(1) if page_index else "1"
                    else:
                        page_index = "1"
                    
                    # bbsIdx 추출을 위해 임시로 상세 페이지 이동
                    try:
                        link.click()
                        time.sleep(1)
                        detail_url = self.page.url
                        self.page.go_back()
                        time.sleep(1)
                    except:
                        detail_url = f"{self.base_url}/kr/board/notice/boardView.do?pageIndex={page_index}"
                    
                    # 공고 정보 파싱
                    item_text = item.inner_text()
                    text_parts = [part.strip() for part in item_text.split('\n') if part.strip()]
                    
                    category = ""
                    date = ""
                    views = ""
                    
                    # 패턴 매칭으로 정보 추출
                    for part in text_parts:
                        if re.match(r'\d{2}\.\d{2}\.\d{2}', part):  # 날짜 패턴
                            date = part
                        elif part.isdigit() and len(part) <= 5:  # 조회수 패턴
                            views = part
                        elif part in ['행사안내', '기타', '채용', '사업공고']:
                            category = part
                    
                    announcement = {
                        'number': str(len(announcements) + 1),
                        'title': title,
                        'url': detail_url,
                        'date': date,
                        'views': views,
                        'category': category,
                        'has_attachment': False
                    }
                    
                    announcements.append(announcement)
                    logger.info(f"공고 추가: [{announcement['number']}] {title}")
                    
                except Exception as e:
                    logger.error(f"공고 파싱 중 오류 발생 (항목 {i}): {e}")
                    continue
            
        except Exception as e:
            logger.error(f"목록 페이지 파싱 중 오류: {e}")
        
        logger.info(f"총 {len(announcements)}개 공고 파싱 완료")
        return announcements

    def parse_detail_page(self, html_content: str) -> dict:
        """상세 페이지 파싱 - Playwright 직접 사용"""
        try:
            # 제목 추출
            title_selectors = [
                '.view_title',
                '.title',
                'h1',
                'h2',
                'h3'
            ]
            
            title = ""
            for selector in title_selectors:
                title_elem = self.page.locator(selector)
                if title_elem.count():
                    title = title_elem.inner_text().strip()
                    if title and len(title) > 5:
                        break
            
            # 본문 추출
            content_selectors = [
                '.view_content',
                '.content',
                '.detail_content',
                '.board_content',
                '#content'
            ]
            
            content = ""
            for selector in content_selectors:
                content_elem = self.page.locator(selector)
                if content_elem.count():
                    content = content_elem.inner_text().strip()
                    if content and len(content) > 10:
                        break
            
            # 테이블에서 내용 추출 시도
            if not content:
                tables = self.page.locator('table')
                for i in range(tables.count()):
                    table = tables.nth(i)
                    table_text = table.inner_text().strip()
                    if len(table_text) > 50:
                        content = table_text
                        break
            
            # 첨부파일 추출
            attachments = self._extract_attachments_playwright()
            
            return {
                'title': title,
                'content': content,
                'attachments': attachments
            }
            
        except Exception as e:
            logger.error(f"상세 페이지 파싱 중 오류: {e}")
            return {
                'title': "제목 없음",
                'content': "내용 없음",
                'attachments': []
            }

    def _extract_attachments_playwright(self) -> list:
        """Playwright로 첨부파일 추출"""
        attachments = []
        
        try:
            # fileDownload.do 링크 찾기
            download_links = self.page.locator('a[href*="fileDownload.do"]')
            
            for i in range(download_links.count()):
                link = download_links.nth(i)
                href = link.get_attribute('href')
                filename = link.inner_text().strip()
                
                # 파일명이 없는 경우 href에서 추출
                if not filename or filename == href:
                    try:
                        if 'usrFile=' in href:
                            usr_file_part = href.split('usrFile=')[1]
                            if '&' in usr_file_part:
                                usr_file_part = usr_file_part.split('&')[0]
                            filename = unquote(usr_file_part, encoding='utf-8')
                    except:
                        filename = f"첨부파일_{len(attachments)+1}"
                
                # 상대 URL을 절대 URL로 변환
                if href.startswith('/'):
                    download_url = urljoin(self.base_url, href)
                elif href.startswith('http'):
                    download_url = href
                else:
                    download_url = urljoin(self.base_url, href)
                
                attachments.append({
                    'filename': filename,
                    'url': download_url
                })
                
                logger.info(f"첨부파일 발견: {filename}")
        
        except Exception as e:
            logger.error(f"첨부파일 추출 중 오류: {e}")
        
        return attachments

    def download_file(self, file_url: str, save_path: str) -> bool:
        """파일 다운로드 - requests 사용 (SSL 검증 비활성화)"""
        try:
            response = self.session.get(file_url, stream=True, timeout=self.timeout, verify=False)
            response.raise_for_status()
            
            # 파일명 추출 및 인코딩 처리
            save_dir = os.path.dirname(save_path)
            filename = os.path.basename(save_path)
            
            # Content-Disposition에서 파일명 추출 시도
            content_disposition = response.headers.get('Content-Disposition', '')
            if content_disposition:
                # RFC 5987 형식 처리
                rfc5987_match = re.search(r"filename\*=([^']*)'([^']*)'(.+)", content_disposition)
                if rfc5987_match:
                    encoding, lang, encoded_filename = rfc5987_match.groups()
                    try:
                        filename = unquote(encoded_filename, encoding=encoding or 'utf-8')
                        save_path = os.path.join(save_dir, self.sanitize_filename(filename))
                    except:
                        pass
                else:
                    # 일반 filename 파라미터 처리
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
                                    save_path = os.path.join(save_dir, clean_filename)
                                    break
                            except:
                                continue
            
            # 파일 저장
            os.makedirs(save_dir, exist_ok=True)
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(save_path)
            logger.info(f"파일 다운로드 완료: {os.path.basename(save_path)} ({file_size} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"파일 다운로드 실패: {file_url} - {e}")
            return False

    def _get_page_announcements(self, page_num: int) -> list:
        """페이지별 공고 목록 가져오기 - Playwright 사용"""
        try:
            self._init_playwright()
            
            # 페이지 이동
            if not self._navigate_to_page(page_num):
                return []
            
            # 페이지 로드 대기
            time.sleep(3)
            
            # 공고 목록 파싱
            announcements = self.parse_list_page_playwright()
            logger.info(f"페이지 {page_num}에서 {len(announcements)}개 공고 발견")
            
            return announcements
            
        except Exception as e:
            logger.error(f"페이지 {page_num} 처리 중 오류: {e}")
            return []

    def _process_announcement_detail(self, announcement: dict, output_dir: str) -> bool:
        """공고 상세 정보 처리 - Playwright 사용"""
        try:
            logger.info(f"공고 상세 처리: {announcement['title']}")
            
            # 상세 페이지로 이동
            self.page.goto(announcement['url'], timeout=30000)
            time.sleep(2)
            
            # 상세 정보 파싱
            detail_info = self.parse_detail_page("")
            
            # 공고 폴더 생성
            safe_title = self.sanitize_filename(announcement['title'])
            announcement_dir = os.path.join(output_dir, f"{announcement['number']:03d}_{safe_title}")
            os.makedirs(announcement_dir, exist_ok=True)
            
            # 본문 저장
            content_file = os.path.join(announcement_dir, f"{safe_title}.md")
            with open(content_file, 'w', encoding='utf-8') as f:
                f.write(f"# {detail_info['title']}\n\n")
                f.write(f"**등록일**: {announcement.get('date', 'N/A')}\n")
                f.write(f"**조회수**: {announcement.get('views', 'N/A')}\n")
                f.write(f"**구분**: {announcement.get('category', 'N/A')}\n")
                f.write(f"**원본 URL**: {announcement['url']}\n\n")
                f.write("## 내용\n\n")
                f.write(detail_info['content'])
            
            # 첨부파일 다운로드
            if detail_info['attachments']:
                attachments_dir = os.path.join(announcement_dir, "attachments")
                os.makedirs(attachments_dir, exist_ok=True)
                
                for attachment in detail_info['attachments']:
                    filename = self.sanitize_filename(attachment['filename'])
                    file_path = os.path.join(attachments_dir, filename)
                    
                    if self.download_file(attachment['url'], file_path):
                        logger.info(f"첨부파일 다운로드 완료: {filename}")
                    else:
                        logger.error(f"첨부파일 다운로드 실패: {filename}")
            
            return True
            
        except Exception as e:
            logger.error(f"공고 상세 처리 중 오류: {e}")
            return False

    def scrape_pages(self, max_pages: int = 3, output_base: str = "output") -> None:
        """메인 스크래핑 함수 - Playwright 버전"""
        try:
            self._init_playwright()
            logger.info(f"스크래핑 시작: 최대 {max_pages}페이지")
            
            # 출력 디렉토리 생성
            os.makedirs(output_base, exist_ok=True)
            
            total_announcements = 0
            
            for page_num in range(1, max_pages + 1):
                logger.info(f"페이지 {page_num} 처리 중")
                
                # 공고 목록 가져오기
                announcements = self._get_page_announcements(page_num)
                
                if not announcements:
                    logger.warning(f"페이지 {page_num}에 공고가 없습니다")
                    continue
                
                # 각 공고 상세 처리
                for announcement in announcements:
                    if self._process_announcement_detail(announcement, output_base):
                        total_announcements += 1
                    
                    # 요청 간격 조절
                    time.sleep(self.delay_between_requests)
                
                logger.info(f"페이지 {page_num} 완료")
            
            logger.info(f"스크래핑 완료: 총 {total_announcements}개 공고 처리")
            
        except Exception as e:
            logger.error(f"스크래핑 중 오류: {e}")
        finally:
            self._close_playwright()

def main():
    """테스트 실행"""
    scraper = EnhancedWinScraperPlaywright()
    output_dir = "output/win"
    os.makedirs(output_dir, exist_ok=True)
    
    # 3페이지까지 스크래핑
    scraper.scrape_pages(max_pages=3, output_base=output_dir)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    main()