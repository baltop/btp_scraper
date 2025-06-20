#!/usr/bin/env python3
"""
음성상공회의소 최종 완전 분석 - POST 방식으로 상세 페이지 접근
"""
import requests
from bs4 import BeautifulSoup
import re

def test_post_detail_access():
    """POST 방식으로 상세 페이지 접근 테스트"""
    
    base_url = "https://eumseongcci.korcham.net"
    list_url = "https://eumseongcci.korcham.net/front/board/boardContentsListPage.do?boardId=10585&menuId=871"
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    })
    
    print("=== 1단계: 메인 페이지 접근 및 세션 생성 ===")
    try:
        # 메인 페이지 접근으로 세션 생성
        response = session.get(list_url, verify=False)
        response.encoding = 'utf-8'
        print(f"메인 페이지 응답 코드: {response.status_code}")
        
        if response.status_code != 200:
            print("메인 페이지 접근 실패")
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        print("=== 2단계: AJAX로 목록 데이터 가져오기 ===")
        
        # AJAX 요청으로 목록 데이터 가져오기
        ajax_url = f"{base_url}/front/board/boardContentsList.do"
        
        post_data = {
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
        }
        
        ajax_response = session.post(ajax_url, data=post_data, verify=False)
        print(f"AJAX 목록 응답 코드: {ajax_response.status_code}")
        
        if ajax_response.status_code == 200:
            ajax_soup = BeautifulSoup(ajax_response.text, 'html.parser')
            table = ajax_soup.find('table')
            
            if table:
                tbody = table.find('tbody')
                if tbody:
                    rows = tbody.find_all('tr')
                    print(f"목록 행 수: {len(rows)}")
                    
                    if rows:
                        first_row = rows[0]
                        cells = first_row.find_all('td')
                        
                        if len(cells) >= 2:
                            title_cell = cells[1]  # 두 번째 셀이 제목
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
                                    
                                    print("=== 3단계: 상세 페이지 접근 테스트 ===")
                                    
                                    # 상세 페이지 POST 요청 데이터 준비
                                    detail_url = f"{base_url}/front/board/boardContentsView.do"
                                    
                                    # 다양한 POST 데이터 조합 테스트
                                    post_variations = [
                                        # 변형 1: 최소한의 데이터
                                        {
                                            'contId': cont_id,
                                            'boardId': '10585'
                                        },
                                        # 변형 2: 기본 폼 데이터 포함
                                        {
                                            'mode': 'E',
                                            'boardId': '10585',
                                            'contId': cont_id,
                                            'menuId': '871',
                                            'boardCd': 'N'
                                        },
                                        # 변형 3: 전체 폼 데이터
                                        {
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
                                            'memNm': '',
                                            'menuId': '871'
                                        }
                                    ]
                                    
                                    for i, detail_data in enumerate(post_variations, 1):
                                        print(f"\n--- 변형 {i}: POST 데이터 ---")
                                        print(f"POST 데이터: {detail_data}")
                                        
                                        try:
                                            detail_response = session.post(detail_url, data=detail_data, verify=False)
                                            print(f"상세 페이지 응답 코드: {detail_response.status_code}")
                                            print(f"응답 URL: {detail_response.url}")
                                            print(f"응답 길이: {len(detail_response.text)} 문자")
                                            
                                            if detail_response.status_code == 200:
                                                detail_soup = BeautifulSoup(detail_response.text, 'html.parser')
                                                
                                                # 상세 페이지 내용 확인
                                                boardview = detail_soup.find('div', class_='boardveiw')
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
                                                                        print(f"✅ 변형 {i} 성공!")
                                                                        
                                                                        # 본문 내용 확인
                                                                        content_rows = tbody.find_all('tr')
                                                                        for row in content_rows:
                                                                            td_p = row.find('td', class_='td_p')
                                                                            if td_p:
                                                                                print(f"본문 내용 발견: {len(td_p.get_text(strip=True))} 문자")
                                                                                
                                                                                # 이미지 확인
                                                                                images = td_p.find_all('img')
                                                                                if images:
                                                                                    print(f"이미지 {len(images)}개 발견")
                                                                                    for img in images:
                                                                                        src = img.get('src', '')
                                                                                        print(f"  - 이미지: {src}")
                                                                        
                                                                        # 첨부파일 확인
                                                                        print("\n=== 4단계: 첨부파일 분석 ===")
                                                                        file_links = detail_soup.find_all('a', href=True)
                                                                        download_links = []
                                                                        
                                                                        for link in file_links:
                                                                            href = link.get('href', '')
                                                                            onclick = link.get('onclick', '')
                                                                            
                                                                            if any(keyword in href.lower() for keyword in ['download', 'file', 'attach']):
                                                                                download_links.append(('href', href, link.get_text(strip=True)))
                                                                            elif any(keyword in onclick.lower() for keyword in ['down(', 'download', 'file']):
                                                                                download_links.append(('onclick', onclick, link.get_text(strip=True)))
                                                                        
                                                                        if download_links:
                                                                            print(f"첨부파일 링크 {len(download_links)}개 발견:")
                                                                            for link_type, link_value, text in download_links:
                                                                                print(f"  - {link_type}: {link_value}")
                                                                                print(f"    텍스트: {text}")
                                                                        else:
                                                                            print("첨부파일 없음")
                                                                        
                                                                        # down() 함수 찾기
                                                                        script_tags = detail_soup.find_all('script')
                                                                        for script in script_tags:
                                                                            script_content = script.get_text()
                                                                            if 'function down(' in script_content:
                                                                                print(f"\ndown() 함수 발견")
                                                                                # down 함수 추출
                                                                                match = re.search(r'function down\([^}]+\}', script_content, re.DOTALL)
                                                                                if match:
                                                                                    print(f"down() 함수:\n{match.group(0)}")
                                                                        
                                                                        print(f"\n🎉 최종 성공!")
                                                                        print(f"✅ 목록 AJAX: POST {ajax_url}")
                                                                        print(f"✅ 상세 페이지: POST {detail_url}")
                                                                        print(f"✅ 성공한 POST 데이터: {detail_data}")
                                                                        return
                                                                    else:
                                                                        print(f"❌ 제목 불일치: 예상({title}) vs 실제({article_title})")
                                                                else:
                                                                    print("제목 셀을 찾을 수 없음")
                                                            else:
                                                                print("제목 행을 찾을 수 없음")
                                                        else:
                                                            print("tbody를 찾을 수 없음")
                                                    else:
                                                        print("테이블을 찾을 수 없음")
                                                else:
                                                    print("boardview를 찾을 수 없음")
                                                
                                                # 에러 페이지인지 확인
                                                if "오류" in detail_response.text or "error" in detail_response.text.lower():
                                                    print(f"❌ 변형 {i} 에러 페이지")
                                                else:
                                                    # HTML 샘플 출력
                                                    sample_html = detail_response.text[:1000]
                                                    print(f"HTML 샘플:\n{sample_html[:500]}...")
                                            else:
                                                print(f"❌ 변형 {i} HTTP 에러: {detail_response.status_code}")
                                        
                                        except Exception as e:
                                            print(f"❌ 변형 {i} 요청 실패: {e}")
                                    
                                    print(f"\n❌ 모든 변형 실패")
                                else:
                                    print("contId 추출 실패")
                            else:
                                print("링크를 찾을 수 없음")
                        else:
                            print(f"셀 수 부족: {len(cells)}")
                    else:
                        print("행이 없음")
                else:
                    print("tbody를 찾을 수 없음")
            else:
                print("테이블을 찾을 수 없음")
        else:
            print(f"AJAX 목록 요청 실패: {ajax_response.status_code}")
    
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_post_detail_access()