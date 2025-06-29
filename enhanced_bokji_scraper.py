# -*- coding: utf-8 -*-
"""
복지넷(bokji.net) 스크래퍼 - Enhanced 버전
"""

import requests
from bs4 import BeautifulSoup
import os
import time
import re
from urllib.parse import urljoin, unquote
import logging
from enhanced_base_scraper import EnhancedBaseScraper
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class EnhancedBokjiScraper(EnhancedBaseScraper):
    """복지넷 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 복지넷 기본 설정
        self.base_url = "https://www.bokji.net"
        self.list_url = "https://www.bokji.net/not/nti/01.bokji"
        self.detail_url = "https://www.bokji.net/not/nti/01_01.bokji"
        self.download_url = "https://www.bokji.net/not/nti/01_02.bokji"
        
        # 사이트별 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        self.delay_between_pages = 2
        
        # 헤더 설정
        self.headers.update({
            'Referer': 'https://www.bokji.net',
            'Origin': 'https://www.bokji.net'
        })
        self.session.headers.update(self.headers)
    
    def get_list_url(self, page_num: int) -> str:
        """페이지네이션 URL 생성"""
        if page_num == 1:
            return self.list_url
        else:
            # JavaScript 함수 goPage()를 POST 요청으로 구현
            return self.list_url
    
    def _get_page_announcements(self, page_num: int) -> List[Dict[str, Any]]:
        """페이지별 공고 목록 가져오기 - POST 요청으로 페이지네이션 구현"""
        if page_num == 1:
            # 첫 페이지는 GET 요청
            response = self.get_page(self.list_url)
        else:
            # 2페이지부터는 POST 요청
            data = {
                'PG': str(page_num),
                'SEARCH_GUBUN': '',
                'SEARCH_KEYWORD': ''
            }
            response = self.post_page(self.list_url, data=data)
        
        if not response:
            logger.warning(f"페이지 {page_num} 응답을 가져올 수 없습니다")
            return []
        
        # 페이지가 에러 상태거나 잘못된 경우 감지
        if response.status_code >= 400:
            logger.warning(f"페이지 {page_num} HTTP 에러: {response.status_code}")
            return []
        
        # 현재 페이지 번호를 인스턴스 변수로 저장
        self.current_page_num = page_num
        announcements = self.parse_list_page(response.text)
        
        return announcements
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 테이블 찾기
        table = soup.find('table', class_='board_list_type1')
        if not table:
            logger.warning("게시판 테이블을 찾을 수 없습니다")
            return announcements
        
        # tbody에서 tr 행들 찾기
        tbody = table.find('tbody')
        if not tbody:
            logger.warning("테이블 본문(tbody)을 찾을 수 없습니다")
            return announcements
        
        rows = tbody.find_all('tr')
        logger.info(f"총 {len(rows)}개 행을 발견했습니다")
        
        for i, row in enumerate(rows):
            try:
                cells = row.find_all('td')
                if len(cells) < 4:  # 번호, 제목, 작성일, 조회수
                    logger.debug(f"행 {i}: 셀 수가 부족함 ({len(cells)}개)")
                    continue
                
                # 번호 (첫 번째 셀) - "공지" 이미지 처리
                number_cell = cells[0]
                number = number_cell.get_text(strip=True)
                
                # 공지 이미지 확인
                is_notice = False
                if number_cell.find('span'):
                    span_text = number_cell.find('span').get_text(strip=True)
                    if span_text == '공지':
                        is_notice = True
                        number = "공지"
                
                # 번호 처리
                if is_notice:
                    number = "공지"
                elif not number:
                    number = f"row_{i+1}"
                
                # 제목 (두 번째 셀)
                title_cell = cells[1]
                link_elem = title_cell.find('a')
                
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                if not title:
                    continue
                
                # JavaScript 함수에서 BOARDIDX 추출 (href 속성에서)
                href = link_elem.get('href', '')
                logger.debug(f"href 속성: {href}")
                boardidx_match = re.search(r"goView\('(\d+)'\)", href)
                if not boardidx_match:
                    logger.debug(f"BOARDIDX를 찾을 수 없음: {href}")
                    continue
                
                boardidx = boardidx_match.group(1)
                
                # 첨부파일 여부 확인
                has_attachment = bool(title_cell.find('img', alt='파일'))
                
                # 작성일 (세 번째 셀)
                date = cells[2].get_text(strip=True)
                
                # 조회수 (네 번째 셀)
                views = cells[3].get_text(strip=True)
                
                announcement = {
                    'title': title,
                    'url': f"{self.detail_url}?BOARDIDX={boardidx}",
                    'boardidx': boardidx,
                    'number': number,
                    'date': date,
                    'views': views,
                    'has_attachment': has_attachment
                }
                
                announcements.append(announcement)
                logger.info(f"공고 추가: [{number}] {title}")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류 (행 {i}): {e}")
                continue
        
        logger.info(f"총 {len(announcements)}개 공고를 파싱했습니다")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 추출
        content = ""
        
        # 제목 추출
        title_elem = soup.find('div', class_='boardColH boardTit')
        title = title_elem.get_text(strip=True) if title_elem else ""
        
        # 본문 내용 추출
        content_elem = soup.find('div', class_='boardContent')
        if content_elem:
            # HTML을 마크다운으로 변환
            content = self.h.handle(str(content_elem))
            # 불필요한 공백 제거
            content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
            content = content.strip()
        else:
            logger.warning("본문 내용을 찾을 수 없습니다")
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup)
        
        return {
            'title': title,
            'content': content,
            'attachments': attachments
        }
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """첨부파일 정보 추출"""
        attachments = []
        
        # 첨부파일 섹션 찾기
        file_box = soup.find('div', class_='box_file')
        if not file_box:
            logger.debug("box_file을 찾을 수 없습니다")
            return attachments
        
        logger.debug("box_file 발견")
        
        file_list = file_box.find('ul', class_='fileList')
        if not file_list:
            logger.debug("fileList를 찾을 수 없습니다")
            return attachments
        
        logger.debug("fileList 발견")
        
        # 각 파일 링크 처리
        li_elements = file_list.find_all('li')
        logger.debug(f"li 요소 {len(li_elements)}개 발견")
        
        for i, li in enumerate(li_elements):
            logger.debug(f"li 요소 {i+1}: {str(li)[:100]}...")
            link_elem = li.find('a')
            if not link_elem:
                logger.debug(f"li 요소 {i+1}에서 a 태그를 찾을 수 없음")
                continue
            
            # JavaScript 함수에서 파라미터 추출 (href에서)
            href = link_elem.get('href', '')
            logger.debug(f"href: {href}")
            down_match = re.search(r"down\('(\d+)','(\d+)'\)", href)
            if not down_match:
                logger.debug(f"down() 함수를 찾을 수 없음: {href}")
                continue
            
            boardidx = down_match.group(1)
            fileseq = down_match.group(2)
            
            # 파일명과 크기 추출 - 공백 정리 후 파싱
            link_text = re.sub(r'\s+', ' ', link_elem.get_text()).strip()
            
            # 파일명과 크기 분리
            size_match = re.search(r'\((\d+)\s*bytes\)', link_text)
            if size_match:
                file_size = int(size_match.group(1))
                filename = link_text.replace(size_match.group(0), '').strip()
            else:
                file_size = 0
                filename = link_text
            
            # 파일 다운로드 URL 구성
            file_url = f"{self.download_url}?BOARDIDX={boardidx}&FILESEQ={fileseq}"
            
            attachment = {
                'filename': filename,
                'url': file_url,
                'size': file_size,
                'boardidx': boardidx,
                'fileseq': fileseq
            }
            
            attachments.append(attachment)
            logger.info(f"첨부파일 발견: {filename} ({file_size:,} bytes)")
        
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment_info: Dict[str, Any] = None) -> bool:
        """복지넷 파일 다운로드 - POST 요청 방식"""
        try:
            logger.info(f"파일 다운로드 시작: {url}")
            
            # POST 데이터 구성
            if attachment_info:
                data = {
                    'BOARDIDX': attachment_info.get('boardidx', ''),
                    'FILESEQ': attachment_info.get('fileseq', '')
                }
            else:
                # URL에서 파라미터 추출
                from urllib.parse import urlparse, parse_qs
                parsed_url = urlparse(url)
                params = parse_qs(parsed_url.query)
                data = {
                    'BOARDIDX': params.get('BOARDIDX', [''])[0],
                    'FILESEQ': params.get('FILESEQ', [''])[0]
                }
            
            # POST 요청으로 파일 다운로드
            response = self.post_page(url, data=data, stream=True)
            if not response:
                logger.error(f"파일 다운로드 요청 실패: {url}")
                return False
            
            response.raise_for_status()
            
            # 실제 파일명 추출
            actual_filename = self._extract_filename_from_response(response, save_path)
            if actual_filename != save_path:
                save_path = actual_filename
            
            # 파일 저장
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(save_path)
            logger.info(f"다운로드 완료: {save_path} ({file_size:,} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"파일 다운로드 실패 {url}: {e}")
            return False
    
    def _extract_filename_from_response(self, response: requests.Response, default_path: str) -> str:
        """Content-Disposition에서 실제 파일명 추출 - 복지넷 특화"""
        save_dir = os.path.dirname(default_path)
        content_disposition = response.headers.get('Content-Disposition', '')
        
        if not content_disposition:
            return default_path
        
        # RFC 5987 형식 우선 처리
        rfc5987_match = re.search(r"filename\*=([^']*)'([^']*)'(.+)", content_disposition)
        if rfc5987_match:
            encoding, lang, filename = rfc5987_match.groups()
            try:
                filename = unquote(filename, encoding=encoding or 'utf-8')
                return os.path.join(save_dir, self.sanitize_filename(filename))
            except:
                pass
        
        # 일반 filename 파라미터 처리
        filename_match = re.search(r'filename[^;=\n]*=([\'"]*)(.*?)\1', content_disposition)
        if filename_match:
            filename = filename_match.group(2)
            
            # 다양한 인코딩 시도
            for encoding in ['utf-8', 'euc-kr', 'cp949']:
                try:
                    if encoding == 'utf-8':
                        decoded = filename.encode('latin-1').decode('utf-8')
                    else:
                        decoded = filename.encode('latin-1').decode(encoding)
                    
                    if decoded and not decoded.isspace():
                        clean_filename = self.sanitize_filename(decoded.replace('+', ' '))
                        return os.path.join(save_dir, clean_filename)
                except:
                    continue
        
        return default_path
    
    def process_announcement(self, announcement: Dict[str, Any], index: int, output_base: str = 'output'):
        """개별 공고 처리 - 복지넷 특화 (POST 요청 사용)"""
        logger.info(f"공고 처리 중 {index}: {announcement['title']}")
        
        # 폴더 생성 - 파일시스템 제한을 고려한 제목 길이 조정
        folder_title = self.sanitize_filename(announcement['title'])[:100]  # 100자로 단축
        folder_name = f"{index:03d}_{folder_title}"
        
        # 최종 폴더명이 200자 이하가 되도록 추가 조정
        if len(folder_name) > 200:
            # 인덱스 부분(4자) + 언더스코어(1자) = 5자를 제외하고 195자로 제한
            folder_title = folder_title[:195]
            folder_name = f"{index:03d}_{folder_title}"
        
        folder_path = os.path.join(output_base, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        # 상세 페이지 가져오기 - POST 요청으로 변경
        boardidx = announcement.get('boardidx')
        if boardidx:
            data = {
                'BOARDIDX': boardidx,
                'PG': '1'
            }
            response = self.post_page(self.detail_url, data=data)
        else:
            response = self.get_page(announcement['url'])
            
        if not response:
            logger.error(f"상세 페이지 가져오기 실패: {announcement['title']}")
            return
        
        # 상세 내용 파싱
        try:
            detail = self.parse_detail_page(response.text)
            logger.info(f"상세 페이지 파싱 완료 - 내용길이: {len(detail['content'])}, 첨부파일: {len(detail['attachments'])}")
        except Exception as e:
            logger.error(f"상세 페이지 파싱 실패: {e}")
            return
        
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
    
    def _create_meta_info(self, announcement: Dict[str, Any]) -> str:
        """메타 정보 생성"""
        meta_lines = [f"# {announcement['title']}", ""]
        
        # 동적으로 메타 정보 추가
        meta_fields = {
            'number': '번호',
            'date': '작성일',
            'views': '조회수'
        }
        
        for field, label in meta_fields.items():
            if field in announcement and announcement[field]:
                meta_lines.append(f"**{label}**: {announcement[field]}")
        
        meta_lines.extend([
            f"**원본 URL**: {announcement['url']}",
            "",
            "---",
            ""
        ])
        
        return "\n".join(meta_lines)
    
    def _download_attachments(self, attachments: List[Dict[str, Any]], folder_path: str):
        """첨부파일 다운로드"""
        if not attachments:
            logger.info("첨부파일이 없습니다")
            return
        
        logger.info(f"{len(attachments)}개 첨부파일 다운로드 시작")
        attachments_folder = os.path.join(folder_path, 'attachments')
        os.makedirs(attachments_folder, exist_ok=True)
        
        for i, attachment in enumerate(attachments):
            try:
                # 파일명 추출
                file_name = attachment.get('filename') or f"attachment_{i+1}"
                logger.info(f"  첨부파일 {i+1}: {file_name}")
                
                # 파일명 처리
                file_name = self.sanitize_filename(file_name)
                if not file_name or file_name.isspace():
                    file_name = f"attachment_{i+1}"
                
                file_path = os.path.join(attachments_folder, file_name)
                
                # 파일 다운로드
                success = self.download_file(attachment['url'], file_path, attachment)
                if not success:
                    logger.warning(f"첨부파일 다운로드 실패: {file_name}")
                
            except Exception as e:
                logger.error(f"첨부파일 처리 중 오류: {e}")


def test_bokji_scraper(pages: int = 3):
    """복지넷 스크래퍼 테스트"""
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('bokji_scraper.log', encoding='utf-8')
        ]
    )
    
    # 출력 디렉토리 생성
    output_dir = "output/bokji"
    os.makedirs(output_dir, exist_ok=True)
    
    # 스크래퍼 실행
    scraper = EnhancedBokjiScraper()
    scraper.scrape_pages(max_pages=pages, output_base=output_dir)
    
    print(f"\n✅ 복지넷 스크래핑 완료!")
    print(f"결과는 {output_dir} 디렉토리에서 확인하세요.")


if __name__ == "__main__":
    test_bokji_scraper(3)