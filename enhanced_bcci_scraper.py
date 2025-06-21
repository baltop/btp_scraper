# -*- coding: utf-8 -*-
"""
BCCI(부산상공회의소) 스크래퍼 - Enhanced 버전
"""

import re
import os
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from enhanced_base_scraper import StandardTableScraper
import logging

logger = logging.getLogger(__name__)

class EnhancedBCCIScraper(StandardTableScraper):
    """부산상공회의소 공지사항 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.bcci.or.kr"
        self.list_url = "https://www.bcci.or.kr/kr/index.php?pCode=notice"
        
        # BCCI 특화 설정
        self.verify_ssl = True  # HTTPS 사이트, SSL 인증서 유효
        self.default_encoding = 'utf-8'  # 현대적인 UTF-8 인코딩
        self.timeout = 30
        self.delay_between_requests = 1  # 서버 부하 고려
        
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 (단순한 GET 파라미터 기반)"""
        if page_num == 1:
            return self.list_url
        else:
            # 단순한 pg 파라미터 기반 페이지네이션
            return f"{self.list_url}&pg={page_num}"
    
    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱 - 표준 HTML 테이블 구조"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 메인 테이블 찾기 - role="table" 속성으로 식별
        table = soup.find('table', attrs={'role': 'table'})
        if not table:
            # 백업: 일반 테이블 찾기
            table = soup.find('table')
        
        if not table:
            logger.warning("테이블을 찾을 수 없습니다.")
            return announcements
        
        tbody = table.find('tbody')
        if not tbody:
            logger.warning("tbody를 찾을 수 없습니다. table에서 직접 tr 찾기")
            tbody = table
        
        rows = tbody.find_all('tr')
        logger.info(f"총 {len(rows)}개 행 발견")
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 5:  # 최소 5개 컬럼 필요 (번호, 제목, 작성자, 등록일, 조회)
                    continue
                
                # 번호 (첫 번째 셀)
                number_cell = cells[0]
                number = number_cell.get_text(strip=True)
                
                # 제목 셀 (두 번째 셀)
                title_cell = cells[1]
                link_elem = title_cell.find('a')
                
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                if not title:
                    continue
                
                href = link_elem.get('href', '')
                if not href:
                    continue
                
                # 상대 URL을 절대 URL로 변환
                detail_url = urljoin(self.base_url, href)
                
                # 작성자 (세 번째 셀)
                author_cell = cells[2]
                author_p = author_cell.find('p')
                author = author_p.get_text(strip=True) if author_p else author_cell.get_text(strip=True)
                
                # 등록일 (네 번째 셀)
                date_cell = cells[3]
                date_p = date_cell.find('p')
                date = date_p.get_text(strip=True) if date_p else date_cell.get_text(strip=True)
                
                # 조회수 (다섯 번째 셀)
                views_cell = cells[4]
                views_p = views_cell.find('p')
                views = views_p.get_text(strip=True) if views_p else views_cell.get_text(strip=True)
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'author': author,
                    'date': date,
                    'views': views,
                    'number': number
                }
                
                announcements.append(announcement)
                logger.debug(f"공고 추가: {title}")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"총 {len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> dict:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 내용 찾기
        content = ""
        title = ""
        date = ""
        author = ""
        views = ""
        
        # 제목 찾기 - h3 태그에서
        title_elem = soup.find('h3')
        if title_elem:
            title = title_elem.get_text(strip=True)
        
        # 메타 정보 찾기 (작성자, 날짜, 조회수)
        # 일반적으로 상단에 span이나 div로 구성됨
        for span in soup.find_all('span'):
            text = span.get_text(strip=True)
            if text.startswith('20') and len(text) == 10:  # 날짜 형식 2025-06-20
                date = text
            elif text.isdigit():  # 조회수
                views = text
        
        # 본문 내용 추출
        # 첨부파일 섹션 이후의 div들에서 본문 찾기
        content_divs = []
        
        # 첨부파일 섹션 이후의 컨텐츠를 찾기
        attachment_marker = soup.find(string='첨부파일')
        if attachment_marker:
            # 첨부파일 섹션 이후의 형제 요소들 확인
            current = attachment_marker.parent
            while current:
                current = current.find_next_sibling()
                if current and current.name == 'div':
                    content_text = current.get_text(strip=True)
                    if content_text and len(content_text) > 10:  # 의미있는 텍스트만
                        content_divs.append(content_text)
        
        # 본문이 없다면 다른 방법으로 찾기
        if not content_divs:
            # 페이지의 모든 div에서 긴 텍스트 찾기
            for div in soup.find_all('div'):
                div_text = div.get_text(strip=True)
                if len(div_text) > 50 and '첨부파일' not in div_text:
                    # 메뉴나 네비게이션이 아닌 본문으로 보이는 텍스트
                    if not any(keyword in div_text for keyword in ['메뉴', '홈', '로그인', 'Copyright']):
                        content_divs.append(div_text)
                        break
        
        if content_divs:
            content = '\n\n'.join(content_divs)
        else:
            content = "공고 내용을 확인하려면 첨부파일을 다운로드하여 확인하세요."
        
        # 첨부파일 찾기
        attachments = self._extract_attachments(soup)
        
        # 마크다운 형태로 정리
        if content and not content.startswith('##'):
            content = f"## 공고 내용\n\n{content}\n\n"
        
        result = {
            'title': title,
            'content': content,
            'attachments': attachments,
            'date': date,
            'author': author,
            'views': views
        }
        
        logger.info(f"상세 페이지 파싱 완료 - 제목: {title}, 날짜: {date}, 내용: {len(content)}자, 첨부파일: {len(attachments)}개")
        return result
    
    def _extract_attachments(self, soup: BeautifulSoup) -> list:
        """첨부파일 추출"""
        attachments = []
        
        # 첨부파일 섹션 찾기
        attachment_marker = soup.find(string='첨부파일')
        if not attachment_marker:
            return attachments
        
        # 첨부파일 섹션의 부모 요소에서 링크 찾기
        attachment_section = attachment_marker.parent
        if attachment_section:
            # 부모나 형제 요소에서 ul, li 찾기
            ul_elem = attachment_section.find_next('ul')
            if not ul_elem:
                ul_elem = attachment_section.find('ul')
            
            if ul_elem:
                for li in ul_elem.find_all('li'):
                    link = li.find('a')
                    if link:
                        href = link.get('href', '')
                        if 'mode=fdn' in href:  # 파일 다운로드 링크 패턴
                            link_text = link.get_text(strip=True)
                            
                            # 파일명 추출 (파일 크기 정보 제거)
                            if '(' in link_text and ')' in link_text:
                                filename = link_text.split('(')[0].strip()
                            else:
                                filename = link_text
                            
                            # 파일 아이콘 텍스트 제거
                            if filename.startswith('pdf 파일') or filename.startswith('hwp 파일'):
                                filename = filename.split(' ', 2)[-1] if len(filename.split(' ')) > 2 else filename
                            
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
            
            # 목록에서 가져온 정보에 상세페이지 정보 업데이트
            if detail.get('date') and not announcement.get('date'):
                announcement['date'] = detail['date']
            if detail.get('author') and not announcement.get('author'):
                announcement['author'] = detail['author']
            if detail.get('views') and not announcement.get('views'):
                announcement['views'] = detail['views']
            
        except Exception as e:
            logger.error(f"상세 페이지 파싱 실패: {e}")
            # 기본 콘텐츠로라도 저장
            detail = {
                'title': announcement.get('title', ''),
                'content': "## 공고 내용\n\n상세 내용을 가져올 수 없습니다. 원본 페이지를 확인해주세요.\n\n",
                'attachments': [],
                'date': announcement.get('date', ''),
                'author': announcement.get('author', ''),
                'views': announcement.get('views', '')
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
def test_bcci_scraper(pages=3):
    """BCCI 스크래퍼 테스트"""
    import os
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    scraper = EnhancedBCCIScraper()
    output_dir = "output/bcci"
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"BCCI 스크래퍼 테스트 시작 - {pages}페이지")
    scraper.scrape_pages(max_pages=pages, output_base=output_dir)
    logger.info("BCCI 스크래퍼 테스트 완료")

if __name__ == "__main__":
    test_bcci_scraper(3)