# -*- coding: utf-8 -*-
"""
한국의료기기안전정보원(KMEDIHUB) Enhanced 스크래퍼
사이트: https://www.kmedihub.re.kr/index.do?menu_id=00000063

사이트 분석 결과:
1. 표준 테이블 기반 게시판 구조
2. 페이지네이션: ?pageIndex=2 형태
3. JavaScript 기반 파일 다운로드: fn_egov_downFile('FILE_ID','INDEX')
4. JavaScript 기반 상세 페이지 접근
5. 첨부파일 정보가 목록에 표시됨
6. UTF-8 인코딩
"""

import requests
from bs4 import BeautifulSoup
import os
import time
import html2text
from urllib.parse import urljoin, parse_qs, urlparse, unquote
import re
import json
import logging
from enhanced_base_scraper import StandardTableScraper
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class EnhancedKMEDIHUBScraper(StandardTableScraper):
    """한국의료기기안전정보원(KMEDIHUB) 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://www.kmedihub.re.kr"
        self.list_url = "https://www.kmedihub.re.kr/index.do?menu_id=00000063"
        
        # 사이트 특화 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        
        # 헤더 설정
        self.headers.update({
            'Referer': self.base_url,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        self.session.headers.update(self.headers)
        
        # 세션 초기화 상태
        self._session_initialized = False
    
    def _initialize_session(self):
        """세션 초기화 - 메인 페이지 방문으로 쿠키 획득"""
        if self._session_initialized:
            return True
            
        try:
            logger.info("KMEDIHUB 세션 초기화 중...")
            # 메인 페이지에 접속하여 세션 쿠키 획득
            response = self.session.get(self.list_url, verify=self.verify_ssl, timeout=10)
            if response.status_code == 200:
                self._session_initialized = True
                logger.info("KMEDIHUB 세션 초기화 성공")
                return True
            else:
                logger.error(f"세션 초기화 실패: HTTP {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"세션 초기화 중 오류: {e}")
            return False
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - 설정 주입과 Fallback 패턴"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: KMEDIHUB 특화 로직
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&pageIndex={page_num}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: KMEDIHUB 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """KMEDIHUB 사이트 특화된 파싱 로직"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        logger.info("KMEDIHUB 목록 페이지 파싱 시작")
        
        # KMEDIHUB의 표준 테이블 구조
        table = soup.find('table')
        if not table:
            logger.warning("테이블을 찾을 수 없습니다")
            logger.debug(f"HTML 구조 확인: {str(soup)[:500]}...")
            return announcements
        
        tbody = table.find('tbody')
        if not tbody:
            logger.warning("테이블 본문(tbody)을 찾을 수 없습니다")
            return announcements
        
        rows = tbody.find_all('tr')
        logger.info(f"테이블에서 {len(rows)}개 행 발견")
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 6:  # 번호, 제목, 부서명, 등록일, 첨부, 조회
                    continue
                
                # 번호
                number = cells[0].get_text(strip=True)
                
                # 제목 및 링크
                title_cell = cells[1]
                title_link = title_cell.find('a')
                if not title_link:
                    continue
                
                title = title_link.get_text(strip=True)
                
                # JavaScript 링크에서 상세 페이지 접근 방법 추출
                onclick = title_link.get('onclick', '')
                detail_url = None
                
                # JavaScript 이벤트가 있는 경우 상세 페이지 URL 생성
                if 'javascript:' in onclick:
                    # KMEDIHUB는 JavaScript로 상세 페이지 접근하므로 목록의 첨부파일 정보를 활용
                    detail_url = None  # JavaScript 기반이므로 상세 페이지 접근 불가
                else:
                    href = title_link.get('href')
                    if href:
                        detail_url = urljoin(self.base_url, href)
                
                # 부서명/작성자
                author = cells[2].get_text(strip=True)
                
                # 등록일
                date = cells[3].get_text(strip=True)
                
                # 첨부파일 정보 추출
                attachment_cell = cells[4]
                attachments = self._extract_attachments_from_list(attachment_cell)
                has_attachment = len(attachments) > 0
                
                # 조회수
                views = cells[5].get_text(strip=True)
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'author': author,
                    'date': date,
                    'views': views,
                    'number': number,
                    'has_attachment': has_attachment,
                    'attachments': attachments,  # 목록에서 추출된 첨부파일 정보
                    'onclick': onclick  # JavaScript 이벤트 정보 보존
                }
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱: {title[:50]}... - 번호: {number}")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"KMEDIHUB 목록에서 {len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def _extract_attachments_from_list(self, attachment_cell) -> List[Dict[str, Any]]:
        """목록 페이지에서 첨부파일 정보 추출"""
        attachments = []
        
        # 첨부파일 링크들을 찾기
        attachment_links = attachment_cell.find_all('a')
        
        for link in attachment_links:
            try:
                href = link.get('href', '')
                name = link.get_text(strip=True)
                
                # 링크의 title 속성에서도 파일명 확인
                title = link.get('title', '')
                if title and len(title) > len(name):
                    name = title
                
                # img 태그 안의 alt 속성에서 파일명 확인
                img = link.find('img')
                if img and img.get('alt'):
                    alt_text = img.get('alt', '')
                    if len(alt_text) > len(name):
                        name = alt_text
                
                # fn_egov_downFile 함수 호출 패턴 확인
                if 'fn_egov_downFile' in href:
                    # javascript:fn_egov_downFile('FILE_000000000012926','0') 패턴 파싱
                    match = re.search(r"fn_egov_downFile\('([^']+)','([^']+)'\)", href)
                    if match:
                        file_id = match.group(1)
                        file_index = match.group(2)
                        
                        attachment = {
                            'name': name,
                            'file_id': file_id,
                            'file_index': file_index,
                            'download_type': 'egov_function',
                            'original_href': href
                        }
                        
                        attachments.append(attachment)
                        logger.debug(f"KMEDIHUB 첨부파일 발견 (목록): {name}")
                
            except Exception as e:
                logger.error(f"첨부파일 추출 중 오류: {e}")
                continue
        
        return attachments
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 내용 추출
        content = ""
        
        # KMEDIHUB 상세 페이지의 본문 구조 파악
        # 일반적으로 definition 태그나 특정 클래스를 가진 div에서 본문을 추출
        
        # 1. definition 태그에서 글내용 찾기
        content_def = soup.find('definition')
        if content_def:
            content = self.h.handle(str(content_def))
            logger.debug("본문을 definition 태그에서 추출")
        
        # 2. 본문이 없으면 다른 방법으로 시도
        if not content or len(content.strip()) < 50:
            # 텍스트가 많은 div 찾기
            all_divs = soup.find_all('div')
            best_div = None
            max_text_length = 0
            
            for div in all_divs:
                div_text = div.get_text(strip=True)
                if len(div_text) > max_text_length and len(div_text) > 50:
                    # 단순한 메타정보가 아닌지 확인
                    if not any(keyword in div_text for keyword in ['부서명', '등록일', '조회수', '첨부파일']):
                        max_text_length = len(div_text)
                        best_div = div
            
            if best_div:
                content = self.h.handle(str(best_div))
                logger.info(f"대체 방법으로 본문 추출 완료 (길이: {len(content)})")
            else:
                # 최후 수단: 전체 페이지에서 텍스트 추출
                content = "상세 내용을 추출할 수 없습니다."
                logger.warning("본문 추출에 실패했습니다")
        
        # 첨부파일 정보 추출 (상세 페이지에서)
        attachments = self._extract_attachments_from_detail(soup)
        
        logger.info(f"상세 페이지 파싱 완료 - 내용길이: {len(content)}, 첨부파일: {len(attachments)}개")
        
        return {
            'content': content,
            'attachments': attachments
        }
    
    def _extract_attachments_from_detail(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """상세 페이지에서 첨부파일 정보 추출"""
        attachments = []
        
        # 첨부파일 목록을 찾기 (여러 가지 방법 시도)
        attachment_containers = []
        
        # 1. definition 태그에서 첨부파일 찾기
        attachment_defs = soup.find_all('definition')
        for def_tag in attachment_defs:
            attachment_links = def_tag.find_all('a')
            if attachment_links:
                attachment_containers.extend(attachment_links)
        
        # 2. fn_egov_downFile 함수를 포함하는 모든 링크 찾기
        all_links = soup.find_all('a', href=lambda x: x and 'fn_egov_downFile' in x)
        attachment_containers.extend(all_links)
        
        for link in attachment_containers:
            try:
                href = link.get('href', '')
                name = link.get_text(strip=True)
                
                # 파일명에서 바이트 정보 제거
                if '[' in name and 'byte]' in name:
                    # "[743941 byte]" 패턴 제거
                    name = re.sub(r'\s*\[\d+\s*byte\]', '', name)
                
                if not name or len(name) < 3:
                    continue
                
                # fn_egov_downFile 함수 호출 패턴 확인
                if 'fn_egov_downFile' in href:
                    match = re.search(r"fn_egov_downFile\('([^']+)','([^']+)'\)", href)
                    if match:
                        file_id = match.group(1)
                        file_index = match.group(2)
                        
                        attachment = {
                            'name': name,
                            'file_id': file_id,
                            'file_index': file_index,
                            'download_type': 'egov_function',
                            'original_href': href
                        }
                        
                        attachments.append(attachment)
                        logger.debug(f"KMEDIHUB 첨부파일 발견 (상세): {name}")
                
            except Exception as e:
                logger.error(f"첨부파일 추출 중 오류: {e}")
                continue
        
        logger.info(f"총 {len(attachments)}개 첨부파일 발견")
        return attachments
    
    def download_file(self, url: str, save_path: str, content_type: str = None) -> bool:
        """파일 다운로드 - KMEDIHUB 특화 처리"""
        try:
            # KMEDIHUB egov 파일 다운로드 처리
            if 'fn_egov_downFile' in url:
                return self._download_egov_file(url, save_path)
            else:
                # 일반적인 파일 다운로드
                return super().download_file(url, save_path, content_type)
            
        except Exception as e:
            logger.error(f"KMEDIHUB 파일 다운로드 실패 {url}: {e}")
            return False
    
    def _download_egov_file(self, javascript_url: str, save_path: str) -> bool:
        """KMEDIHUB egov 시스템 파일 다운로드 - 수정된 버전"""
        try:
            # 세션 초기화 확인
            if not self._initialize_session():
                logger.error("세션 초기화에 실패했습니다.")
                return False
                
            # JavaScript 함수에서 파라미터 추출
            match = re.search(r"fn_egov_downFile\('([^']+)','([^']+)'\)", javascript_url)
            if not match:
                logger.error(f"JavaScript 함수 파라미터를 추출할 수 없습니다: {javascript_url}")
                return False
            
            file_id = match.group(1)
            file_index = match.group(2)
            
            # 실제 KMEDIHUB egov 다운로드 URL 구성 (GET 방식)
            # 실제 JavaScript: window.open("/icms/cmm/fms/FileDown.do?atchFileId="+atchFileId+"&fileSn="+fileSn+"")
            download_url = f"{self.base_url}/icms/cmm/fms/FileDown.do?atchFileId={file_id}&fileSn={file_index}"
            
            logger.info(f"KMEDIHUB egov 파일 다운로드 시작: {file_id}[{file_index}]")
            logger.debug(f"다운로드 URL: {download_url}")
            
            # GET 요청으로 변경 (실제 JavaScript 방식과 동일)
            response = self.session.get(
                download_url,
                verify=self.verify_ssl,
                stream=True,
                timeout=30
            )
            
            if response.status_code == 200:
                # Content-Type 확인
                content_type = response.headers.get('content-type', '')
                if 'text/html' in content_type.lower():
                    logger.error(f"HTML 응답을 받았습니다. 파일 다운로드 실패: {download_url}")
                    # HTML 응답 내용을 로그로 출력 (디버깅용)
                    html_content = response.text[:500] if response.text else "(빈 응답)"
                    logger.debug(f"HTML 응답 내용: {html_content}...")
                    return False
                
                # 파일명 추출
                filename = self._extract_filename_from_response(response, save_path)
                if filename and filename != os.path.basename(save_path):
                    final_save_path = os.path.join(os.path.dirname(save_path), filename)
                else:
                    # Content-Disposition에서 파일명을 얻지 못한 경우 기본 파일명 사용
                    final_save_path = save_path
                
                # 디렉토리 생성
                os.makedirs(os.path.dirname(final_save_path), exist_ok=True)
                
                # 파일 저장
                with open(final_save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                file_size = os.path.getsize(final_save_path)
                logger.info(f"다운로드 완료: {final_save_path} ({file_size:,} bytes)")
                return True
            else:
                logger.error(f"다운로드 실패 - HTTP {response.status_code}: {download_url}")
                return False
                
        except Exception as e:
            logger.error(f"KMEDIHUB egov 파일 다운로드 중 오류: {e}")
            import traceback
            logger.debug(f"상세 오류: {traceback.format_exc()}")
            return False
    
    def _extract_filename_from_response(self, response: requests.Response, default_path: str) -> str:
        """응답에서 파일명 추출 (KMEDIHUB UTF-8 인코딩 처리)"""
        # Content-Disposition 헤더에서 파일명 추출
        content_disposition = response.headers.get('content-disposition', '')
        
        if content_disposition and 'filename=' in content_disposition:
            # RFC 5987 형식 처리 (filename*=UTF-8''%ED%95%9C%EA%B8%80.hwp)
            rfc5987_match = re.search(r"filename\*=([^']*)'([^']*)'(.+)", content_disposition)
            if rfc5987_match:
                encoding, lang, filename = rfc5987_match.groups()
                try:
                    filename = unquote(filename)
                    decoded = filename.encode('latin-1').decode(encoding or 'utf-8')
                    return self.sanitize_filename(decoded)
                except:
                    pass
            
            # 일반적인 filename 파라미터
            filename_match = re.search(r'filename=([^;]+)', content_disposition)
            if filename_match:
                filename = filename_match.group(1).strip().strip('"')
                
                try:
                    # UTF-8 디코딩 시도
                    decoded_filename = filename.encode('latin-1').decode('utf-8')
                    if decoded_filename and not decoded_filename.isspace():
                        clean_filename = self.sanitize_filename(decoded_filename)
                        logger.debug(f"UTF-8 파일명 추출: {clean_filename}")
                        return clean_filename
                except:
                    pass
                
                try:
                    # EUC-KR 디코딩 시도
                    decoded_filename = filename.encode('latin-1').decode('euc-kr')
                    if decoded_filename and not decoded_filename.isspace():
                        clean_filename = self.sanitize_filename(decoded_filename)
                        logger.debug(f"EUC-KR 파일명 추출: {clean_filename}")
                        return clean_filename
                except:
                    pass
                
                try:
                    # URL 디코딩 시도
                    decoded_filename = unquote(filename)
                    if decoded_filename and not decoded_filename.isspace():
                        clean_filename = self.sanitize_filename(decoded_filename)
                        logger.debug(f"URL 디코딩 파일명 추출: {clean_filename}")
                        return clean_filename
                except:
                    pass
                
                # 원본 파일명 사용 (최후 수단)
                clean_filename = self.sanitize_filename(filename)
                logger.debug(f"원본 파일명 사용: {clean_filename}")
                return clean_filename
        
        # 기본 파일명 사용
        default_filename = os.path.basename(default_path)
        logger.debug(f"기본 파일명 사용: {default_filename}")
        return self.sanitize_filename(default_filename)
    
    def process_announcement(self, announcement: Dict[str, Any], index: int, output_dir: str) -> bool:
        """공고 처리 - KMEDIHUB 특화"""
        try:
            title = announcement['title']
            url = announcement.get('url', '')
            
            logger.info(f"공고 처리 중 {index}: {title}")
            
            # 디렉토리 생성
            safe_title = self.sanitize_filename(title)[:100]  # 길이 제한
            announcement_dir = os.path.join(output_dir, f"{index:03d}_{safe_title}")
            os.makedirs(announcement_dir, exist_ok=True)
            
            # 본문 내용
            content = ""
            
            # 상세 페이지가 있으면 접근 (JavaScript가 아닌 경우만)
            if url and url != 'javascript:;' and 'javascript:' not in announcement.get('onclick', ''):
                try:
                    detail_response = self.session.get(url, verify=self.verify_ssl, timeout=10)
                    if detail_response.status_code == 200:
                        detail_data = self.parse_detail_page(detail_response.text)
                        content = detail_data.get('content', '')
                        # 상세 페이지의 첨부파일 정보가 있으면 업데이트
                        if detail_data.get('attachments'):
                            announcement['attachments'] = detail_data['attachments']
                except Exception as e:
                    logger.warning(f"상세 페이지 접근 실패: {e}")
            
            # 기본 정보로 본문 구성
            if not content:
                content = f"# {title}\n\n"
                content += f"**작성자**: {announcement.get('author', '')}\n"
                content += f"**등록일**: {announcement.get('date', '')}\n"
                content += f"**조회수**: {announcement.get('views', '')}\n\n"
                content += "상세 내용을 확인할 수 없습니다.\n"
            
            # 원본 URL 추가
            if url:
                content += f"\n\n**원본 URL**: {url}\n"
            
            # 첨부파일 정보 추가
            attachments = announcement.get('attachments', [])
            if attachments:
                content += f"\n**첨부파일**:\n"
                for att in attachments:
                    content += f"- {att['name']}\n"
            
            # 본문 저장
            content_path = os.path.join(announcement_dir, "content.md")
            with open(content_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"내용 저장 완료: {content_path}")
            
            # 첨부파일 다운로드
            if attachments:
                attachments_dir = os.path.join(announcement_dir, "attachments")
                os.makedirs(attachments_dir, exist_ok=True)
                
                logger.info(f"{len(attachments)}개 첨부파일 다운로드 시작")
                
                for i, attachment in enumerate(attachments, 1):
                    try:
                        attachment_name = attachment.get('name', '')
                        logger.info(f"  첨부파일 {i}: {attachment_name}")
                        
                        # 파일명이 비어있으면 기본 파일명 생성
                        if not attachment_name or len(attachment_name.strip()) < 3:
                            file_id = attachment.get('file_id', 'unknown')
                            file_index = attachment.get('file_index', '0')
                            attachment_name = f"attachment_{file_id}_{file_index}"
                            logger.warning(f"파일명이 비어있어 기본 파일명 사용: {attachment_name}")
                        
                        # egov 함수 기반 다운로드
                        if attachment.get('download_type') == 'egov_function':
                            original_href = attachment.get('original_href', '')
                            if original_href:
                                safe_filename = self.sanitize_filename(attachment_name)
                                file_path = os.path.join(attachments_dir, safe_filename)
                                
                                success = self.download_file(original_href, file_path)
                                if success:
                                    logger.info(f"다운로드 성공: {file_path}")
                                else:
                                    logger.error(f"다운로드 실패: {attachment_name}")
                        
                        # 다운로드 간격
                        time.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"첨부파일 다운로드 중 오류: {e}")
                        continue
            
            return True
            
        except Exception as e:
            logger.error(f"공고 처리 중 오류: {e}")
            return False


# 하위 호환성을 위한 별칭
KMEDIHUBScraper = EnhancedKMEDIHUBScraper