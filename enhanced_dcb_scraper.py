# -*- coding: utf-8 -*-
"""
대구경북디자인센터(DCB) 스크래퍼 - Enhanced 버전
향상된 아키텍처와 중복 체크, 로깅 지원
"""

from enhanced_base_scraper import StandardTableScraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
import re
import time
import logging
import os
from typing import Dict, List, Any, Optional
import requests

logger = logging.getLogger(__name__)

class EnhancedDCBScraper(StandardTableScraper):
    """대구경북디자인센터(DCB) 스크래퍼 - Enhanced 버전"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.dcb.or.kr"
        self.list_url = "https://www.dcb.or.kr/01_news/?mcode=0401010000"
        
        # DCB 사이트 특성상 추가 헤더 설정
        self.dcb_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # 세션 헤더 업데이트
        self.session.headers.update(self.dcb_headers)
    
    def get_list_url(self, page_num: int) -> str:
        """페이지 번호에 따른 목록 URL 반환"""
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&page={page_num}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - Enhanced 버전"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 테이블에서 공고 목록 찾기 (board-text 영역 안의 table)
        board_text = soup.find('div', class_='board-text')
        if not board_text:
            logger.warning("Board text div를 찾을 수 없습니다")
            return announcements
        
        table = board_text.find('table')
        if not table:
            logger.warning("테이블을 찾을 수 없습니다")
            return announcements
        
        tbody = table.find('tbody')
        if not tbody:
            logger.warning("테이블 본문을 찾을 수 없습니다")
            return announcements
        
        rows = tbody.find_all('tr')
        logger.debug(f"테이블에서 {len(rows)}개 행 발견")
        
        for i, row in enumerate(rows):
            try:
                announcement = self._parse_list_row(row, i)
                if announcement:
                    announcements.append(announcement)
                    
            except Exception as e:
                logger.error(f"행 {i} 파싱 중 오류: {e}")
                continue
        
        logger.info(f"총 {len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def _parse_list_row(self, row, row_index: int) -> Optional[Dict[str, Any]]:
        """테이블 행 파싱"""
        cells = row.find_all('td')
        if len(cells) < 7:
            return None
        
        # 번호 (첫 번째 열) - Notice 이미지나 숫자
        number_cell = cells[0]
        number_img = number_cell.find('img')
        if number_img and number_img.get('alt') == 'Notice':
            number = "Notice"
            status = "공지"
        else:
            number = number_cell.get_text(strip=True)
            status = "일반"
        
        # 분류 (두 번째 열)
        category_cell = cells[1]
        category = category_cell.get_text(strip=True)
        
        # 제목 및 링크 (세 번째 열)
        title_cell = cells[2]
        title_link = title_cell.find('a')
        if not title_link:
            return None
        
        title = title_link.get_text(strip=True)
        detail_url = title_link.get('href')
        
        # 절대 URL로 변환
        if detail_url:
            detail_url = urljoin(self.base_url, detail_url)
        else:
            return None
        
        # 상태 (네 번째 열) - 모집상태 등
        status_cell = cells[3]
        status_span = status_cell.find('span')
        recruit_status = status_span.get_text(strip=True) if status_span else status_cell.get_text(strip=True)
        
        # 작성자 (다섯 번째 열)
        writer_cell = cells[4]
        writer = writer_cell.get_text(strip=True)
        
        # 조회수 (여섯 번째 열)
        views_cell = cells[5]
        views = views_cell.get_text(strip=True)
        
        # 작성일 (일곱 번째 열)
        date_cell = cells[6] if len(cells) > 6 else None
        date = date_cell.get_text(strip=True) if date_cell else "N/A"
        
        # 첨부파일 여부 확인 (파일 아이콘이 있는지 확인)
        has_attachment = bool(title_cell.find('img', alt='파일'))
        
        return {
            'number': number,
            'category': category,
            'title': title,
            'url': detail_url,
            'status': status,
            'recruit_status': recruit_status,
            'writer': writer,
            'views': views,
            'date': date,
            'has_attachment': has_attachment,
            'organization': '대구경북디자인센터'
        }
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱 - Enhanced 버전"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        result = {
            'content': '',
            'attachments': []
        }
        
        try:
            # 본문 내용 추출
            content = self._extract_detail_content(soup)
            result['content'] = content
            
            # 첨부파일 추출
            attachments = self._extract_detail_attachments(soup)
            result['attachments'] = attachments
            
            logger.debug(f"상세 페이지 파싱 완료 - 내용: {len(content)}자, 첨부파일: {len(attachments)}개")
            
        except Exception as e:
            logger.error(f"상세 페이지 파싱 중 오류: {e}")
        
        return result
    
    def _extract_detail_content(self, soup: BeautifulSoup) -> str:
        """상세 페이지 본문 추출"""
        content = ""
        
        # 1. 제목 추출
        title_elem = soup.find('h4', class_='view_title')
        if title_elem:
            content += f"# {title_elem.get_text(strip=True)}\n\n"
        
        # 2. 메타 정보 추출
        meta_info = soup.find('div', class_='listInfo')
        if meta_info:
            content += "## 공고 정보\n\n"
            info_items = meta_info.find_all('li')
            for item in info_items:
                info_text = item.get_text(strip=True)
                if info_text:
                    content += f"- {info_text}\n"
            content += "\n"
        
        # 3. 본문 내용 추출
        view_box = soup.find('div', class_='viewBox')
        if view_box:
            # PDF 뷰어가 있는 경우
            pdf_iframes = view_box.find_all('iframe', class_='isPDFifrm')
            if pdf_iframes:
                content += "## 공고 내용\n\n"
                content += "본 공고는 PDF 형태로 제공됩니다. 상세 내용은 첨부파일을 참조하시기 바랍니다.\n\n"
                logger.debug("PDF 뷰어 감지 - 첨부파일 참조 안내 추가")
            else:
                # 일반 텍스트 내용
                content += "## 공고 내용\n\n"
                
                # HTML을 마크다운으로 변환
                try:
                    view_html = str(view_box)
                    view_markdown = self.h.handle(view_html)
                    
                    # 내용 정리
                    view_markdown = re.sub(r'\n\s*\n\s*\n', '\n\n', view_markdown)
                    view_markdown = re.sub(r'&nbsp;', ' ', view_markdown)
                    
                    if view_markdown.strip():
                        content += view_markdown + "\n\n"
                    else:
                        content += "내용을 추출할 수 없습니다.\n\n"
                        
                except Exception as e:
                    logger.error(f"본문 마크다운 변환 오류: {e}")
                    text_content = view_box.get_text(strip=True)
                    if text_content:
                        content += text_content + "\n\n"
        
        # 4. 이전글/다음글 정보 (선택사항)
        nav_info = soup.find('nav', class_='listNavi')
        if nav_info:
            content += "## 관련 공고\n\n"
            nav_links = nav_info.find_all('a')
            for link in nav_links:
                nav_text = link.get_text(strip=True)
                if nav_text:
                    content += f"- {nav_text}\n"
            content += "\n"
        
        # 기본 내용이 없으면 대체 방법 시도
        if not content.strip() or content.strip() == "#":
            logger.warning("기본 본문 추출 실패 - 대체 방법 시도")
            main_content = soup.find('div', id='sub_content')
            if main_content:
                content = self.h.handle(str(main_content))
            else:
                content = "내용을 추출할 수 없습니다."
        
        return content
    
    def _extract_detail_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """상세 페이지 첨부파일 추출"""
        attachments = []
        
        # 1. view-info 영역에서 첨부파일 추출 (우선순위)
        view_info = soup.find('div', class_='view-info')
        if view_info:
            info_cont = view_info.find('div', class_='info-cont')
            if info_cont:
                file_links = info_cont.find_all('a')
                for link in file_links:
                    try:
                        file_url = link.get('href')
                        file_name_span = link.find('span')
                        
                        if file_url and file_name_span:
                            # 절대 URL로 변환
                            file_url = urljoin(self.base_url, file_url)
                            file_name = file_name_span.get_text(strip=True)
                            
                            if file_name:
                                attachments.append({
                                    'name': file_name,
                                    'url': file_url
                                })
                                logger.debug(f"첨부파일 발견 (view-info): {file_name}")
                                
                    except Exception as e:
                        logger.error(f"view-info 첨부파일 파싱 오류: {e}")
                        continue
        
        # 2. file 클래스에서 추출 (대체 방법)
        if not attachments:
            file_list = soup.find('div', class_='file')
            if file_list:
                file_links = file_list.find_all('a')
                for link in file_links:
                    try:
                        file_url = link.get('href')
                        file_name_elem = link.find('span')
                        
                        if file_url and file_name_elem:
                            # 절대 URL로 변환
                            file_url = urljoin(self.base_url, file_url)
                            file_name = file_name_elem.get_text(strip=True)
                            
                            if file_name:
                                attachments.append({
                                    'name': file_name,
                                    'url': file_url
                                })
                                logger.debug(f"첨부파일 발견 (file): {file_name}")
                                
                    except Exception as e:
                        logger.error(f"file 클래스 첨부파일 파싱 오류: {e}")
                        continue
        
        # 3. 일반적인 다운로드 링크 패턴 찾기 (추가 시도)
        if not attachments:
            download_links = soup.find_all('a', href=re.compile(r'(download|file)'))
            for link in download_links:
                try:
                    file_url = link.get('href')
                    file_name = link.get_text(strip=True)
                    
                    # 파일명이 없거나 너무 짧으면 href에서 추출 시도
                    if not file_name or len(file_name) < 3:
                        url_parts = file_url.split('/')
                        if url_parts:
                            file_name = url_parts[-1]
                    
                    if file_url and file_name:
                        # 절대 URL로 변환
                        file_url = urljoin(self.base_url, file_url)
                        
                        attachments.append({
                            'name': file_name,
                            'url': file_url
                        })
                        logger.debug(f"첨부파일 발견 (일반 패턴): {file_name}")
                        
                except Exception as e:
                    logger.error(f"일반 패턴 첨부파일 파싱 오류: {e}")
                    continue
        
        # 중복 제거
        seen = set()
        unique_attachments = []
        for att in attachments:
            key = (att['name'], att['url'])
            if key not in seen:
                seen.add(key)
                unique_attachments.append(att)
        
        return unique_attachments
    
    def get_page(self, url: str, **kwargs) -> Optional[requests.Response]:
        """페이지 가져오기 - Enhanced 버전"""
        try:
            # DCB 사이트 전용 헤더 추가
            headers = self.dcb_headers.copy()
            headers.update(kwargs.get('headers', {}))
            
            response = self.session.get(
                url, 
                headers=headers, 
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # 인코딩 자동 수정
            self._fix_encoding(response)
            
            return response
            
        except Exception as e:
            logger.error(f"페이지 가져오기 실패 {url}: {e}")
            return None
    
    def process_announcement(self, announcement: Dict[str, Any], index: int, output_base: str = 'output'):
        """Enhanced 공고 처리"""
        logger.info(f"공고 처리 중 {index}: {announcement['title']}")
        
        # 폴더 생성
        folder_title = self.sanitize_filename(announcement['title'])[:50]
        folder_name = f"{index:03d}_{folder_title}"
        folder_path = os.path.join(output_base, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        # 상세 페이지 가져오기
        response = self.get_page(announcement['url'])
        if not response:
            logger.error(f"상세 페이지 가져오기 실패: {announcement['title']}")
            return
        
        # 상세 내용 파싱
        try:
            detail = self.parse_detail_page(response.text)
            logger.debug(f"상세 페이지 파싱 완료 - 내용길이: {len(detail['content'])}, 첨부파일: {len(detail['attachments'])}")
        except Exception as e:
            logger.error(f"상세 페이지 파싱 실패: {e}")
            return
        
        # 메타 정보 생성
        meta_info = self._create_dcb_meta_info(announcement)
        
        # 본문 저장
        content_path = os.path.join(folder_path, 'content.md')
        with open(content_path, 'w', encoding='utf-8') as f:
            f.write(meta_info + detail['content'])
        
        logger.info(f"내용 저장 완료: {content_path}")
        
        # 첨부파일 다운로드
        self._download_attachments(detail['attachments'], folder_path)
        
        # 처리된 제목으로 추가
        self.add_processed_title(announcement['title'])
        
        # 요청 간 대기
        if self.delay_between_requests > 0:
            time.sleep(self.delay_between_requests)
    
    def _create_dcb_meta_info(self, announcement: Dict[str, Any]) -> str:
        """DCB 전용 메타 정보 생성"""
        meta_lines = [f"# {announcement['title']}", ""]
        
        # DCB 특화 메타 정보
        meta_fields = [
            ('writer', '작성자'),
            ('date', '작성일'),
            ('category', '분류'),
            ('status', '상태'),
            ('recruit_status', '모집상태'),
            ('views', '조회수'),
            ('number', '번호'),
            ('organization', '기관')
        ]
        
        for field, label in meta_fields:
            if field in announcement and announcement[field] and announcement[field] != 'N/A':
                meta_lines.append(f"**{label}**: {announcement[field]}")
        
        if announcement.get('has_attachment'):
            meta_lines.append("**첨부파일**: 있음")
        
        meta_lines.extend([
            f"**원본 URL**: {announcement['url']}",
            "",
            "---",
            ""
        ])
        
        return "\n".join(meta_lines)
    
    def scrape_pages(self, max_pages: int = 4, output_base: str = 'output'):
        """Enhanced 페이지 스크래핑"""
        logger.info(f"DCB 스크래핑 시작: 최대 {max_pages}페이지")
        
        # 처리된 제목 목록 로드
        self.load_processed_titles(output_base)
        
        announcement_count = 0
        processed_count = 0
        early_stop = False
        stop_reason = ""
        
        for page_num in range(1, max_pages + 1):
            logger.info(f"페이지 {page_num} 처리 중")
            
            try:
                # 목록 가져오기 및 파싱
                announcements = self._get_page_announcements(page_num)
                
                if not announcements:
                    logger.warning(f"페이지 {page_num}에 공고가 없습니다")
                    stop_reason = "공고 없음"
                    break
                
                logger.info(f"페이지 {page_num}에서 {len(announcements)}개 공고 발견")
                
                # 새로운 공고만 필터링 및 중복 임계값 체크
                new_announcements, should_stop = self.filter_new_announcements(announcements)
                
                # 중복 임계값 도달시 조기 종료
                if should_stop:
                    logger.info(f"중복 공고 {self.duplicate_threshold}개 연속 발견으로 조기 종료")
                    early_stop = True
                    stop_reason = f"중복 {self.duplicate_threshold}개 연속"
                    break
                
                # 새로운 공고가 없으면 조기 종료 (연속된 페이지에서)
                if not new_announcements and page_num > 1:
                    logger.info("새로운 공고가 없어 스크래핑 조기 종료")
                    early_stop = True
                    stop_reason = "새로운 공고 없음"
                    break
                
                # 각 공고 처리
                for ann in new_announcements:
                    announcement_count += 1
                    processed_count += 1
                    self.process_announcement(ann, announcement_count, output_base)
                
                # 페이지 간 대기
                if page_num < max_pages and self.delay_between_pages > 0:
                    time.sleep(self.delay_between_pages)
                
            except Exception as e:
                logger.error(f"페이지 {page_num} 처리 중 오류: {e}")
                stop_reason = f"오류: {e}"
                break
        
        # 처리된 제목 목록 저장
        self.save_processed_titles()
        
        if early_stop:
            logger.info(f"DCB 스크래핑 완료: 총 {processed_count}개 새로운 공고 처리 (조기종료: {stop_reason})")
        else:
            logger.info(f"DCB 스크래핑 완료: 총 {processed_count}개 새로운 공고 처리")


# 하위 호환성을 위한 별칭
DCBScraper = EnhancedDCBScraper

if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    scraper = EnhancedDCBScraper()
    scraper.scrape_pages(max_pages=1, output_base='output/dcb_enhanced')