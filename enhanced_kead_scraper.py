# -*- coding: utf-8 -*-
"""
KEAD(한국농업기술진흥원) Enhanced 스크래퍼
"""

import requests
from bs4 import BeautifulSoup
import re
import logging
import os
from urllib.parse import urljoin, unquote
from enhanced_base_scraper import StandardTableScraper
import time
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class EnhancedKEADScraper(StandardTableScraper):
    """KEAD(한국농업기술진흥원) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://www.kead.or.kr"
        self.list_url = "https://www.kead.or.kr/bbs/deptgongji/bbsPage.do?menuId=MENU0895"
        
        # 사이트 특화 설정
        self.verify_ssl = True  # HTTPS 사이트
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 2
        
        # 향상된 헤더 설정
        self.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        })
        self.session.headers.update(self.headers)
        
        # KEAD 특화 설정
        self.post_data = {
            'bbsCode': 'deptgongji',
            'bbsNm': '부서 공지사항',
            'menuId': 'MENU0895'
        }
        
        # 상세 페이지 URL
        self.detail_url = "https://www.kead.or.kr/bbs/deptgongji/bbsView.do"
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - KEAD는 POST 기반이므로 동일 URL 반환"""
        return self.list_url
    
    def fetch_page_with_post(self, page_num: int) -> str:
        """POST 요청으로 페이지 가져오기"""
        try:
            # 첫 번째 페이지인 경우 GET 요청
            if page_num == 1:
                logger.debug(f"1페이지 GET 요청: {self.list_url}")
                response = self.session.get(self.list_url, verify=self.verify_ssl, timeout=self.timeout)
                response.raise_for_status()
                return response.text
            
            # 2페이지 이상은 POST 요청
            post_data = self.post_data.copy()
            post_data['pageIndex'] = str(page_num)
            
            logger.debug(f"{page_num}페이지 POST 요청: {self.list_url}")
            logger.debug(f"POST 데이터: {post_data}")
            
            response = self.session.post(
                self.list_url,
                data=post_data,
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.text
            
        except Exception as e:
            logger.error(f"페이지 {page_num} 요청 실패: {e}")
            raise
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - KEAD POST 기반 테이블 구조 특화"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # KEAD 사이트의 공지사항 테이블 찾기
        table = soup.find('table')
        if not table:
            logger.warning("공지사항 테이블을 찾을 수 없습니다")
            return announcements
        
        tbody = table.find('tbody')
        if not tbody:
            tbody = table
        
        rows = tbody.find_all('tr')
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for i, row in enumerate(rows):
            try:
                cells = row.find_all('td')
                if len(cells) < 6:  # 번호, 제목, 담당부서, 등록일, 첨부, 조회수
                    logger.debug(f"행 {i}: 셀 수가 부족 ({len(cells)}개)")
                    continue
                
                # 번호 셀 (첫 번째)
                number_cell = cells[0]
                number = number_cell.get_text(strip=True)
                
                # 빈 행이나 헤더 행 스킵
                if not number or number in ['번호', 'No'] or not number.isdigit():
                    logger.debug(f"행 {i}: 번호가 없거나 헤더행 ({number})")
                    continue
                
                # 제목 셀 (두 번째)
                title_cell = cells[1]
                
                # JavaScript 링크 찾기
                # fn_bbsView('206727') 패턴
                link_elem = title_cell.find('a')
                if not link_elem:
                    continue
                
                onclick = link_elem.get('onclick', '')
                title = link_elem.get_text(strip=True)
                
                if not title or not onclick:
                    continue
                
                # JavaScript 파라미터 파싱
                # fn_bbsView('206727')
                bbsview_match = re.search(r"fn_bbsView\s*\(\s*'([^']+)'\s*\)", onclick)
                
                if not bbsview_match:
                    logger.debug(f"fn_bbsView 패턴을 찾을 수 없음: {onclick}")
                    continue
                
                bbs_cn_id = bbsview_match.group(1)
                
                # 기본 공고 정보
                announcement = {
                    'title': title,
                    'url': self.detail_url,  # POST로 접근하므로 URL은 동일
                    'number': number,
                    'id': bbs_cn_id,
                    'post_data': {
                        'pageIndex': '1',  # 현재 페이지 번호
                        'bbsCode': 'deptgongji',
                        'bbsCnId': bbs_cn_id,
                        'bbsNm': '부서 공지사항',
                        'menuId': 'MENU0895'
                    }
                }
                
                # 담당부서 추출 (세 번째 셀)
                if len(cells) >= 3:
                    dept_cell = cells[2]
                    dept = dept_cell.get_text(strip=True)
                    announcement['department'] = dept
                
                # 등록일 추출 (네 번째 셀)
                if len(cells) >= 4:
                    date_cell = cells[3]
                    date = date_cell.get_text(strip=True)
                    announcement['date'] = date
                
                # 첨부파일 추출 (다섯 번째 셀)
                attachments = []
                if len(cells) >= 5:
                    attach_cell = cells[4]
                    
                    # 첨부파일 링크들 찾기
                    # /cmm/fms/downloadDirect.do?key=해시값 패턴
                    attach_links = attach_cell.find_all('a')
                    for link in attach_links:
                        href = link.get('href', '')
                        if 'downloadDirect.do' in href:
                            # 키 추출: key=ACEAFC4A89845E1A9C59
                            key_match = re.search(r'key=([A-F0-9]+)', href)
                            if key_match:
                                file_key = key_match.group(1)
                                file_url = urljoin(self.base_url, href)
                                filename = link.get_text(strip=True)
                                
                                attachment = {
                                    'filename': filename,
                                    'url': file_url,
                                    'key': file_key,
                                    'size': 0
                                }
                                attachments.append(attachment)
                                logger.debug(f"첨부파일 발견: {filename}")
                
                announcement['attachments'] = attachments
                
                # 조회수 추출 (여섯 번째 셀)
                if len(cells) >= 6:
                    views_cell = cells[5]
                    views = views_cell.get_text(strip=True)
                    announcement['views'] = views
                
                announcements.append(announcement)
                logger.debug(f"공고 추가: {title[:50]}...")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱 - KEAD 구조 특화"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        content_text = ""
        attachments = []
        
        # KEAD 상세 페이지 구조 파싱
        # 1. 메인 컨테이너 찾기
        board_view = soup.find('article', class_='board_view')
        if not board_view:
            board_view = soup.find('div', class_='board_view')
        
        if board_view:
            # 본문 내용 추출
            main_text = board_view.find('div', class_='main_text')
            if not main_text:
                main_text = board_view.find('div', class_='data_cnt_body')
            
            if main_text:
                # 불필요한 태그 제거
                for tag in main_text.find_all(['script', 'style', 'nav', 'header', 'footer']):
                    tag.decompose()
                
                # 이미지 URL을 절대 URL로 변환
                for img in main_text.find_all('img'):
                    src = img.get('src', '')
                    if src and not src.startswith('http'):
                        img['src'] = urljoin(self.base_url, src)
                
                # 링크 URL 변환
                for link in main_text.find_all('a'):
                    href = link.get('href', '')
                    if href and not href.startswith('http') and not href.startswith('javascript'):
                        link['href'] = urljoin(self.base_url, href)
                
                content_html = str(main_text)
                content_text = self.h.handle(content_html)
                content_text = re.sub(r'\n\s*\n\s*\n', '\n\n', content_text).strip()
                logger.debug(f"본문 추출 완료: {len(content_text)}자")
            
            # 첨부파일 추출
            file_list = board_view.find('ul', class_='file_list')
            if file_list:
                file_items = file_list.find_all('li')
                for item in file_items:
                    link = item.find('a')
                    if link and 'downloadDirect.do' in link.get('href', ''):
                        href = link.get('href', '')
                        filename = link.get_text(strip=True)
                        
                        # 키 추출
                        key_match = re.search(r'key=([A-F0-9]+)', href)
                        if key_match:
                            file_key = key_match.group(1)
                            file_url = urljoin(self.base_url, href)
                            
                            attachment = {
                                'filename': filename,
                                'url': file_url,
                                'key': file_key,
                                'size': 0
                            }
                            attachments.append(attachment)
                            logger.debug(f"상세 페이지 첨부파일: {filename}")
        
        # Fallback: 일반적인 선택자들 시도
        if not content_text or len(content_text) < 50:
            selectors = [
                '.board_view .main_text',
                '.data_cnt_body',
                '.board_content',
                '.view_content',
                '#content',
                '.content',
            ]
            
            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    content_area = max(elements, key=lambda x: len(x.get_text(strip=True)))
                    
                    # 불필요한 태그 제거
                    for tag in content_area.find_all(['script', 'style', 'nav', 'header', 'footer']):
                        tag.decompose()
                    
                    # 이미지 URL을 절대 URL로 변환
                    for img in content_area.find_all('img'):
                        src = img.get('src', '')
                        if src and not src.startswith('http'):
                            img['src'] = urljoin(self.base_url, src)
                    
                    content_html = str(content_area)
                    content_text = self.h.handle(content_html)
                    content_text = re.sub(r'\n\s*\n\s*\n', '\n\n', content_text).strip()
                    
                    if len(content_text) >= 50:
                        logger.debug(f"{selector}에서 본문 영역 발견 (길이: {len(content_text)}자)")
                        break
        
        # 첨부파일이 아직 없으면 다시 시도
        if not attachments:
            all_links = soup.find_all('a')
            for link in all_links:
                href = link.get('href', '')
                if 'downloadDirect.do' in href:
                    key_match = re.search(r'key=([A-F0-9]+)', href)
                    if key_match:
                        file_key = key_match.group(1)
                        file_url = urljoin(self.base_url, href)
                        filename = link.get_text(strip=True) or f"attachment_{file_key[:8]}.file"
                        
                        attachment = {
                            'filename': filename,
                            'url': file_url,
                            'key': file_key,
                            'size': 0
                        }
                        attachments.append(attachment)
                        logger.debug(f"Fallback 첨부파일: {filename}")
        
        # 최종적으로 내용이 없는 경우
        if not content_text:
            content_text = "내용을 추출할 수 없습니다."
            logger.warning("본문 내용을 찾을 수 없음")
        
        return {
            'content': content_text,
            'attachments': attachments
        }
    
    def get_detail_page(self, announcement: dict) -> str:
        """상세 페이지 HTML 가져오기 - POST 요청"""
        try:
            post_data = announcement.get('post_data', {})
            
            logger.debug(f"상세 페이지 POST 요청: {self.detail_url}")
            logger.debug(f"POST 데이터: {post_data}")
            
            response = self.session.post(
                self.detail_url,
                data=post_data,
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            return response.text
            
        except Exception as e:
            logger.error(f"상세 페이지 요청 실패: {e}")
            raise
    
    def scrape_pages(self, max_pages: int = 3, output_base: str = "output") -> dict:
        """페이지 스크래핑 - POST 요청 처리"""
        try:
            results = {
                'total_announcements': 0,
                'successful_items': 0,
                'pages_scraped': 0,
                'attachments_downloaded': 0,
                'errors': []
            }
            
            # 출력 디렉토리 생성
            os.makedirs(output_base, exist_ok=True)
            
            announcement_count = 0
            
            for page_num in range(1, max_pages + 1):
                try:
                    logger.info(f"=== {page_num}페이지 처리 시작 ===")
                    
                    # POST 요청으로 페이지 가져오기
                    html_content = self.fetch_page_with_post(page_num)
                    
                    # 공고 목록 파싱
                    announcements = self.parse_list_page(html_content)
                    
                    if not announcements:
                        logger.warning(f"{page_num}페이지에 공고가 없습니다")
                        break
                    
                    # 중복 제거
                    new_announcements, early_stop = self.filter_new_announcements(announcements)
                    
                    if early_stop:
                        logger.info(f"연속 {self.duplicate_threshold}개 중복 발견, 조기 종료")
                        break
                    
                    logger.info(f"{page_num}페이지: {len(new_announcements)}개 새 공고 발견")
                    
                    # 각 공고 처리
                    for announcement in new_announcements:
                        try:
                            announcement_count += 1
                            folder_name = f"{announcement_count:03d}_{self.sanitize_filename(announcement['title'][:50])}"
                            announcement_dir = os.path.join(output_base, folder_name)
                            os.makedirs(announcement_dir, exist_ok=True)
                            
                            logger.info(f"공고 {announcement_count}: {announcement['title']}")
                            
                            # 상세 페이지 가져오기 (POST 요청)
                            detail_html = self.get_detail_page(announcement)
                            detail_data = self.parse_detail_page(detail_html)
                            
                            # 제목 중복 방지를 위해 처리됨으로 표시
                            if hasattr(self, 'mark_title_as_processed'):
                                self.mark_title_as_processed(announcement['title'])
                            
                            # 마크다운 저장
                            content_file = os.path.join(announcement_dir, 'content.md')
                            with open(content_file, 'w', encoding='utf-8') as f:
                                f.write(f"# {announcement['title']}\n\n")
                                f.write(f"**번호**: {announcement.get('number', 'N/A')}\n")
                                f.write(f"**담당부서**: {announcement.get('department', 'N/A')}\n")
                                f.write(f"**등록일**: {announcement.get('date', 'N/A')}\n")
                                f.write(f"**조회수**: {announcement.get('views', 'N/A')}\n")
                                f.write(f"**원본 URL**: {announcement['url']}\n\n")
                                f.write("## 내용\n\n")
                                f.write(detail_data['content'])
                                
                                if detail_data['attachments']:
                                    f.write("\n\n## 첨부파일\n\n")
                                    for att in detail_data['attachments']:
                                        f.write(f"- [{att['filename']}]({att['url']})\n")
                            
                            # 첨부파일 다운로드
                            if detail_data['attachments']:
                                attachments_dir = os.path.join(announcement_dir, 'attachments')
                                os.makedirs(attachments_dir, exist_ok=True)
                                
                                for attachment in detail_data['attachments']:
                                    if self.download_file(attachment['url'], attachments_dir, attachment['filename']):
                                        results['attachments_downloaded'] += 1
                            
                            results['successful_items'] += 1
                            
                        except Exception as e:
                            error_msg = f"공고 {announcement_count} 처리 실패: {e}"
                            logger.error(error_msg)
                            results['errors'].append(error_msg)
                            continue
                    
                    results['total_announcements'] += len(new_announcements)
                    results['pages_scraped'] += 1
                    
                    # 페이지 간 대기
                    if page_num < max_pages:
                        time.sleep(self.delay_between_requests)
                
                except Exception as e:
                    error_msg = f"{page_num}페이지 처리 실패: {e}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
                    continue
            
            # 결과 요약
            logger.info("=== 스크래핑 완료 ===")
            logger.info(f"처리된 페이지: {results['pages_scraped']}")
            logger.info(f"총 공고 수: {results['total_announcements']}")
            logger.info(f"성공 처리: {results['successful_items']}")
            logger.info(f"첨부파일 다운로드: {results['attachments_downloaded']}개")
            if results['errors']:
                logger.warning(f"오류 {len(results['errors'])}개 발생")
            
            return results
            
        except Exception as e:
            logger.error(f"스크래핑 중 치명적 오류: {e}")
            raise

# 하위 호환성을 위한 별칭
KEADScraper = EnhancedKEADScraper