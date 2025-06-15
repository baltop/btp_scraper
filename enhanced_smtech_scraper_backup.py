#!/usr/bin/env python3
"""
SMTECH 사이트 전용 Enhanced 스크래퍼

분석 완료된 내용:
1. 파일 다운로드 메커니즘: cfn_AtchFileDownload(fileId, context, target)
2. 실제 다운로드 URL: /front/comn/AtchFileDownload.do (GET/POST 모두 지원)
3. 대안 URL: /front/comn/fileDownload.do (GET/POST 모두 지원)
4. 파라미터: atchFileId
5. 첨부파일과 제출서류의 구분:
   - 첨부파일: 실제 파일 ID가 있는 JavaScript 함수 호출
   - 제출서류: #list로 연결된 템플릿 파일들 (다운로드 불가)
"""

from enhanced_base_scraper import StandardTableScraper
import requests
from bs4 import BeautifulSoup
import re
import os
from urllib.parse import urljoin, unquote
import logging

logger = logging.getLogger(__name__)

class EnhancedSmtechScraper(StandardTableScraper):
    """SMTECH 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.smtech.go.kr"
        self.list_url = "https://www.smtech.go.kr/front/ifg/no/notice02_list.do"
        self.verify_ssl = False  # SMTECH는 SSL 인증서 문제 있음
        self.default_encoding = 'utf-8'
        
        # 다운로드 URL 패턴 (우선순위 순)
        self.download_urls = [
            "/front/comn/AtchFileDownload.do",
            "/front/comn/fileDownload.do"
        ]
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성"""
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}?pageIndex={page_num}"
    
    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱"""
        logger.info("SMTECH 목록 페이지 파싱 시작")
        
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 테이블 찾기
        table = soup.find('table')
        if not table:
            logger.warning("테이블을 찾을 수 없습니다")
            return announcements
        
        # 데이터 행들 찾기 (헤더 제외)
        tbody = table.find('tbody')
        if not tbody:
            logger.warning("tbody를 찾을 수 없습니다")
            return announcements
        
        rows = tbody.find_all('tr')
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for i, row in enumerate(rows):
            try:
                cells = row.find_all('td')
                if len(cells) < 6:
                    continue
                
                # 링크 요소 찾기
                title_cell = cells[2]  # 제목 컬럼
                link = title_cell.find('a')
                if not link:
                    continue
                
                title = link.get_text().strip()
                detail_url = link.get('href', '')
                
                # 상대 URL을 절대 URL로 변환
                if detail_url.startswith('/'):
                    detail_url = urljoin(self.base_url, detail_url)
                
                announcement = {
                    'title': title,
                    'detail_url': detail_url,
                    'business_name': cells[1].get_text().strip(),
                    'period': cells[3].get_text().strip(),
                    'date': cells[4].get_text().strip(),
                    'status': cells[5].get_text().strip()
                }
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱 완료: {title}")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> dict:
        """상세 페이지 파싱"""
        logger.info("SMTECH 상세 페이지 파싱 시작")
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 메타 정보 추출
        result = {
            'content': '',
            'attachments': []
        }
        
        # 테이블에서 정보 추출
        table = soup.find('table')
        if table:
            rows = table.find_all('tr')
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    header = cells[0].get_text().strip()
                    
                    if header == '내용':
                        # 본문 내용 추출
                        content_cell = cells[1]
                        result['content'] = self._html_to_markdown(str(content_cell))
                    
                    elif header == '첨부파일':
                        # 첨부파일 추출
                        result['attachments'] = self._extract_attachments(cells[1])
        
        logger.info(f"상세 페이지 파싱 완료: 첨부파일 {len(result['attachments'])}개")
        return result
    
    def _extract_attachments(self, attachment_cell) -> list:
        """첨부파일 정보 추출"""
        attachments = []
        
        # JavaScript 함수 호출이 있는 링크만 찾기
        links = attachment_cell.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '')
            text = link.get_text().strip()
            
            # cfn_AtchFileDownload 함수 호출인지 확인
            if 'cfn_AtchFileDownload' in href:
                # 파일 ID 추출
                match = re.search(r"cfn_AtchFileDownload\(['\"]([^'\"]+)['\"]", href)
                if match:
                    file_id = match.group(1)
                    
                    attachment = {
                        'filename': text,
                        'file_id': file_id,
                        'download_url': None  # 나중에 실제 다운로드 시 설정
                    }
                    
                    attachments.append(attachment)
                    logger.debug(f"첨부파일 발견: {text} (ID: {file_id})")
            
            elif href == '#list':
                # 제출서류 템플릿 파일 (다운로드 불가)
                logger.debug(f"제출서류 템플릿: {text} (다운로드 불가)")
        
        return attachments
    
    def _html_to_markdown(self, html_content: str) -> str:
        """HTML을 Markdown으로 변환"""
        try:
            from html2text import HTML2Text
            h = HTML2Text()
            h.ignore_links = False
            h.ignore_images = False
            return h.handle(html_content)
        except ImportError:
            # html2text가 없으면 기본 텍스트 추출
            soup = BeautifulSoup(html_content, 'html.parser')
            return soup.get_text().strip()
    
    def download_file(self, file_info: dict, save_dir: str) -> bool:
        """파일 다운로드"""
        file_id = file_info.get('file_id')
        if not file_id:
            logger.error(f"파일 ID가 없습니다: {file_info}")
            return False
        
        logger.info(f"파일 다운로드 시작: {file_info['filename']}")
        
        # 여러 다운로드 URL 시도
        for download_path in self.download_urls:
            full_url = urljoin(self.base_url, download_path)
            
            # GET 방식 시도
            try:
                response = self.session.get(
                    f"{full_url}?atchFileId={file_id}",
                    verify=self.verify_ssl,
                    stream=True
                )
                
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '')
                    if 'application' in content_type:
                        # 파일 다운로드 성공
                        save_path = self._save_file(response, file_info, save_dir)
                        if save_path:
                            logger.info(f"다운로드 완료: {save_path}")
                            return True
                
            except Exception as e:
                logger.debug(f"GET 방식 실패 {full_url}: {e}")
            
            # POST 방식 시도
            try:
                response = self.session.post(
                    full_url,
                    data={'atchFileId': file_id},
                    verify=self.verify_ssl,
                    stream=True
                )
                
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '')
                    if 'application' in content_type:
                        # 파일 다운로드 성공
                        save_path = self._save_file(response, file_info, save_dir)
                        if save_path:
                            logger.info(f"다운로드 완료: {save_path}")
                            return True
                
            except Exception as e:
                logger.debug(f"POST 방식 실패 {full_url}: {e}")
        
        logger.error(f"파일 다운로드 실패: {file_info['filename']}")
        return False
    
    def _save_file(self, response: requests.Response, file_info: dict, save_dir: str) -> str:
        """파일 저장"""
        # 파일명 추출
        filename = self._extract_filename(response, file_info['filename'])
        
        # 저장 경로 생성
        save_path = os.path.join(save_dir, filename)
        
        # 파일 저장
        try:
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(save_path)
            logger.info(f"파일 저장 완료: {save_path} ({file_size:,} bytes)")
            return save_path
            
        except Exception as e:
            logger.error(f"파일 저장 실패: {e}")
            return None
    
    def _extract_filename(self, response: requests.Response, default_filename: str) -> str:
        """Content-Disposition 헤더에서 파일명 추출"""
        content_disposition = response.headers.get('content-disposition', '')
        
        if content_disposition:
            # filename 파라미터 찾기
            filename_match = re.search(r'filename=([^;]+)', content_disposition)
            if filename_match:
                filename = filename_match.group(1).strip().strip('"')
                
                # URL 디코딩
                try:
                    filename = unquote(filename)
                    # 파일명이 올바르게 디코딩되었으면 사용
                    if filename and not filename.isspace():
                        return self.sanitize_filename(filename)
                except:
                    pass
        
        # Content-Disposition에서 추출 실패 시 기본 파일명 사용
        return self.sanitize_filename(default_filename)
    
    def scrape_announcements(self, max_pages: int = 1) -> list:
        """공고 목록 수집"""
        logger.info(f"SMTECH 공고 수집 시작 (최대 {max_pages}페이지)")
        
        all_announcements = []
        
        for page_num in range(1, max_pages + 1):
            try:
                logger.info(f"페이지 {page_num} 처리 중...")
                
                # 페이지 URL 생성
                url = self.get_list_url(page_num)
                
                # HTML 가져오기
                response = self.session.get(url, verify=self.verify_ssl)
                response.encoding = self.default_encoding
                
                # 공고 목록 파싱
                announcements = self.parse_list_page(response.text)
                
                if not announcements:
                    logger.warning(f"페이지 {page_num}에서 공고를 찾을 수 없습니다")
                    break
                
                all_announcements.extend(announcements)
                logger.info(f"페이지 {page_num}: {len(announcements)}개 공고")
                
                # 페이지 간 지연
                if page_num < max_pages:
                    time.sleep(self.delay_between_pages)
                    
            except Exception as e:
                logger.error(f"페이지 {page_num} 처리 중 오류: {e}")
                break
        
        logger.info(f"총 {len(all_announcements)}개 공고 수집 완료")
        return all_announcements
    
    def scrape_detail_page(self, url: str) -> dict:
        """상세 페이지 수집"""
        logger.info(f"상세 페이지 수집: {url}")
        
        try:
            response = self.session.get(url, verify=self.verify_ssl)
            response.encoding = self.default_encoding
            
            result = self.parse_detail_page(response.text)
            result['url'] = url
            
            return result
            
        except Exception as e:
            logger.error(f"상세 페이지 수집 실패 {url}: {e}")
            return {'content': '', 'attachments': [], 'url': url}

# 하위 호환성을 위한 별칭
SmtechScraper = EnhancedSmtechScraper

def test_smtech_scraper():
    """SMTECH 스크래퍼 테스트"""
    print("=== SMTECH Enhanced 스크래퍼 테스트 ===")
    
    scraper = EnhancedSmtechScraper()
    announcements = []
    
    # 1. 목록 페이지 테스트
    print("\n1. 목록 페이지 파싱 테스트")
    try:
        announcements = scraper.scrape_announcements(max_pages=1)
        print(f"공고 수집 완료: {len(announcements)}개")
        
        for i, ann in enumerate(announcements[:3], 1):
            print(f"{i}. {ann['title']}")
            print(f"   사업명: {ann['business_name']}")
            print(f"   기간: {ann['period']}")
            print(f"   상태: {ann['status']}")
    
    except Exception as e:
        print(f"목록 페이지 테스트 실패: {e}")
    
    # 2. 상세 페이지 및 파일 다운로드 테스트
    if announcements:
        print(f"\n2. 상세 페이지 테스트: {announcements[0]['title']}")
        try:
            detail_data = scraper.scrape_detail_page(announcements[0]['detail_url'])
            print(f"첨부파일 수: {len(detail_data['attachments'])}")
            
            for att in detail_data['attachments']:
                print(f"  - {att['filename']} (ID: {att['file_id']})")
            
            # 첫 번째 파일 다운로드 테스트
            if detail_data['attachments']:
                print(f"\n3. 파일 다운로드 테스트")
                save_dir = "./test_downloads"
                os.makedirs(save_dir, exist_ok=True)
                
                first_file = detail_data['attachments'][0]
                success = scraper.download_file(first_file, save_dir)
                print(f"다운로드 결과: {'성공' if success else '실패'}")
        
        except Exception as e:
            print(f"상세 페이지 테스트 실패: {e}")

if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # SSL 경고 무시
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    test_smtech_scraper()