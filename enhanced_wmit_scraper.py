# -*- coding: utf-8 -*-
"""
여성과학기술인지원센터(WMIT) Enhanced 스크래퍼 - POST 기반 페이지네이션
"""

import requests
from bs4 import BeautifulSoup
import re
import logging
import os
from urllib.parse import urljoin, parse_qs, urlparse, unquote
from enhanced_base_scraper import StandardTableScraper
import time
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class EnhancedWMITScraper(StandardTableScraper):
    """여성과학기술인지원센터(WMIT) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        
        # 향상된 헤더 설정 (차단 방지)
        self.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1',
        })
        self.session.headers.update(self.headers)
        
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "http://wmit.or.kr"
        self.list_url = "http://wmit.or.kr/announce/businessAnnounceList.do"
        
        # 사이트 특화 설정
        self.verify_ssl = False  # HTTP 사이트
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - POST 요청이므로 기본 URL 반환"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: WMIT는 POST 요청 방식
        return self.list_url
    
    def _get_page_announcements(self, page_num: int) -> List[Dict[str, Any]]:
        """페이지별 공고 목록 가져오기 - POST 요청 사용"""
        try:
            # POST 데이터 구성
            post_data = {
                'page': str(page_num)
            }
            
            logger.info(f"페이지 {page_num} POST 요청 시도")
            
            # POST 요청으로 페이지 가져오기
            response = self.session.post(
                self.list_url,
                data=post_data,
                headers=self.headers,
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            
            if not response:
                logger.warning(f"페이지 {page_num} 응답을 가져올 수 없습니다")
                return []
            
            # 페이지가 에러 상태거나 잘못된 경우 감지
            if response.status_code >= 400:
                logger.warning(f"페이지 {page_num} HTTP 에러: {response.status_code}")
                return []
            
            # 인코딩 처리
            response.encoding = self.default_encoding
            
            announcements = self.parse_list_page(response.text)
            
            # 추가 마지막 페이지 감지 로직
            if not announcements and page_num > 1:
                logger.info(f"페이지 {page_num}에 공고가 없어 마지막 페이지로 판단됩니다")
            
            return announcements
            
        except Exception as e:
            logger.error(f"페이지 {page_num} 가져오기 중 오류: {e}")
            return []
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: 사이트 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """WMIT 특화된 목록 파싱 로직"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 테이블 찾기 - class가 "tbl text-center"인 테이블
        table = soup.find('table', class_='tbl text-center')
        if not table:
            # 백업: 일반적인 테이블 찾기
            table = soup.find('table')
            if table:
                logger.debug("일반 테이블로 fallback")
        
        if not table:
            logger.warning("공고 목록 테이블을 찾을 수 없습니다")
            return announcements
        
        # tbody에서 행 찾기
        tbody = table.find('tbody')
        if not tbody:
            logger.warning("테이블 tbody를 찾을 수 없습니다")
            return announcements
        
        rows = tbody.find_all('tr')
        if not rows:
            logger.warning("테이블 행을 찾을 수 없습니다")
            return announcements
        
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for i, row in enumerate(rows):
            try:
                cells = row.find_all('td')
                if len(cells) < 8:  # 번호, 구분, 제목, 신청기간, 공고번호, 진행상태, 담당부서, 등록일, 첨부 (9개)
                    logger.debug(f"행 {i}: 셀 수 부족 ({len(cells)}개)")
                    continue
                
                # 제목 셀에서 링크 찾기 (세 번째 셀)
                title_cell = cells[2] if len(cells) > 2 else cells[1]
                
                # 제목과 링크 추출
                title = title_cell.get_text(strip=True)
                
                # 링크 추출 (다양한 패턴 시도)
                link_elem = title_cell.find('a')
                detail_url = ""
                notice_idx = ""
                
                if link_elem:
                    href = link_elem.get('href', '')
                    onclick = link_elem.get('onclick', '')
                    
                    if href and href != '#':
                        # 직접 링크가 있는 경우
                        detail_url = urljoin(self.base_url, href)
                    elif onclick:
                        # JavaScript onclick에서 링크 추출
                        # 예: onclick="moveDetail('12345')" 
                        match = re.search(r"moveDetail\(['\"]([^'\"]+)['\"]\)", onclick)
                        if match:
                            notice_idx = match.group(1)
                            detail_url = f"{self.base_url}/announce/businessAnnounceDetail.do?noticeIdx={notice_idx}"
                
                if not title or len(title) < 3:
                    logger.debug(f"행 {i}: 제목이 너무 짧음: '{title}'")
                    continue
                
                # 번호 추출 (첫 번째 셀)
                number = ""
                number_cell = cells[0]
                if number_cell:
                    number_text = number_cell.get_text(strip=True)
                    if number_text and number_text != "번호":
                        number = number_text
                
                # 구분 추출 (두 번째 셀)
                category = ""
                if len(cells) > 1:
                    category_cell = cells[1]
                    category = category_cell.get_text(strip=True)
                
                # 신청기간 추출 (네 번째 셀)
                application_period = ""
                if len(cells) > 3:
                    period_cell = cells[3]
                    application_period = period_cell.get_text(strip=True)
                
                # 공고번호 추출 (다섯 번째 셀)
                notice_number = ""
                if len(cells) > 4:
                    notice_number_cell = cells[4]
                    notice_number = notice_number_cell.get_text(strip=True)
                
                # 진행상태 추출 (여섯 번째 셀)
                status = ""
                if len(cells) > 5:
                    status_cell = cells[5]
                    status = status_cell.get_text(strip=True)
                
                # 담당부서 추출 (일곱 번째 셀)
                department = ""
                if len(cells) > 6:
                    department_cell = cells[6]
                    department = department_cell.get_text(strip=True)
                
                # 등록일 추출 (여덟 번째 셀)
                date = ""
                if len(cells) > 7:
                    date_cell = cells[7]
                    date_text = date_cell.get_text(strip=True)
                    # 날짜 패턴 매칭 (YYYY-MM-DD 또는 YYYY.MM.DD)
                    date_match = re.search(r'(\d{4}[-.]?\d{1,2}[-.]?\d{1,2})', date_text)
                    if date_match:
                        date = date_match.group(1)
                
                # 첨부파일 여부 확인 (아홉 번째 셀)
                has_attachment = False
                if len(cells) > 8:
                    attach_cell = cells[8]
                    # xi-file 아이콘이나 다운로드 링크 확인
                    if attach_cell.find('i', class_='xi-file') or attach_cell.find('a'):
                        has_attachment = True
                
                logger.debug(f"행 {i}: 공고 발견 - {title[:30]}... (날짜: {date})")
                
                # 공고 정보 구성
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'number': number,
                    'category': category,
                    'application_period': application_period,
                    'notice_number': notice_number,
                    'status': status,
                    'department': department,
                    'date': date,
                    'has_attachment': has_attachment,
                    'notice_idx': notice_idx,
                    'summary': ""
                }
                
                announcements.append(announcement)
                
            except Exception as e:
                logger.error(f"행 {i} 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str, announcement_url: str = None) -> Dict[str, Any]:
        """상세 페이지 파싱 - WMIT 실제 HTML 구조 기반"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 제목 추출
        title = ""
        # 제목 후보들 검색 (h1, h2, h3 순서로)
        for tag in ['h1', 'h2', 'h3', 'h4']:
            title_elem = soup.find(tag)
            if title_elem:
                title_text = title_elem.get_text(strip=True)
                if title_text and len(title_text) > 5:  # 유효한 제목
                    title = title_text
                    logger.debug(f"제목을 {tag} 태그에서 찾음: {title[:50]}...")
                    break
        
        # 백업: 상세 페이지 특정 클래스에서 제목 찾기
        if not title:
            for elem in soup.find_all(['div', 'p', 'span']):
                text = elem.get_text(strip=True)
                if len(text) > 10 and len(text) < 200:  # 제목 같은 길이
                    classes = elem.get('class', [])
                    if any('title' in cls.lower() or 'subject' in cls.lower() for cls in classes):
                        title = text
                        break
        
        # 본문 내용 추출
        content = ""
        
        # 방법 1: 본문이 있는 div나 section에서 찾기
        content_candidates = []
        for elem in soup.find_all(['div', 'section', 'article']):
            elem_text = elem.get_text(strip=True)
            if len(elem_text) > 100:  # 충분히 긴 텍스트
                # 메뉴나 네비게이션이 아닌 본문 같은 내용 필터링
                if not any(nav_word in elem_text for nav_word in ['목록', '이전', '다음', '메뉴', '로그인', '회원가입']):
                    content_candidates.append((len(elem_text), elem_text))
        
        # 가장 긴 텍스트를 본문으로 선택
        if content_candidates:
            content_candidates.sort(key=lambda x: x[0], reverse=True)
            content = content_candidates[0][1]
            logger.debug(f"본문 추출: {len(content)}자")
        
        # 방법 2: 백업 - 전체 텍스트에서 본문 부분 추출
        if not content or len(content) < 50:
            all_text = soup.get_text()
            # 본문 시작점 찾기
            content_start_markers = ['공고', '모집', '안내', '신청', '지원', '사업', '접수', '선정', '선발']
            for marker in content_start_markers:
                if marker in all_text:
                    start_idx = all_text.find(marker)
                    content = all_text[start_idx:start_idx+3000]  # 적당한 길이로 제한
                    break
        
        if not content or len(content) < 30:
            logger.warning("본문 영역을 찾을 수 없거나 내용이 부족합니다")
            content = "본문 내용을 추출할 수 없습니다."
        else:
            logger.info(f"본문 추출 성공: {len(content)}자")
        
        # 첨부파일 추출
        attachments = self._extract_attachments(soup, announcement_url)
        
        return {
            'title': title,
            'content': content,
            'attachments': attachments
        }
    
    def _extract_attachments(self, soup: BeautifulSoup, page_url: str = None) -> List[Dict[str, Any]]:
        """첨부파일 추출 - WMIT downloadBizAnnounceFile.do 기반 다운로드"""
        attachments = []
        
        # downloadBizAnnounceFile.do 패턴 링크 찾기
        for link in soup.find_all('a'):
            href = link.get('href', '')
            
            # 파일 다운로드 링크 확인
            if 'downloadBizAnnounceFile.do' in href:
                # 파일명 추출 (링크 텍스트에서)
                filename = link.get_text(strip=True)
                
                # 절대 URL로 변환
                if href.startswith('/'):
                    download_url = f"{self.base_url}{href}"
                else:
                    download_url = urljoin(self.base_url, href)
                
                if filename and download_url:
                    attachments.append({
                        'name': filename,
                        'url': download_url
                    })
                    
                    logger.debug(f"downloadBizAnnounceFile.do 첨부파일 발견: {filename}")
        
        # xi-file 아이콘과 함께 있는 다운로드 링크도 확인
        for icon in soup.find_all('i', class_='xi-file'):
            # 아이콘 근처의 링크 찾기
            parent = icon.parent
            while parent:
                link = parent.find('a')
                if link:
                    href = link.get('href', '')
                    if 'download' in href.lower() or 'file' in href.lower():
                        filename = link.get_text(strip=True) or "첨부파일"
                        download_url = urljoin(self.base_url, href)
                        
                        if download_url:
                            attachments.append({
                                'name': filename,
                                'url': download_url
                            })
                            
                            logger.debug(f"xi-file 아이콘 첨부파일 발견: {filename}")
                    break
                parent = parent.parent
                if parent and parent.name == 'body':  # 너무 위로 올라가지 않도록
                    break
        
        # 파일 확장자가 있는 직접 링크도 확인
        for link in soup.find_all('a'):
            href = link.get('href', '')
            filename = link.get_text(strip=True)
            
            # 파일 확장자가 있는 직접 링크 확인
            if any(ext in href.lower() for ext in ['.pdf', '.hwp', '.doc', '.xls', '.zip', '.jpg', '.png']):
                download_url = urljoin(self.base_url, href)
                
                if filename:
                    attachments.append({
                        'name': filename,
                        'url': download_url
                    })
                    
                    logger.debug(f"직접 다운로드 링크 발견: {filename}")
        
        logger.info(f"총 {len(attachments)}개 첨부파일 발견")
        return attachments
    
    def download_file(self, url: str, save_path: str, filename: str = None) -> bool:
        """파일 다운로드 - WMIT downloadBizAnnounceFile.do 처리"""
        try:
            logger.info(f"파일 다운로드 시도: {url}")
            
            # 강화된 헤더로 다운로드 시도
            download_headers = self.headers.copy()
            download_headers.update({
                'Referer': self.base_url,
                'Accept': '*/*',
            })
            
            response = self.session.get(
                url, 
                headers=download_headers,
                verify=self.verify_ssl,
                stream=True,
                timeout=120
            )
            
            # 응답 상태 확인
            if response.status_code != 200:
                logger.error(f"파일 다운로드 실패 {url}: HTTP {response.status_code}")
                return False
            
            # Content-Type 확인
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' in content_type:
                logger.warning(f"HTML 응답 수신 (파일이 없을 수 있음): {url}")
                # 실제로 HTML 에러 페이지인지 확인
                content_preview = response.content[:500].decode('utf-8', errors='ignore')
                if '<html' in content_preview.lower():
                    logger.error(f"HTML 에러 페이지 수신: {url}")
                    return False
            
            # 파일 저장
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # 파일 크기 확인
            file_size = os.path.getsize(save_path)
            if file_size == 0:
                logger.error(f"다운로드된 파일이 비어있음: {save_path}")
                os.remove(save_path)
                return False
            
            logger.info(f"파일 다운로드 완료: {save_path} ({file_size:,} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"파일 다운로드 중 오류 {url}: {e}")
            return False
    
    def process_announcement(self, announcement: Dict[str, Any], index: int, output_base: str = 'output') -> None:
        """개별 공고 처리 - WMIT 메타데이터 중심 처리"""
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
        
        # 상세 페이지 접근 실패 시 메타데이터만으로 콘텐츠 생성
        if not announcement.get('url') or announcement['url'] == "":
            logger.warning(f"상세 페이지 URL이 없어 메타데이터만 저장: {announcement['title']}")
            detail = {
                'title': announcement['title'],
                'content': "상세 페이지에 접근할 수 없어 목록 페이지의 메타데이터만 수집했습니다.\n\n" +
                          f"**구분**: {announcement.get('category', 'N/A')}\n" +
                          f"**신청기간**: {announcement.get('application_period', 'N/A')}\n" +
                          f"**공고번호**: {announcement.get('notice_number', 'N/A')}\n" +
                          f"**진행상태**: {announcement.get('status', 'N/A')}\n" +
                          f"**담당부서**: {announcement.get('department', 'N/A')}\n" +
                          f"**등록일**: {announcement.get('date', 'N/A')}\n" +
                          f"**첨부파일**: {'있음' if announcement.get('has_attachment') else '없음'}",
                'attachments': []
            }
        else:
            # 상세 페이지 가져오기 시도
            response = self.get_page(announcement['url'])
            if not response or response.status_code >= 400:
                logger.warning(f"상세 페이지 접근 실패 (HTTP {response.status_code if response else 'None'}): {announcement['title']}")
                # 메타데이터만으로 콘텐츠 생성
                detail = {
                    'title': announcement['title'],
                    'content': f"상세 페이지 접근 실패 (HTTP {response.status_code if response else 'None'}). 목록 페이지의 메타데이터를 수집했습니다.\n\n" +
                              f"**구분**: {announcement.get('category', 'N/A')}\n" +
                              f"**신청기간**: {announcement.get('application_period', 'N/A')}\n" +
                              f"**공고번호**: {announcement.get('notice_number', 'N/A')}\n" +
                              f"**진행상태**: {announcement.get('status', 'N/A')}\n" +
                              f"**담당부서**: {announcement.get('department', 'N/A')}\n" +
                              f"**등록일**: {announcement.get('date', 'N/A')}\n" +
                              f"**첨부파일**: {'있음' if announcement.get('has_attachment') else '없음'}",
                    'attachments': []
                }
            else:
                try:
                    # 상세 내용 파싱
                    detail = self.parse_detail_page(response.text, announcement['url'])
                    logger.info(f"상세 페이지 파싱 완료 - 내용길이: {len(detail['content'])}, 첨부파일: {len(detail['attachments'])}")
                except Exception as e:
                    logger.error(f"상세 페이지 파싱 실패: {e}")
                    # 메타데이터만으로 콘텐츠 생성
                    detail = {
                        'title': announcement['title'],
                        'content': f"상세 페이지 파싱 실패: {str(e)}. 목록 페이지의 메타데이터를 수집했습니다.\n\n" +
                                  f"**구분**: {announcement.get('category', 'N/A')}\n" +
                                  f"**신청기간**: {announcement.get('application_period', 'N/A')}\n" +
                                  f"**공고번호**: {announcement.get('notice_number', 'N/A')}\n" +
                                  f"**진행상태**: {announcement.get('status', 'N/A')}\n" +
                                  f"**담당부서**: {announcement.get('department', 'N/A')}\n" +
                                  f"**등록일**: {announcement.get('date', 'N/A')}\n" +
                                  f"**첨부파일**: {'있음' if announcement.get('has_attachment') else '없음'}",
                        'attachments': []
                    }
        
        # 메타 정보 생성
        meta_info = self._create_meta_info(announcement)
        
        # 본문 저장
        content_path = os.path.join(folder_path, 'content.md')
        with open(content_path, 'w', encoding='utf-8') as f:
            f.write(meta_info + detail['content'])
        
        logger.info(f"내용 저장 완료: {content_path}")
        
        # 첨부파일 다운로드 (있는 경우에만)
        if detail['attachments']:
            self._download_attachments(detail['attachments'], folder_path)
        else:
            logger.info("첨부파일이 없거나 접근할 수 없습니다")
        
        # 처리된 제목으로 추가
        self.add_processed_title(announcement['title'])
        
        # 요청 간 대기
        if self.delay_between_requests > 0:
            time.sleep(self.delay_between_requests)
    
    def _create_meta_info(self, announcement: Dict[str, Any]) -> str:
        """WMIT 메타 정보 생성"""
        meta_lines = [f"# {announcement['title']}", ""]
        
        # WMIT 특화 메타 정보
        if 'number' in announcement and announcement['number']:
            meta_lines.append(f"**번호**: {announcement['number']}")
        if 'category' in announcement and announcement['category']:
            meta_lines.append(f"**구분**: {announcement['category']}")
        if 'application_period' in announcement and announcement['application_period']:
            meta_lines.append(f"**신청기간**: {announcement['application_period']}")
        if 'notice_number' in announcement and announcement['notice_number']:
            meta_lines.append(f"**공고번호**: {announcement['notice_number']}")
        if 'status' in announcement and announcement['status']:
            meta_lines.append(f"**진행상태**: {announcement['status']}")
        if 'department' in announcement and announcement['department']:
            meta_lines.append(f"**담당부서**: {announcement['department']}")
        if 'date' in announcement and announcement['date']:
            meta_lines.append(f"**등록일**: {announcement['date']}")
        if 'has_attachment' in announcement and announcement['has_attachment']:
            meta_lines.append(f"**첨부파일**: 있음")
        if 'summary' in announcement and announcement['summary']:
            meta_lines.append(f"**요약**: {announcement['summary']}")
        
        meta_lines.extend([
            f"**원본 URL**: {announcement['url']}",
            "",
            "---",
            ""
        ])
        
        return "\n".join(meta_lines)

# 하위 호환성을 위한 별칭
WMITScraper = EnhancedWMITScraper