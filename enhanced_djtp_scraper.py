# -*- coding: utf-8 -*-
"""
대전테크노파크(DJTP) Enhanced 스크래퍼 - PDF 뷰어 기반
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

class EnhancedDJTPScraper(StandardTableScraper):
    """대전테크노파크(DJTP) 전용 스크래퍼 - 향상된 버전"""
    
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
        self.base_url = "https://www.djtp.or.kr"
        self.list_url = "https://www.djtp.or.kr/pbanc?mid=a20101000000"
        
        # 사이트 특화 설정
        self.verify_ssl = True  # HTTPS 사이트
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - nPage 파라미터 방식"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: 사이트 특화 로직
        if page_num == 1:
            return self.list_url
        else:
            return f"{self.list_url}&nPage={page_num}&pbancYr=&pgmTpNm=&prgStt=&cgDeptNm=&pbancNm=&bizTpNm="
    
    def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
        """목록 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: 사이트 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """DJTP 특화된 목록 파싱 로직"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # 테이블 찾기
        table = soup.find('table')
        if not table:
            logger.warning("테이블을 찾을 수 없습니다")
            return announcements
        
        # tbody 또는 전체 테이블에서 행 찾기
        tbody = table.find('tbody')
        if tbody:
            rows = tbody.find_all('tr')
            logger.info(f"tbody에서 {len(rows)}개 행 발견")
        else:
            rows = table.find_all('tr')[1:]  # 헤더 제외
            logger.info(f"테이블에서 {len(rows)}개 행 발견 (헤더 제외)")
        
        for i, row in enumerate(rows):
            try:
                cells = row.find_all('td')
                if len(cells) < 7:  # 최소 7개 컬럼 필요
                    logger.debug(f"행 {i}: 컬럼 수 부족 ({len(cells)}개)")
                    continue
                
                # 컬럼 파싱: 번호, 유형, 공고명, 사업신청, 접수기간, 부서, 조회수
                number = cells[0].get_text(strip=True)
                category = cells[1].get_text(strip=True)
                title_cell = cells[2]
                status_cell = cells[3]
                period = cells[4].get_text(strip=True)
                department = cells[5].get_text(strip=True)
                views = cells[6].get_text(strip=True)
                
                # 제목과 PDF 링크 추출
                link_elem = title_cell.find('a')
                if not link_elem:
                    logger.debug(f"행 {i}: 링크 없음")
                    continue
                
                title = link_elem.get_text(strip=True)
                href = link_elem.get('href', '')
                
                # PDF 뷰어 URL에서 실제 PDF 파일 URL 추출
                pdf_url = None
                if 'pdfviewer' in href and 'file=' in href:
                    # file= 파라미터에서 PDF 경로 추출
                    file_match = re.search(r'file=([^#&]+)', href)
                    if file_match:
                        file_path = file_match.group(1)
                        # 절대 URL로 변환
                        if file_path.startswith('/'):
                            pdf_url = f"https://pms.dips.or.kr{file_path}"
                        else:
                            pdf_url = file_path
                
                # 공고 정보 구성
                announcement = {
                    'number': number,
                    'category': category,
                    'title': title,
                    'url': href,  # PDF 뷰어 URL
                    'pdf_url': pdf_url,  # 실제 PDF 파일 URL
                    'status': status_cell.get_text(strip=True),
                    'period': period,
                    'department': department,
                    'views': views,
                    # 첨부파일 정보 - 안전한 파일명 생성
                    'attachments': []
                }
                
                # PDF 첨부파일 추가
                if pdf_url:
                    # 안전한 파일명 생성
                    safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)[:100]  # 100자 제한
                    filename = f"{number}_{safe_title}.pdf"
                    announcement['attachments'] = [{
                        'url': pdf_url, 
                        'filename': filename
                    }]
                
                announcements.append(announcement)
                logger.debug(f"공고 파싱 완료: {title[:50]}...")
                
            except Exception as e:
                logger.error(f"행 {i} 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def parse_detail_page(self, html_content: str, announcement_url: str = None) -> Dict[str, Any]:
        """상세 페이지 파싱 - PDF 뷰어 페이지 처리"""
        # PDF 뷰어의 경우 실제 내용 파싱이 어려우므로 기본 정보만 반환
        # 첨부파일은 목록에서 이미 추출했으므로 여기서는 빈 리스트 반환
        return {
            'content': "PDF 파일로 제공되는 공고입니다. 첨부파일을 다운로드하여 확인해주세요.",
            'attachments': []
        }
    
    def _extract_attachments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """첨부파일 추출 - PDF 파일 중심"""
        # DJTP의 경우 목록에서 이미 PDF URL을 추출하므로 여기서는 빈 리스트 반환
        return []
    
    def process_announcement(self, announcement: Dict[str, Any], index: int, output_base: str = 'output'):
        """개별 공고 처리 - DJTP 특화 버전 (목록에서 추출한 첨부파일 처리)"""
        logger.info(f"공고 처리 중 {index}: {announcement['title']}")
        
        # 폴더 생성
        folder_title = self.sanitize_filename(announcement['title'])[:200]
        folder_name = f"{index:03d}_{folder_title}"
        folder_path = os.path.join(output_base, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        # 상세 페이지 가져오기
        response = self.get_page(announcement['url'])
        if not response:
            logger.error(f"상세 페이지 가져오기 실패: {announcement['title']}")
            return
        
        # 상세 내용 파싱
        try:
            detail = self.parse_detail_page(response.text, announcement['url'])
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
        
        # 첨부파일 다운로드 - 목록에서 추출한 것과 상세에서 추출한 것 합치기
        all_attachments = announcement.get('attachments', []) + detail.get('attachments', [])
        self._download_attachments_djtp(all_attachments, folder_path)
        
        # 처리된 제목으로 추가
        self.add_processed_title(announcement['title'])
        
        # 요청 간 대기
        if self.delay_between_requests > 0:
            time.sleep(self.delay_between_requests)
    
    def _download_attachments_djtp(self, attachments: List[Dict[str, Any]], folder_path: str):
        """DJTP 특화 첨부파일 다운로드"""
        if not attachments:
            logger.info("첨부파일이 없습니다")
            return
        
        logger.info(f"{len(attachments)}개 첨부파일 다운로드 시작")
        attachments_folder = os.path.join(folder_path, 'attachments')
        os.makedirs(attachments_folder, exist_ok=True)
        
        for i, attachment in enumerate(attachments):
            try:
                # filename 또는 name 키 사용
                file_name = attachment.get('filename') or attachment.get('name', f"attachment_{i+1}")
                logger.info(f"  첨부파일 {i+1}: {file_name}")
                
                # 파일명 처리
                clean_filename = self.sanitize_filename(file_name)
                if not clean_filename or clean_filename.isspace():
                    clean_filename = f"attachment_{i+1}.pdf"
                
                file_path = os.path.join(attachments_folder, clean_filename)
                
                # 파일 다운로드
                success = self.download_file(attachment['url'], file_path)
                if not success:
                    logger.warning(f"첨부파일 다운로드 실패: {file_name}")
                
            except Exception as e:
                logger.error(f"첨부파일 처리 중 오류: {e}")
    
    def _create_meta_info(self, announcement: Dict[str, Any]) -> str:
        """DJTP 메타 정보 생성"""
        meta_lines = [f"# {announcement['title']}", ""]
        
        # DJTP 특화 메타 정보
        if 'period' in announcement and announcement['period']:
            meta_lines.append(f"**접수기간**: {announcement['period']}")
        if 'status' in announcement and announcement['status']:
            meta_lines.append(f"**상태**: {announcement['status']}")
        if 'department' in announcement and announcement['department']:
            meta_lines.append(f"**담당부서**: {announcement['department']}")
        if 'category' in announcement and announcement['category']:
            meta_lines.append(f"**사업유형**: {announcement['category']}")
        if 'views' in announcement and announcement['views']:
            meta_lines.append(f"**조회수**: {announcement['views']}")
        
        meta_lines.extend([
            f"**원본 URL**: {announcement['url']}",
            "",
            "---",
            ""
        ])
        
        return "\n".join(meta_lines)
    
    def download_file(self, url: str, save_path: str) -> bool:
        """파일 다운로드 - PDF 파일 특화"""
        try:
            logger.info(f"PDF 파일 다운로드 시작: {url}")
            
            # PDF 파일 다운로드 (스트리밍)
            response = self.session.get(url, stream=True, verify=self.verify_ssl, timeout=60)
            response.raise_for_status()
            
            # Content-Type 확인
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' not in content_type and 'application/octet-stream' not in content_type:
                logger.warning(f"PDF가 아닌 파일 타입: {content_type}")
            
            # 파일 크기 확인
            content_length = response.headers.get('content-length')
            if content_length:
                file_size = int(content_length)
                logger.info(f"파일 크기: {file_size:,} bytes")
            
            # 디렉토리 생성
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # 파일 저장
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # 다운로드 완료 확인
            if os.path.exists(save_path):
                actual_size = os.path.getsize(save_path)
                logger.info(f"다운로드 완료: {save_path} ({actual_size:,} bytes)")
                return True
            else:
                logger.error("파일 저장 실패")
                return False
                
        except requests.RequestException as e:
            logger.error(f"PDF 다운로드 실패 {url}: {e}")
            return False
        except Exception as e:
            logger.error(f"파일 저장 중 오류 {save_path}: {e}")
            return False

# 하위 호환성을 위한 별칭
DJTPScraper = EnhancedDJTPScraper