# -*- coding: utf-8 -*-
"""
강릉과학산업진흥원(GSIF) 스크래퍼 - 향상된 아키텍처
Base64 인코딩된 파라미터와 특수한 테이블 구조 처리
"""

from enhanced_base_scraper import StandardTableScraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import base64
import logging
import os

logger = logging.getLogger(__name__)

class EnhancedGSIFScraper(StandardTableScraper):
    """강릉과학산업진흥원 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://mybiz.gsipa.or.kr"
        self.list_url = "https://mybiz.gsipa.or.kr/gsipa/bbs_list.do?code=sub03a&keyvalue=sub03"
        
        # GSIF 특화 설정
        self.verify_ssl = True  # SSL 인증서 검증 사용
        self.default_encoding = 'utf-8'
    
    def get_list_url(self, page_num: int) -> str:
        """페이지 번호에 따른 목록 URL 반환 - Base64 인코딩 파라미터 처리"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: 기존 GSIF 특화 로직
        if page_num == 1:
            return self.list_url
        else:
            # 페이지당 15개씩, startPage 계산
            start_page = (page_num - 1) * 15
            # Base64 인코딩된 파라미터 생성
            params = f"startPage={start_page}&listNo=&table=cs_bbs_data&code=sub03a&search_item=&search_order=&url=sub03a&keyvalue=sub03"
            encoded = base64.b64encode(params.encode('utf-8')).decode('utf-8')
            return f"{self.base_url}/gsipa/bbs_list.do?bbs_data={encoded}||"
    
    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: 기존 GSIF 특화 로직
        return self._parse_list_fallback(html_content)
    
    def _parse_list_fallback(self, html_content: str) -> list:
        """기존 방식의 목록 파싱 (Fallback)"""
        soup = BeautifulSoup(html_content, 'html.parser')
        announcements = []
        
        # GSIF의 특수한 테이블 구조 처리
        table = soup.find('table')
        if not table:
            logger.warning("목록 테이블을 찾을 수 없습니다")
            return announcements
        
        rows = table.find_all('tr')
        logger.info(f"{len(rows)}개 행 발견")
        
        for row in rows:
            try:
                tds = row.find_all('td')
                if len(tds) < 5:  # 헤더 행이거나 데이터가 부족한 경우 스킵
                    continue
                
                # 번호 확인 (첫 번째 td)
                num = tds[0].get_text(strip=True)
                if not num.isdigit():  # 번호가 아닌 경우 스킵
                    continue
                
                # 제목 및 링크 (두 번째 td)
                title_td = tds[1]
                link_elem = title_td.find('a')
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                if not title:
                    continue
                
                # 상세 페이지 URL 추출
                detail_url = self._extract_detail_url(link_elem)
                if not detail_url:
                    continue
                
                announcement = {
                    'num': num,
                    'title': title,
                    'url': detail_url
                }
                
                # 추가 정보 추출
                self._extract_additional_fields(tds, announcement)
                
                announcements.append(announcement)
                
            except Exception as e:
                logger.error(f"행 파싱 중 오류: {e}")
                continue
        
        logger.info(f"{len(announcements)}개 공고 파싱 완료")
        return announcements
    
    def _extract_detail_url(self, link_elem) -> str:
        """상세 페이지 URL 추출 - GSIF 특화"""
        onclick = link_elem.get('onclick', '')
        href = link_elem.get('href', '')
        
        # onclick에서 URL 추출
        if 'bbs_view.do' in onclick:
            match = re.search(r"location\.href='([^']+)'", onclick)
            if match:
                return urljoin(self.base_url, match.group(1))
        
        # href에서 URL 추출
        elif 'bbs_view.do' in href:
            # href가 /로 시작하지 않으면 /gsipa/를 앞에 추가
            if not href.startswith('http'):
                if not href.startswith('/'):
                    href = '/gsipa/' + href
                elif not href.startswith('/gsipa'):
                    href = '/gsipa' + href
            return urljoin(self.base_url, href)
        
        return None
    
    def _extract_additional_fields(self, tds: list, announcement: dict):
        """추가 필드 추출"""
        try:
            # 작성자 (세 번째 td)
            if len(tds) > 2:
                announcement['writer'] = tds[2].get_text(strip=True)
            
            # 날짜 (네 번째 td)
            if len(tds) > 3:
                announcement['date'] = tds[3].get_text(strip=True)
            
            # 조회수 (다섯 번째 td)
            if len(tds) > 4:
                announcement['views'] = tds[4].get_text(strip=True)
        except Exception as e:
            logger.error(f"추가 필드 추출 중 오류: {e}")
    
    def parse_detail_page(self, html_content: str) -> dict:
        """상세 페이지 파싱"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        result = {
            'content': '',
            'attachments': []
        }
        
        try:
            # 본문 추출
            content = self._extract_content(soup)
            result['content'] = content
            
            # 첨부파일 추출
            attachments = self._extract_attachments(soup)
            result['attachments'] = attachments
            
            logger.debug(f"상세 페이지 파싱 완료 - 내용: {len(content)}자, 첨부파일: {len(attachments)}개")
            
        except Exception as e:
            logger.error(f"상세 페이지 파싱 중 오류: {e}")
        
        return result
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """본문 내용 추출 - GSIF 특화"""
        content_area = None
        
        # GSIF의 특수한 테이블 구조에서 본문 찾기
        table = soup.find('table')
        if table:
            rows = table.find_all('tr')
            
            # img_td 클래스를 가진 td 찾기 (본문이 있는 곳)
            content_td = soup.find('td', class_='img_td')
            if content_td:
                content_area = content_td
            elif len(rows) >= 4:
                # 대체 방법: 4번째 행에서 찾기
                content_td = rows[3].find('td')
                if content_td:
                    content_area = content_td
        
        # 다른 일반적인 선택자들도 시도
        if not content_area:
            content_selectors = [
                '.board-view-content',
                '.view-content', 
                '.content',
                '#content',
                '.board-content'
            ]
            
            for selector in content_selectors:
                content_area = soup.select_one(selector)
                if content_area:
                    break
        
        if not content_area:
            # 대체 방법: 가장 큰 텍스트 블록 찾기
            all_divs = soup.find_all(['div', 'td'])
            if all_divs:
                content_area = max(all_divs, key=lambda x: len(x.get_text()))
        
        if content_area:
            # HTML을 마크다운으로 변환
            return self.h.handle(str(content_area))
        else:
            logger.warning("본문 내용을 찾을 수 없습니다")
            return ""
    
    def _extract_attachments(self, soup: BeautifulSoup) -> list:
        """첨부파일 목록 추출 - GSIF 특화"""
        attachments = []
        
        # GSIF의 테이블 구조에서 파일 행 찾기
        table = soup.find('table')
        if table:
            rows = table.find_all('tr')
            
            # "파일"이 포함된 th를 가진 행 찾기
            for row in rows:
                th = row.find('th')
                if th and '파일' in th.get_text():
                    # 이 행에서 모든 링크 찾기
                    file_links = row.find_all('a')
                    for link in file_links:
                        file_name = link.get_text(strip=True)
                        file_url = link.get('href', '')
                        
                        if file_url and 'bbs_download.do' in file_url:
                            # 상대 경로를 절대 경로로 변환
                            if not file_url.startswith('http'):
                                if not file_url.startswith('/'):
                                    file_url = '/gsipa/' + file_url
                                elif not file_url.startswith('/gsipa'):
                                    file_url = '/gsipa' + file_url
                            file_url = urljoin(self.base_url, file_url)
                            
                            if file_name and not file_name.isspace():
                                attachments.append({
                                    'name': file_name,
                                    'url': file_url
                                })
                    break
        
        # 일반적인 첨부파일 링크도 찾기
        attachment_selectors = [
            'a[href*="download"]',
            'a[href*="file"]',
            '.attach a',
            '.attachment a',
            '.file-list a'
        ]
        
        for selector in attachment_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href', '')
                if not href or 'bbs_download.do' not in href:
                    continue
                
                # 파일명 추출
                filename = link.get_text(strip=True)
                if not filename:
                    filename = href.split('/')[-1]
                
                # 절대 URL 생성
                if href.startswith('http'):
                    file_url = href
                else:
                    if not href.startswith('/'):
                        href = '/gsipa/' + href
                    elif not href.startswith('/gsipa'):
                        href = '/gsipa' + href
                    file_url = urljoin(self.base_url, href)
                
                # 중복 체크
                if not any(att['url'] == file_url for att in attachments):
                    attachments.append({
                        'name': filename,
                        'url': file_url
                    })
        
        return attachments
    
    def download_file(self, url: str, save_path: str, attachment_info: dict = None) -> bool:
        """파일 다운로드 - GSIF 맞춤형 (EUC-KR 파일명 처리)"""
        try:
            logger.info(f"파일 다운로드 시작: {url}")
            
            # Referer 헤더 추가
            headers = self.headers.copy()
            headers['Referer'] = self.base_url
            
            response = self.session.get(
                url, 
                headers=headers, 
                stream=True, 
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Content-Disposition에서 파일명 추출 (GSIF 특화 처리)
            actual_filename = self._extract_gsif_filename(response, save_path)
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
    
    def _extract_gsif_filename(self, response, default_path: str) -> str:
        """GSIF 특화 파일명 추출 (EUC-KR 처리)"""
        import os
        from urllib.parse import unquote
        
        content_disposition = response.headers.get('Content-Disposition', '')
        if not content_disposition:
            return default_path
        
        # filename*= 형식 먼저 확인 (RFC 5987)
        filename_star_match = re.search(r"filename\*=([^;]+)", content_disposition)
        if filename_star_match:
            # filename*=UTF-8''%ED%95%9C%EA%B8%80.hwp 형식
            filename_part = filename_star_match.group(1)
            if "''" in filename_part:
                encoding, filename = filename_part.split("''", 1)
                filename = unquote(filename)
                save_dir = os.path.dirname(default_path)
                return os.path.join(save_dir, self.sanitize_filename(filename))
        
        # 일반 filename= 형식
        filename_match = re.search(r'filename[^;=\n]*=(([\'"]).*?\2|[^;\n]*)', content_disposition)
        if filename_match:
            filename = filename_match.group(1).strip('"\'')
            
            # EUC-KR로 인코딩된 파일명 처리 (GSIF 특화)
            for encoding in ['euc-kr', 'utf-8']:
                try:
                    # 먼저 latin-1로 디코딩 후 실제 인코딩으로 재디코딩
                    decoded = filename.encode('latin-1').decode(encoding)
                    if decoded and not decoded.isspace():
                        save_dir = os.path.dirname(default_path)
                        # + 기호를 공백으로 변경
                        decoded = decoded.replace('+', ' ')
                        # URL 디코딩
                        decoded = unquote(decoded)
                        clean_filename = self.sanitize_filename(decoded)
                        return os.path.join(save_dir, clean_filename)
                except:
                    continue
        
        return default_path


# 하위 호환성을 위한 별칭
GSIFScraper = EnhancedGSIFScraper