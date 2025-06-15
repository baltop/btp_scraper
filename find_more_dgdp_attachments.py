#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DGDP 여러 페이지에서 첨부파일이 있는 공고들 찾기
"""

import requests
import json
import re
from enhanced_dgdp_scraper import EnhancedDGDPScraper

def find_announcements_with_attachments():
    """여러 페이지에서 첨부파일이 있는 공고들 찾기"""
    print("=== DGDP 첨부파일이 있는 공고 찾기 ===")
    
    scraper = EnhancedDGDPScraper()
    
    attachments_found = []
    
    # 4페이지까지 검색
    for page_num in range(1, 5):
        print(f"\n--- 페이지 {page_num} 검색 중 ---")
        
        # API 요청 데이터
        request_data = {
            "searchCategory": "",
            "searchCategorySub": "",
            "searchValue": "",
            "searchType": "all",
            "pageIndex": page_num,
            "pageUnit": 10,
            "pageSize": 5
        }
        
        try:
            response = scraper.session.post(
                scraper.api_url,
                json=request_data,
                headers=scraper.headers,
                verify=False,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data['data']['dataList']
                
                print(f"페이지 {page_num}에서 {len(items)}개 공고 발견")
                
                for item in items:
                    announcement_id = item.get('id')
                    title = item.get('title', 'Unknown')
                    category = item.get('category', 'Unknown')
                    
                    # 상세 페이지에서 첨부파일 확인
                    detail_url = f"https://dgdp.or.kr/notice/public/{announcement_id}"
                    
                    try:
                        detail_response = scraper.session.get(detail_url, verify=False, timeout=20)
                        
                        if detail_response.status_code == 200:
                            # JavaScript에서 파일 정보 추출
                            pattern = r'{"fileUploadId":\d+,"fileNm":"[^"]*","fileSize":\d+,"fileExt":"[^"]*","fileUuid":"[^"]*"}'
                            matches = re.findall(pattern, detail_response.text)
                            
                            if matches:
                                files = []
                                for match in matches:
                                    try:
                                        file_data = json.loads(match)
                                        files.append(file_data)
                                    except json.JSONDecodeError:
                                        continue
                                
                                if files:
                                    print(f"  ✓ {title} (ID: {announcement_id}) - {len(files)}개 파일")
                                    
                                    attachment_info = {
                                        'page': page_num,
                                        'id': announcement_id,
                                        'title': title,
                                        'category': category,
                                        'url': detail_url,
                                        'files': files
                                    }
                                    
                                    attachments_found.append(attachment_info)
                                    
                                    # 파일 상세 정보 출력
                                    for file_info in files:
                                        file_name = file_info.get('fileNm', 'Unknown')
                                        file_ext = file_info.get('fileExt', 'Unknown')
                                        file_size = file_info.get('fileSize', 0)
                                        file_uuid = file_info.get('fileUuid', '')
                                        
                                        print(f"    - {file_name}.{file_ext} ({file_size:,} bytes)")
                                        print(f"      UUID: {file_uuid}")
                                        print(f"      다운로드 URL: https://dgdp.or.kr/file/download/board/{file_uuid}")
                            else:
                                print(f"  - {title} (ID: {announcement_id}) - 첨부파일 없음")
                        else:
                            print(f"  - {title} (ID: {announcement_id}) - 상세 페이지 로드 실패")
                            
                    except Exception as e:
                        print(f"  - {title} (ID: {announcement_id}) - 오류: {e}")
                        
            else:
                print(f"페이지 {page_num} API 호출 실패: {response.status_code}")
                break
                
        except Exception as e:
            print(f"페이지 {page_num} 처리 중 오류: {e}")
    
    # 결과 요약
    print(f"\n=== 첨부파일이 있는 공고 요약 ===")
    print(f"총 {len(attachments_found)}개 공고에서 첨부파일 발견")
    
    total_files = 0
    korean_files = 0
    pdf_files = 0
    hwp_files = 0
    other_files = 0
    
    for announcement in attachments_found:
        print(f"\n📋 {announcement['title']}")
        print(f"   URL: {announcement['url']}")
        print(f"   분류: {announcement['category']}")
        print(f"   페이지: {announcement['page']}")
        print(f"   첨부파일 {len(announcement['files'])}개:")
        
        for file_info in announcement['files']:
            file_name = file_info.get('fileNm', 'Unknown')
            file_ext = file_info.get('fileExt', 'Unknown')
            file_size = file_info.get('fileSize', 0)
            
            # 한글 파일명 확인
            has_korean = any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in file_name)
            if has_korean:
                korean_files += 1
            
            # 파일 타입별 카운트
            if file_ext.lower() == 'pdf':
                pdf_files += 1
            elif file_ext.lower() == 'hwp':
                hwp_files += 1
            else:
                other_files += 1
            
            total_files += 1
            
            korean_indicator = "🇰🇷" if has_korean else ""
            print(f"     📄 {file_name}.{file_ext} ({file_size:,} bytes) {korean_indicator}")
    
    print(f"\n=== 파일 통계 ===")
    print(f"총 파일 수: {total_files}개")
    print(f"한글 파일명: {korean_files}개")
    print(f"PDF 파일: {pdf_files}개")
    print(f"HWP 파일: {hwp_files}개")
    print(f"기타 파일: {other_files}개")
    
    return attachments_found

def test_sample_downloads(attachments_found):
    """샘플 파일 다운로드 테스트"""
    print(f"\n=== 샘플 파일 다운로드 테스트 ===")
    
    if not attachments_found:
        print("테스트할 첨부파일이 없습니다.")
        return
    
    scraper = EnhancedDGDPScraper()
    
    # 처음 3개 공고의 첫 번째 파일들만 테스트
    for i, announcement in enumerate(attachments_found[:3]):
        if announcement['files']:
            file_info = announcement['files'][0]  # 첫 번째 파일만
            
            file_name = file_info.get('fileNm', 'Unknown')
            file_ext = file_info.get('fileExt', 'Unknown')
            file_uuid = file_info.get('fileUuid', '')
            file_size = file_info.get('fileSize', 0)
            
            download_url = f"https://dgdp.or.kr/file/download/board/{file_uuid}"
            
            print(f"\n{i+1}. {file_name}.{file_ext}")
            print(f"   URL: {download_url}")
            print(f"   크기: {file_size:,} bytes")
            
            try:
                # HEAD 요청으로 확인
                response = scraper.session.head(download_url, verify=False, timeout=10)
                
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    content_disposition = response.headers.get('content-disposition', '')
                    
                    print(f"   ✓ 다운로드 가능")
                    print(f"   Content-Type: {content_type}")
                    
                    # Content-Disposition에서 파일명 추출
                    if content_disposition:
                        import re
                        filename_match = re.search(r'filename[*]?="?([^";\s]+)"?', content_disposition)
                        if filename_match:
                            encoded_filename = filename_match.group(1)
                            try:
                                from urllib.parse import unquote
                                decoded_filename = unquote(encoded_filename)
                                print(f"   서버 파일명: {decoded_filename}")
                            except:
                                print(f"   서버 파일명 (인코딩): {encoded_filename}")
                else:
                    print(f"   ✗ 다운로드 실패: {response.status_code}")
                    
            except Exception as e:
                print(f"   ✗ 오류: {e}")

if __name__ == "__main__":
    attachments_found = find_announcements_with_attachments()
    test_sample_downloads(attachments_found)