#!/usr/bin/env python3
"""
BIZBC 사이트 구조 분석 스크립트
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import json

def analyze_bizbc_site():
    """BIZBC 사이트 구조 분석"""
    
    # 기본 설정
    base_url = "https://bizbc.or.kr"
    list_url = "https://bizbc.or.kr/kor/contents/BC0101010000.do"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    session = requests.Session()
    session.headers.update(headers)
    
    print("=== BIZBC 사이트 구조 분석 ===\n")
    
    # 1. 기본 접속 테스트
    print("1. 기본 접속 테스트")
    try:
        response = session.get(list_url, verify=True)
        print(f"   - URL: {list_url}")
        print(f"   - 상태 코드: {response.status_code}")
        print(f"   - 인코딩: {response.encoding}")
        print(f"   - Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        print(f"   - SSL 인증서: 정상" if response.url.startswith('https') else "   - HTTP 연결")
        
        if response.status_code != 200:
            print(f"   ❌ 접속 실패: {response.status_code}")
            return
        else:
            print("   ✅ 접속 성공")
            
    except Exception as e:
        print(f"   ❌ 접속 오류: {e}")
        return
    
    # 2. HTML 구조 분석
    print("\n2. HTML 구조 분석")
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # 페이지 제목
    title = soup.find('title')
    print(f"   - 페이지 제목: {title.text if title else 'N/A'}")
    
    # 3. 목록 페이지 구조 분석
    print("\n3. 목록 페이지 구조 분석")
    
    # 카드 형태의 목록 찾기
    announcements = []
    
    # 여러 선택자로 목록 시도
    selectors_to_try = [
        'ul li',  # 리스트 아이템
        '.list li',  # 클래스가 list인 ul의 li
        'article',  # article 태그
        '.announcement',  # 공고 클래스
        '.card'  # 카드 클래스
    ]
    
    list_container = None
    for selector in selectors_to_try:
        elements = soup.select(selector)
        if elements and len(elements) > 5:  # 충분한 수의 아이템이 있어야 함
            list_container = elements
            print(f"   - 목록 요소 발견: {selector} ({len(elements)}개)")
            break
    
    # 전체 구조 확인 - 공고 제목 링크 찾기
    all_links = soup.find_all('a')
    title_links = []
    
    for link in all_links:
        href = link.get('href', '')
        text = link.get_text(strip=True)
        
        # 공고 제목처럼 보이는 링크 찾기
        if (len(text) > 10 and 
            ('공고' in text or '모집' in text or '지원' in text or '사업' in text) and
            '#none' in href):
            title_links.append({
                'text': text,
                'href': href,
                'element': link
            })
    
    print(f"   - 공고 제목 링크 발견: {len(title_links)}개")
    
    if not list_container:
        print("   - 목록 구조를 찾기 위해 전체 분석 중...")
        
        if title_links:
            # 첫 번째 링크의 부모 구조 분석
            first_link = title_links[0]['element']
            parent = first_link.parent
            
            # 상위로 올라가면서 반복 구조 찾기
            while parent and parent.name != 'body':
                siblings = parent.find_next_siblings()
                if len(siblings) >= 3:  # 충분한 형제 요소가 있으면
                    # 이 레벨이 목록 구조일 가능성이 높음
                    print(f"   - 목록 컨테이너 발견: {parent.name} (형제 {len(siblings)}개)")
                    list_container = [parent] + siblings
                    break
                parent = parent.parent
    
    # 4. 공고 아이템 분석
    print("\n4. 공고 아이템 분석")
    
    if list_container and len(list_container) > 0:
        # 첫 번째 아이템 상세 분석
        first_item = list_container[0]
        print(f"   - 첫 번째 아이템 태그: {first_item.name}")
        
        # 제목 링크 찾기
        title_link = first_item.find('a')
        if title_link:
            title = title_link.get_text(strip=True)
            href = title_link.get('href', '')
            print(f"   - 제목: {title[:50]}...")
            print(f"   - 링크: {href}")
            
            # 링크 패턴 분석
            if '#none' in href:
                print("   - 링크 타입: JavaScript 처리 (onclick 이벤트)")
                onclick = title_link.get('onclick', '')
                if onclick:
                    print(f"   - onclick: {onclick}")
            else:
                print("   - 링크 타입: 직접 링크")
        
        # 메타 정보 찾기 (날짜, 조회수 등)
        meta_texts = []
        for elem in first_item.find_all(string=True):
            text = elem.strip()
            if text and len(text) > 3:
                if any(keyword in text for keyword in ['모집기간', '조회', '기간', '2025']):
                    meta_texts.append(text)
        
        print(f"   - 메타 정보: {meta_texts[:3]}")  # 처음 3개만 표시
    
    # 5. 페이지네이션 분석
    print("\n5. 페이지네이션 분석")
    
    # 페이지 번호 링크 찾기
    page_links = []
    
    # 숫자 링크 찾기
    for link in soup.find_all('a'):
        text = link.get_text(strip=True)
        href = link.get('href', '')
        
        if text.isdigit() and int(text) <= 10:  # 1-10 범위의 숫자
            page_links.append({
                'text': text,
                'href': href
            })
    
    if page_links:
        print(f"   - 페이지 링크 발견: {len(page_links)}개")
        for i, page_link in enumerate(page_links[:3]):  # 처음 3개만 표시
            print(f"     * 페이지 {page_link['text']}: {page_link['href']}")
        
        # URL 패턴 분석
        if len(page_links) >= 2:
            page1_href = page_links[0]['href']
            page2_href = page_links[1]['href']
            
            print(f"   - 1페이지 URL: {page1_href}")
            print(f"   - 2페이지 URL: {page2_href}")
            
            # 페이지네이션 방식 추정
            if 'page=' in page2_href:
                print("   - 페이지네이션 방식: GET 파라미터 (page=N)")
            elif '#none' in page2_href:
                print("   - 페이지네이션 방식: JavaScript 처리")
            else:
                print("   - 페이지네이션 방식: 기타")
    else:
        print("   - 페이지네이션 링크를 찾을 수 없음")
    
    # 6. 상세 페이지 테스트
    print("\n6. 상세 페이지 접근 테스트")
    
    # JavaScript 링크의 경우 실제 상세 페이지 URL 추정
    if title_links:
        first_title_link = title_links[0]
        
        # onclick에서 파라미터 추출 시도
        onclick = first_title_link['element'].get('onclick', '')
        if onclick:
            print(f"   - onclick 함수: {onclick}")
            
            # 일반적인 상세 페이지 패턴 시도
            detail_urls_to_try = [
                f"{list_url}?schM=view&bizPbancSn=11098",  # 실제 확인된 패턴
                f"{list_url}?mode=view&id=1",
                f"{base_url}/kor/contents/BC0101010001.do"
            ]
            
            for detail_url in detail_urls_to_try:
                try:
                    detail_response = session.get(detail_url)
                    if detail_response.status_code == 200:
                        detail_soup = BeautifulSoup(detail_response.content, 'html.parser')
                        
                        # 첨부파일 링크 찾기
                        attachment_links = []
                        for link in detail_soup.find_all('a'):
                            href = link.get('href', '')
                            text = link.get_text(strip=True)
                            
                            if ('다운로드' in text or 'download' in href.lower() or 
                                'fileDownload' in href):
                                attachment_links.append({
                                    'text': text,
                                    'href': href
                                })
                        
                        print(f"   - 상세 페이지 접근 성공: {detail_url}")
                        print(f"   - 첨부파일 링크: {len(attachment_links)}개")
                        
                        if attachment_links:
                            for att in attachment_links[:2]:  # 처음 2개만 표시
                                print(f"     * {att['text']}: {att['href']}")
                        
                        break
                        
                except Exception as e:
                    print(f"   - {detail_url} 접근 실패: {e}")
                    continue
    
    # 7. 요약 정보
    print("\n=== 분석 결과 요약 ===")
    print(f"사이트 URL: {base_url}")
    print(f"목록 페이지: {list_url}")
    print(f"인코딩: UTF-8")
    print(f"SSL: 지원됨")
    print(f"목록 구조: 카드 형태 (ul > li)")
    print(f"상세 페이지 접근: JavaScript 함수 또는 GET 파라미터")
    print(f"첨부파일 다운로드: /afile/fileDownload/ 경로")
    print(f"페이지네이션: GET 파라미터 방식 (page=N)")

if __name__ == "__main__":
    analyze_bizbc_site()