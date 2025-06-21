#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JBSOS 스크래퍼 업데이트 테스트
실제 HTML 구조를 반영한 개선사항 검증
"""

import os
import sys
import logging
from enhanced_jbsos_scraper import EnhancedJBSOSScraper

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_jbsos_scraper():
    """JBSOS 스크래퍼 테스트 - 첫 페이지만"""
    try:
        # 스크래퍼 초기화
        scraper = EnhancedJBSOSScraper()
        
        # 출력 디렉토리 생성
        output_dir = "output/jbsos_test"
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info("JBSOS 스크래퍼 테스트 시작")
        
        # 첫 페이지 목록 가져오기
        list_url = scraper.get_list_url(1)
        logger.info(f"목록 페이지 URL: {list_url}")
        
        # 목록 페이지 다운로드
        response = scraper.session.get(list_url, timeout=30)
        response.raise_for_status()
        
        logger.info(f"목록 페이지 응답 상태: {response.status_code}")
        logger.info(f"페이지 크기: {len(response.text):,} 문자")
        
        # 목록 파싱
        announcements = scraper.parse_list_page(response.text)
        logger.info(f"파싱된 공고 수: {len(announcements)}")
        
        if announcements:
            # 첫 번째 공고 상세 페이지 테스트
            first_announcement = announcements[0]
            logger.info(f"첫 번째 공고: {first_announcement['title']}")
            logger.info(f"상세 URL: {first_announcement['url']}")
            
            # 상세 페이지 다운로드
            detail_response = scraper.session.get(first_announcement['url'], timeout=30)
            detail_response.raise_for_status()
            
            logger.info(f"상세 페이지 응답 상태: {detail_response.status_code}")
            
            # 상세 페이지 파싱
            detail_result = scraper.parse_detail_page(detail_response.text)
            
            logger.info(f"본문 길이: {len(detail_result['content'])} 문자")
            logger.info(f"첨부파일 수: {len(detail_result['attachments'])}")
            
            # 첨부파일 정보 출력
            for i, attachment in enumerate(detail_result['attachments']):
                logger.info(f"첨부파일 {i+1}: {attachment['name']}")
                logger.info(f"  URL: {attachment['url']}")
            
            # 결과 파일 저장
            safe_title = scraper.sanitize_filename(first_announcement['title'])
            content_file = os.path.join(output_dir, f"{safe_title}.md")
            
            with open(content_file, 'w', encoding='utf-8') as f:
                f.write(detail_result['content'])
            
            logger.info(f"본문 저장 완료: {content_file}")
            
            # 첫 번째 첨부파일 다운로드 테스트
            if detail_result['attachments']:
                first_attachment = detail_result['attachments'][0]
                safe_filename = scraper.sanitize_filename(first_attachment['name'])
                attachment_path = os.path.join(output_dir, safe_filename)
                
                success = scraper.download_file(first_attachment['url'], attachment_path)
                if success:
                    logger.info(f"첨부파일 다운로드 성공: {attachment_path}")
                else:
                    logger.warning(f"첨부파일 다운로드 실패: {first_attachment['name']}")
        
        logger.info("JBSOS 스크래퍼 테스트 완료")
        return True
        
    except Exception as e:
        logger.error(f"테스트 실패: {e}")
        return False

def print_analysis_results():
    """분석 결과 요약 출력"""
    print("\n" + "="*60)
    print("JBSOS 사이트 HTML 구조 분석 결과")
    print("="*60)
    
    print("\n1. 목록 페이지 구조:")
    print("   - 기본 구조: <ul> > <li> 요소들")
    print("   - 각 공고: <li> 내부의 <a> 태그로 링크")
    print("   - URL 패턴: board.php?bo_table=s_sub04_01&wr_id=XXX")
    
    print("\n2. 상세 페이지 구조:")
    print("   - 본문: <article> 태그 내부")
    print("   - 첨부파일: <h2>첨부파일</h2> 다음의 <ul> 리스트")
    print("   - 다운로드: download.php?bo_table=...&wr_id=...&no=...&nonce=...")
    
    print("\n3. 페이지네이션:")
    print("   - URL 패턴: board.php?bo_table=s_sub04_01&page=N")
    print("   - 현재 페이지: <strong> 태그로 표시")
    
    print("\n4. 개선사항:")
    print("   - 실제 HTML 선택자 사용 (ul li, article 등)")
    print("   - 첨부파일 추출 로직 개선")
    print("   - 다양한 폴백 방식 적용")
    print("   - 한글 파일명 처리 강화")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    print_analysis_results()
    
    print("\nJBSOS 스크래퍼 테스트를 시작합니다...")
    success = test_jbsos_scraper()
    
    if success:
        print("\n✅ 테스트 성공! 스크래퍼가 정상적으로 작동합니다.")
    else:
        print("\n❌ 테스트 실패! 로그를 확인해주세요.")