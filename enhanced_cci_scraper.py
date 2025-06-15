# -*- coding: utf-8 -*-
"""
청주상공회의소 스크래퍼 - Enhanced 버전
향상된 아키텍처와 중복 체크, 로깅 지원
"""

import requests
from bs4 import BeautifulSoup
import os
import time
import html2text
import logging
from urllib.parse import urljoin, urlparse, parse_qs
import re
from typing import List, Dict, Any, Optional
from enhanced_base_scraper import StandardTableScraper

logger = logging.getLogger(__name__)

class EnhancedCCIScraper(StandardTableScraper):
    """청주상공회의소 스크래퍼 - Enhanced 버전"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://cheongjucci.korcham.net"
        self.list_ajax_url = "https://cheongjucci.korcham.net/front/board/boardContentsList.do"
        self.detail_base_url = "https://cheongjucci.korcham.net/front/board/boardContentsView.do"
        self.board_id = "10701"
        self.menu_id = "1561"
        
        # AJAX 요청을 위한 추가 헤더
        self.ajax_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # 세션 헤더 업데이트
        self.session.headers.update(self.ajax_headers)
    
    def get_list_url(self, page_num: int) -> str:
        """페이지 번호에 따른 목록 AJAX URL 반환"""
        return f"{self.list_ajax_url}?boardId={self.board_id}&menuId={self.menu_id}&miv_pageNo={page_num}&miv_pageSize=10"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - Enhanced 버전"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 테이블에서 공고 목록 찾기
        table = soup.find('table')
        if not table:
            logger.warning("테이블을 찾을 수 없습니다")
            return []
        
        tbody = table.find('tbody')
        if not tbody:
            logger.warning("테이블 본문을 찾을 수 없습니다")
            return []
        
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
    
    def _get_page_announcements(self, page_num: int) -> List[Dict[str, Any]]:
        """페이지별 공고 목록 가져오기 - CCI 전용"""
        page_url = self.get_list_url(page_num)
        response = self.get_page(page_url)
        
        if not response:
            logger.warning(f"페이지 {page_num} 응답을 가져올 수 없습니다")
            return []
        
        # 페이지가 에러 상태거나 잘못된 경우 감지
        if response.status_code >= 400:
            logger.warning(f"페이지 {page_num} HTTP 에러: {response.status_code}")
            return []
        
        announcements = self.parse_list_page(response.text)
        
        # CCI 특화: 페이지에 "검색된 내용이 없습니다" 또는 빈 테이블이 있는지 확인
        if not announcements and page_num > 1:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # "검색된 내용이 없습니다" 메시지 확인
            no_result_elements = soup.find_all(text=lambda text: text and ('검색된 내용이 없습니다' in text or '게시물이 없습니다' in text))
            
            if no_result_elements:
                logger.info(f"CCI 페이지 {page_num}: '검색된 내용이 없습니다' 메시지 발견 - 마지막 페이지")
            else:
                logger.info(f"CCI 페이지 {page_num}: 공고가 없어 마지막 페이지로 판단됩니다")
        
        return announcements
    
    def _parse_list_row(self, row, row_index: int) -> Optional[Dict[str, Any]]:
        """테이블 행 파싱"""
        cells = row.find_all('td')
        if len(cells) < 2:
            return None
        
        # 번호 (첫 번째 열)
        number_cell = cells[0]
        # 공지사항 아이콘이 있는지 확인
        notice_img = number_cell.find('img', alt='공지')
        if notice_img:
            number = "공지"
            status = "공지"
        else:
            number = number_cell.get_text(strip=True)
            status = "일반"
        
        # 제목 및 링크 (두 번째 열)
        title_cell = cells[1]
        title_link = title_cell.find('a')
        if not title_link:
            return None
        
        title = title_link.get_text(strip=True)
        
        # JavaScript 링크에서 contId 추출
        onclick = title_link.get('href', '')
        if not onclick or onclick == 'javascript:void(0)':
            onclick = title_link.get('onclick', '')
        
        # contentsView('116475') 형태에서 ID 추출
        cont_id_match = re.search(r"contentsView\('(\d+)'\)", onclick)
        if not cont_id_match:
            logger.warning(f"contId 추출 실패: {onclick}")
            return None
        
        cont_id = cont_id_match.group(1)
        detail_url = f"{self.detail_base_url}?contId={cont_id}&boardId={self.board_id}&menuId={self.menu_id}"
        
        # 추가 정보 추출 (날짜 등이 있는 경우)
        writer = 'N/A'
        date = 'N/A'
        
        # 3번째, 4번째 열에서 추가 정보 추출 시도
        if len(cells) > 2:
            # 작성자 정보가 있을 수 있음
            writer_cell = cells[2]
            writer_text = writer_cell.get_text(strip=True)
            if writer_text and writer_text != '-':
                writer = writer_text
        
        if len(cells) > 3:
            # 날짜 정보가 있을 수 있음
            date_cell = cells[3]
            date_text = date_cell.get_text(strip=True)
            if date_text and date_text != '-':
                date = date_text
        
        return {
            'number': number,
            'title': title,
            'url': detail_url,
            'cont_id': cont_id,
            'writer': writer,
            'date': date,
            'status': status,
            'organization': '청주상공회의소'
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
        
        # 1. 기본 정보 추출 (제목, 작성자, 작성일 등)
        board_view = soup.find('div', class_='boardveiw')
        if board_view:
            table = board_view.find('table')
            if table:
                rows = table.find_all('tr')
                
                # 메타데이터 수집
                meta_data = {}
                for row in rows:
                    th = row.find('th')
                    td = row.find('td')
                    if th and td:
                        key = th.get_text(strip=True)
                        value = td.get_text(strip=True)
                        if key in ['제목', '작성자', '작성일', '조회수']:
                            meta_data[key] = value
                
                # 메타데이터를 content에 추가
                if meta_data.get('제목'):
                    content += f"# {meta_data['제목']}\n\n"
                
                content += "## 공고 정보\n\n"
                for key, value in meta_data.items():
                    if key != '제목':
                        content += f"- **{key}**: {value}\n"
                content += "\n"
        
        # 2. 본문 내용 추출
        content_cell = soup.find('td', class_='td_p')
        if content_cell:
            content += "## 공고 내용\n\n"
            
            # HTML 구조 정리
            self._clean_html_content(content_cell)
            
            # HTML을 마크다운으로 변환
            content_html = str(content_cell)
            content_md = self.h.handle(content_html)
            
            # 과도한 공백 정리
            content_md = re.sub(r'\n\s*\n\s*\n', '\n\n', content_md)
            content_md = re.sub(r'&nbsp;', ' ', content_md)
            
            content += content_md
        else:
            logger.warning("본문 내용 추출 실패")
            content += "본문 내용을 추출할 수 없습니다.\n"
        
        return content
    
    def _clean_html_content(self, content_element):
        """HTML 내용 정리"""
        # 불필요한 태그 제거
        for element in content_element.find_all(True):
            if element.name in ['style', 'script']:
                element.decompose()
            else:
                # 스타일 속성 제거
                if element.has_attr('style'):
                    del element['style']
                # 기타 불필요한 속성 제거
                for attr in ['class', 'id', 'width', 'height', 'cellspacing', 'cellpadding', 'border']:
                    if element.has_attr(attr):
                        del element[attr]
    
    def _extract_detail_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """상세 페이지 첨부파일 추출"""
        attachments = []
        
        # 첨부파일 영역 찾기
        file_view = soup.find('ul', class_='file_view')
        if file_view:
            file_links = file_view.find_all('li')
            logger.debug(f"첨부파일 영역에서 {len(file_links)}개 항목 발견")
            
            for li in file_links:
                try:
                    link = li.find('a')
                    if link:
                        file_url = link.get('href')
                        file_name = link.get('title') or link.get_text(strip=True)
                        
                        # 상대 URL을 절대 URL로 변환
                        if file_url:
                            file_url = urljoin(self.base_url, file_url)
                            
                            # 파일명 정리
                            if not file_name or file_name.isspace():
                                file_name = f"attachment_{len(attachments) + 1}"
                            
                            attachments.append({
                                'name': file_name,
                                'url': file_url
                            })
                            logger.debug(f"첨부파일 발견: {file_name}")
                        
                except Exception as e:
                    logger.error(f"첨부파일 링크 파싱 오류: {e}")
                    continue
        else:
            logger.debug("첨부파일 영역을 찾을 수 없습니다")
        
        return attachments
    
    def get_page(self, url: str, **kwargs) -> Optional[requests.Response]:
        """페이지 가져오기 - Enhanced 버전 (세션 관리 포함)"""
        try:
            # CCI 사이트 전용 헤더 추가
            headers = self.ajax_headers.copy()
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
        meta_info = self._create_cci_meta_info(announcement)
        
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
    
    def _create_cci_meta_info(self, announcement: Dict[str, Any]) -> str:
        """CCI 전용 메타 정보 생성"""
        meta_lines = [f"# {announcement['title']}", ""]
        
        # CCI 특화 메타 정보
        meta_fields = [
            ('writer', '작성자'),
            ('date', '작성일'),
            ('status', '상태'),
            ('number', '번호'),
            ('organization', '기관'),
            ('cont_id', 'Content ID')
        ]
        
        for field, label in meta_fields:
            if field in announcement and announcement[field] and announcement[field] != 'N/A':
                meta_lines.append(f"**{label}**: {announcement[field]}")
        
        meta_lines.extend([
            f"**원본 URL**: {announcement['url']}",
            "",
            "---",
            ""
        ])
        
        return "\n".join(meta_lines)
    
    def scrape_pages(self, max_pages: int = 4, output_base: str = 'output'):
        """Enhanced 페이지 스크래핑"""
        logger.info(f"CCI 스크래핑 시작: 최대 {max_pages}페이지")
        
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
            logger.info(f"CCI 스크래핑 완료: 총 {processed_count}개 새로운 공고 처리 (조기종료: {stop_reason})")
        else:
            logger.info(f"CCI 스크래핑 완료: 총 {processed_count}개 새로운 공고 처리")


# 하위 호환성을 위한 별칭
CCIScraper = EnhancedCCIScraper

if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    scraper = EnhancedCCIScraper()
    scraper.scrape_pages(max_pages=1, output_base='output/cci_enhanced')