# -*- coding: utf-8 -*-
"""
수출바우처 Enhanced 스크래퍼
사이트: https://www.exportvoucher.com/portal/board/boardList?bbs_id=1

사이트 분석 결과:
1. 표준 테이블 기반 게시판 구조
2. 페이지네이션: ?pageNo=2 형태
3. JavaScript 기반 상세 페이지 접근: javascript:void(0)
4. 파일 다운로드: /common.FileDownload.do?file_id=FILE_XXX&sec_code=XXX
5. 테이블 구조: 번호, 제목, 등록일, 조회수 (4컬럼)
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

class EnhancedExportVoucherScraper(StandardTableScraper):
    """수출바우처 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://www.exportvoucher.com"
        self.list_url = "https://www.exportvoucher.com/portal/board/boardList?bbs_id=1"
        
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
            logger.info("Export Voucher 세션 초기화 중...")
            # 메인 페이지에 접속하여 세션 쿠키 획득
            response = self.session.get(self.list_url, verify=self.verify_ssl, timeout=10)
            if response.status_code == 200:
                self._session_initialized = True
                logger.info("Export Voucher 세션 초기화 성공")
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
        
        # Fallback: Export Voucher 특화 로직
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&pageNo={page_num}"
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: Export Voucher 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """Export Voucher 사이트 특화된 파싱 로직"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        logger.info("Export Voucher 목록 페이지 파싱 시작")
        
        # Export Voucher의 표준 테이블 구조 찾기
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
                if len(cells) < 4:  # 번호, 제목, 등록일, 조회수
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
                href = title_link.get('href', '')
                detail_url = None
                
                # Export Voucher는 JavaScript로 상세 페이지 접근 (goDetail 함수 사용)
                if 'javascript:void(0)' in href or href == 'javascript:void(0)':
                    # onclick에서 ntt_id 추출: goDetail(xxxx) 패턴
                    ntt_id = None
                    if onclick and 'goDetail(' in onclick:
                        # goDetail(9325) 형태에서 숫자 추출
                        import re
                        match = re.search(r'goDetail\((\d+)\)', onclick)
                        if match:
                            ntt_id = match.group(1)
                            logger.debug(f"onclick에서 ntt_id 추출: {ntt_id}")
                    
                    # onclick에서 추출 실패 시 번호 사용 (숫자인 경우만)
                    if not ntt_id and number.isdigit():
                        ntt_id = number
                        logger.debug(f"번호를 ntt_id로 사용: {ntt_id}")
                    
                    # ntt_id가 있으면 상세 페이지 URL 생성
                    if ntt_id:
                        detail_url = f"{self.base_url}/portal/board/boardView?pageNo=1&bbs_id=1&ntt_id={ntt_id}&active_menu_cd=EZ005004000&search_type=SJ&search_text=&start_date=&end_date=&pageUnit=10"
                        logger.debug(f"상세 URL 생성: ntt_id={ntt_id}")
                    else:
                        logger.warning(f"ntt_id를 찾을 수 없음: title={title}, onclick={onclick}, number={number}")
                else:
                    if href and href != '#':
                        detail_url = urljoin(self.base_url, href)
                
                # 등록일
                date = cells[2].get_text(strip=True)
                
                # 조회수
                views = cells[3].get_text(strip=True)
                
                # 첨부파일 여부 확인 (아이콘이나 텍스트로 표시될 수 있음)
                has_attachment = False
                # 첨부파일 아이콘이나 텍스트 확인
                for cell in cells:
                    cell_text = cell.get_text(strip=True)
                    if '첨부' in cell_text or 'attach' in cell_text.lower():
                        has_attachment = True
                        break
                    # 이미지 태그로 첨부파일 표시 확인
                    img_tags = cell.find_all('img')
                    for img in img_tags:
                        alt = img.get('alt', '')
                        src = img.get('src', '')
                        if '첨부' in alt or 'attach' in alt.lower() or 'file' in src.lower():
                            has_attachment = True
                            break
                
                announcement = {
                    'title': title,
                    'url': detail_url,
                    'date': date,
                    'views': views,
                    'number': number,
                    'has_attachment': has_attachment,
                    'onclick': onclick,  # JavaScript 이벤트 정보 보존
                    'href': href  # 원본 href 보존
                }
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱: {title[:50]}... - 번호: {number}")
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"Export Voucher 목록에서 {len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str) -> Dict[str, Any]:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 본문 내용 추출
        content = ""
        
        # Export Voucher 상세 페이지의 본문 구조 파악
        # 1. 일반적인 본문 영역 클래스들 시도
        content_selectors = [
            '.board_view',
            '.view_content', 
            '.board_content',
            '.content',
            '.view_con',
            '.board_con'
        ]
        
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                content = self.h.handle(str(content_area))
                logger.debug(f"본문을 {selector} 선택자로 찾음")
                break
        
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
                    if not any(keyword in div_text for keyword in ['등록일', '조회수', '첨부파일', 'HOME', '로그인']):
                        max_text_length = len(div_text)
                        best_div = div
            
            if best_div:
                content = self.h.handle(str(best_div))
                logger.info(f"대체 방법으로 본문 추출 완료 (길이: {len(content)})")
            else:
                # 최후 수단: 전체 페이지에서 텍스트 추출
                content = "상세 내용을 추출할 수 없습니다."
                logger.warning("본문 추출에 실패했습니다")
        
        # 첨부파일 정보 추출
        attachments = self._extract_attachments(soup)
        
        logger.info(f"상세 페이지 파싱 완료 - 내용길이: {len(content)}, 첨부파일: {len(attachments)}개")
        
        return {
            'content': content,
            'attachments': attachments
        }
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """상세 페이지에서 첨부파일 정보 추출"""
        attachments = []
        
        # Export Voucher는 JavaScript로 첨부파일을 동적 로드하므로 API 직접 호출
        logger.debug("첨부파일 추출 시작")
        
        # 1단계: JavaScript로 로드되는 첨부파일 영역 찾기
        # data-doc-id 속성이 있는 div 찾기
        file_containers = soup.find_all('div', {'data-doc-id': True})
        logger.debug(f"data-doc-id가 있는 컨테이너 {len(file_containers)}개 발견")
        
        for container in file_containers:
            doc_id = container.get('data-doc-id')
            logger.debug(f"DOC ID 발견: {doc_id}")
            
            # File2List API로 실제 파일 정보 가져오기
            api_files = self._get_files_from_api(doc_id)
            if api_files:
                attachments.extend(api_files)
                logger.debug(f"DOC ID {doc_id}에 대해 API에서 {len(api_files)}개 파일 획득")
        
        # 2단계: 폴백 - 일반적인 FileDownload.do 링크 찾기 (공통 파일 제외)
        if not attachments:
            logger.debug("API 호출 실패, 일반 링크 방식으로 폴백")
            
            all_file_links = soup.find_all('a', href=lambda x: x and 'FileDownload.do' in x)
            logger.debug(f"전체 FileDownload.do 링크 {len(all_file_links)}개 발견")
            
            for link in all_file_links:
                href = link.get('href', '')
                
                # 공통 파일들 제외 (정산가이드, 관리지침)
                if ('FILE_000000005266736' not in href and 
                    'FILE_000000005255759' not in href):
                    
                    # 헤더/푸터 영역이 아닌지 확인
                    is_in_header_footer = any(
                        ancestor.name in ['banner', 'contentinfo', 'nav', 'navigation', 'header', 'footer'] 
                        for ancestor in link.parents
                    )
                    
                    if not is_in_header_footer:
                        name = link.get_text(strip=True) or "첨부파일"
                        file_url = urljoin(self.base_url, href)
                        
                        attachment = {
                            'name': name,
                            'url': file_url,
                            'download_type': 'direct_download',
                            'original_href': href
                        }
                        attachments.append(attachment)
                        logger.debug(f"일반 첨부파일 링크 발견: {name}")
        
        logger.debug(f"최종 {len(attachments)}개 첨부파일")
        return attachments
    
    def _get_files_from_api(self, doc_id: str) -> List[Dict[str, Any]]:
        """File2List API로 실제 파일 정보 가져오기"""
        try:
            api_url = f"{self.base_url}/common/File2List"
            logger.debug(f"File2List API 호출: {api_url}, DOC ID: {doc_id}")
            
            # GET 요청으로 파일 목록 가져오기
            response = self.session.get(
                api_url,
                params={'docId': doc_id},
                verify=self.verify_ssl,
                timeout=10
            )
            
            if response.status_code == 200:
                try:
                    file_data = response.json()
                    logger.debug(f"API에서 {len(file_data)}개 파일 정보 획득")
                    
                    attachments = []
                    for file_info in file_data:
                        if 'fileName' in file_info and 'fileId' in file_info and 'secCode' in file_info:
                            download_url = f"{self.base_url}/common.FileDownload.do?file_id={file_info['fileId']}&sec_code={file_info['secCode']}"
                            
                            attachment = {
                                'name': file_info['fileName'],
                                'url': download_url,
                                'download_type': 'direct_download',
                                'file_id': file_info['fileId'],
                                'sec_code': file_info['secCode'],
                                'file_size': file_info.get('fileSize', 0)
                            }
                            attachments.append(attachment)
                            logger.debug(f"API 파일: {file_info['fileName']} (ID: {file_info['fileId']}, sec_code: {file_info['secCode']})")
                    
                    return attachments
                    
                except json.JSONDecodeError as e:
                    logger.error(f"File2List API JSON 파싱 실패: {e}")
                    logger.debug(f"응답 내용: {response.text[:200]}")
                    
            else:
                logger.warning(f"File2List API 호출 실패: HTTP {response.status_code}")
                logger.debug(f"응답: {response.text[:200]}")
                
        except Exception as e:
            logger.error(f"File2List API 호출 중 오류: {e}")
        
        return []
    
    def download_file(self, url: str, save_path: str, content_type: str = None) -> bool:
        """파일 다운로드 - Export Voucher 특화 처리"""
        try:
            # 세션 초기화 확인
            if not self._initialize_session():
                logger.error("세션 초기화에 실패했습니다.")
                return False
            
            logger.info(f"Export Voucher 파일 다운로드 시작: {url}")
            
            # 파일 다운로드 요청
            response = self.session.get(
                url,
                verify=self.verify_ssl,
                stream=True,
                timeout=30
            )
            
            if response.status_code == 200:
                # Content-Type 확인
                content_type = response.headers.get('content-type', '')
                if 'text/html' in content_type.lower():
                    logger.error(f"HTML 응답을 받았습니다. 파일 다운로드 실패: {url}")
                    # HTML 응답 내용을 로그로 출력 (디버깅용)
                    html_content = response.text[:500] if response.text else "(빈 응답)"
                    logger.debug(f"HTML 응답 내용: {html_content}...")
                    return False
                
                # 파일명 추출
                filename = self._extract_filename_from_response(response, save_path)
                if filename and filename != os.path.basename(save_path):
                    final_save_path = os.path.join(os.path.dirname(save_path), filename)
                else:
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
                logger.error(f"다운로드 실패 - HTTP {response.status_code}: {url}")
                return False
                
        except Exception as e:
            logger.error(f"Export Voucher 파일 다운로드 중 오류: {e}")
            import traceback
            logger.debug(f"상세 오류: {traceback.format_exc()}")
            return False
    
    def _extract_filename_from_response(self, response: requests.Response, default_path: str) -> str:
        """응답에서 파일명 추출 (Export Voucher UTF-8 인코딩 처리)"""
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


# 하위 호환성을 위한 별칭
ExportVoucherScraper = EnhancedExportVoucherScraper