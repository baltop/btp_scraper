#!/usr/bin/env python3
"""
WMIT 사이트 세부 기능 테스트 - 상세 페이지와 페이지네이션
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time

def test_pagination_and_detail():
    """페이지네이션과 상세 페이지 테스트"""
    
    base_url = "http://wmit.or.kr"
    list_url = "http://wmit.or.kr/announce/businessAnnounceList.do"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    session = requests.Session()
    session.headers.update(headers)
    
    print("=" * 60)
    print("WMIT 사이트 세부 기능 테스트")
    print("=" * 60)
    
    # 1. 첫 번째 페이지 분석
    print("\n1. 첫 번째 페이지 분석")
    print("-" * 30)
    
    try:
        response = session.get(list_url, timeout=30)
        print(f"응답 코드: {response.status_code}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', class_=['tbl', 'text-center'])
        
        if table:
            tbody = table.find('tbody')
            rows = tbody.find_all('tr') if tbody else []
            print(f"공고 수: {len(rows)}")
            
            # 첫 번째 공고 상세 정보
            if rows:
                first_row = rows[0]
                cells = first_row.find_all('td')
                
                # 제목과 링크 추출
                title_cell = cells[2] if len(cells) > 2 else None
                if title_cell:
                    link = title_cell.find('a')
                    if link:
                        title = link.get_text(strip=True)
                        detail_href = link.get('href', '')
                        detail_url = urljoin(base_url, detail_href)
                        
                        print(f"첫 번째 공고 제목: {title}")
                        print(f"상세 페이지 URL: {detail_url}")
                        
                        # 2. 상세 페이지 접근 테스트
                        print(f"\n2. 상세 페이지 접근 테스트")
                        print("-" * 30)
                        
                        try:
                            detail_response = session.get(detail_url, timeout=30)
                            print(f"상세 페이지 응답 코드: {detail_response.status_code}")
                            
                            detail_soup = BeautifulSoup(detail_response.text, 'html.parser')
                            
                            # 페이지 제목 확인
                            page_title = detail_soup.find('title')
                            if page_title:
                                print(f"상세 페이지 제목: {page_title.get_text().strip()}")
                            
                            # 본문 영역 찾기
                            content_areas = [
                                '.content', '.view_content', '.board_content',
                                '.detail_content', '.notice_content', '[class*="content"]'
                            ]
                            
                            content_found = False
                            for selector in content_areas:
                                content_area = detail_soup.select_one(selector)
                                if content_area:
                                    content_text = content_area.get_text(strip=True)
                                    if len(content_text) > 100:  # 충분한 내용이 있는 경우
                                        print(f"본문 영역 발견 ({selector}): {len(content_text)} 문자")
                                        print(f"본문 미리보기: {content_text[:200]}...")
                                        content_found = True
                                        break
                            
                            if not content_found:
                                # 전체 본문에서 텍스트가 많은 영역 찾기
                                all_divs = detail_soup.find_all(['div', 'section', 'article'])
                                max_text_length = 0
                                best_div = None
                                
                                for div in all_divs:
                                    text = div.get_text(strip=True)
                                    if len(text) > max_text_length:
                                        max_text_length = len(text)
                                        best_div = div
                                
                                if best_div and max_text_length > 200:
                                    print(f"가장 긴 텍스트 영역: {max_text_length} 문자")
                                    print(f"미리보기: {best_div.get_text(strip=True)[:200]}...")
                            
                            # 첨부파일 확인
                            print(f"\n첨부파일 확인:")
                            file_links = detail_soup.find_all('a', href=lambda x: x and ('download' in x.lower() or 'file' in x.lower()))
                            if file_links:
                                for i, link in enumerate(file_links):
                                    href = link.get('href', '')
                                    text = link.get_text(strip=True)
                                    print(f"  {i+1}. {text} -> {href}")
                            else:
                                print("  첨부파일 링크를 찾을 수 없습니다.")
                            
                            # 상세 페이지 HTML 저장
                            with open('/home/baltop/work/bizsupnew/btp_scraper/wmit_detail.html', 'w', encoding='utf-8') as f:
                                f.write(detail_response.text)
                            print("상세 페이지 HTML 저장: wmit_detail.html")
                            
                        except Exception as e:
                            print(f"상세 페이지 접근 실패: {e}")
                
                # 첨부파일 다운로드 테스트 (목록 페이지에서)
                print(f"\n3. 첨부파일 다운로드 테스트")
                print("-" * 30)
                
                attach_cell = cells[8] if len(cells) > 8 else None  # 첨부 컬럼
                if attach_cell:
                    attach_link = attach_cell.find('a')
                    if attach_link:
                        download_href = attach_link.get('href', '')
                        download_url = urljoin(base_url, download_href)
                        print(f"첨부파일 다운로드 URL: {download_url}")
                        
                        try:
                            # HEAD 요청으로 파일 정보만 확인
                            file_response = session.head(download_url, timeout=30)
                            print(f"파일 응답 코드: {file_response.status_code}")
                            
                            content_type = file_response.headers.get('Content-Type', '')
                            content_length = file_response.headers.get('Content-Length', '')
                            content_disposition = file_response.headers.get('Content-Disposition', '')
                            
                            print(f"Content-Type: {content_type}")
                            if content_length:
                                print(f"파일 크기: {content_length} bytes")
                            if content_disposition:
                                print(f"Content-Disposition: {content_disposition}")
                                
                        except Exception as e:
                            print(f"첨부파일 접근 실패: {e}")
        
        # 4. 페이지네이션 테스트
        print(f"\n4. 페이지네이션 테스트")
        print("-" * 30)
        
        # move_page 함수 분석을 위해 JavaScript 확인
        scripts = soup.find_all('script')
        move_page_found = False
        
        for script in scripts:
            if script.string and 'move_page' in script.string:
                print("move_page 함수 발견:")
                lines = script.string.split('\n')
                for line in lines:
                    if 'move_page' in line and ('function' in line or '{' in line):
                        print(f"  {line.strip()}")
                        move_page_found = True
        
        if not move_page_found:
            print("move_page 함수를 찾을 수 없습니다. POST 요청 방식일 수 있습니다.")
        
        # 2페이지 접근 시도 (POST 방식 추정)
        print(f"\n2페이지 접근 시도...")
        
        # 일반적인 페이지네이션 POST 파라미터들 시도
        post_params_list = [
            {'page': 2},
            {'pageNo': 2},
            {'currentPage': 2},
            {'pageIndex': 2},
        ]
        
        for params in post_params_list:
            try:
                page2_response = session.post(list_url, data=params, timeout=30)
                if page2_response.status_code == 200:
                    page2_soup = BeautifulSoup(page2_response.text, 'html.parser')
                    page2_table = page2_soup.find('table', class_=['tbl', 'text-center'])
                    
                    if page2_table:
                        page2_tbody = page2_table.find('tbody')
                        page2_rows = page2_tbody.find_all('tr') if page2_tbody else []
                        
                        if page2_rows:
                            # 첫 번째 공고 번호 확인 (다른 페이지인지 확인)
                            first_cell = page2_rows[0].find_all('td')[0]
                            page2_first_num = first_cell.get_text(strip=True)
                            
                            # 원래 페이지의 첫 번째 공고 번호와 비교
                            original_first_num = rows[0].find_all('td')[0].get_text(strip=True)
                            
                            if page2_first_num != original_first_num:
                                print(f"2페이지 접근 성공! (파라미터: {params})")
                                print(f"  첫 번째 공고 번호: {page2_first_num}")
                                break
                            else:
                                print(f"같은 페이지 반환됨 (파라미터: {params})")
                        else:
                            print(f"2페이지에 데이터 없음 (파라미터: {params})")
                    else:
                        print(f"2페이지 테이블 없음 (파라미터: {params})")
                else:
                    print(f"2페이지 접근 실패 (파라미터: {params}): {page2_response.status_code}")
                    
            except Exception as e:
                print(f"2페이지 접근 오류 (파라미터: {params}): {e}")
        
    except Exception as e:
        print(f"전체 테스트 실패: {e}")
    
    print(f"\n테스트 완료!")

if __name__ == "__main__":
    test_pagination_and_detail()