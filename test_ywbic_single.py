#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YWBIC 단일 공고 테스트 (첫 번째 공고 - 첨부파일 포함)
"""

import os
import sys
import logging
from datetime import datetime
from enhanced_ywbic_scraper import EnhancedYwbicScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def test_first_announcement():
    """첫 번째 공고만 테스트 (첨부파일 확인용)"""
    print("🔍 YWBIC 첫 번째 공고 테스트 (첨부파일 포함)")
    print("=" * 50)
    
    # 출력 디렉토리 설정
    output_dir = "output/ywbic_single"
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # 스크래퍼 초기화
        scraper = EnhancedYwbicScraper()
        
        # 먼저 목록 페이지에서 실제 링크를 가져오기
        list_response = scraper.session.get(scraper.list_url)
        list_response.raise_for_status()
        
        announcements = scraper.parse_list_page(list_response.text)
        if not announcements:
            print("❌ 목록에서 공고를 찾을 수 없습니다")
            return
        
        # 첫 번째 공고 선택
        first_announcement = announcements[0]
        detail_url = first_announcement['url']
        print(f"📋 선택된 공고: {first_announcement['title']}")
        print(f"📋 번호: {first_announcement['number']}")
        
        print(f"📄 상세 페이지 접근: {detail_url}")
        
        # 상세 페이지 가져오기 (Referer 헤더 추가)
        headers = {
            'Referer': scraper.list_url,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # SSL 검증 비활성화하고 요청
        response = scraper.session.get(detail_url, headers=headers, verify=False)
        response.raise_for_status()
        
        print(f"✅ 페이지 로드 성공 (길이: {len(response.text)})")
        
        # 상세 페이지 파싱
        detail_data = scraper.parse_detail_page(response.text)
        
        print(f"📋 제목: {detail_data['title']}")
        print(f"📄 본문 길이: {len(detail_data['content'])}")
        print(f"📎 첨부파일 수: {len(detail_data['attachments'])}")
        
        # 첨부파일 정보 출력
        for i, attachment in enumerate(detail_data['attachments'], 1):
            print(f"   {i}. {attachment['filename']}")
            print(f"      URL: {attachment['url']}")
        
        # 공고 디렉토리 생성 (첨부파일 여부와 관계없이)
        announcement_dir = os.path.join(output_dir, "001_첨부파일_테스트")
        os.makedirs(announcement_dir, exist_ok=True)
        
        if detail_data['attachments']:
            
            # 본문 저장
            content_file = os.path.join(announcement_dir, "content.md")
            with open(content_file, 'w', encoding='utf-8') as f:
                f.write(f"# {detail_data['title']}\n\n")
                f.write(f"**원본 URL**: {detail_url}\n\n")
                f.write("---\n\n")
                f.write(detail_data['content'])
            
            print(f"💾 본문 저장: {content_file}")
            
            # 첨부파일 다운로드
            for attachment in detail_data['attachments']:
                print(f"\n📥 다운로드 시도: {attachment['filename']}")
                
                downloaded_file = scraper.download_file(
                    attachment['url'], 
                    attachment['filename'], 
                    announcement_dir
                )
                
                if downloaded_file:
                    file_size = os.path.getsize(downloaded_file)
                    print(f"✅ 다운로드 성공: {os.path.basename(downloaded_file)} ({file_size:,} bytes)")
                else:
                    print(f"❌ 다운로드 실패: {attachment['filename']}")
        
        else:
            print("❌ 첨부파일이 검출되지 않았습니다")
            
        # 결과 확인
        print(f"\n📊 결과 확인:")
        if os.path.exists(announcement_dir):
            files = os.listdir(announcement_dir)
            print(f"   생성된 파일: {len(files)}개")
            for file in files:
                file_path = os.path.join(announcement_dir, file)
                if os.path.isfile(file_path):
                    size = os.path.getsize(file_path)
                    print(f"   - {file}: {size:,} bytes")
        
        print("\n✅ 테스트 완료!")
        
    except Exception as e:
        logger.error(f"테스트 실패: {e}")
        raise

if __name__ == "__main__":
    test_first_announcement()