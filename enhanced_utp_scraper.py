# -*- coding: utf-8 -*-
"""
UTP (울산테크노파크) 향상된 스크래퍼
- AJAX API 기반 사이트
- 지원사업공고 수집
"""

import requests
import json
import os
import logging
from urllib.parse import urljoin, urlparse, unquote
from enhanced_base_scraper import AjaxAPIScraper
from bs4 import BeautifulSoup
import re
import time

logger = logging.getLogger(__name__)

class EnhancedUTPScraper(AjaxAPIScraper):
    """UTP (울산테크노파크) 전용 스크래퍼 - AJAX API 기반"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.utp.or.kr"
        self.list_url = "https://www.utp.or.kr/include/contents.php?mnuno=M0000018&menu_group=1&sno=0102"
        self.api_url = "https://www.utp.or.kr/proc/re_ancmt/list.php"
        self.download_base_url = "https://www.utp.or.kr/proc/re_ancmt/download.php"
        
        # UTP 사이트별 설정
        self.verify_ssl = True
        self.default_encoding = 'utf-8'
        self.timeout = 30
        self.delay_between_requests = 1
        self.delay_between_pages = 2
        
        # 헤더 설정 - Referer 추가
        self.headers.update({
            'Referer': self.list_url,
            'X-Requested-With': 'XMLHttpRequest'
        })
        self.session.headers.update(self.headers)
        
        logger.info("UTP 스크래퍼 초기화 완료")
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 API URL 반환 (실제로는 API 엔드포인트 사용)"""
        return self.api_url
    
    def _get_page_announcements(self, page_num: int) -> list:
        """API를 통한 공고 목록 가져오기"""
        try:
            # API 호출 데이터 구성
            data = {
                'task': 'list',
                'page': str(page_num),
                's_state': '',  # 상태 필터 (전체)
                'sear': ''      # 검색어 (없음)
            }
            
            logger.info(f"페이지 {page_num} API 호출 시작")
            
            # API 호출
            response = self.session.get(
                self.api_url,
                params=data,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            
            if response.status_code != 200:
                logger.error(f"API 호출 실패: HTTP {response.status_code}")
                return []
            
            # JSON 응답 파싱
            try:
                json_data = response.json()
                logger.info(f"API 응답 받음: {json_data.get('code', 'N/A')}")
                
                if json_data.get('code') != 'OK':
                    logger.error(f"API 오류: {json_data.get('msg', '알 수 없는 오류')}")
                    return []
                
                # 공고 목록 추출
                announcements = self.parse_api_response(json_data, page_num)
                logger.info(f"페이지 {page_num}에서 {len(announcements)}개 공고 추출")
                
                return announcements
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON 파싱 실패: {e}")
                return []
                
        except Exception as e:
            logger.error(f"페이지 {page_num} API 호출 중 오류: {e}")
            return []
    
    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱 - 사용되지 않음 (API 사용)"""
        return []
    
    def parse_api_response(self, json_data: dict, page_num: int) -> list:
        """API 응답에서 공고 목록 추출"""
        announcements = []
        
        try:
            data_list = json_data.get('data', [])
            
            for item in data_list:
                try:
                    # 제목과 상세 URL 구성
                    seq = item.get('seq', '')
                    title = item.get('title', '').replace('&amp;', '&')
                    
                    if not title or not seq:
                        continue
                    
                    # 상세 페이지 URL 구성
                    detail_url = f"{self.list_url}&task=view&seq={seq}"
                    
                    # 접수 기간 정보
                    apply_start = item.get('apply_start_dt', '')[:10]
                    apply_end = item.get('apply_end_dt', '')[:10]
                    period = f"{apply_start.replace('-', '.')} ~ {apply_end.replace('-', '.')}" if apply_start and apply_end else ''
                    
                    # 상태 정보
                    status_code = item.get('status', '')
                    status_map = {
                        '1': '접수중',
                        '2': '접수전', 
                        '3': '마감'
                    }
                    status = status_map.get(status_code, '알 수 없음')
                    
                    # 작성일
                    created_dt = item.get('created_dt', '')[:10]
                    date = created_dt.replace('-', '.') if created_dt else ''
                    
                    announcement = {
                        'title': title,
                        'url': detail_url,
                        'seq': seq,
                        'period': period,
                        'status': status,
                        'date': date,
                        'views': item.get('hit_cnt', '0'),
                        'is_notice': item.get('is_gonggi', 'N') == 'Y'
                    }
                    
                    announcements.append(announcement)
                    logger.debug(f"공고 추출: {title[:50]}...")
                    
                except Exception as e:
                    logger.error(f"개별 공고 파싱 중 오류: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"API 응답 파싱 중 오류: {e}")
        
        return announcements
    
    def parse_detail_page(self, html_content: str, detail_url: str = None) -> dict:
        """상세 페이지에서 공고 정보 및 첨부파일 추출 (API 기반)"""
        try:
            # URL에서 seq 추출
            if not detail_url:
                logger.error("상세 페이지 URL이 없습니다")
                return {'content': '', 'attachments': []}
            
            # seq 파라미터 추출
            seq_match = re.search(r'seq=(\d+)', detail_url)
            if not seq_match:
                logger.error("URL에서 seq를 찾을 수 없습니다")
                return {'content': '', 'attachments': []}
            
            seq = seq_match.group(1)
            logger.info(f"상세 페이지 API 호출: seq={seq}")
            
            # 상세 정보 API 호출
            response = self.session.get(
                self.api_url,
                params={
                    'task': 'getItem',
                    'seq': seq
                },
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            
            if response.status_code != 200:
                logger.error(f"상세 정보 API 호출 실패: HTTP {response.status_code}")
                return {'content': '', 'attachments': []}
            
            # JSON 응답 파싱
            json_data = response.json()
            
            if json_data.get('code') != 'OK':
                logger.error(f"상세 정보 API 오류: {json_data.get('msg', '알 수 없는 오류')}")
                return {'content': '', 'attachments': []}
            
            # 상세 정보 추출
            data = json_data.get('data', {})
            files = json_data.get('files', [])
            
            # 본문 내용 구성
            content_parts = []
            
            # 기본 정보
            if data.get('outline'):
                content_parts.append(f"## 사업 개요\n{data['outline']}\n")
            
            if data.get('content'):
                content_parts.append(f"## 상세 내용\n{data['content']}\n")
            
            if data.get('supported_target'):
                content_parts.append(f"## 지원 대상\n{data['supported_target']}\n")
            
            # 접수 기간 정보
            notice_start = data.get('notice_start_date', '')
            notice_end = data.get('notice_end_date', '')
            if notice_start and notice_end:
                content_parts.append(f"## 공고 기간\n{notice_start} ~ {notice_end}\n")
            
            apply_start = data.get('apply_start_dt', '')
            apply_end = data.get('apply_end_dt', '')
            if apply_start and apply_end:
                content_parts.append(f"## 접수 기간\n{apply_start} ~ {apply_end}\n")
            
            # 담당자 정보
            if data.get('contact_info'):
                content_parts.append(f"## 담당자 정보\n{data['contact_info']}\n")
            
            # 외부 링크 정보
            if data.get('platform_no') and data['platform_no'] != '0':
                platform_url = f"https://www.utp.or.kr/lib/bizplatform.lib.php?rq_gonggopgrm={data['platform_no']}"
                content_parts.append(f"## 사업 플랫폼 링크\n{platform_url}\n")
            
            if data.get('rips_no') and data['rips_no'] not in ['', 'null']:
                rips_url = f"http://www.rips.or.kr/rgind/bsarcp/selectBizAnnRecpt.do?taskPostId={data['rips_no']}"
                content_parts.append(f"## RIPS 신청 링크\n{rips_url}\n")
            
            content = '\n'.join(content_parts)
            
            # 첨부파일 정보 추출
            attachments = []
            for file_info in files:
                try:
                    file_name = file_info.get('f_source', '')
                    file_no = file_info.get('f_no', '')
                    re_seq = file_info.get('re_seq', seq)
                    
                    if file_name and file_no:
                        file_url = f"{self.download_base_url}?seq={re_seq}&no={file_no}"
                        
                        attachment = {
                            'filename': file_name,
                            'url': file_url,
                            'file_no': file_no,
                            're_seq': re_seq
                        }
                        
                        attachments.append(attachment)
                        logger.debug(f"첨부파일 추출: {file_name}")
                    
                except Exception as e:
                    logger.error(f"첨부파일 정보 추출 중 오류: {e}")
                    continue
            
            logger.info(f"상세 페이지 파싱 완료 - 내용길이: {len(content)}, 첨부파일: {len(attachments)}")
            
            return {
                'content': content,
                'attachments': attachments
            }
            
        except Exception as e:
            logger.error(f"상세 페이지 파싱 중 오류: {e}")
            return {'content': '', 'attachments': []}
    
    def process_announcement(self, announcement: dict, index: int, output_base: str = 'output'):
        """개별 공고 처리 - UTP API 전용 오버라이드"""
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
        
        # 상세 내용 파싱 - URL 직접 전달
        try:
            detail = self.parse_detail_page("", announcement['url'])
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

    def download_file(self, url: str, save_path: str, attachment_info: dict = None) -> bool:
        """파일 다운로드 - UTP 전용 처리"""
        try:
            logger.info(f"파일 다운로드 시작: {url}")
            
            # 다운로드 헤더 설정
            download_headers = self.headers.copy()
            download_headers['Referer'] = self.list_url
            
            response = self.session.get(
                url,
                headers=download_headers,
                stream=True,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            
            # Content-Disposition에서 파일명 추출 시도
            actual_filename = self._extract_filename(response, save_path)
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
            # 빈 파일이 생성된 경우 삭제
            if os.path.exists(save_path) and os.path.getsize(save_path) == 0:
                try:
                    os.remove(save_path)
                except:
                    pass
            return False


def main():
    """테스트 실행"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    scraper = EnhancedUTPScraper()
    output_dir = "output/utp"
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # 3페이지까지 스크래핑
        scraper.scrape_pages(max_pages=3, output_base=output_dir)
        logger.info("UTP 스크래핑 완료")
    except Exception as e:
        logger.error(f"스크래핑 중 오류 발생: {e}")


if __name__ == "__main__":
    main()