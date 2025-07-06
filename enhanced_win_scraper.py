#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote
from enhanced_base_scraper import StandardTableScraper
import logging

logger = logging.getLogger(__name__)

class EnhancedWinScraper(StandardTableScraper):
    """윈윈사회적경제지원센터 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.win-win.or.kr"
        self.list_url = "https://www.win-win.or.kr/kr/board/notice/boardList.do"
        
        # WIN 사이트별 특화 설정
        self.verify_ssl = False  # SSL 인증서 문제로 False 설정
        self.default_encoding = 'utf-8'
        self.timeout = 60
        self.delay_between_requests = 2
        
        # 세션 설정
        self.session.verify = self.verify_ssl
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        logger.info("Enhanced WIN 스크래퍼 초기화 완료")

    def get_list_url(self, page_num: int) -> str:
        """페이지네이션 URL 생성"""
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}?pageIndex={page_num}"

    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱 - ul.bbs_table.notice 구조"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # ul.bbs_table.notice 구조 찾기
        notice_list = soup.find('ul', class_='bbs_table notice')
        if not notice_list:
            logger.warning("공지사항 목록을 찾을 수 없습니다")
            return announcements
        
        items = notice_list.find_all('li')
        logger.info(f"총 {len(items)}개 항목 발견")
        
        for i, item in enumerate(items):
            try:
                # 헤더 행 제외 (class="th"인 경우)
                if item.get('class') and 'th' in item.get('class'):
                    continue
                
                # onclick에서 URL 추출
                onclick = item.get('onclick', '')
                if not onclick or 'location.href=' not in onclick:
                    continue
                
                # onclick에서 URL 추출: location.href='/kr/board/notice/boardView.do?bbsIdx=54269&pageIndex=1...'
                url_match = re.search(r"location\.href='([^']*)'", onclick)
                if not url_match:
                    continue
                
                relative_url = url_match.group(1)
                detail_url = urljoin(self.base_url, relative_url)
                
                # 제목 추출 (p.w03.tit a 태그에서)
                title_elem = item.find('p', class_='w03')
                if not title_elem:
                    continue
                
                title_link = title_elem.find('a')
                if not title_link:
                    continue
                
                title = title_link.get_text(strip=True)
                
                # 구분 추출 (p.w02.cate에서)
                category_elem = item.find('p', class_='w02 cate')
                category = category_elem.get_text(strip=True) if category_elem else ""
                
                # 등록일 추출 (p.w04에서)
                date_elem = item.find('p', class_='w04')
                date = date_elem.get_text(strip=True) if date_elem else ""
                
                # 조회수 추출 (p.w05에서)
                views_elem = item.find('p', class_='w05')
                views = views_elem.get_text(strip=True) if views_elem else ""
                
                announcement = {
                    'number': str(len(announcements) + 1),
                    'title': title,
                    'url': detail_url,
                    'date': date,
                    'views': views,
                    'category': category,
                    'has_attachment': False
                }
                
                announcements.append(announcement)
                logger.info(f"공고 추가: [{announcement['number']}] {title}")
                
            except Exception as e:
                logger.error(f"공고 파싱 중 오류 발생 (항목 {i}): {e}")
                continue
        
        logger.info(f"총 {len(announcements)}개 공고 파싱 완료")
        return announcements

    def parse_detail_page(self, html_content: str) -> dict:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 제목 추출 - 여러 selector 시도
        title = ""
        title_selectors = [
            '.view_title',
            '.title', 
            'h1',
            'h2',
            'h3'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = title_elem.get_text(strip=True)
                if title and len(title) > 5:
                    break
        
        # URL에서 제목 추출 시도
        if not title:
            # 이전 페이지의 제목 사용 (목록에서 가져온 제목)
            title = "제목 없음"
        
        # 본문 추출 - 여러 selector 시도
        content = ""
        content_selectors = [
            '.view_content',
            '.content',
            '.detail_content',
            '.board_content',
            '#content'
        ]
        
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                content = content_elem.get_text(strip=True)
                if content and len(content) > 10:
                    break
        
        # 테이블 구조에서 내용 추출 시도
        if not content:
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    for cell in cells:
                        cell_text = cell.get_text(strip=True)
                        if len(cell_text) > 50:  # 충분히 긴 텍스트인 경우
                            content = cell_text
                            break
                    if content:
                        break
                if content:
                    break
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup)
        
        return {
            'title': title,
            'content': content,
            'attachments': attachments
        }

    def _extract_attachments(self, soup: BeautifulSoup) -> list:
        """첨부파일 추출 - fileDownload.do 패턴"""
        attachments = []
        
        # fileDownload.do 링크 찾기
        download_links = soup.find_all('a', href=re.compile(r'fileDownload\.do'))
        
        for link in download_links:
            href = link.get('href')
            filename = link.get_text(strip=True)
            
            # 파일명이 없는 경우 href에서 추출
            if not filename or filename == href:
                try:
                    # URL에서 usrFile 파라미터 추출
                    if 'usrFile=' in href:
                        usr_file_part = href.split('usrFile=')[1]
                        if '&' in usr_file_part:
                            usr_file_part = usr_file_part.split('&')[0]
                        filename = unquote(usr_file_part, encoding='utf-8')
                except:
                    filename = f"첨부파일_{len(attachments)+1}"
            
            # 상대 URL을 절대 URL로 변환
            if href.startswith('/'):
                download_url = urljoin(self.base_url, href)
            elif href.startswith('http'):
                download_url = href
            else:
                download_url = urljoin(self.base_url, href)
            
            attachments.append({
                'filename': filename,
                'url': download_url
            })
            
            logger.info(f"첨부파일 발견: {filename}")
        
        return attachments

    def download_file(self, file_url: str, save_path: str, filename: str = None) -> bool:
        """파일 다운로드 - SSL 검증 비활성화"""
        try:
            # WIN 사이트는 SSL 인증서 문제가 있어 verify=False 필요
            response = self.session.get(file_url, stream=True, timeout=self.timeout, verify=False)
            response.raise_for_status()
            
            # 파일명 추출 및 인코딩 처리
            save_dir = os.path.dirname(save_path)
            filename = os.path.basename(save_path)
            
            # Content-Disposition에서 파일명 추출 시도
            content_disposition = response.headers.get('Content-Disposition', '')
            if content_disposition:
                # RFC 5987 형식 처리
                rfc5987_match = re.search(r"filename\*=([^']*)'([^']*)'(.+)", content_disposition)
                if rfc5987_match:
                    encoding, lang, encoded_filename = rfc5987_match.groups()
                    try:
                        filename = unquote(encoded_filename, encoding=encoding or 'utf-8')
                        save_path = os.path.join(save_dir, self.sanitize_filename(filename))
                    except:
                        pass
                else:
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
                                    save_path = os.path.join(save_dir, clean_filename)
                                    break
                            except:
                                continue
            
            # 파일 저장
            os.makedirs(save_dir, exist_ok=True)
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(save_path)
            logger.info(f"파일 다운로드 완료: {os.path.basename(save_path)} ({file_size} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"파일 다운로드 실패: {file_url} - {e}")
            return False

    def _get_page_announcements(self, page_num: int) -> list:
        """페이지별 공고 목록 가져오기 - 오버라이드"""
        page_url = self.get_list_url(page_num)
        
        try:
            logger.info(f"페이지 {page_num} 요청: {page_url}")
            response = self.session.get(page_url, timeout=self.timeout, verify=False)
            response.raise_for_status()
            response.encoding = self.default_encoding
            
            announcements = self.parse_list_page(response.text)
            logger.info(f"페이지 {page_num}에서 {len(announcements)}개 공고 발견")
            
            return announcements
            
        except Exception as e:
            logger.error(f"페이지 {page_num} 처리 중 오류: {e}")
            return []

def main():
    """테스트 실행"""
    scraper = EnhancedWinScraper()
    output_dir = "output/win"
    os.makedirs(output_dir, exist_ok=True)
    
    # 3페이지까지 스크래핑
    scraper.scrape_pages(max_pages=3, output_base=output_dir)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    main()