#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced GIB 스크래퍼 테스트
"""

import os
import sys
import logging

# 현재 디렉토리를 Python path에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from enhanced_gib_scraper import EnhancedGIBScraper

def test_enhanced_gib():
    """Enhanced GIB 스크래퍼 테스트"""
    print("Enhanced GIB 스크래퍼 테스트 시작")
    print("="*80)
    
    scraper = EnhancedGIBScraper()
    
    # 1. 목록 페이지 테스트
    print("\n1. 목록 페이지 테스트")
    print("-" * 40)
    
    try:
        response = scraper.get_page(scraper.list_url)
        if response:
            print(f"목록 페이지 응답: {response.status_code}")
            
            announcements = scraper.parse_list_page(response.text)
            print(f"파싱된 공고 수: {len(announcements)}개")
            
            if announcements:
                for i, ann in enumerate(announcements[:3]):  # 처음 3개만 출력
                    print(f"  {i+1}. {ann['title'][:50]}...")
                    print(f"     URL: {ann['url']}")
                    print(f"     첨부파일: {'있음' if ann['has_attachment'] else '없음'}")
                    if 'date' in ann:
                        print(f"     날짜: {ann['date']}")
                    print()
        else:
            print("목록 페이지 가져오기 실패")
            return
            
    except Exception as e:
        print(f"목록 페이지 테스트 오류: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 2. 상세 페이지 테스트
    if announcements:
        print("\n2. 상세 페이지 테스트")
        print("-" * 40)
        
        test_announcement = announcements[0]
        print(f"테스트 대상: {test_announcement['title']}")
        
        try:
            response = scraper.get_page(test_announcement['url'])
            if response:
                print(f"상세 페이지 응답: {response.status_code}")
                
                detail = scraper.parse_detail_page(response.text, test_announcement['url'])
                print(f"본문 길이: {len(detail['content'])}자")
                print(f"첨부파일 수: {len(detail['attachments'])}개")
                
                if detail['attachments']:
                    print("첨부파일 목록:")
                    for i, att in enumerate(detail['attachments']):
                        print(f"  {i+1}. {att['name']}")
                        print(f"     URL: {att.get('url', 'N/A')}")
                        if att.get('gib_download'):
                            print(f"     GIB 특별 다운로드: {att.get('attf_flag', '')}")
                        print()
                
                # 본문 미리보기
                if detail['content']:
                    print(f"본문 미리보기:\n{detail['content'][:200]}...")
                
            else:
                print("상세 페이지 가져오기 실패")
                
        except Exception as e:
            print(f"상세 페이지 테스트 오류: {e}")
            import traceback
            traceback.print_exc()
    
    # 3. 간단한 스크래핑 테스트 (1페이지만)
    print("\n3. 간단한 스크래핑 테스트")
    print("-" * 40)
    
    try:
        output_dir = "output/test_gib_enhanced"
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"출력 디렉토리: {output_dir}")
        print("1페이지만 스크래핑 시작...")
        
        scraper.scrape_pages(max_pages=1, output_base=output_dir)
        
        # 결과 확인
        if os.path.exists(output_dir):
            folders = [f for f in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, f))]
            print(f"생성된 폴더 수: {len(folders)}개")
            
            for folder in folders[:3]:  # 처음 3개 폴더만 확인
                folder_path = os.path.join(output_dir, folder)
                files = os.listdir(folder_path)
                print(f"  {folder}: {len(files)}개 파일")
                
                # content.md 파일 확인
                content_file = os.path.join(folder_path, 'content.md')
                if os.path.exists(content_file):
                    with open(content_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        print(f"    content.md: {len(content)}자")
                
                # attachments 폴더 확인
                attachments_folder = os.path.join(folder_path, 'attachments')
                if os.path.exists(attachments_folder):
                    att_files = os.listdir(attachments_folder)
                    print(f"    첨부파일: {len(att_files)}개")
        
    except Exception as e:
        print(f"스크래핑 테스트 오류: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*80}")
    print("Enhanced GIB 스크래퍼 테스트 완료")

if __name__ == "__main__":
    test_enhanced_gib()