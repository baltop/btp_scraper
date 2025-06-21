# -*- coding: utf-8 -*-
"""
DCCI(대구상공회의소) 스크래퍼 - Enhanced 버전
"""

import re
import os
import time
import urllib.parse
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from enhanced_base_scraper import StandardTableScraper
import logging

logger = logging.getLogger(__name__)

class EnhancedDCCIScraper(StandardTableScraper):
    """대구상공회의소 공지사항 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.dcci.or.kr"
        self.list_url = "https://www.dcci.or.kr/content.html?md=0028"
        
        # DCCI 특화 설정
        self.verify_ssl = True  # HTTPS 사이트
        self.default_encoding = 'utf-8'  # 페이지 인코딩
        self.file_encoding = 'euc-kr'  # 파일명 인코딩
        self.timeout = 30
        self.delay_between_requests = 1
        
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성"""
        if page_num == 1:
            return f"{self.list_url}&cnt=1"
        else:
            return f"{self.list_url}&cnt={page_num}"
    
    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱 - 복잡한 테이블 구조 처리"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 메인 공지사항 테이블 찾기
        main_table = None
        
        # caption으로 테이블 찾기
        for table in soup.find_all('table'):
            caption = table.find('caption')
            if caption and '공지사항게시판' in caption.get_text():
                main_table = table
                break
        
        if not main_table:
            # 백업: 테이블 구조로 찾기
            tables = soup.find_all('table')
            for table in tables:
                tbody = table.find('tbody')
                if tbody:
                    rows = tbody.find_all('tr')
                    if len(rows) > 1:  # 헤더 + 데이터 행이 있는 테이블
                        first_row = rows[0]
                        cells = first_row.find_all(['th', 'td'])
                        if len(cells) >= 5:  # 최소 5개 컬럼
                            main_table = table
                            break
        
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
                cells = row.find_all(['td', 'th'])
                if len(cells) < 6:  # 최소 6개 컬럼 필요
                    logger.debug(f"행 {i}: 컬럼 수 부족 ({len(cells)}개)")
                    continue
                
                # 헤더 행 건너뛰기
                if row.find('th'):
                    logger.debug(f"행 {i}: 헤더 행 건너뛰기")
                    continue
                
                # 번호 (첫 번째 셀) - "공지글1" 같은 고정글도 있음
                post_num_cell = cells[0]
                post_num = post_num_cell.get_text(strip=True)
                
                # 제목 (세 번째 셀) - 보통 번호, 분류, 제목 순
                title_cell = cells[2] if len(cells) > 2 else cells[1]
                link_elem = title_cell.find('a')
                
                if not link_elem:
                    logger.debug(f"행 {i}: 링크를 찾을 수 없음")
                    continue
                
                title = link_elem.get_text(strip=True)
                if not title:
                    logger.debug(f"행 {i}: 제목이 비어있음")
                    continue
                
                href = link_elem.get('href', '')
                if not href:
                    logger.debug(f"행 {i}: href가 비어있음")
                    continue
                
                # 상대 URL을 절대 URL로 변환
                detail_url = urljoin(self.base_url, href)
                
                # 담당부서 (네 번째 셀)
                department = cells[3].get_text(strip=True) if len(cells) > 3 else ""
                
                # 상태 (다섯 번째 셀) - 진행중/종료
                status = cells[4].get_text(strip=True) if len(cells) > 4 else ""
                
                # 등록일 (여섯 번째 셀)
                date = cells[5].get_text(strip=True) if len(cells) > 5 else ""
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'post_num': post_num,
                    'department': department,
                    'status': status,
                    'date': date
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
        
        # 메인 내용 테이블 찾기
        content_table = None
        
        # caption으로 찾기
        for table in soup.find_all('table'):
            caption = table.find('caption')
            if caption and ('게시물 내용' in caption.get_text() or '공지사항' in caption.get_text()):
                content_table = table
                break
        
        if not content_table:
            # 백업: 큰 테이블 찾기
            tables = soup.find_all('table')
            max_rows = 0
            for table in tables:
                rows = table.find_all('tr')
                if len(rows) > max_rows:
                    max_rows = len(rows)
                    content_table = table
        
        if content_table:
            rows = content_table.find_all('tr')
            
            # 제목 추출 - 첫 번째 행에서 긴 텍스트 찾기
            for row in rows[:3]:  # 처음 몇 행에서 제목 찾기
                cells = row.find_all(['td', 'th'])
                for cell in cells:
                    cell_text = cell.get_text(strip=True)
                    if len(cell_text) > 10 and not any(keyword in cell_text for keyword in ['작성자', '조회수', '등록일', '담당부서']):
                        if not title or len(cell_text) > len(title):
                            title = cell_text
            
            # 메타데이터 추출
            for row in rows:
                row_text = row.get_text()
                if '작성자' in row_text:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        metadata['author'] = cells[1].get_text(strip=True)
                elif '담당부서' in row_text:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        metadata['department'] = cells[1].get_text(strip=True)
                elif '조회수' in row_text:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        metadata['views'] = cells[1].get_text(strip=True)
            
            # 본문 내용 추출 - 긴 텍스트가 있는 셀 찾기
            content_candidates = []
            for row in rows:
                cells = row.find_all('td')
                for cell in cells:
                    cell_text = cell.get_text(strip=True)
                    # 긴 텍스트이고 메타데이터가 아닌 경우
                    if (len(cell_text) > 100 and 
                        not any(keyword in cell_text for keyword in ['작성자', '조회수', '등록일', '담당부서', '첨부파일'])):
                        content_candidates.append(cell_text)
            
            if content_candidates:
                content = max(content_candidates, key=len)  # 가장 긴 텍스트 선택
        
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
        """첨부파일 추출 - DCCI 특화 파일 다운로드 패턴"""
        attachments = []
        
        # 첨부파일 섹션 찾기
        for row in soup.find_all('tr'):
            row_text = row.get_text()
            if '첨부파일' in row_text:
                # 이 행에서 파일 링크 찾기
                links = row.find_all('a')
                for link in links:
                    href = link.get('href', '')
                    if '/include/filedown.html' in href:
                        # 파일명 추출
                        link_text = link.get_text(strip=True)
                        
                        # URL에서 filename 파라미터 추출
                        try:
                            parsed_url = urllib.parse.urlparse(href)
                            query_params = urllib.parse.parse_qs(parsed_url.query)
                            
                            # filename 파라미터에서 한글 파일명 추출
                            if 'filename' in query_params:
                                encoded_filename = query_params['filename'][0]
                                try:
                                    # EUC-KR로 인코딩된 파일명 디코딩
                                    url_decoded = urllib.parse.unquote(encoded_filename)
                                    korean_filename = url_decoded.encode('latin-1').decode('euc-kr')
                                    filename = korean_filename
                                except:
                                    # 디코딩 실패시 링크 텍스트 사용
                                    filename = link_text
                            else:
                                filename = link_text
                            
                            # 파일명이 비어있으면 기본값 사용
                            if not filename.strip():
                                filename = f"attachment_{len(attachments) + 1}"
                            
                        except Exception as e:
                            logger.warning(f"파일명 추출 실패: {e}")
                            filename = link_text if link_text else f"attachment_{len(attachments) + 1}"
                        
                        file_url = urljoin(self.base_url, href)
                        
                        attachment = {
                            'filename': filename,
                            'url': file_url
                        }
                        attachments.append(attachment)
                        logger.info(f"첨부파일 발견: {filename}")
        
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
            logger.info(f"상세 페이지 파싱 완료 - 내용길이: {len(detail['content'])}, 첨부파일: {len(detail['attachments'])}")
            
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

# 테스트용 함수
def test_dcci_scraper(pages=3):
    """DCCI 스크래퍼 테스트"""
    import os
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    scraper = EnhancedDCCIScraper()
    output_dir = "output/dcci"
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"DCCI 스크래퍼 테스트 시작 - {pages}페이지")
    scraper.scrape_pages(max_pages=pages, output_base=output_dir)
    logger.info("DCCI 스크래퍼 테스트 완료")

if __name__ == "__main__":
    test_dcci_scraper(3)