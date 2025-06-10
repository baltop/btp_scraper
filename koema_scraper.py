# -*- coding: utf-8 -*-
"""
한국에너지공단 조합 (KOEMA) 공고 스크래퍼

표준 HTML 테이블 기반 게시판으로 추정하여 구현
"""

import logging
from bs4 import BeautifulSoup
from enhanced_base_scraper import StandardTableScraper
from urllib.parse import urljoin
from typing import Dict, List, Any
import re

logger = logging.getLogger(__name__)

class KOEMAScraper(StandardTableScraper):
    """한국에너지공단 조합 공고 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.koema.or.kr"
        self.list_url = "https://www.koema.or.kr/koema/report/total_notice.html"
        
        # SSL 인증서 문제가 있을 수 있으므로 비활성화
        self.verify_ssl = True
        
        # 기본 요청 헤더 설정
        self.headers.update({
            'Referer': self.base_url,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate'
        })
        self.session.headers.update(self.headers)
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성"""
        if page_num == 1:
            return self.list_url
        else:
            # 일반적인 페이지네이션 패턴 추측
            separator = '&' if '?' in self.list_url else '?'
            return f"{self.list_url}{separator}page={page_num}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱"""
        announcements = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # KOEMA 특화 - tbody.bbs_list 찾기
            tbody = soup.select_one('tbody.bbs_list')
            if not tbody:
                logger.warning("tbody.bbs_list를 찾을 수 없습니다")
                return announcements
            
            logger.info("KOEMA 게시판 리스트 발견")
            
            # 행들 찾기
            rows = tbody.select('tr')
            logger.info(f"총 {len(rows)}개 행 발견")
            
            for i, row in enumerate(rows):
                try:
                    # onclick 속성에서 URL 추출
                    onclick = row.get('onclick', '')
                    if not onclick or 'board_view.html' not in onclick:
                        continue
                    
                    # onclick="location.href='/koema/report/board_view.html?idx=78340&page=1&sword=&category=all'"
                    # 정규표현식으로 URL 추출
                    url_match = re.search(r"location\.href='([^']+)'", onclick)
                    if not url_match:
                        continue
                    
                    relative_url = url_match.group(1)
                    detail_url = urljoin(self.base_url, relative_url)
                    
                    # 테이블 셀들 파싱
                    cells = row.select('td')
                    if len(cells) < 5:
                        continue
                    
                    # 순서: 번호, 제목, 작성자, 작성일, 조회수
                    num = cells[0].get_text(strip=True)
                    title = cells[1].get_text(strip=True)
                    writer = cells[2].get_text(strip=True)
                    date = cells[3].get_text(strip=True)
                    views = cells[4].get_text(strip=True)
                    
                    if not title or len(title) < 3:
                        continue
                    
                    announcement = {
                        'num': num,
                        'title': title,
                        'writer': writer,
                        'date': date,
                        'views': views,
                        'url': detail_url
                    }
                    
                    announcements.append(announcement)
                    logger.debug(f"공고 추가: {title}")
                    
                except Exception as e:
                    logger.error(f"행 {i} 파싱 중 오류: {e}")
                    continue
            
            logger.info(f"총 {len(announcements)}개 공고 파싱 완료")
            
        except Exception as e:
            logger.error(f"목록 페이지 파싱 실패: {e}")
        
        return announcements
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱"""
        result = {
            'content': '',
            'attachments': []
        }
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # KOEMA 특화 - 본문 내용 찾기 (EditView 클래스)
            content_elem = soup.select_one('td.EditView')
            if not content_elem:
                # 대체 방법: 본문이 있는 테이블 셀 찾기
                content_selectors = [
                    'div.view-content',
                    'div.board-view-content', 
                    'div.content',
                    'td[class*="content"]',
                    'td[style*="height:400px"]'  # KOEMA 특화
                ]
                
                for selector in content_selectors:
                    content_elem = soup.select_one(selector)
                    if content_elem:
                        logger.info(f"본문 영역 발견: {selector}")
                        break
            else:
                logger.info("KOEMA 본문 영역 발견: td.EditView")
            
            # 본문을 찾지 못한 경우 전체 body에서 추출
            if not content_elem:
                logger.warning("본문 영역을 찾지 못했습니다. body 전체 사용")
                content_elem = soup.find('body') or soup
            
            # HTML을 마크다운으로 변환
            if content_elem:
                # 불필요한 요소들 제거
                for unwanted in content_elem.select('script, style, nav, header, footer, .navigation, .menu'):
                    unwanted.decompose()
                
                content_html = str(content_elem)
                content_text = self.h.handle(content_html)
                
                # 빈 줄 정리
                content_lines = [line.strip() for line in content_text.split('\n')]
                content_lines = [line for line in content_lines if line]
                result['content'] = '\n\n'.join(content_lines)
            
            # KOEMA 특화 - 첨부파일 찾기
            # 패턴: <td>첨부화일</td> 다음에 파일명과 _pds_down.html 링크
            
            # 방법 1: "첨부화일" 텍스트가 있는 행들 찾기
            attach_rows = []
            for td in soup.find_all('td'):
                if td.get_text(strip=True) == '첨부화일':
                    # 같은 행의 다음 셀들에서 파일 정보 찾기
                    parent_row = td.find_parent('tr')
                    if parent_row:
                        attach_rows.append(parent_row)
            
            logger.info(f"첨부파일 행 {len(attach_rows)}개 발견")
            
            for row in attach_rows:
                try:
                    # _pds_down.html 링크 찾기
                    download_link = row.select_one('a[href*="_pds_down.html"]')
                    if not download_link:
                        continue
                    
                    download_url = download_link.get('href', '')
                    if not download_url:
                        continue
                    
                    # 파일명 추출 - 링크 앞의 텍스트에서 찾기
                    # 패턴: &nbsp;파일명.확장자&nbsp;<a href="...">
                    row_text = row.get_text()
                    
                    # 파일명 패턴 찾기 (확장자가 있는 파일명)
                    file_patterns = [
                        r'([^&\s]+\.(pdf|hwp|doc|docx|xls|xlsx|ppt|pptx|zip|rar|txt))',
                        r'([가-힣a-zA-Z0-9\s\(\)_-]+\.(pdf|hwp|doc|docx|xls|xlsx|ppt|pptx|zip|rar|txt))'
                    ]
                    
                    file_name = None
                    for pattern in file_patterns:
                        match = re.search(pattern, row_text, re.IGNORECASE)
                        if match:
                            file_name = match.group(1).strip()
                            break
                    
                    # 파일명을 찾지 못한 경우 URL에서 추출 시도
                    if not file_name:
                        # 셀 내용에서 파일명 직접 추출
                        cells = row.select('td')
                        for cell in cells:
                            cell_text = cell.get_text(strip=True)
                            if ('.' in cell_text and 
                                any(ext in cell_text.lower() for ext in ['.pdf', '.hwp', '.doc', '.xls', '.ppt', '.zip'])):
                                # 파일명으로 추정되는 부분 추출
                                parts = cell_text.split()
                                for part in parts:
                                    if '.' in part and any(ext in part.lower() for ext in ['.pdf', '.hwp', '.doc', '.xls', '.ppt', '.zip']):
                                        file_name = part.strip('&nbsp;').strip()
                                        break
                                if file_name:
                                    break
                    
                    if not file_name:
                        file_name = f"첨부파일_{len(result['attachments']) + 1}"
                    
                    # 절대 URL 생성
                    full_download_url = urljoin(self.base_url, download_url)
                    
                    result['attachments'].append({
                        'name': file_name,
                        'url': full_download_url
                    })
                    
                    logger.info(f"첨부파일 발견: {file_name} -> {full_download_url}")
                    
                except Exception as e:
                    logger.error(f"첨부파일 행 파싱 중 오류: {e}")
                    continue
            
            # 방법 2: 직접 _pds_down.html 링크 찾기 (보완)
            if not result['attachments']:
                download_links = soup.select('a[href*="_pds_down.html"]')
                logger.info(f"직접 다운로드 링크 {len(download_links)}개 발견")
                
                for i, link in enumerate(download_links):
                    href = link.get('href', '')
                    if not href:
                        continue
                    
                    # 링크 주변 텍스트에서 파일명 찾기
                    parent = link.find_parent(['td', 'tr'])
                    file_name = f"첨부파일_{i+1}"
                    
                    if parent:
                        parent_text = parent.get_text()
                        # 파일명 패턴 찾기
                        for pattern in file_patterns:
                            match = re.search(pattern, parent_text, re.IGNORECASE)
                            if match:
                                file_name = match.group(1).strip()
                                break
                    
                    full_url = urljoin(self.base_url, href)
                    result['attachments'].append({
                        'name': file_name,
                        'url': full_url
                    })
                    
                    logger.info(f"추가 첨부파일 발견: {file_name} -> {full_url}")
            
            logger.info(f"본문 길이: {len(result['content'])}, 첨부파일: {len(result['attachments'])}개")
            
        except Exception as e:
            logger.error(f"상세 페이지 파싱 실패: {e}")
        
        return result


if __name__ == "__main__":
    # 테스트 실행
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    scraper = KOEMAScraper()
    
    try:
        scraper.scrape_pages(max_pages=1)
    except KeyboardInterrupt:
        print("\n사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"실행 중 오류 발생: {e}")
        sys.exit(1)