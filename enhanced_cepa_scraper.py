# -*- coding: utf-8 -*-
"""
충남경제진흥원(CEPA) 스크래퍼 - Enhanced 버전
향상된 아키텍처와 중복 체크, 로깅 지원
"""

from enhanced_base_scraper import StandardTableScraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin, parse_qs
import re
import time
import logging
import os
from typing import Dict, List, Any, Optional
import requests

logger = logging.getLogger(__name__)

class EnhancedCEPAScraper(StandardTableScraper):
    """충남경제진흥원(CEPA) 스크래퍼 - Enhanced 버전"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.cepa.or.kr"
        self.list_url = "https://www.cepa.or.kr/notice/notice.do?pm=6&ms=32"
        self.verify_ssl = False  # SSL 검증 비활성화
        
        # CEPA 사이트 특성상 추가 헤더 설정
        self.cepa_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # 세션 헤더 업데이트
        self.session.headers.update(self.cepa_headers)
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 목록 URL 생성"""
        return f"{self.list_url}&page={page_num}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - Enhanced 버전"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 게시판 테이블 찾기
        tbody = soup.find('tbody')
        if not tbody:
            logger.warning("tbody를 찾을 수 없습니다")
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
        # 제목 컬럼 찾기 - class="tbl-subject"인 td를 찾기
        title_cell = row.find('td', class_='tbl-subject')
        if not title_cell:
            # 대체 방법: 링크가 있는 td 찾기
            for td in row.find_all('td'):
                if td.find('a'):
                    title_cell = td
                    break
        
        if not title_cell:
            return None
        
        # 링크 찾기
        link_tag = title_cell.find('a')
        if not link_tag:
            return None
        
        title = link_tag.get_text(strip=True)
        if not title:
            return None
        
        # URL 구성
        href = link_tag.get('href', '')
        onclick = link_tag.get('onclick', '')
        detail_url = None
        
        if onclick:
            # JavaScript 함수에서 파라미터 추출
            match = re.search(r"fn_view\('([^']+)'\)", onclick)
            if match:
                notice_id = match.group(1)
                detail_url = f"{self.base_url}/notice/noticeView.do?noticeSeq={notice_id}"
        elif href and not href.startswith('#'):
            if href.startswith('http'):
                detail_url = href
            else:
                detail_url = urljoin(self.base_url, href)
        
        if not detail_url:
            logger.warning(f"URL을 구성할 수 없습니다: {title}")
            return None
        
        # 추가 정보 추출
        cells = row.find_all('td')
        
        # 번호, 작성자, 날짜 등 추출 시도
        number = ""
        writer = ""
        date = ""
        status = "일반"
        
        if len(cells) >= 3:
            # 첫 번째 셀: 번호
            number_cell = cells[0]
            number_text = number_cell.get_text(strip=True)
            if number_text.isdigit():
                number = number_text
            elif '공지' in number_text:
                status = "공지"
                number = "공지"
        
        if len(cells) >= 4:
            # 세 번째 셀: 작성자 (있는 경우)
            writer_cell = cells[2]
            writer_text = writer_cell.get_text(strip=True)
            if writer_text and writer_text != '-':
                writer = writer_text
        
        if len(cells) >= 5:
            # 네 번째 셀: 날짜 (있는 경우)
            date_cell = cells[3]
            date_text = date_cell.get_text(strip=True)
            if date_text and date_text != '-':
                date = date_text
        
        return {
            'title': title,
            'url': detail_url,
            'number': number,
            'writer': writer,
            'date': date,
            'status': status,
            'organization': '충남경제진흥원'
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
        
        # 본문 내용 찾기 - 여러 패턴 시도
        content_selectors = [
            'td.board-content',
            'div.view_content', 
            'div.board_view',
            '.content-area',
            '.board-content-area'
        ]
        
        content_area = None
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                logger.debug(f"본문 영역 발견: {selector}")
                break
        
        if content_area:
            # HTML을 마크다운으로 변환
            content = self.h.handle(str(content_area))
            
            # 내용 정리
            content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
            content = re.sub(r'&nbsp;', ' ', content)
        else:
            logger.warning("본문 영역을 찾을 수 없습니다")
            content = "본문 내용을 추출할 수 없습니다."
        
        return content
    
    def _extract_detail_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """상세 페이지 첨부파일 추출"""
        attachments = []
        
        # 첨부파일 영역 찾기 - 다양한 패턴 시도
        file_areas = []
        
        # 패턴 1: 파일 영역 클래스
        for class_name in ['file', 'attach', 'attachment', 'file_list', 'file-area']:
            file_area = soup.find('div', class_=class_name)
            if file_area:
                file_areas.append(file_area)
                logger.debug(f"첨부파일 영역 발견: {class_name}")
        
        # 패턴 2: 첨부파일 제목이 있는 영역
        for td in soup.find_all('td'):
            text = td.get_text()
            if '첨부' in text:
                # 파일 아이콘이 있는지 확인
                if td.find('i', class_='fa-file-text-o') or td.find('a'):
                    file_areas.append(td)
                    logger.debug("첨부파일 영역 발견: 텍스트 기반")
        
        # 패턴 3: 테이블 형태의 첨부파일 영역
        for table in soup.find_all('table'):
            if any('첨부' in cell.get_text() for cell in table.find_all(['th', 'td'])):
                file_areas.append(table)
                logger.debug("첨부파일 영역 발견: 테이블")
        
        # 파일 링크 추출
        for area in file_areas:
            for link in area.find_all('a'):
                try:
                    file_name = link.get_text(strip=True)
                    href = link.get('href', '')
                    onclick = link.get('onclick', '')
                    file_url = None
                    
                    if onclick:
                        # JavaScript 함수에서 파일 다운로드 파라미터 추출
                        match = re.search(r"fn_download\('([^']+)'\)", onclick)
                        if match:
                            file_id = match.group(1)
                            file_url = f"{self.base_url}/notice/download.do?fileSeq={file_id}"
                    elif href and not href.startswith('#'):
                        if href.startswith('http'):
                            file_url = href
                        else:
                            file_url = urljoin(self.base_url, href)
                        
                        # 다운로드 URL이 아닌 경우 스킵
                        if '/download' not in file_url and '/file' not in file_url:
                            continue
                    
                    if file_url and file_name:
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
        
        return attachments
    
    def get_page(self, url: str, **kwargs) -> Optional[requests.Response]:
        """페이지 가져오기 - Enhanced 버전 (SSL 검증 비활성화)"""
        try:
            # CEPA 사이트 전용 헤더 추가
            headers = self.cepa_headers.copy()
            headers.update(kwargs.get('headers', {}))
            
            response = self.session.get(
                url, 
                headers=headers, 
                verify=self.verify_ssl,  # SSL 검증 비활성화
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
        meta_info = self._create_cepa_meta_info(announcement)
        
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
    
    def _create_cepa_meta_info(self, announcement: Dict[str, Any]) -> str:
        """CEPA 전용 메타 정보 생성"""
        meta_lines = [f"# {announcement['title']}", ""]
        
        # CEPA 특화 메타 정보
        meta_fields = [
            ('writer', '작성자'),
            ('date', '작성일'),
            ('status', '상태'),
            ('number', '번호'),
            ('organization', '기관')
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
        logger.info(f"CEPA 스크래핑 시작: 최대 {max_pages}페이지")
        
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
            logger.info(f"CEPA 스크래핑 완료: 총 {processed_count}개 새로운 공고 처리 (조기종료: {stop_reason})")
        else:
            logger.info(f"CEPA 스크래핑 완료: 총 {processed_count}개 새로운 공고 처리")


# 하위 호환성을 위한 별칭
CEPAScraper = EnhancedCEPAScraper

if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    scraper = EnhancedCEPAScraper()
    scraper.scrape_pages(max_pages=1, output_base='output/cepa_enhanced')