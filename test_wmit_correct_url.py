#!/usr/bin/env python3
"""
WMIT 사이트 올바른 URL로 테스트
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time

def test_correct_urls():
    """올바른 URL 패턴으로 테스트"""
    
    base_url = "http://wmit.or.kr"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    session = requests.Session()
    session.headers.update(headers)
    
    print("=" * 60)
    print("WMIT 사이트 올바른 URL 테스트")
    print("=" * 60)
    
    # 1. 올바른 상세 페이지 URL 테스트
    detail_url = "http://wmit.or.kr/businessAnnounceDetail.do?noticeIdx=266&category=&menuId=2911"
    print(f"\n1. 상세 페이지 접근 테스트")
    print(f"URL: {detail_url}")
    print("-" * 60)
    
    try:
        detail_response = session.get(detail_url, timeout=30)
        print(f"응답 코드: {detail_response.status_code}")
        
        if detail_response.status_code == 200:
            detail_soup = BeautifulSoup(detail_response.text, 'html.parser')
            
            # 페이지 제목
            title = detail_soup.find('title')
            if title:
                print(f"페이지 제목: {title.get_text().strip()}")
            
            # 공고 제목 찾기
            title_selectors = [
                'h1', 'h2', 'h3', '.title', '.subject', '.notice-title',
                '[class*="title"]', '[class*="subject"]'
            ]
            
            announcement_title = None
            for selector in title_selectors:
                title_elem = detail_soup.select_one(selector)
                if title_elem:
                    title_text = title_elem.get_text(strip=True)
                    if len(title_text) > 10:  # 충분한 길이의 제목
                        announcement_title = title_text
                        print(f"공고 제목: {title_text}")
                        break
            
            # 본문 영역 찾기
            content_selectors = [
                '.content', '.view-content', '.board-content', '.detail-content',
                '.notice-content', '[class*="content"]', '.view', '.detail'
            ]
            
            content_found = False
            for selector in content_selectors:
                content_area = detail_soup.select_one(selector)
                if content_area:
                    content_text = content_area.get_text(strip=True)
                    if len(content_text) > 200:  # 충분한 내용
                        print(f"\n본문 영역 발견 ({selector})")
                        print(f"본문 길이: {len(content_text)} 문자")
                        print(f"본문 미리보기: {content_text[:300]}...")
                        content_found = True
                        break
            
            if not content_found:
                # 모든 div 중 가장 긴 텍스트 찾기
                all_divs = detail_soup.find_all(['div', 'section', 'article'])
                max_length = 0
                best_content = ""
                
                for div in all_divs:
                    text = div.get_text(strip=True)
                    if len(text) > max_length:
                        max_length = len(text)
                        best_content = text
                
                if max_length > 300:
                    print(f"\n가장 긴 텍스트 영역: {max_length} 문자")
                    print(f"내용 미리보기: {best_content[:300]}...")
            
            # 첨부파일 확인
            print(f"\n첨부파일 확인:")
            
            # 다양한 첨부파일 패턴 찾기
            file_patterns = [
                'a[href*="download"]',
                'a[href*="file"]',
                'a[href*="attach"]',
                '[class*="file"]',
                '[class*="attach"]'
            ]
            
            attachments = []
            for pattern in file_patterns:
                elements = detail_soup.select(pattern)
                for elem in elements:
                    href = elem.get('href', '')
                    text = elem.get_text(strip=True)
                    if href and ('download' in href.lower() or 'file' in href.lower()):
                        attachments.append((text, href))
            
            if attachments:
                for i, (text, href) in enumerate(attachments):
                    full_url = urljoin(base_url, href)
                    print(f"  {i+1}. {text} -> {full_url}")
            else:
                print("  첨부파일 링크를 찾을 수 없습니다.")
            
            # 상세 페이지 HTML 저장
            with open('/home/baltop/work/bizsupnew/btp_scraper/wmit_detail_correct.html', 'w', encoding='utf-8') as f:
                f.write(detail_response.text)
            print(f"\n상세 페이지 HTML 저장: wmit_detail_correct.html")
        
        else:
            print(f"상세 페이지 접근 실패: {detail_response.status_code}")
    
    except Exception as e:
        print(f"상세 페이지 테스트 실패: {e}")
    
    # 2. 첨부파일 다운로드 테스트
    print(f"\n2. 첨부파일 다운로드 테스트")
    print("-" * 60)
    
    download_url = "http://wmit.or.kr/downloadBizAnnounceFile.do?noticeIdx=266"
    print(f"다운로드 URL: {download_url}")
    
    try:
        # HEAD 요청으로 파일 정보 확인
        file_response = session.head(download_url, timeout=30)
        print(f"파일 응답 코드: {file_response.status_code}")
        
        if file_response.status_code == 200:
            content_type = file_response.headers.get('Content-Type', '')
            content_length = file_response.headers.get('Content-Length', '')
            content_disposition = file_response.headers.get('Content-Disposition', '')
            
            print(f"Content-Type: {content_type}")
            if content_length:
                print(f"파일 크기: {content_length} bytes")
            if content_disposition:
                print(f"Content-Disposition: {content_disposition}")
                
                # 파일명 추출
                import re
                filename_match = re.search(r'filename[^;=\n]*=([\'"]*)(.*?)\1', content_disposition)
                if filename_match:
                    filename = filename_match.group(2)
                    print(f"파일명: {filename}")
            
            # 실제 파일 다운로드 (작은 부분만)
            try:
                file_response_full = session.get(download_url, timeout=30)
                if file_response_full.status_code == 200:
                    print(f"실제 다운로드 성공! 파일 크기: {len(file_response_full.content)} bytes")
                    
                    # 첫 100바이트로 파일 타입 확인
                    content_start = file_response_full.content[:100]
                    if content_start.startswith(b'%PDF'):
                        print("파일 타입: PDF")
                    elif content_start.startswith(b'PK'):
                        print("파일 타입: ZIP/Office 문서")
                    elif b'<html' in content_start.lower():
                        print("파일 타입: HTML (오류 페이지일 수 있음)")
                    else:
                        print(f"파일 타입: 알 수 없음 (첫 20바이트: {content_start[:20]})")
                        
            except Exception as e:
                print(f"실제 다운로드 실패: {e}")
                
        else:
            print(f"파일 접근 실패: {file_response.status_code}")
    
    except Exception as e:
        print(f"첨부파일 테스트 실패: {e}")
    
    # 3. 페이지네이션 심화 테스트
    print(f"\n3. 페이지네이션 심화 테스트")
    print("-" * 60)
    
    list_url = "http://wmit.or.kr/announce/businessAnnounceList.do"
    
    # 페이지 2 POST 요청 성공 확인
    try:
        page2_response = session.post(list_url, data={'page': 2}, timeout=30)
        print(f"2페이지 POST 응답 코드: {page2_response.status_code}")
        
        if page2_response.status_code == 200:
            page2_soup = BeautifulSoup(page2_response.text, 'html.parser')
            page2_table = page2_soup.find('table', class_=['tbl', 'text-center'])
            
            if page2_table:
                page2_tbody = page2_table.find('tbody')
                page2_rows = page2_tbody.find_all('tr') if page2_tbody else []
                
                if page2_rows:
                    print(f"2페이지 공고 수: {len(page2_rows)}")
                    
                    # 첫 번째 공고 정보
                    first_row = page2_rows[0]
                    cells = first_row.find_all('td')
                    
                    print("\n2페이지 첫 번째 공고:")
                    if len(cells) >= 3:
                        num = cells[0].get_text(strip=True)
                        category = cells[1].get_text(strip=True)
                        title_cell = cells[2]
                        title_link = title_cell.find('a')
                        
                        print(f"  번호: {num}")
                        print(f"  구분: {category}")
                        
                        if title_link:
                            title = title_link.get_text(strip=True)
                            href = title_link.get('href', '')
                            print(f"  제목: {title}")
                            print(f"  링크: {href}")
                
                # 2페이지 HTML 저장
                with open('/home/baltop/work/bizsupnew/btp_scraper/wmit_page2.html', 'w', encoding='utf-8') as f:
                    f.write(page2_response.text)
                print(f"\n2페이지 HTML 저장: wmit_page2.html")
                
            else:
                print("2페이지에서 테이블을 찾을 수 없습니다.")
        else:
            print(f"2페이지 접근 실패: {page2_response.status_code}")
    
    except Exception as e:
        print(f"2페이지 테스트 실패: {e}")
    
    print(f"\n테스트 완료!")
    print("생성된 파일:")
    print("- wmit_detail_correct.html")
    print("- wmit_page2.html")

if __name__ == "__main__":
    test_correct_urls()