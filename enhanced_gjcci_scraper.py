# -*- coding: utf-8 -*-
"""
GJCCI(광주상공회의소) 스크래퍼 - Enhanced 버전
"""

import re
import os
import time
import urllib.parse
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from enhanced_base_scraper import StandardTableScraper
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class EnhancedGJCCIScraper(StandardTableScraper):
    """광주상공회의소 공지사항 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "http://www.gjcci.or.kr"
        self.list_url = "http://www.gjcci.or.kr/user/board/lists/board_cd/3010"
        
        # GJCCI 특화 설정
        self.verify_ssl = False  # SSL 인증서 문제 (인증서 불일치)
        self.default_encoding = 'utf-8'  # 페이지 인코딩
        self.timeout = 30
        self.delay_between_requests = 1
        self.use_playwright = False  # 정적 HTML 파싱 가능
        
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성"""
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}/page/{page_num}"
    
    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱 - dc_bbslist 테이블 구조 처리"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # dc_bbslist 테이블 찾기
        main_table = soup.find('table', {'class': 'dc_bbslist'})
        
        if not main_table:
            logger.warning("공지사항 테이블을 찾을 수 없습니다.")
            return announcements
        
        tbody = main_table.find('tbody')
        if not tbody:
            tbody = main_table
        
        rows = tbody.find_all('tr')
        logger.info(f"총 {len(rows)}개 행 발견")
        
        for i, row in enumerate(rows):
            try:
                # 행 클래스 확인 (rowtitle: 공지사항, row: 일반 게시물)
                row_class = row.get('class', [])
                if isinstance(row_class, list):
                    row_class = ' '.join(row_class)
                
                # 빈 행이나 헤더 행 건너뛰기
                if 'rowtitle' not in row_class and 'row' not in row_class:
                    logger.debug(f"행 {i}: 데이터 행이 아님 (클래스: {row_class})")
                    continue
                
                cells = row.find_all('td')
                if len(cells) < 4:  # 최소 4개 컬럼 필요 (번호, 제목, 등록일, 조회수)
                    logger.debug(f"행 {i}: 컬럼 수 부족 ({len(cells)}개)")
                    continue
                
                # 번호 (첫 번째 셀) - 공지사항인지 일반 게시물인지 확인
                num_cell = cells[0]
                notice_elem = num_cell.find('p', {'class': 'dc_notice'})
                number_elem = num_cell.find('p', {'class': 'dc_number'})
                
                if notice_elem:
                    post_num = "공지"
                    post_type = "notice"
                elif number_elem:
                    post_num = number_elem.get_text(strip=True)
                    post_type = "normal"
                else:
                    post_num = num_cell.get_text(strip=True)
                    post_type = "normal"
                
                # 제목 (두 번째 셀)
                title_cell = cells[1]
                link_elem = title_cell.find('a')
                
                if not link_elem:
                    logger.debug(f"행 {i}: 링크 요소를 찾을 수 없음")
                    continue
                
                title = link_elem.get_text(strip=True)
                href = link_elem.get('href', '')
                
                if not title or not href:
                    logger.debug(f"행 {i}: 제목 또는 링크가 비어있음")
                    continue
                
                # 상세 페이지 URL 구성 (절대 URL로 변환)
                detail_url = urljoin(self.base_url, href)
                
                # 게시물 번호 추출 (URL에서 wr_no 파라미터)
                match = re.search(r'/wr_no/(\d+)', href)
                wr_no = match.group(1) if match else ""
                
                # 첨부파일 여부 확인
                has_attachment = bool(title_cell.find('img', {'alt': '파일'}))
                
                # 등록일 (세 번째 셀)
                date_cell = cells[2]
                date_elem = date_cell.find('p', {'class': 'dc_date'})
                date = date_elem.get_text(strip=True) if date_elem else date_cell.get_text(strip=True)
                
                # 조회수 (네 번째 셀)
                hit_cell = cells[3]
                hit_elem = hit_cell.find('p', {'class': 'dc_hit'})
                views = hit_elem.get_text(strip=True) if hit_elem else hit_cell.get_text(strip=True)
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'post_num': post_num,
                    'post_type': post_type,
                    'wr_no': wr_no,
                    'date': date,
                    'views': views,
                    'has_attachment': has_attachment
                }
                
                announcements.append(announcement)
                logger.debug(f"공고 추가: {title}")
                
            except Exception as e:
                logger.error(f"행 {i} 파싱 중 오류: {e}")
                continue
        
        logger.info(f"총 {len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> dict:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 기본값
        title = ""
        content = ""
        metadata = {}
        
        # 제목 추출 - dc_viewtitle 클래스
        title_elem = soup.find('p', {'class': 'dc_viewtitle'})
        if title_elem:
            title = title_elem.get_text(strip=True)
        
        # 본문 내용 추출 - dc_viewcontent 클래스
        content_elem = soup.find('div', {'class': 'dc_viewcontent'})
        if content_elem:
            # HTML 태그 제거하고 텍스트만 추출
            content = content_elem.get_text(strip=True)
            
            # 너무 짧은 경우 HTML 내용 그대로 사용
            if len(content) < 50:
                content = str(content_elem)
        
        # 메타데이터 추출 - dc_viewinfo 클래스
        info_elem = soup.find('div', {'class': 'dc_viewinfo'})
        if info_elem:
            info_text = info_elem.get_text()
            
            # 등록일 추출
            date_match = re.search(r'등록일.*?(\d{4}-\d{2}-\d{2})', info_text)
            if date_match:
                metadata['date'] = date_match.group(1)
            
            # 조회수 추출
            views_match = re.search(r'조회.*?(\d+)', info_text)
            if views_match:
                metadata['views'] = views_match.group(1)
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup)
        
        # 본문이 비어있으면 기본 텍스트
        if not content.strip():
            content = "공고 내용을 확인하려면 첨부파일을 다운로드하여 확인하세요."
        
        # 마크다운 형태로 정리
        if content and not content.startswith('##'):
            content = f"## 공고 내용\n\n{content}\n\n"
        
        result = {
            'title': title,
            'content': content,
            'attachments': attachments,
            'metadata': metadata
        }
        
        logger.info(f"상세 페이지 파싱 완료 - 제목: {title}, 내용: {len(content)}자, 첨부파일: {len(attachments)}개")
        return result
    
    def _extract_attachments(self, soup: BeautifulSoup) -> list:
        """첨부파일 추출 - GJCCI 특화 패턴"""
        attachments = []
        
        # 첨부파일 섹션 찾기 - dc_viewaddfile 클래스
        addfile_div = soup.find('div', {'class': 'dc_viewaddfile'})
        
        if addfile_div:
            # 첨부파일 링크들 찾기
            file_links = addfile_div.find_all('a')
            
            for i, link in enumerate(file_links, 1):
                href = link.get('href', '')
                link_text = link.get_text(strip=True)
                
                if '/user/board/download/' in href:
                    # 파일명과 크기 분리 (예: "파일명.hwp : 1.2MB")
                    if ' : ' in link_text:
                        filename, file_size = link_text.split(' : ', 1)
                        filename = filename.strip()
                        file_size = file_size.strip()
                    else:
                        filename = link_text
                        file_size = ""
                    
                    # 파일명이 비어있으면 기본값 사용
                    if not filename.strip():
                        filename = f"attachment_{i}"
                    
                    # 상대 URL을 절대 URL로 변환
                    file_url = urljoin(self.base_url, href)
                    
                    attachment = {
                        'filename': filename,
                        'url': file_url,
                        'size': file_size
                    }
                    attachments.append(attachment)
                    logger.info(f"첨부파일 발견: {filename} ({file_size})")
        
        return attachments
    
    def process_announcement(self, announcement: dict, index: int, output_base: str = 'output'):
        """개별 공고 처리"""
        logger.info(f"공고 처리 중 {index}: {announcement['title']}")
        
        # 폴더 생성
        folder_title = self.sanitize_filename(announcement['title'])[:100]
        folder_name = f"{index:03d}_{folder_title}"
        
        if len(folder_name) > 200:
            folder_title = folder_title[:195]
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
            logger.info(f"상세 페이지 파싱 완료 - 내용길이: {len(detail['content'])}, 첨부파일: {len(detail['attachments'])}개")
            
            # 메타데이터 업데이트
            for key, value in detail['metadata'].items():
                if value and key not in announcement:
                    announcement[key] = value
            
        except Exception as e:
            logger.error(f"상세 페이지 파싱 실패: {e}")
            # 기본 콘텐츠로라도 저장
            detail = {
                'title': announcement.get('title', ''),
                'content': "## 공고 내용\n\n상세 내용을 가져올 수 없습니다. 원본 페이지를 확인해주세요.\n\n",
                'attachments': [],
                'metadata': {}
            }
        
        # 메타 정보 생성
        meta_info = self._create_meta_info(announcement)
        
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
    
    def _create_meta_info(self, announcement: dict) -> str:
        """메타 정보 생성"""
        meta_info = f"# {announcement['title']}\n\n"
        meta_info += "## 공고 정보\n\n"
        
        meta_info += f"- **제목**: {announcement['title']}\n"
        if announcement.get('post_num'):
            meta_info += f"- **공고번호**: {announcement['post_num']}\n"
        if announcement.get('wr_no'):
            meta_info += f"- **게시물번호**: {announcement['wr_no']}\n"
        if announcement.get('post_type'):
            post_type_kr = "공지사항" if announcement['post_type'] == "notice" else "일반공고"
            meta_info += f"- **게시물유형**: {post_type_kr}\n"
        if announcement.get('date'):
            meta_info += f"- **등록일**: {announcement['date']}\n"
        if announcement.get('views'):
            meta_info += f"- **조회수**: {announcement['views']}\n"
        
        meta_info += f"- **원본URL**: {announcement['url']}\n"
        meta_info += f"- **수집일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        if announcement.get('has_attachment'):
            meta_info += f"- **첨부파일유무**: 있음\n"
        
        meta_info += "\n"
        return meta_info
    
    def _download_attachments(self, attachments: list, folder_path: str):
        """첨부파일 다운로드"""
        if not attachments:
            return
        
        # attachments 폴더 생성
        attachments_dir = os.path.join(folder_path, 'attachments')
        os.makedirs(attachments_dir, exist_ok=True)
        
        for i, attachment in enumerate(attachments, 1):
            try:
                file_url = attachment['url']
                filename = attachment['filename']
                
                # 파일명 정리
                safe_filename = self.sanitize_filename(filename)
                if not safe_filename:
                    safe_filename = f"attachment_{i}"
                
                file_path = os.path.join(attachments_dir, safe_filename)
                
                # 파일 다운로드
                logger.info(f"첨부파일 다운로드 시작: {filename}")
                success = self.download_file(file_url, file_path)
                
                if success:
                    file_size = os.path.getsize(file_path)
                    logger.info(f"첨부파일 다운로드 완료: {filename} ({file_size:,} bytes)")
                else:
                    logger.error(f"첨부파일 다운로드 실패: {filename}")
                    
            except Exception as e:
                logger.error(f"첨부파일 다운로드 중 오류 ({attachment['filename']}): {e}")

# 테스트용 함수
def test_gjcci_scraper(pages=3):
    """GJCCI 스크래퍼 테스트"""
    import os
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    scraper = EnhancedGJCCIScraper()
    output_dir = "output/gjcci"
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"GJCCI 스크래퍼 테스트 시작 - {pages}페이지")
    scraper.scrape_pages(max_pages=pages, output_base=output_dir)
    logger.info("GJCCI 스크래퍼 테스트 완료")

if __name__ == "__main__":
    test_gjcci_scraper(3)