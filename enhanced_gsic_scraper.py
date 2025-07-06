# -*- coding: utf-8 -*-
"""
경기도경제과학진흥원(GSIC) 스크래퍼 - Enhanced 버전
URL: https://gsic.or.kr/home/kor/M837392473/board.do
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, parse_qs, urlparse
import re
import os
import time
import logging
from enhanced_base_scraper import StandardTableScraper

logger = logging.getLogger(__name__)

class EnhancedGsicScraper(StandardTableScraper):
    """경기도경제과학진흥원 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://gsic.or.kr"
        self.list_url = "https://gsic.or.kr/home/kor/M837392473/board.do?deleteAt=N&idx=&eSearchValue3=&searchValue1=0&searchKeyword=&pageIndex=1"
        
        # GSIC 특화 설정
        self.verify_ssl = False  # SSL 인증서 문제로 비활성화
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 2
        
        # 세션 설정
        self.session.headers.update({
            'Referer': self.base_url,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성"""
        if page_num == 1:
            return self.list_url
        else:
            # pageIndex를 변경
            return self.list_url.replace('pageIndex=1', f'pageIndex={page_num}')
    
    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 메인 테이블 찾기
        table = soup.find('table', class_='table_basics_area')
        if not table:
            logger.warning("메인 테이블을 찾을 수 없습니다")
            return announcements
        
        rows = table.find_all('tr')[1:]  # 헤더 제외
        logger.info(f"총 {len(rows)}개 행 발견")
        
        for i, row in enumerate(rows):
            try:
                cells = row.find_all('td')
                if len(cells) < 6:
                    continue
                
                # 번호 (첫 번째 셀) - "주요", "공지" 등 처리
                number_cell = cells[0]
                number = number_cell.get_text(strip=True)
                
                # 구분 (두 번째 셀) - "공지" 등
                category_cell = cells[1]
                category = category_cell.get_text(strip=True)
                
                # 제목 (세 번째 셀)
                title_cell = cells[2]
                title_link = title_cell.find('a')
                if not title_link:
                    continue
                
                title = title_link.get_text(strip=True)
                if not title:
                    continue
                
                # onclick에서 ID 추출
                onclick = title_link.get('onclick', '')
                id_match = re.search(r"fn_edit\('detail',\s*'([^']+)'", onclick)
                if not id_match:
                    logger.warning(f"ID를 추출할 수 없습니다: {onclick}")
                    continue
                
                detail_id = id_match.group(1)
                
                # 첨부파일 (네 번째 셀)
                attachment_cell = cells[3]
                has_attachment = attachment_cell.get_text(strip=True) != '-'
                
                # 등록일 (다섯 번째 셀)
                date_cell = cells[4]
                date = date_cell.get_text(strip=True)
                
                # 조회수 (여섯 번째 셀)
                views_cell = cells[5]
                views = views_cell.get_text(strip=True)
                
                # 상세 페이지 URL 구성 (JavaScript 함수 기반)
                detail_url = f"{self.base_url}/home/kor/M837392473/board.do?deleteAt=N&act=detail&idx={detail_id}&eSearchValue3=&searchValue1=0&searchKeyword=&pageIndex=1"
                
                announcement = {
                    'number': number,
                    'category': category,
                    'title': title,
                    'url': detail_url,
                    'date': date,
                    'views': views,
                    'has_attachment': has_attachment,
                    'detail_id': detail_id
                }
                
                announcements.append(announcement)
                logger.info(f"공고 추가: [{number}] {title}")
                
            except Exception as e:
                logger.error(f"행 파싱 오류 (행 {i+1}): {e}")
                continue
        
        logger.info(f"총 {len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> dict:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 다양한 방법으로 내용 영역 찾기
        content_area = None
        content_selectors = [
            'div.contents',
            'div.content',
            'div.detail_content',
            'div#contents',
            'div#content',
            '.board_view',
            '.detail_view'
        ]
        
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                break
        
        if not content_area:
            logger.warning("내용 영역을 찾을 수 없습니다")
            # 전체 페이지에서 content 찾기
            content_area = soup
        
        # 실제 공고 내용이 있는 테이블 찾기
        content_tables = content_area.find_all('table', class_='table_area')
        content_parts = []
        
        # 특별히 공고 내용을 포함할 가능성이 높은 패턴들
        content_keywords = [
            '공고명', '제목', '내용', '공고내용', '사업내용', 
            '신청방법', '기타사항', '개요', '목적', '지원내용',
            '모집요강', '신청기간', '선정방법', '문의처'
        ]
        
        for table in content_tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['th', 'td'])
                if len(cells) >= 2:
                    header = cells[0].get_text(strip=True)
                    content_text = cells[1].get_text(strip=True)
                    
                    # 키워드가 포함된 헤더이거나 내용이 충분히 긴 경우
                    if any(keyword in header for keyword in content_keywords) or len(content_text) > 30:
                        content_parts.append(f"**{header}**\n{content_text}\n")
        
        # 테이블에서 내용을 찾지 못한 경우, div나 다른 요소에서 찾기
        if not content_parts:
            # 본문 내용이 있을 수 있는 다른 패턴들
            content_divs = content_area.find_all(['div', 'p'], class_=lambda x: x and ('content' in str(x).lower() or 'text' in str(x).lower()))
            for div in content_divs:
                text = div.get_text(strip=True)
                if text and len(text) > 50:  # 충분한 길이의 텍스트만
                    content_parts.append(text)
        
        # 여전히 내용이 없는 경우 전체 내용에서 추출
        if not content_parts:
            all_text = content_area.get_text(strip=True)
            # 불필요한 네비게이션 텍스트 제거
            if '처음 페이지로 이동' in all_text:
                # 목록 페이지 내용이 포함된 경우 - 실제 내용만 추출
                lines = all_text.split('\n')
                filtered_lines = []
                skip_keywords = ['번호', '구분', '제목', '첨부파일', '등록일', '조회수', '처음 페이지로 이동']
                
                for line in lines:
                    line = line.strip()
                    if line and not any(keyword in line for keyword in skip_keywords) and len(line) > 10:
                        filtered_lines.append(line)
                
                if filtered_lines:
                    content_parts.extend(filtered_lines[:10])  # 처음 10줄만
            elif all_text and len(all_text) > 100:
                content_parts.append(all_text[:1000])  # 처음 1000자만
        
        content = '\n'.join(content_parts) if content_parts else ''
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup)
        
        return {
            'content': content,
            'attachments': attachments
        }
    
    def _extract_attachments(self, soup: BeautifulSoup) -> list:
        """첨부파일 추출 - GSIC 특화"""
        attachments = []
        
        # GSIC 특화: board_view_file 클래스에서 첨부파일 찾기
        file_section = soup.find('div', class_='board_view_file')
        if file_section:
            file_links = file_section.find_all('a')
            for link in file_links:
                onclick = link.get('onclick', '')
                text = link.get_text(strip=True)
                
                # kssFileDownloadForKeyAct 함수에서 파일 ID 추출
                if 'kssFileDownloadForKeyAct' in onclick:
                    id_match = re.search(r"kssFileDownloadForKeyAct\('([^']+)'\)", onclick)
                    if id_match:
                        file_id = id_match.group(1)
                        # GSIC 파일 다운로드 URL 구성 (올바른 패턴)
                        file_url = f"{self.base_url}/fileDownload.do"
                        attachments.append({
                            'name': text or f'file_{file_id[:8]}',
                            'url': file_url,
                            'file_id': file_id,
                            'unique_key': file_id  # POST 파라미터용
                        })
        
        # 추가 패턴 - 다른 첨부파일 패턴도 체크
        if not attachments:
            # file_box 클래스에서도 찾기
            file_boxes = soup.find_all('div', class_='file_box')
            for box in file_boxes:
                links = box.find_all('a')
                for link in links:
                    onclick = link.get('onclick', '')
                    text = link.get_text(strip=True)
                    href = link.get('href', '')
                    
                    if 'kssFileDownloadForKeyAct' in onclick:
                        id_match = re.search(r"kssFileDownloadForKeyAct\('([^']+)'\)", onclick)
                        if id_match:
                            file_id = id_match.group(1)
                            file_url = f"{self.base_url}/fileDownload.do"
                            attachments.append({
                                'name': text or f'file_{file_id[:8]}',
                                'url': file_url,
                                'file_id': file_id,
                                'unique_key': file_id  # POST 파라미터용
                            })
                    elif href and href.startswith('http') and any(ext in href.lower() for ext in ['.pdf', '.hwp', '.doc', '.xls', '.ppt', '.zip', '.jpg', '.png']):
                        # 직접 링크인 경우
                        attachments.append({
                            'name': text or 'attachment',
                            'url': href
                        })
        
        # 중복 제거
        seen_urls = set()
        unique_attachments = []
        for att in attachments:
            if att['url'] not in seen_urls:
                seen_urls.add(att['url'])
                unique_attachments.append(att)
        
        logger.info(f"첨부파일 {len(unique_attachments)}개 발견")
        for att in unique_attachments:
            logger.info(f"  - {att['name']}: {att['url']}")
        
        return unique_attachments
    
    def download_file(self, file_url: str, save_path: str, attachment_info = None, **kwargs) -> bool:
        """파일 다운로드 - GSIC 특화 (POST 요청)"""
        try:
            # attachment_info에서 unique_key 추출 (GSIC 전용)
            unique_key = None
            file_name = None
            
            if isinstance(attachment_info, dict):
                unique_key = attachment_info.get('unique_key')
                file_name = attachment_info.get('name') or attachment_info.get('filename')
            elif isinstance(attachment_info, str):
                file_name = attachment_info
            
            # kwargs에서도 확인
            if not unique_key:
                unique_key = kwargs.get('unique_key')
            
            if unique_key:
                # GSIC 파일 다운로드: POST 요청 사용
                logger.info(f"GSIC 파일 다운로드 시도: {file_url} (uniqueKey: {unique_key[:20]}...)")
                
                # POST 데이터 설정
                data = {'uniqueKey': unique_key}
                
                # GSIC 특화 헤더 설정
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': self.base_url + '/home/kor/M837392473/board.do',
                    'User-Agent': self.headers['User-Agent'],
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }
                
                # POST 요청으로 파일 다운로드
                response = self.session.post(file_url, data=data, headers=headers, 
                                           stream=True, timeout=self.timeout, verify=self.verify_ssl)
                
            else:
                # 일반 파일 다운로드: GET 요청 사용
                logger.info(f"일반 파일 다운로드 시도: {file_url}")
                
                headers = {
                    'Referer': self.base_url + '/home/kor/M837392473/board.do',
                    'User-Agent': self.headers['User-Agent'],
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }
                
                response = self.session.get(file_url, headers=headers, stream=True, 
                                          timeout=self.timeout, verify=self.verify_ssl)
            
            response.raise_for_status()
            
            logger.info(f"응답 상태: {response.status_code}, Content-Type: {response.headers.get('Content-Type', 'N/A')}")
            
            # 파일명 처리
            if file_name:
                # 확장자가 없는 경우 Content-Type에서 추측
                if '.' not in file_name:
                    content_type = response.headers.get('Content-Type', '').lower()
                    if 'image/jpeg' in content_type or 'image/jpg' in content_type:
                        file_name += '.jpg'
                    elif 'image/png' in content_type:
                        file_name += '.png'
                    elif 'application/pdf' in content_type:
                        file_name += '.pdf'
                    elif 'application/hwp' in content_type or 'application/x-hwp' in content_type:
                        file_name += '.hwp'
                    elif 'application/msword' in content_type:
                        file_name += '.doc'
                    elif 'application/vnd.ms-excel' in content_type:
                        file_name += '.xls'
                
                final_path = os.path.join(os.path.dirname(save_path), self.sanitize_filename(file_name))
            else:
                final_path = self._extract_filename_from_response(response, save_path)
            
            # 디렉토리 생성
            os.makedirs(os.path.dirname(final_path), exist_ok=True)
            
            # 파일 저장
            with open(final_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(final_path)
            if file_size > 0:
                logger.info(f"파일 다운로드 완료: {os.path.basename(final_path)} ({file_size:,} bytes)")
                return True
            else:
                logger.warning(f"파일 크기가 0입니다: {final_path}")
                os.remove(final_path)  # 빈 파일 삭제
                return False
            
        except Exception as e:
            logger.error(f"파일 다운로드 실패 {file_url}: {e}")
            return False

def create_scraper():
    """스크래퍼 인스턴스 생성"""
    return EnhancedGsicScraper()

if __name__ == "__main__":
    # 테스트 실행
    scraper = EnhancedGsicScraper()
    scraper.scrape_pages(max_pages=3, output_base='output/gsic')