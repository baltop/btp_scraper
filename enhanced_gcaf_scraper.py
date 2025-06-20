"""
Enhanced GCAF (경남문화예술진흥원) 스크래퍼 - 향상된 버전
사업공고·입찰 게시판 전용 스크래퍼
"""

import os
import re
import time
import logging
from urllib.parse import urljoin, unquote
from bs4 import BeautifulSoup
from enhanced_base_scraper import StandardTableScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gcaf_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EnhancedGCAFScraper(StandardTableScraper):
    """GCAF 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.gcaf.or.kr"
        self.list_url = "https://www.gcaf.or.kr/bbs/board.php?bo_table=sub3_7"
        
        # 사이트별 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        
        # 중복 검사 설정
        self.duplicate_threshold = 3
        
        logger.info("Enhanced GCAF 스크래퍼 초기화 완료")
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성"""
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&page={page_num}"
    
    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 테이블 찾기
        table = soup.find('table')
        if not table:
            logger.error("테이블을 찾을 수 없습니다")
            return []
        
        tbody = table.find('tbody')
        if not tbody:
            tbody = table
        
        logger.info(f"테이블에서 {len(tbody.find_all('tr'))}개 행 발견")
        
        for row in tbody.find_all('tr'):
            try:
                cells = row.find_all('td')
                if len(cells) < 5:
                    continue
                
                # 제목 셀 추출 (두 번째 컬럼)
                title_cell = cells[1]
                link_elem = title_cell.find('a')
                
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                href = link_elem.get('href', '')
                
                if not href:
                    continue
                
                # 절대 URL로 변환
                detail_url = urljoin(self.base_url, href)
                
                # 날짜 추출 (마지막 컬럼)
                date_cell = cells[-1]
                date_text = date_cell.get_text(strip=True)
                
                # 조회수 추출 (마지막에서 두 번째 컬럼)
                views_cell = cells[-2]
                views_text = views_cell.get_text(strip=True)
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'date': date_text,
                    'views': views_text
                }
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱 완료: {title[:50]}...")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str, announcement_url: str) -> dict:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 제목 추출
        title_elem = soup.find('h1', {'id': 'bo_v_title'}) or soup.find('h2', {'id': 'bo_v_title'})
        if not title_elem:
            title_elem = soup.find('span', {'id': 'bo_v_title'})
        
        title = title_elem.get_text(strip=True) if title_elem else "제목 없음"
        
        # 본문 내용 추출
        content_area = soup.find('div', {'id': 'bo_v_con'})
        if not content_area:
            content_area = soup.find('div', class_='bo_v_con')
        
        content = ""
        if content_area:
            # 불필요한 스크립트 제거
            for script in content_area.find_all('script'):
                script.decompose()
            
            content = content_area.get_text(separator='\n', strip=True)
            logger.debug(f"본문 추출 완료: {len(content)} 문자")
        else:
            logger.warning("본문 영역을 찾을 수 없습니다")
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup)
        
        return {
            'title': title,
            'content': content,
            'attachments': attachments,
            'url': announcement_url
        }
    
    def _extract_attachments(self, soup: BeautifulSoup) -> list:
        """첨부파일 추출"""
        attachments = []
        
        # 첨부파일 영역 찾기 - section 태그와 div 태그 모두 확인
        file_area = soup.find('section', {'id': 'bo_v_file'})
        if not file_area:
            file_area = soup.find('div', {'id': 'bo_v_file'})
        if not file_area:
            file_area = soup.find('div', class_='bo_v_file')
        
        if file_area:
            logger.debug("첨부파일 영역 발견")
            
            # 파일 링크 추출 - ul > li > a 구조에서 링크 찾기
            file_links = file_area.find_all('a', class_='view_file_download')
            if not file_links:
                # 클래스 없는 경우도 확인
                file_links = file_area.find_all('a')
                
            for link in file_links:
                href = link.get('href', '')
                if href and 'download.php' in href:
                    # 절대 URL로 변환
                    file_url = urljoin(self.base_url, href)
                    
                    # 파일명 추출 - strong 태그 안의 텍스트 또는 링크 텍스트
                    strong_elem = link.find('strong')
                    if strong_elem:
                        file_name = strong_elem.get_text(strip=True)
                    else:
                        file_name = link.get_text(strip=True)
                    
                    # 파일명 정리 (파일 크기 정보 제거)
                    file_name = re.sub(r'\s*\([0-9.]+[KMG]?\)\s*$', '', file_name)
                    
                    if file_name:
                        attachments.append({
                            'url': file_url,
                            'name': file_name
                        })
                        logger.debug(f"첨부파일 발견: {file_name} -> {file_url}")
        else:
            logger.debug("첨부파일 영역을 찾을 수 없습니다")
        
        logger.info(f"{len(attachments)}개 첨부파일 발견")
        return attachments
    
    def download_file(self, url: str, save_path: str) -> bool:
        """파일 다운로드"""
        try:
            response = self.session.get(url, timeout=self.timeout, verify=self.verify_ssl)
            response.raise_for_status()
            
            # 파일 저장
            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            file_size = len(response.content)
            logger.info(f"다운로드 완료: {save_path} ({file_size:,} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"파일 다운로드 실패 {url}: {e}")
            return False
    
    def scrape_pages(self, max_pages: int = 3, output_base: str = "output/gcaf") -> None:
        """페이지별 스크래핑 실행"""
        logger.info(f"GCAF 스크래퍼 시작 - 최대 {max_pages}페이지")
        
        # 출력 디렉토리 생성
        os.makedirs(output_base, exist_ok=True)
        
        # 처리된 제목 목록 로드
        self.load_processed_titles(output_base)
        
        for page_num in range(1, max_pages + 1):
            logger.info(f"=== 페이지 {page_num} 처리 시작 ===")
            
            # 목록 페이지 가져오기
            list_url = self.get_list_url(page_num)
            logger.info(f"목록 페이지 URL: {list_url}")
            
            try:
                response = self.session.get(list_url, timeout=self.timeout, verify=self.verify_ssl)
                response.raise_for_status()
                
                # 공고 목록 파싱
                announcements = self.parse_list_page(response.text)
                
                # 중복 검사 및 필터링
                new_announcements, should_stop = self.filter_new_announcements(announcements)
                
                if not new_announcements:
                    logger.info("새로운 공고가 없습니다")
                    if should_stop:
                        logger.info("중복 임계값 도달로 스크래핑 중단")
                        break
                    continue
                
                # 각 공고 처리
                for idx, announcement in enumerate(new_announcements, 1):
                    logger.info(f"공고 {idx}/{len(new_announcements)} 처리: {announcement['title'][:50]}...")
                    
                    # 상세 페이지 가져오기
                    detail_response = self.session.get(announcement['url'], timeout=self.timeout, verify=self.verify_ssl)
                    detail_response.raise_for_status()
                    
                    # 상세 페이지 파싱
                    detail_data = self.parse_detail_page(detail_response.text, announcement['url'])
                    
                    # 저장 디렉토리 생성
                    safe_title = self.sanitize_filename(detail_data['title'])
                    folder_name = f"{idx:03d}_{safe_title}"
                    save_dir = os.path.join(output_base, folder_name)
                    os.makedirs(save_dir, exist_ok=True)
                    
                    # 본문 저장
                    content_path = os.path.join(save_dir, 'content.md')
                    with open(content_path, 'w', encoding='utf-8') as f:
                        f.write(f"# {detail_data['title']}\n\n")
                        f.write(f"**게시일**: {announcement.get('date', 'N/A')}\n")
                        f.write(f"**조회수**: {announcement.get('views', 'N/A')}\n")
                        f.write(f"**원본 URL**: {detail_data['url']}\n\n")
                        f.write(detail_data['content'])
                    
                    # 첨부파일 다운로드
                    if detail_data['attachments']:
                        attachments_dir = os.path.join(save_dir, 'attachments')
                        os.makedirs(attachments_dir, exist_ok=True)
                        
                        for att_idx, attachment in enumerate(detail_data['attachments'], 1):
                            att_name = attachment['name'] or f"attachment_{att_idx}"
                            safe_att_name = self.sanitize_filename(att_name)
                            att_path = os.path.join(attachments_dir, safe_att_name)
                            
                            if self.download_file(attachment['url'], att_path):
                                logger.info(f"첨부파일 다운로드 성공: {safe_att_name}")
                            else:
                                logger.error(f"첨부파일 다운로드 실패: {safe_att_name}")
                    
                    # 제목 해시 저장
                    self.add_processed_title(detail_data['title'])
                    
                    # 요청 간격 조절
                    time.sleep(self.delay_between_requests)
                
                if should_stop:
                    logger.info("중복 임계값 도달로 스크래핑 중단")
                    break
                    
            except Exception as e:
                logger.error(f"페이지 {page_num} 처리 중 오류: {e}")
                continue
            
            # 페이지 간 대기
            time.sleep(self.delay_between_requests)
        
        # 처리된 제목 저장
        self.save_processed_titles()
        
        logger.info("GCAF 스크래퍼 완료")

# 하위 호환성을 위한 별칭
GCAFScraper = EnhancedGCAFScraper

if __name__ == "__main__":
    scraper = EnhancedGCAFScraper()
    scraper.scrape_pages(max_pages=3, output_base="output/gcaf")