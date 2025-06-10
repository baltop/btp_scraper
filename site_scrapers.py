# -*- coding: utf-8 -*-
"""
sitelist.csv에 있는 추가 사이트들을 위한 스크래퍼 모음
각 사이트는 구조가 다르므로 개별적으로 구현 필요
"""

from base_scraper import BaseScraper
from enhanced_base_scraper import StandardTableScraper
from enhanced_mire_scraper import EnhancedMIREScraper
from enhanced_kidp_scraper import EnhancedKIDPScraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin, parse_qs, urlparse
import re
import os
import time
import json
import logging

logger = logging.getLogger(__name__)

class GEPAScraper(BaseScraper):
    """광주광역시 기업지원시스템(GEPA) 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "http://203.251.57.106:82"
        self.list_url = "http://203.251.57.106:82/jwsys_site/gepa/main.html"
        
    def get_list_url(self, page_num):
        # 추가 분석 필요
        return self.list_url
        
    def parse_list_page(self, html_content):
        # 구현 필요
        return []
        
    def parse_detail_page(self, html_content):
        # 구현 필요
        return {'content': '', 'attachments': []}


class DCBScraper(BaseScraper):
    """부산디자인진흥원(DCB) 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.dcb.or.kr"
        self.list_url = "https://www.dcb.or.kr/01_news/?mcode=0401010000"
        
    def get_list_url(self, page_num):
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&page={page_num}"
            
    def parse_list_page(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # DCB는 table 구조 사용
        board_container = soup.find('div', class_='board-text')
        if not board_container:
            # 대체 방법: table 직접 찾기
            table = soup.find('table', class_=re.compile('board|list'))
            if table:
                board_container = table
        
        if board_container:
            # 모든 tr 태그 찾기
            rows = board_container.find_all('tr')
            
            for row in rows:
                try:
                    tds = row.find_all('td')
                    if len(tds) < 2:
                        continue
                    
                    # 번호 셀 확인 (공지사항은 icon_notice.png)
                    num_td = tds[0]
                    num_text = num_td.get_text(strip=True)
                    
                    # 제목 셀에서 링크 찾기
                    title_td = None
                    for td in tds:
                        if td.find('a'):
                            title_td = td
                            break
                    
                    if not title_td:
                        continue
                        
                    link = title_td.find('a')
                    if not link:
                        continue
                    
                    title = link.get_text(strip=True)
                    href = link.get('href', '')
                    
                    if href:
                        # URL이 상대경로인 경우 절대경로로 변환
                        if href.startswith('/'):
                            detail_url = self.base_url + href
                        else:
                            detail_url = urljoin(self.base_url, href)
                    else:
                        continue
                    
                    # 날짜 찾기 (보통 마지막에서 두 번째 td)
                    date = ''
                    if len(tds) >= 4:
                        date = tds[-2].get_text(strip=True)
                    
                    # 파일 첨부 여부 확인
                    has_file = False
                    if title_td.find('img', alt='파일'):
                        has_file = True
                    
                    announcements.append({
                        'num': num_text,
                        'title': title,
                        'url': detail_url,
                        'date': date,
                        'has_file': has_file
                    })
                    
                except Exception as e:
                    continue
                    
        return announcements
        
    def parse_detail_page(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 영역 찾기 - DCB는 특정 구조 사용
        content_area = None
        
        # 방법 1: board-view 클래스 찾기
        content_area = soup.find('div', class_='board-view')
        
        # 방법 2: 본문이 있는 테이블 찾기
        if not content_area:
            tables = soup.find_all('table')
            for table in tables:
                # 본문은 보통 긴 텍스트가 있는 셀에 있음
                tds = table.find_all('td')
                for td in tds:
                    text_length = len(td.get_text(strip=True))
                    if text_length > 200:  # 본문으로 추정되는 긴 텍스트
                        content_area = td
                        break
                if content_area:
                    break
        
        # 첨부파일 찾기
        attachments = []
        
        # 방법 1: 파일 다운로드 링크 패턴으로 찾기
        file_patterns = [
            r'/_Bbs/board/download\.php',
            r'/download\.php',
            r'act_download',
            r'fileDown',
            r'file_down'
        ]
        
        for pattern in file_patterns:
            file_links = soup.find_all('a', href=re.compile(pattern))
            for link in file_links:
                file_name = link.get_text(strip=True)
                file_url = link.get('href', '')
                
                # 빈 파일명 처리
                if not file_name or file_name.isspace():
                    # href에서 파일명 추출 시도
                    if 'filename=' in file_url:
                        import urllib.parse
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(file_url).query)
                        if 'filename' in parsed:
                            file_name = parsed['filename'][0]
                    else:
                        file_name = "첨부파일"
                
                if file_url:
                    file_url = urljoin(self.base_url, file_url)
                    attachments.append({
                        'name': file_name,
                        'url': file_url
                    })
        
        # 방법 2: 첨부파일 영역에서 찾기
        file_areas = soup.find_all(['div', 'td'], class_=re.compile('file|attach|download'))
        for area in file_areas:
            links = area.find_all('a')
            for link in links:
                if link in [a for a in attachments]:  # 중복 제거
                    continue
                    
                file_name = link.get_text(strip=True)
                file_url = link.get('href', '')
                
                if file_url and file_name and not file_name.isspace():
                    file_url = urljoin(self.base_url, file_url)
                    attachments.append({
                        'name': file_name,
                        'url': file_url
                    })
        
        # 본문을 마크다운으로 변환
        content_md = ""
        if content_area:
            # 불필요한 스크립트나 스타일 태그 제거
            for tag in content_area.find_all(['script', 'style']):
                tag.decompose()
            content_md = self.h.handle(str(content_area))
        
        return {
            'content': content_md,
            'attachments': attachments
        }


class JBFScraper(BaseScraper):
    """전남바이오진흥원(JBF) 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "http://www.jbf.kr"
        self.list_url = "http://www.jbf.kr/main/board.action?cmsid=101050200000"
        
    def get_list_url(self, page_num):
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&pageIndex={page_num}"
            
    def parse_list_page(self, html_content):
        # 구현 필요
        return []
        
    def parse_detail_page(self, html_content):
        # 구현 필요
        return {'content': '', 'attachments': []}


class CEPAScraper(BaseScraper):
    """충남경제진흥원(CEPA) 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.cepa.or.kr"
        self.list_url = "https://www.cepa.or.kr/notice/notice.do?pm=6&ms=32"
        
    def get_list_url(self, page_num):
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&pageIndex={page_num}"
            
    def parse_list_page(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 테이블 구조 찾기
        table = soup.find('table', class_=re.compile('board|list'))
        if not table:
            return announcements
            
        rows = table.find_all('tr')
        
        for row in rows:
            try:
                tds = row.find_all('td')
                if len(tds) < 3:
                    continue
                
                # 제목 찾기
                title_td = None
                for td in tds:
                    if td.find('a'):
                        title_td = td
                        break
                        
                if not title_td:
                    continue
                    
                link = title_td.find('a')
                title = link.get_text(strip=True)
                
                # URL 추출
                href = link.get('href', '')
                onclick = link.get('onclick', '')
                
                if onclick and 'view' in onclick:
                    # JavaScript에서 파라미터 추출
                    match = re.search(r"view\(([^)]+)\)", onclick)
                    if match:
                        params = match.group(1)
                        # 파라미터 처리 로직
                        detail_url = f"{self.base_url}/notice/view.do?seq={params}"
                    else:
                        continue
                elif href:
                    detail_url = urljoin(self.base_url, href)
                else:
                    continue
                
                announcements.append({
                    'title': title,
                    'url': detail_url
                })
                
            except Exception as e:
                continue
                
        return announcements
        
    def parse_detail_page(self, html_content):
        # 구현 필요
        return {'content': '', 'attachments': []}


class CheongjuCCIScraper(BaseScraper):
    """청주상공회의소(CheongjuCCI) 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://cheongjucci.korcham.net"
        self.list_url = "https://cheongjucci.korcham.net/front/board/boardContentsListPage.do?boardId=10701&menuId=1561"
        
    def get_list_url(self, page_num):
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&pageIndex={page_num}"
            
    def parse_list_page(self, html_content):
        # 구현 필요
        return []
        
    def parse_detail_page(self, html_content):
        # 구현 필요
        return {'content': '', 'attachments': []}


class GIBScraper(BaseScraper):
    """경북바이오산업연구원(GIB) 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://gib.re.kr"
        self.list_url = "https://gib.re.kr/module/bbs/list.php?mid=/news/notice"
        
    def get_list_url(self, page_num):
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&page={page_num}"
            
    def parse_list_page(self, html_content):
        # 구현 필요
        return []
        
    def parse_detail_page(self, html_content):
        # 구현 필요
        return {'content': '', 'attachments': []}


class GBTPScraper(BaseScraper):
    """경북테크노파크(GBTP) 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://gbtp.or.kr"
        self.list_url = "https://gbtp.or.kr/user/board.do?bbsId=BBSMSTR_000000000023"
        
    def get_list_url(self, page_num):
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&pageIndex={page_num}"
            
    def parse_list_page(self, html_content):
        # 구현 필요
        return []
        
    def parse_detail_page(self, html_content):
        # 구현 필요
        return {'content': '', 'attachments': []}


class DGDPScraper(BaseScraper):
    """대구경북디자인진흥원(DGDP) 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://dgdp.or.kr"
        self.list_url = "https://dgdp.or.kr/notice/public"
        
    def get_list_url(self, page_num):
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}?page={page_num}"
            
    def parse_list_page(self, html_content):
        # 구현 필요
        return []
        
    def parse_detail_page(self, html_content):
        # 구현 필요
        return {'content': '', 'attachments': []}


class KOEMAScraper(StandardTableScraper):
    """한국에너지공단 조합(KOEMA) 스크래퍼"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.koema.or.kr"
        self.list_url = "https://www.koema.or.kr/koema/report/total_notice.html"
        
        # SSL 인증서 문제가 있을 수 있으므로 설정
        self.verify_ssl = True
        
        # 기본 요청 헤더 설정
        self.headers.update({
            'Referer': self.base_url,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate'
        })
        self.session.headers.update(self.headers)
        
    def get_list_url(self, page_num):
        if page_num == 1:
            return self.list_url
        else:
            # 일반적인 페이지네이션 패턴 추측
            separator = '&' if '?' in self.list_url else '?'
            return f"{self.list_url}{separator}page={page_num}"
            
    def parse_list_page(self, html_content):
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
        
    def parse_detail_page(self, html_content):
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
                        break
            
            # 본문을 찾지 못한 경우 전체 body에서 추출
            if not content_elem:
                logger.warning("본문 영역을 찾지 못했습니다. body 전체 사용")
                content_elem = soup.find('body') or soup
            else:
                logger.info("KOEMA 본문 영역 발견")
            
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