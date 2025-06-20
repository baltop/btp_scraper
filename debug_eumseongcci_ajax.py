#!/usr/bin/env python3
"""
음성상공회의소 AJAX 요청 분석
"""
import requests
from bs4 import BeautifulSoup
import re
import json

def analyze_ajax_requests():
    """AJAX 요청 분석"""
    
    base_url = "https://eumseongcci.korcham.net"
    list_url = "https://eumseongcci.korcham.net/front/board/boardContentsListPage.do?boardId=10585&menuId=871"
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    try:
        response = session.get(list_url, verify=False)
        response.encoding = 'utf-8'
        
        print(f"메인 페이지 응답 코드: {response.status_code}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # JavaScript에서 AJAX URL 찾기
        script_tags = soup.find_all('script')
        ajax_urls = []
        
        for script in script_tags:
            script_content = script.get_text()
            
            # boardContentsListUrl 찾기
            if 'boardContentsListUrl' in script_content:
                match = re.search(r'boardContentsListUrl\s*=\s*["\']([^"\']+)["\']', script_content)
                if match:
                    ajax_url = match.group(1)
                    ajax_urls.append(('boardContentsListUrl', ajax_url))
                    print(f"boardContentsListUrl 발견: {ajax_url}")
            
            # search() 함수 찾기
            if 'function search()' in script_content:
                print("\n--- search() 함수 발견 ---")
                # search 함수 추출
                match = re.search(r'function search\(\)[^}]*\{[^}]*\}', script_content, re.DOTALL)
                if match:
                    print(f"search() 함수:\n{match.group(0)}")
            
            # boardLiat() 함수 찾기 (오타 주의)
            if 'function boardLiat()' in script_content:
                print("\n--- boardLiat() 함수 발견 ---")
                match = re.search(r'function boardLiat\(\)[^}]*\{[^}]*\}', script_content, re.DOTALL)
                if match:
                    print(f"boardLiat() 함수:\n{match.group(0)}")
        
        # AJAX 요청 시도
        if ajax_urls:
            for url_name, ajax_url in ajax_urls:
                print(f"\n=== {url_name} AJAX 요청 테스트 ===")
                
                full_ajax_url = f"{base_url}{ajax_url}"
                
                # 방법 1: GET 요청
                print("--- GET 요청 ---")
                try:
                    ajax_response = session.get(full_ajax_url, verify=False)
                    print(f"GET 응답 코드: {ajax_response.status_code}")
                    print(f"응답 길이: {len(ajax_response.text)} 문자")
                    
                    if ajax_response.status_code == 200:
                        # HTML인지 JSON인지 확인
                        content_type = ajax_response.headers.get('Content-Type', '')
                        print(f"Content-Type: {content_type}")
                        
                        if 'json' in content_type.lower():
                            try:
                                json_data = ajax_response.json()
                                print(f"JSON 응답: {json.dumps(json_data, ensure_ascii=False, indent=2)[:500]}...")
                            except:
                                print("JSON 파싱 실패")
                        else:
                            # HTML로 파싱
                            ajax_soup = BeautifulSoup(ajax_response.text, 'html.parser')
                            tables = ajax_soup.find_all('table')
                            print(f"AJAX 응답의 테이블 수: {len(tables)}")
                            
                            if tables:
                                table = tables[0]
                                tbody = table.find('tbody')
                                if tbody:
                                    rows = tbody.find_all('tr')
                                    print(f"첫 번째 테이블의 행 수: {len(rows)}")
                                    
                                    if rows:
                                        first_row = rows[0]
                                        cells = first_row.find_all(['td', 'th'])
                                        print(f"첫 번째 행의 셀 수: {len(cells)}")
                                        
                                        for j, cell in enumerate(cells):
                                            cell_text = cell.get_text(strip=True)[:30]
                                            print(f"  셀 {j+1}: {cell_text}")
                                            
                                            # 링크 확인
                                            links = cell.find_all('a')
                                            for link in links:
                                                href = link.get('href', '')
                                                if 'contentsView' in href:
                                                    print(f"    contentsView 링크: {href}")
                                                    
                                                    # contId 추출
                                                    match = re.search(r"contentsView\('(\d+)'\)", href)
                                                    if match:
                                                        cont_id = match.group(1)
                                                        print(f"    contId: {cont_id}")
                                                        return session, cont_id, link.get_text(strip=True)
                            
                            # 샘플 HTML 출력
                            sample_html = ajax_response.text[:1000]
                            print(f"AJAX HTML 샘플:\n{sample_html}")
                        
                except Exception as e:
                    print(f"GET 요청 실패: {e}")
                
                # 방법 2: POST 요청 (폼 데이터 포함)
                print("\n--- POST 요청 (폼 데이터 포함) ---")
                try:
                    # 페이지에서 폼 데이터 추출
                    form = soup.find('form', {'id': 'listFrm'})
                    post_data = {}
                    
                    if form:
                        inputs = form.find_all('input')
                        for input_tag in inputs:
                            name = input_tag.get('name', '')
                            value = input_tag.get('value', '')
                            if name:
                                post_data[name] = value
                    
                    # 기본값 설정
                    post_data.update({
                        'miv_pageNo': '1',
                        'miv_pageSize': '15',
                        'total_cnt': '',
                        'LISTOP': '',
                        'mode': 'W',
                        'contId': '',
                        'delYn': 'N',
                        'menuId': '871',
                        'boardId': '10585',
                        'readRat': 'A',
                        'boardCd': 'N',
                        'searchKey': 'A',
                        'searchTxt': '',
                        'pageSize': '15'
                    })
                    
                    print(f"POST 데이터: {post_data}")
                    
                    ajax_response = session.post(full_ajax_url, data=post_data, verify=False)
                    print(f"POST 응답 코드: {ajax_response.status_code}")
                    print(f"응답 길이: {len(ajax_response.text)} 문자")
                    
                    if ajax_response.status_code == 200:
                        ajax_soup = BeautifulSoup(ajax_response.text, 'html.parser')
                        tables = ajax_soup.find_all('table')
                        print(f"POST AJAX 응답의 테이블 수: {len(tables)}")
                        
                        if tables:
                            table = tables[0]
                            tbody = table.find('tbody')
                            if tbody:
                                rows = tbody.find_all('tr')
                                print(f"POST 첫 번째 테이블의 행 수: {len(rows)}")
                                
                                if rows:
                                    print("✅ POST 요청으로 테이블 데이터 획득 성공!")
                                    
                                    first_row = rows[0]
                                    cells = first_row.find_all(['td', 'th'])
                                    
                                    for j, cell in enumerate(cells):
                                        cell_text = cell.get_text(strip=True)[:50]
                                        print(f"  셀 {j+1}: {cell_text}")
                                        
                                        # 링크 확인
                                        links = cell.find_all('a')
                                        for link in links:
                                            href = link.get('href', '')
                                            if 'contentsView' in href:
                                                print(f"    ✅ contentsView 링크 발견: {href}")
                                                
                                                # contId 추출
                                                match = re.search(r"contentsView\('(\d+)'\)", href)
                                                if match:
                                                    cont_id = match.group(1)
                                                    title = link.get_text(strip=True)
                                                    print(f"    contId: {cont_id}")
                                                    print(f"    제목: {title}")
                                                    return session, cont_id, title, full_ajax_url, post_data
                        
                        # 샘플 HTML 출력
                        sample_html = ajax_response.text[:2000]
                        print(f"POST AJAX HTML 샘플:\n{sample_html}")
                        
                except Exception as e:
                    print(f"POST 요청 실패: {e}")
    
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
    
    return None

def test_detail_access_with_ajax_info(session, cont_id, title):
    """AJAX 정보를 바탕으로 상세 페이지 접근 테스트"""
    
    print(f"\n=== 상세 페이지 접근 테스트 (contId: {cont_id}) ===")
    
    base_url = "https://eumseongcci.korcham.net"
    
    # 방법 1: 직접 GET 요청
    print("--- 방법 1: 직접 GET 요청 ---")
    try:
        detail_url = f"{base_url}/front/board/boardContentsView.do?contId={cont_id}"
        response = session.get(detail_url, verify=False)
        print(f"GET 응답 코드: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 제목 확인
            boardview = soup.find('div', class_='boardveiw')
            if boardview:
                table = boardview.find('table')
                if table:
                    tbody = table.find('tbody')
                    if tbody:
                        title_row = tbody.find('tr')
                        if title_row:
                            title_cells = title_row.find_all('td')
                            if title_cells:
                                article_title = title_cells[0].get_text(strip=True)
                                print(f"게시글 제목: {article_title}")
                                
                                if title in article_title or article_title in title:
                                    print("✅ 상세 페이지 접근 성공!")
                                    return True
                                else:
                                    print(f"❌ 제목 불일치")
        
    except Exception as e:
        print(f"상세 페이지 접근 실패: {e}")
    
    return False

def main():
    """메인 함수"""
    print("음성상공회의소 AJAX 요청 분석")
    print("=" * 50)
    
    result = analyze_ajax_requests()
    
    if result:
        session, cont_id, title = result[:3]
        print(f"\n✅ AJAX를 통해 정보 획득 성공!")
        print(f"contId: {cont_id}")
        print(f"제목: {title}")
        
        # 상세 페이지 접근 테스트
        success = test_detail_access_with_ajax_info(session, cont_id, title)
        
        if success:
            print(f"\n🎉 최종 결론:")
            print(f"1. 목록 데이터는 AJAX POST 요청으로 로드됨")
            print(f"2. 상세 페이지는 GET 요청으로 직접 접근 가능")
            print(f"3. URL 패턴: /front/board/boardContentsView.do?contId=<ID>")
        else:
            print(f"\n❌ 상세 페이지 접근 실패")
    else:
        print(f"\n❌ AJAX 정보 획득 실패")

if __name__ == "__main__":
    main()