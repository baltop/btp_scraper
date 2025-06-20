#!/usr/bin/env python3
"""
음성상공회의소 상세 페이지 접근 방법 완전 분석
"""
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re

def test_eumseongcci_detail_access():
    """음성상공회의소 상세 페이지 접근 방법 테스트"""
    
    # 기본 설정
    base_url = "https://eumseongcci.korcham.net"
    list_url = "https://eumseongcci.korcham.net/front/board/boardContentsListPage.do?boardId=10585&menuId=871"
    
    # 세션 생성
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    print("=== 1단계: 목록 페이지 접근 ===")
    try:
        response = session.get(list_url, verify=False)
        response.encoding = 'utf-8'
        print(f"목록 페이지 응답 코드: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 첫 번째 공고 정보 추출
            table = soup.find('table')
            if table:
                tbody = table.find('tbody')
                if tbody:
                    first_row = tbody.find('tr')
                    if first_row:
                        title_cell = first_row.find('td', class_='title')
                        if title_cell:
                            link = title_cell.find('a')
                            if link:
                                href = link.get('href', '')
                                title = link.get_text(strip=True)
                                
                                # contId 추출
                                match = re.search(r"contentsView\('(\d+)'\)", href)
                                if match:
                                    cont_id = match.group(1)
                                    print(f"첫 번째 공고 제목: {title}")
                                    print(f"contId: {cont_id}")
                                    print(f"JavaScript 링크: {href}")
                                    
                                    return session, cont_id, title
                                else:
                                    print("contId 추출 실패")
                            else:
                                print("링크를 찾을 수 없습니다")
                        else:
                            print("제목 셀을 찾을 수 없습니다")
                    else:
                        print("첫 번째 행을 찾을 수 없습니다")
                else:
                    print("tbody를 찾을 수 없습니다")
            else:
                print("테이블을 찾을 수 없습니다")
        else:
            print(f"목록 페이지 접근 실패: {response.status_code}")
            
    except Exception as e:
        print(f"목록 페이지 접근 중 오류: {e}")
    
    return None, None, None

def test_detail_access_methods(session, cont_id, title):
    """다양한 상세 페이지 접근 방법 테스트"""
    
    base_url = "https://eumseongcci.korcham.net"
    
    print(f"\n=== 2단계: 상세 페이지 접근 방법 테스트 (contId: {cont_id}) ===")
    
    # 방법 1: GET 요청으로 직접 접근
    print("\n--- 방법 1: GET 요청 ---")
    try:
        detail_url = f"{base_url}/front/board/boardContentsView.do?contId={cont_id}"
        response = session.get(detail_url, verify=False)
        print(f"GET 요청 응답 코드: {response.status_code}")
        print(f"응답 URL: {response.url}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 상세 페이지 내용 확인
            contents_title = soup.find('div', class_='contents_title')
            if contents_title:
                page_title = contents_title.find('h2')
                if page_title:
                    print(f"페이지 제목: {page_title.get_text(strip=True)}")
            
            # 게시글 제목 확인
            boardview = soup.find('div', class_='boardveiw')
            if boardview:
                table = boardview.find('table')
                if table:
                    tbody = table.find('tbody')
                    if tbody:
                        title_row = tbody.find('tr')
                        if title_row:
                            title_cell = title_row.find_all('td')
                            if title_cell and len(title_cell) > 0:
                                article_title = title_cell[0].get_text(strip=True)
                                print(f"게시글 제목: {article_title}")
                                
                                if title in article_title or article_title in title:
                                    print("✅ GET 요청 성공!")
                                    return "GET", detail_url
                                else:
                                    print(f"❌ 제목 불일치: 예상({title}) vs 실제({article_title})")
                            else:
                                print("제목 셀을 찾을 수 없습니다")
                        else:
                            print("제목 행을 찾을 수 없습니다")
                    else:
                        print("tbody를 찾을 수 없습니다")
                else:
                    print("테이블을 찾을 수 없습니다")
            else:
                print("boardview를 찾을 수 없습니다")
        else:
            print(f"❌ GET 요청 실패: {response.status_code}")
            
    except Exception as e:
        print(f"GET 요청 중 오류: {e}")
    
    # 방법 2: POST 요청으로 접근 (contentsView 함수 모방)
    print("\n--- 방법 2: POST 요청 (contentsView 함수 모방) ---")
    try:
        detail_url = f"{base_url}/front/board/boardContentsView.do"
        
        # contentsView 함수에서 사용하는 데이터 구조 모방
        post_data = {
            'mode': 'E',
            'boardId': '10585',
            'contId': cont_id,
            'recommend_yn': '',
            'miv_pageNo': '',
            's_reply_ststus': '',
            'searchKey': 'A',
            'searchTxt': '',
            's_cate_id': '',
            'file_path': '',
            'file_nm': '',
            'orignl_file_nm': '',
            'boardCd': 'N',
            'regMemNm': '',
            'memNm': ''
        }
        
        response = session.post(detail_url, data=post_data, verify=False)
        print(f"POST 요청 응답 코드: {response.status_code}")
        print(f"응답 URL: {response.url}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 상세 페이지 내용 확인
            boardview = soup.find('div', class_='boardveiw')
            if boardview:
                table = boardview.find('table')
                if table:
                    tbody = table.find('tbody')
                    if tbody:
                        title_row = tbody.find('tr')
                        if title_row:
                            title_cell = title_row.find_all('td')
                            if title_cell and len(title_cell) > 0:
                                article_title = title_cell[0].get_text(strip=True)
                                print(f"게시글 제목: {article_title}")
                                
                                if title in article_title or article_title in title:
                                    print("✅ POST 요청 성공!")
                                    return "POST", detail_url, post_data
                                else:
                                    print(f"❌ 제목 불일치: 예상({title}) vs 실제({article_title})")
        else:
            print(f"❌ POST 요청 실패: {response.status_code}")
            
    except Exception as e:
        print(f"POST 요청 중 오류: {e}")
    
    # 방법 3: 세션 상태와 Referer 헤더 포함
    print("\n--- 방법 3: Referer 헤더 포함 GET 요청 ---")
    try:
        detail_url = f"{base_url}/front/board/boardContentsView.do?contId={cont_id}"
        
        # Referer 헤더 추가
        headers = {
            'Referer': 'https://eumseongcci.korcham.net/front/board/boardContentsListPage.do?boardId=10585&menuId=871',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
        
        response = session.get(detail_url, headers=headers, verify=False)
        print(f"Referer 포함 GET 요청 응답 코드: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            boardview = soup.find('div', class_='boardveiw')
            if boardview:
                table = boardview.find('table')
                if table:
                    tbody = table.find('tbody')
                    if tbody:
                        title_row = tbody.find('tr')
                        if title_row:
                            title_cell = title_row.find_all('td')
                            if title_cell and len(title_cell) > 0:
                                article_title = title_cell[0].get_text(strip=True)
                                print(f"게시글 제목: {article_title}")
                                
                                if title in article_title or article_title in title:
                                    print("✅ Referer 포함 GET 요청 성공!")
                                    return "GET_WITH_REFERER", detail_url, headers
                                    
    except Exception as e:
        print(f"Referer 포함 GET 요청 중 오류: {e}")
    
    print("❌ 모든 접근 방법 실패")
    return None

def analyze_detail_page_structure(session, cont_id):
    """상세 페이지 구조 분석"""
    print(f"\n=== 3단계: 상세 페이지 구조 분석 ===")
    
    try:
        detail_url = f"https://eumseongcci.korcham.net/front/board/boardContentsView.do?contId={cont_id}"
        response = session.get(detail_url, verify=False)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            print("--- 본문 내용 구조 ---")
            # 본문 내용 찾기
            boardview = soup.find('div', class_='boardveiw')
            if boardview:
                table = boardview.find('table')
                if table:
                    tbody = table.find('tbody')
                    if tbody:
                        # 모든 행 분석
                        rows = tbody.find_all('tr')
                        for i, row in enumerate(rows):
                            cells = row.find_all(['th', 'td'])
                            print(f"행 {i+1}: {len(cells)}개 셀")
                            for j, cell in enumerate(cells):
                                text = cell.get_text(strip=True)[:50]
                                if text:
                                    print(f"  셀 {j+1}: {text}...")
                            
                            # 본문 내용이 있는 행 찾기
                            if row.find('td', class_='td_p'):
                                print(f"  ✅ 본문 내용 발견 (행 {i+1})")
                                content_cell = row.find('td', class_='td_p')
                                if content_cell:
                                    # 이미지나 다른 컨텐츠 확인
                                    images = content_cell.find_all('img')
                                    if images:
                                        print(f"     - 이미지 {len(images)}개 발견")
                                        for img in images:
                                            src = img.get('src', '')
                                            print(f"       이미지 URL: {src}")
                                    
                                    # 텍스트 내용 확인
                                    text_content = content_cell.get_text(strip=True)
                                    if text_content:
                                        print(f"     - 텍스트 내용: {text_content[:100]}...")
            
            print("\n--- 첨부파일 구조 분석 ---")
            # 첨부파일 링크 찾기
            file_links = soup.find_all('a', href=True)
            download_links = []
            
            for link in file_links:
                href = link.get('href', '')
                onclick = link.get('onclick', '')
                
                # 다운로드 관련 링크 찾기
                if any(keyword in href.lower() for keyword in ['download', 'file', 'attach']):
                    download_links.append(('href', href, link.get_text(strip=True)))
                elif any(keyword in onclick.lower() for keyword in ['download', 'down(', 'file']):
                    download_links.append(('onclick', onclick, link.get_text(strip=True)))
            
            if download_links:
                print(f"첨부파일 링크 {len(download_links)}개 발견:")
                for link_type, link_value, text in download_links:
                    print(f"  - {link_type}: {link_value}")
                    print(f"    텍스트: {text}")
            else:
                print("첨부파일 링크 없음")
            
            # down() 함수 분석
            script_tags = soup.find_all('script')
            for script in script_tags:
                script_content = script.get_text()
                if 'function down(' in script_content:
                    print("\n--- down() 함수 발견 ---")
                    # down 함수 추출
                    match = re.search(r'function down\([^}]+\}', script_content, re.DOTALL)
                    if match:
                        print(f"down() 함수:\n{match.group(0)}")
            
            return True
            
    except Exception as e:
        print(f"상세 페이지 구조 분석 중 오류: {e}")
        return False

def main():
    """메인 함수"""
    print("음성상공회의소 상세 페이지 접근 방법 완전 분석")
    print("=" * 60)
    
    # 1단계: 목록 페이지에서 정보 추출
    session, cont_id, title = test_eumseongcci_detail_access()
    
    if session and cont_id and title:
        # 2단계: 상세 페이지 접근 방법 테스트
        access_result = test_detail_access_methods(session, cont_id, title)
        
        if access_result:
            print(f"\n✅ 성공한 접근 방법: {access_result[0]}")
            if len(access_result) > 2:
                print(f"추가 파라미터: {access_result[2]}")
        
        # 3단계: 상세 페이지 구조 분석
        analyze_detail_page_structure(session, cont_id)
        
        print(f"\n=== 결론 ===")
        print(f"1. 상세 페이지 URL 패턴: /front/board/boardContentsView.do?contId=<ID>")
        print(f"2. GET 요청으로 직접 접근 가능")
        print(f"3. contentsView JavaScript 함수는 POST 폼 제출 방식 사용")
        print(f"4. 세션이나 특별한 인증 불필요")
        print(f"5. 본문은 td.td_p 클래스 내부에 위치")
    else:
        print("❌ 목록 페이지에서 정보 추출 실패")

if __name__ == "__main__":
    main()