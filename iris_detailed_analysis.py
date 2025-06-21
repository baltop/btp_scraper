#!/usr/bin/env python3
"""
IRIS 사이트 상세 분석 - 공고 데이터 및 파일 다운로드 완전 분석
"""

import requests
import json
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, unquote
import os


class IrisDetailedAnalyzer:
    def __init__(self):
        self.base_url = "https://www.iris.go.kr"
        self.ajax_url = "https://www.iris.go.kr/contents/retrieveBsnsAncmBtinSituList.do"
        self.detail_url_base = "https://www.iris.go.kr/contents/retrieveBsnsAncmBtinSituDetailView.do"
        self.session = requests.Session()
        
        # 기본 헤더 설정
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        # SSL 경고 무시
        requests.packages.urllib3.disable_warnings()
    
    def analyze_iris_completely(self):
        """IRIS 사이트 완전 분석"""
        print("🔍 IRIS 사이트 완전 분석 시작...")
        
        # 1. 공고 목록 가져오기
        announcements = self._get_announcements()
        
        if not announcements:
            print("❌ 공고 목록을 가져올 수 없습니다.")
            return
        
        print(f"✅ {len(announcements)}개 공고 발견")
        
        # 2. 첫 3개 공고 상세 분석
        for i, announcement in enumerate(announcements[:3]):
            print(f"\n{'='*60}")
            print(f"📋 공고 {i+1} 분석: {announcement.get('ancmTl', 'N/A')}")
            print(f"{'='*60}")
            
            self._analyze_single_announcement(announcement)
        
        # 3. 다운로드 메커니즘 종합 분석
        self._analyze_download_mechanism()
        
        # 4. 스크래퍼 구현 가이드 생성
        self._generate_scraper_guide()
    
    def _get_announcements(self):
        """공고 목록 가져오기"""
        print("📡 공고 목록 AJAX 요청...")
        
        ajax_data = {
            'pageIndex': '1',
            'prgmId': '',
            'srchGbnCd': 'all'
        }
        
        try:
            response = self.session.post(
                self.ajax_url,
                data=ajax_data,
                verify=False,
                timeout=30
            )
            
            if response.status_code == 200:
                json_data = response.json()
                
                if 'listBsnsAncmBtinSitu' in json_data:
                    return json_data['listBsnsAncmBtinSitu']
                else:
                    print("❌ 공고 목록 키를 찾을 수 없습니다.")
                    print(f"사용 가능한 키: {list(json_data.keys())}")
                    return None
            else:
                print(f"❌ AJAX 요청 실패: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ AJAX 요청 중 오류: {e}")
            return None
    
    def _analyze_single_announcement(self, announcement):
        """개별 공고 상세 분석"""
        ancm_id = announcement.get('ancmId')
        if not ancm_id:
            print("❌ 공고 ID가 없습니다.")
            return
        
        print(f"🔍 공고 ID: {ancm_id}")
        print(f"📄 제목: {announcement.get('ancmTl')}")
        print(f"🏢 기관: {announcement.get('sorgnNm')}")
        print(f"📅 공고일: {announcement.get('ancmDe')}")
        
        # 상세 페이지 접근
        detail_url = f"{self.detail_url_base}?ancmId={ancm_id}"
        print(f"🔗 상세 페이지: {detail_url}")
        
        try:
            response = self.session.get(detail_url, verify=False, timeout=30)
            
            if response.status_code == 200:
                print("✅ 상세 페이지 접근 성공")
                
                # HTML 파싱
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 1. 페이지 구조 분석
                self._analyze_page_structure(soup)
                
                # 2. 첨부파일 분석
                download_info = self._analyze_attachments(soup, ancm_id)
                
                # 3. 실제 다운로드 테스트
                if download_info:
                    self._test_file_download(download_info[0])  # 첫 번째 파일만 테스트
                
            else:
                print(f"❌ 상세 페이지 접근 실패: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 상세 페이지 분석 중 오류: {e}")
    
    def _analyze_page_structure(self, soup):
        """페이지 구조 분석"""
        print("\n📊 페이지 구조 분석:")
        
        # 제목 영역
        title_elements = soup.find_all(['h1', 'h2', 'h3'], class_=re.compile(r'title|head', re.I))
        if title_elements:
            print(f"  📌 제목 요소: {len(title_elements)}개")
            for elem in title_elements[:2]:
                print(f"    - {elem.name}.{elem.get('class', '')}: {elem.get_text(strip=True)[:50]}")
        
        # 본문 영역
        content_selectors = [
            '.content', '.board-content', '.view-content', 
            '#content', '[class*="content"]', '.detail-content'
        ]
        
        for selector in content_selectors:
            content = soup.select_one(selector)
            if content:
                text_length = len(content.get_text(strip=True))
                print(f"  📝 본문 영역 ({selector}): {text_length}자")
                break
        
        # 테이블 구조
        tables = soup.find_all('table')
        if tables:
            print(f"  📋 테이블: {len(tables)}개")
            for i, table in enumerate(tables[:3]):
                rows = len(table.find_all('tr'))
                print(f"    - 테이블 {i+1}: {rows}행")
    
    def _analyze_attachments(self, soup, ancm_id):
        """첨부파일 분석"""
        print("\n📎 첨부파일 분석:")
        
        download_info = []
        
        # 1. onclick 속성에서 다운로드 함수 찾기
        onclick_links = soup.find_all('a', onclick=True)
        
        for link in onclick_links:
            onclick = link.get('onclick', '')
            if 'download' in onclick.lower():
                text = link.get_text(strip=True)
                print(f"  📁 첨부파일 발견: {text}")
                print(f"    onclick: {onclick}")
                
                # 다운로드 파라미터 추출
                params = self._extract_download_params(onclick)
                if params:
                    download_info.append({
                        'text': text,
                        'onclick': onclick,
                        'params': params,
                        'ancm_id': ancm_id
                    })
        
        # 2. href 속성에서 다운로드 링크 찾기
        href_links = soup.find_all('a', href=True)
        
        for link in href_links:
            href = link.get('href', '')
            if 'download' in href.lower() or 'file' in href.lower():
                text = link.get_text(strip=True)
                print(f"  📁 다운로드 링크: {text}")
                print(f"    href: {href}")
                
                download_info.append({
                    'text': text,
                    'href': href,
                    'ancm_id': ancm_id
                })
        
        # 3. 첨부파일 관련 텍스트 패턴 찾기
        file_patterns = [
            r'첨부\s*:\s*([^\n\r]+)',
            r'파일\s*:\s*([^\n\r]+)',
            r'(\w+\.(hwp|pdf|doc|docx|xls|xlsx))',
        ]
        
        page_text = soup.get_text()
        for pattern in file_patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                print(f"  📄 파일 패턴 발견: {match}")
        
        print(f"  ✅ 총 {len(download_info)}개의 다운로드 정보 수집")
        return download_info
    
    def _extract_download_params(self, onclick_str):
        """다운로드 함수에서 파라미터 추출"""
        # 다양한 패턴 시도
        patterns = [
            r"f_bsnsAncm_downloadAtchFile\s*\(\s*'([^']+)'\s*,\s*'([^']+)'\s*\)",
            r"downloadAtchFile\s*\(\s*'([^']+)'\s*,\s*'([^']+)'\s*\)",
            r"download\s*\(\s*'([^']+)'\s*,\s*'([^']+)'\s*\)",
            r"f_downloadFile\s*\(\s*'([^']+)'\s*,\s*'([^']+)'\s*\)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, onclick_str)
            if match:
                return {
                    'param1': match.group(1),
                    'param2': match.group(2),
                    'pattern': pattern
                }
        
        # 단일 파라미터 패턴
        single_patterns = [
            r"download\s*\(\s*'([^']+)'\s*\)",
            r"downloadFile\s*\(\s*'([^']+)'\s*\)"
        ]
        
        for pattern in single_patterns:
            match = re.search(pattern, onclick_str)
            if match:
                return {
                    'param1': match.group(1),
                    'pattern': pattern
                }
        
        return None
    
    def _test_file_download(self, download_info):
        """실제 파일 다운로드 테스트"""
        print(f"\n📥 파일 다운로드 테스트: {download_info['text']}")
        
        if 'params' in download_info:
            # JavaScript 함수 기반 다운로드
            params = download_info['params']
            
            # 다양한 다운로드 URL 패턴 시도
            download_urls = [
                f"{self.base_url}/downloadAtchFile.do?atchFileId={params['param1']}&atchFileSn={params['param2']}",
                f"{self.base_url}/common/downloadAtchFile.do?atchFileId={params['param1']}&atchFileSn={params['param2']}",
                f"{self.base_url}/contents/downloadAtchFile.do?atchFileId={params['param1']}&atchFileSn={params['param2']}",
                f"{self.base_url}/iris/downloadAtchFile.do?atchFileId={params['param1']}&atchFileSn={params['param2']}"
            ]
            
        elif 'href' in download_info:
            # 직접 href 링크
            href = download_info['href']
            if href.startswith('http'):
                download_urls = [href]
            else:
                download_urls = [urljoin(self.base_url, href)]
        else:
            print("❌ 다운로드 URL을 구성할 수 없습니다.")
            return
        
        # 각 URL 시도
        for i, url in enumerate(download_urls):
            print(f"  {i+1}. 시도: {url}")
            
            try:
                # HEAD 요청으로 먼저 확인
                head_response = self.session.head(url, verify=False, timeout=10)
                print(f"    HEAD 응답: {head_response.status_code}")
                
                if head_response.status_code == 200:
                    # Content-Disposition 헤더 확인
                    content_disposition = head_response.headers.get('Content-Disposition', '')
                    content_type = head_response.headers.get('Content-Type', '')
                    content_length = head_response.headers.get('Content-Length', '')
                    
                    print(f"    Content-Type: {content_type}")
                    print(f"    Content-Length: {content_length}")
                    print(f"    Content-Disposition: {content_disposition}")
                    
                    # 파일명 추출
                    filename = self._extract_filename(content_disposition)
                    if filename:
                        print(f"    ✅ 파일명: {filename}")
                    
                    # 실제 다운로드 (일부만)
                    get_response = self.session.get(url, verify=False, timeout=10, stream=True)
                    if get_response.status_code == 200:
                        # 처음 1KB만 읽어서 파일 형식 확인
                        first_chunk = next(get_response.iter_content(1024), b'')
                        if first_chunk:
                            print(f"    ✅ 다운로드 성공! (첫 {len(first_chunk)} bytes 확인)")
                            
                            # 파일 시그니처 확인
                            file_type = self._identify_file_type(first_chunk)
                            print(f"    📄 파일 타입: {file_type}")
                            
                            return {
                                'success': True,
                                'url': url,
                                'filename': filename,
                                'content_type': content_type,
                                'file_type': file_type,
                                'size': content_length
                            }
                    
                elif head_response.status_code == 302:
                    location = head_response.headers.get('Location', '')
                    print(f"    🔄 리다이렉트: {location}")
                    
                else:
                    print(f"    ❌ 실패: {head_response.status_code}")
                    
            except Exception as e:
                print(f"    ❌ 오류: {e}")
        
        return {'success': False}
    
    def _extract_filename(self, content_disposition):
        """Content-Disposition 헤더에서 파일명 추출"""
        if not content_disposition:
            return None
        
        # RFC 5987 형식 우선 (filename*=UTF-8''encoded_filename)
        rfc5987_match = re.search(r"filename\*=([^']*)'([^']*)'(.+)", content_disposition)
        if rfc5987_match:
            encoding, lang, encoded_filename = rfc5987_match.groups()
            try:
                return unquote(encoded_filename, encoding=encoding or 'utf-8')
            except:
                pass
        
        # 일반 filename 파라미터
        filename_match = re.search(r'filename[^;=\n]*=([\'"]*)(.*?)\1', content_disposition)
        if filename_match:
            filename = filename_match.group(2)
            
            # 다양한 인코딩 시도
            for encoding in ['utf-8', 'euc-kr', 'cp949']:
                try:
                    if encoding == 'utf-8':
                        return filename.encode('latin-1').decode('utf-8')
                    else:
                        return filename.encode('latin-1').decode(encoding)
                except:
                    continue
            
            return filename
        
        return None
    
    def _identify_file_type(self, data):
        """파일 시그니처로 파일 타입 식별"""
        if not data:
            return "Unknown"
        
        # 파일 시그니처 매칭
        signatures = {
            b'\x50\x4B\x03\x04': 'ZIP/Office',
            b'\x50\x4B\x05\x06': 'ZIP/Office',
            b'\x50\x4B\x07\x08': 'ZIP/Office',
            b'%PDF': 'PDF',
            b'\xD0\xCF\x11\xE0': 'MS Office (Old)',
            b'HWP Document File': 'HWP',
            b'\xFF\xFE': 'Unicode text',
            b'\xFE\xFF': 'Unicode text',
            b'\xEF\xBB\xBF': 'UTF-8 text'
        }
        
        for sig, file_type in signatures.items():
            if data.startswith(sig):
                return file_type
        
        # 텍스트 파일 여부 확인
        try:
            data.decode('utf-8')
            return 'Text file'
        except:
            pass
        
        return 'Binary file'
    
    def _analyze_download_mechanism(self):
        """다운로드 메커니즘 종합 분석"""
        print("\n" + "="*80)
        print("🔧 다운로드 메커니즘 종합 분석")
        print("="*80)
        
        print("\n1️⃣ 다운로드 URL 패턴:")
        print("  - /downloadAtchFile.do?atchFileId={id}&atchFileSn={sn}")
        print("  - /common/downloadAtchFile.do?atchFileId={id}&atchFileSn={sn}")
        print("  - /contents/downloadAtchFile.do?atchFileId={id}&atchFileSn={sn}")
        
        print("\n2️⃣ JavaScript 함수 패턴:")
        print("  - f_bsnsAncm_downloadAtchFile('atchFileId', 'atchFileSn')")
        print("  - downloadAtchFile('atchFileId', 'atchFileSn')")
        
        print("\n3️⃣ 파라미터 구조:")
        print("  - atchFileId: 첨부파일 그룹 ID")
        print("  - atchFileSn: 첨부파일 순번")
        
        print("\n4️⃣ 세션 요구사항:")
        print("  - JSESSIONID 쿠키 필수")
        print("  - Referer 헤더 설정 권장")
        print("  - User-Agent 설정 필수")
        
        print("\n5️⃣ 응답 특성:")
        print("  - Content-Disposition 헤더로 파일명 제공")
        print("  - 한글 파일명은 UTF-8 또는 EUC-KR 인코딩")
        print("  - 파일 타입: HWP, PDF, DOC, XLS 등")
    
    def _generate_scraper_guide(self):
        """스크래퍼 구현 가이드 생성"""
        print("\n" + "="*80)
        print("📋 IRIS 스크래퍼 구현 가이드")
        print("="*80)
        
        guide = """
1. 공고 목록 수집:
   - POST /contents/retrieveBsnsAncmBtinSituList.do
   - 파라미터: pageIndex=1, prgmId='', srchGbnCd='all'
   - 응답: JSON 형태, listBsnsAncmBtinSitu 키에 공고 배열

2. 상세 페이지 접근:
   - GET /contents/retrieveBsnsAncmBtinSituDetailView.do?ancmId={ancmId}
   - ancmId는 목록에서 획득

3. 첨부파일 추출:
   - HTML 파싱으로 onclick 속성에서 다운로드 함수 찾기
   - 정규표현식으로 atchFileId, atchFileSn 파라미터 추출

4. 파일 다운로드:
   - GET /downloadAtchFile.do?atchFileId={id}&atchFileSn={sn}
   - 세션 쿠키 유지 필수
   - Content-Disposition 헤더에서 파일명 추출

5. 특수 고려사항:
   - 한글 파일명 인코딩 처리 (UTF-8, EUC-KR)
   - 파일 확장자별 처리 (HWP, PDF 등)
   - 네트워크 타임아웃 설정
   - SSL 인증서 검증 비활성화 (verify=False)

6. 추천 라이브러리:
   - requests: HTTP 요청
   - BeautifulSoup: HTML 파싱
   - re: 정규표현식
   - urllib.parse: URL 처리
        """
        
        print(guide)
        
        # 가이드를 파일로 저장
        with open('/tmp/iris_scraper_guide.txt', 'w', encoding='utf-8') as f:
            f.write("IRIS 사이트 스크래퍼 구현 가이드\n")
            f.write("=" * 50 + "\n")
            f.write(guide)
        
        print(f"\n📁 구현 가이드가 /tmp/iris_scraper_guide.txt에 저장되었습니다.")


def main():
    analyzer = IrisDetailedAnalyzer()
    analyzer.analyze_iris_completely()


if __name__ == "__main__":
    main()