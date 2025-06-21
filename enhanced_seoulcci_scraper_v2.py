# -*- coding: utf-8 -*-
"""
서울상공회의소(SeoulCCI) 스크래퍼 - Enhanced 버전 V2 (POST 기반)
"""

import re
import os
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, quote
from enhanced_base_scraper import StandardTableScraper
import logging

logger = logging.getLogger(__name__)

class EnhancedSeoulCCIScraper(StandardTableScraper):
    """서울상공회의소 공지사항 스크래퍼 - POST 기반 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.korcham.net"
        self.list_url = "https://www.korcham.net/nCham/Service/Kcci/appl/KcciNoticeList.asp"
        self.detail_url = "https://www.korcham.net/nCham/Service/Kcci/appl/KcciNoticeDetail.asp"
        self.download_url = "https://www.korcham.net/nCham/Service/include/Download.asp"
        
        # SeoulCCI 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'euc-kr'  # ASP 사이트는 주로 EUC-KR
        self.timeout = 30
        self.delay_between_requests = 2
        
        # 세션 설정 (중요: POST 요청을 위한 세션 유지)
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # 전체 공고 인덱스 (페이지별로 계속 증가)
        self.global_index = 0
        
    def get_list_page(self, page_num: int) -> str:
        """페이지별 HTML 가져오기 (POST 요청 사용)"""
        if page_num == 1:
            # 첫 페이지는 GET 요청
            response = self.session.get(self.list_url)
        else:
            # 2페이지부터는 POST 요청 (JavaScript page() 함수 모방)
            form_data = {
                'nPageNo': str(page_num),
                'nKey': ''
            }
            response = self.session.post(self.list_url, data=form_data)
        
        if response:
            response.encoding = self.default_encoding
            return response.text
        return ""
    
    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 테이블 찾기 - 다양한 방법으로 시도
        tables = soup.find_all('table')
        target_table = None
        
        for table in tables:
            # caption이 '목록'인 테이블 찾기
            caption = table.find('caption')
            if caption and '목록' in caption.get_text():
                target_table = table
                break
            
            # 헤더에 '번호', '제목' 등이 있는 테이블 찾기
            thead = table.find('thead')
            if thead:
                header_text = thead.get_text()
                if '번호' in header_text and '제목' in header_text:
                    target_table = table
                    break
        
        if not target_table:
            logger.warning("목록 테이블을 찾을 수 없습니다.")
            return []
        
        tbody = target_table.find('tbody')
        if not tbody:
            tbody = target_table
            
        rows = tbody.find_all('tr')
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 4:  # 번호, 제목, 담당부서, 등록일
                    continue
                
                # 번호 (첫 번째 셀)
                number = cells[0].get_text(strip=True)
                if not number or not number.replace(',', '').isdigit():
                    continue
                
                # 제목 셀 (두 번째 셀)
                title_cell = cells[1]
                link_elem = title_cell.find('a')
                
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                if not title:
                    continue
                
                # href에서 goDetail ID 추출 (javascript:goDetail('ID') 패턴)
                href = link_elem.get('href', '')
                article_id = None
                
                if href and 'goDetail' in href:
                    match = re.search(r"javascript:goDetail\s*\(\s*['\"]([^'\"]+)['\"]", href)
                    if match:
                        article_id = match.group(1)
                
                if not article_id:
                    logger.warning(f"기사 ID를 찾을 수 없습니다: {title}")
                    continue
                
                # 담당부서 (세 번째 셀)
                department_cell = cells[2]
                department = department_cell.get_text(strip=True)
                
                # 등록일 (네 번째 셀)
                date_cell = cells[3]
                date = date_cell.get_text(strip=True)
                
                # 전체 인덱스 증가
                self.global_index += 1
                
                announcement = {
                    'title': title,
                    'url': f"POST:{self.detail_url}",  # POST 요청임을 표시
                    'date': date,
                    'number': number,
                    'department': department,
                    'article_id': article_id,
                    'global_index': self.global_index  # 전체 인덱스 추가
                }
                
                announcements.append(announcement)
                logger.debug(f"공고 추가: {title} (인덱스: {self.global_index})")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"총 {len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def get_detail_page(self, article_id: str) -> str:
        """POST 요청으로 상세 페이지 가져오기"""
        try:
            # JavaScript goDetail() 함수 모방
            form_data = {
                'nKey': article_id,
                'nPageNo': '1'
            }
            
            response = self.session.post(self.detail_url, data=form_data)
            if response:
                response.encoding = self.default_encoding
                logger.info(f"상세 페이지 HTML 길이: {len(response.text)}")
                return response.text
            else:
                logger.error(f"상세 페이지 가져오기 실패: HTTP {response.status_code}")
                return ""
                
        except Exception as e:
            logger.error(f"상세 페이지 POST 요청 실패: {e}")
            return ""
    
    def parse_detail_page(self, html_content: str) -> dict:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 내용 찾기
        content = ""
        title = ""
        
        # 제목 추출
        title_elem = soup.find('h3')
        if title_elem:
            title = title_elem.get_text(strip=True)
        
        # 본문 내용 추출 - 테이블 구조에서 찾기
        content_table = soup.find('table')
        if content_table:
            # 테이블의 모든 행을 확인하여 긴 내용을 가진 셀 찾기
            rows = content_table.find_all('tr')
            for row in rows:
                cells = row.find_all(['th', 'td'])
                for cell in cells:
                    cell_text = cell.get_text(strip=True)
                    # 긴 내용을 가진 셀을 본문으로 간주
                    if len(cell_text) > 200:  # 200자 이상인 경우
                        # HTML을 마크다운으로 변환
                        paragraphs = cell.find_all(['p', 'div', 'br'])
                        if paragraphs:
                            content_parts = []
                            for p in cell.find_all(['p', 'div']):
                                p_text = p.get_text(strip=True)
                                if p_text and len(p_text) > 10:
                                    content_parts.append(p_text)
                            content = '\n\n'.join(content_parts)
                        else:
                            content = cell_text
                        
                        # 불필요한 공백 정리
                        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
                        break
                if content:
                    break
        
        # 첨부파일 찾기 - javascript:down() 패턴
        attachments = []
        download_links = soup.find_all('a', href=re.compile(r'javascript:down'))
        
        for link in download_links:
            href = link.get('href', '')
            filename = link.get_text(strip=True)
            
            if href and filename:
                # down('filename','dirname') 패턴에서 파라미터 추출
                match = re.search(r"down\s*\(\s*['\"]([^'\"]+)['\"][,\s]*['\"]([^'\"]*)['\"]", href)
                if match:
                    file_name = match.group(1)
                    dirname = match.group(2)
                    
                    # 다운로드 URL 구성
                    download_url = f"{self.download_url}?filename={quote(file_name)}&dirname={dirname}"
                    
                    attachment = {
                        'filename': file_name,
                        'url': download_url,
                        'dirname': dirname,
                        'original_link': href
                    }
                    attachments.append(attachment)
                    logger.info(f"첨부파일 발견: {file_name}")
        
        # 본문이 비어있으면 기본 텍스트 추가
        if not content.strip():
            content = "## 공고 내용\n\n공고 내용을 확인하려면 첨부파일을 다운로드하여 확인하세요.\n\n"
        else:
            # 마크다운 형태로 정리
            content = f"## 공고 내용\n\n{content}\n\n"
        
        result = {
            'title': title,
            'content': content,
            'attachments': attachments
        }
        
        logger.info(f"상세 페이지 파싱 완료 - 제목: {title}, 내용: {len(content)}자, 첨부파일: {len(attachments)}개")
        return result
    
    def download_file(self, attachment: dict, save_dir: str) -> bool:
        """첨부파일 다운로드 (세션 및 Referer 헤더 포함)"""
        try:
            filename = attachment['filename']
            download_url = attachment['url']
            
            # 안전한 파일명 생성
            safe_filename = self.sanitize_filename(filename)
            file_path = os.path.join(save_dir, safe_filename)
            
            # 다운로드 헤더 설정 (Referer 추가)
            download_headers = {
                'Referer': self.detail_url,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin'
            }
            
            # 세션을 유지하면서 파일 다운로드
            response = self.session.get(download_url, headers=download_headers, stream=True)
            
            # 404나 403 에러는 무시하고 500만 재시도
            if response.status_code == 500:
                logger.warning(f"서버 에러 500 - 다른 방법으로 재시도: {filename}")
                # dirname 파라미터 없이 시도
                clean_url = download_url.split('&dirname=')[0]
                response = self.session.get(clean_url, headers=download_headers, stream=True)
            
            response.raise_for_status()
            
            # Content-Disposition 헤더에서 실제 파일명 추출 시도
            content_disposition = response.headers.get('Content-Disposition', '')
            if content_disposition:
                # 다양한 인코딩 방식으로 파일명 추출 시도
                filename_match = re.search(r'filename[^;=\n]*=([\'"]*)(.*?)\1', content_disposition)
                if filename_match:
                    extracted_filename = filename_match.group(2)
                    # EUC-KR 디코딩 시도
                    try:
                        if extracted_filename:
                            decoded_filename = extracted_filename.encode('latin-1').decode('euc-kr')
                            safe_filename = self.sanitize_filename(decoded_filename)
                            file_path = os.path.join(save_dir, safe_filename)
                    except:
                        pass
            
            # 파일 저장
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            file_size = os.path.getsize(file_path)
            logger.info(f"파일 다운로드 완료: {safe_filename} ({file_size:,} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"파일 다운로드 실패 ({filename}): {e}")
            return False
    
    def process_announcement(self, announcement: dict, output_base: str = 'output'):
        """개별 공고 처리"""
        global_index = announcement.get('global_index', 0)
        logger.info(f"공고 처리 중 {global_index}: {announcement['title']}")
        
        # 폴더 생성 (전체 인덱스 사용)
        folder_title = self.sanitize_filename(announcement['title'])[:100]
        folder_name = f"{global_index:03d}_{folder_title}"
        
        if len(folder_name) > 200:
            folder_title = folder_title[:195]
            folder_name = f"{global_index:03d}_{folder_title}"
        
        folder_path = os.path.join(output_base, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        # POST 요청으로 상세 페이지 가져오기
        article_id = announcement.get('article_id')
        if not article_id:
            logger.error(f"기사 ID가 없습니다: {announcement['title']}")
            return
        
        html_content = self.get_detail_page(article_id)
        if not html_content:
            logger.error(f"상세 페이지 가져오기 실패: {announcement['title']}")
            return
        
        # 상세 내용 파싱
        try:
            detail = self.parse_detail_page(html_content)
            logger.info(f"상세 페이지 파싱 완료 - 내용길이: {len(detail['content'])}, 첨부파일: {len(detail['attachments'])}개")
            
        except Exception as e:
            logger.error(f"상세 페이지 파싱 실패: {e}")
            # 기본 콘텐츠로라도 저장
            detail = {
                'title': announcement.get('title', ''),
                'content': "## 공고 내용\n\n상세 내용을 가져올 수 없습니다. 원본 페이지를 확인해주세요.\n\n",
                'attachments': []
            }
        
        # 메타 정보 생성
        meta_info = self._create_meta_info(announcement)
        
        # 본문 저장
        content_path = os.path.join(folder_path, 'content.md')
        with open(content_path, 'w', encoding='utf-8') as f:
            f.write(meta_info + detail['content'])
        
        logger.info(f"내용 저장 완료: {content_path}")
        
        # 첨부파일 다운로드
        if detail['attachments']:
            logger.info(f"{len(detail['attachments'])}개 첨부파일 다운로드 시작")
            for attachment in detail['attachments']:
                success = self.download_file(attachment, folder_path)
                if success:
                    logger.info(f"첨부파일 다운로드 성공: {attachment['filename']}")
                else:
                    logger.warning(f"첨부파일 다운로드 실패: {attachment['filename']}")
                
                # 다운로드 간 대기
                time.sleep(1)
        
        # 처리된 제목으로 추가
        self.add_processed_title(announcement['title'])
        
        # 요청 간 대기
        if self.delay_between_requests > 0:
            time.sleep(self.delay_between_requests)
    
    def scrape_pages(self, max_pages: int = 3, output_base: str = 'output') -> bool:
        """페이지별 스크래핑 실행"""
        logger.info(f"스크래핑 시작: 최대 {max_pages}페이지")
        
        # 기존 처리된 공고 로드
        processed_count = self.load_processed_titles()
        if processed_count is None:
            processed_count = 0
        logger.info(f"기존 처리된 공고 {processed_count}개 로드")
        
        # 전체 인덱스 초기화
        self.global_index = 0
        
        try:
            for page_num in range(1, max_pages + 1):
                logger.info(f"페이지 {page_num} 처리 중")
                
                # 페이지 HTML 가져오기 (POST 요청)
                html_content = self.get_list_page(page_num)
                if not html_content:
                    logger.error(f"페이지 {page_num} HTML 가져오기 실패")
                    continue
                
                # 목록 파싱
                announcements = self.parse_list_page(html_content)
                
                if not announcements:
                    logger.warning(f"페이지 {page_num}에서 공고를 찾을 수 없습니다.")
                    continue
                
                logger.info(f"페이지 {page_num}에서 {len(announcements)}개 공고 발견")
                
                # 중복 체크
                new_announcements = []
                consecutive_duplicates = 0
                
                for announcement in announcements:
                    if self.is_title_processed(announcement['title']):
                        consecutive_duplicates += 1
                        logger.debug(f"중복 공고 건너뜀: {announcement['title']}")
                        if consecutive_duplicates >= 3:
                            logger.info("중복 공고 3개 연속 발견 - 조기 종료 신호")
                            break
                    else:
                        consecutive_duplicates = 0
                        new_announcements.append(announcement)
                
                logger.info(f"전체 {len(announcements)}개 중 새로운 공고 {len(new_announcements)}개, 이전 실행 중복 {consecutive_duplicates}개 발견")
                
                # 조기 종료 조건
                if consecutive_duplicates >= 3:
                    logger.info("중복 공고 3개 연속 발견으로 조기 종료")
                    break
                
                # 새로운 공고 처리
                for announcement in new_announcements:
                    try:
                        self.process_announcement(announcement, output_base)
                    except Exception as e:
                        logger.error(f"공고 처리 실패 ({announcement['title']}): {e}")
                        continue
                
                # 페이지 간 대기
                time.sleep(self.delay_between_requests)
                
        except Exception as e:
            logger.error(f"스크래핑 중 오류: {e}")
            return False
        
        # 처리된 제목 저장
        saved_count = self.save_processed_titles()
        if saved_count is None:
            saved_count = 0
        logger.info(f"처리된 제목 {saved_count}개 저장 완료 (이전: {processed_count}, 현재 세션: {saved_count - processed_count})")
        
        total_processed = saved_count - processed_count
        logger.info(f"스크래핑 완료: 총 {total_processed}개 새로운 공고 처리")
        
        return True

# 테스트용 함수
def test_seoulcci_scraper_v2(pages=3):
    """SeoulCCI 스크래퍼 V2 테스트"""
    import os
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    scraper = EnhancedSeoulCCIScraper()
    output_dir = "output/seoulcci_v2"
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"SeoulCCI 스크래퍼 V2 테스트 시작 - {pages}페이지")
    scraper.scrape_pages(max_pages=pages, output_base=output_dir)
    logger.info("SeoulCCI 스크래퍼 V2 테스트 완료")

if __name__ == "__main__":
    test_seoulcci_scraper_v2(3)