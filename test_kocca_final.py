#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KOCCA 스크래퍼 최종 테스트
"""

import os
import logging
from enhanced_kocca_scraper import EnhancedKOCCAScraper

def test_kocca_scraper():
    """KOCCA 스크래퍼 테스트"""
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 출력 디렉토리 생성
    output_dir = "output/kocca_test"
    os.makedirs(output_dir, exist_ok=True)
    
    # 스크래퍼 생성
    scraper = EnhancedKOCCAScraper()
    
    print("=== KOCCA 스크래퍼 테스트 시작 ===")
    
    # 테스트할 공고 URLs
    test_urls = [
        'https://www.kocca.kr/kocca/pims/view.do?intcNo=325D00059001&menuNo=204104',  # VP 활용 콘텐츠
        'https://www.kocca.kr/kocca/pims/view.do?intcNo=325D00091008&menuNo=204104',  # 차이나 라이선싱
    ]
    
    success_count = 0
    total_attachments = 0
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n--- 공고 {i} 테스트 ---")
        print(f"URL: {url}")
        
        try:
            # 상세 페이지 파싱
            response = scraper.session.get(url)
            if response.status_code != 200:
                print(f"HTTP 오류: {response.status_code}")
                continue
                
            result = scraper.parse_detail_page(response.text, url)
            
            # 결과 출력
            print(f"본문 길이: {len(result['content'])} 문자")
            print(f"첨부파일 수: {len(result['attachments'])}개")
            
            if result['attachments']:
                success_count += 1
                total_attachments += len(result['attachments'])
                
                for j, att in enumerate(result['attachments'], 1):
                    print(f"  {j}. {att['name']}")
                    print(f"     타입: {att.get('type', 'unknown')}")
                    print(f"     크기: {att.get('size', '알 수 없음')}")
                    print(f"     URL: {att['url']}")
                    
                    # 다운로드 테스트 (첫 번째 파일만)
                    if j == 1:
                        file_dir = os.path.join(output_dir, f"announcement_{i}")
                        os.makedirs(file_dir, exist_ok=True)
                        
                        # 안전한 파일명 생성
                        safe_filename = att['name'].replace('/', '_').replace('\\', '_')
                        save_path = os.path.join(file_dir, safe_filename)
                        
                        print(f"     다운로드 테스트: {save_path}")
                        
                        # 직접 다운로드 (스크래퍼 함수 대신)
                        try:
                            dl_response = scraper.session.get(
                                att['url'], 
                                stream=True, 
                                headers={'Referer': scraper.pms_base_url}
                            )
                            if dl_response.status_code == 200:
                                with open(save_path, 'wb') as f:
                                    for chunk in dl_response.iter_content(chunk_size=8192):
                                        if chunk:
                                            f.write(chunk)
                                
                                file_size = os.path.getsize(save_path)
                                print(f"     다운로드 성공: {file_size:,} bytes")
                            else:
                                print(f"     다운로드 실패: HTTP {dl_response.status_code}")
                        except Exception as e:
                            print(f"     다운로드 오류: {e}")
            else:
                print("  첨부파일이 없습니다.")
                
        except Exception as e:
            print(f"오류: {e}")
            continue
    
    print(f"\n=== 테스트 완료 ===")
    print(f"성공한 공고: {success_count}/{len(test_urls)}")
    print(f"총 첨부파일: {total_attachments}개")
    print(f"출력 디렉토리: {output_dir}")
    
    return success_count > 0

if __name__ == "__main__":
    test_kocca_scraper()