#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py 테스트 (3개 스크래퍼만)
"""

import os
import sys
import logging
import concurrent.futures
from datetime import datetime
import time

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 테스트용 Enhanced 스크래퍼들 import
from enhanced_gsif_scraper import EnhancedGSIFScraper
from enhanced_jbf_scraper import EnhancedJBFScraper
from enhanced_koema_scraper import EnhancedKOEMAScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 테스트용 스크래퍼 정의
TEST_SCRAPERS = {
    'gsif': {
        'class': EnhancedGSIFScraper,
        'name': 'GSIF (강릉과학산업진흥원)',
        'output_dir': 'gsif_enhanced'
    },
    'jbf': {
        'class': EnhancedJBFScraper,
        'name': 'JBF (전남바이오진흥원)',
        'output_dir': 'jbf_enhanced'
    },
    'koema': {
        'class': EnhancedKOEMAScraper,
        'name': 'KOEMA (한국에너지공단)',
        'output_dir': 'koema_enhanced'
    }
}

def run_single_scraper(scraper_config, max_pages=1):
    """단일 스크래퍼 실행"""
    scraper_key = scraper_config['key']
    scraper_info = scraper_config['info']
    
    start_time = time.time()
    
    try:
        logger.info(f"🚀 [{scraper_key.upper()}] {scraper_info['name']} 스크래핑 시작")
        
        # 스크래퍼 인스턴스 생성
        scraper_class = scraper_info['class']
        scraper = scraper_class()
        
        # 출력 디렉토리 설정
        output_dir = f"./output/{scraper_info['output_dir']}"
        
        # 스크래핑 실행
        scraper.scrape_pages(max_pages=max_pages, output_base=output_dir)
        
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info(f"✅ [{scraper_key.upper()}] 완료 - {duration:.1f}초")
        
        return {
            'scraper': scraper_key,
            'name': scraper_info['name'],
            'status': 'success',
            'duration': duration,
            'output_dir': output_dir
        }
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        
        logger.error(f"❌ [{scraper_key.upper()}] 실패 - {e}")
        
        return {
            'scraper': scraper_key,
            'name': scraper_info['name'],
            'status': 'error',
            'error': str(e),
            'duration': duration
        }

def test_concurrent_execution():
    """동시 실행 테스트"""
    print("🚀 Enhanced 스크래퍼 동시 실행 테스트")
    print("="*50)
    
    start_time = datetime.now()
    
    # 스크래퍼 설정 준비
    scraper_configs = []
    for key, info in TEST_SCRAPERS.items():
        scraper_configs.append({
            'key': key,
            'info': info
        })
    
    print(f"📋 테스트 대상: {len(scraper_configs)}개 스크래퍼")
    for config in scraper_configs:
        print(f"   • {config['info']['name']}")
    print()
    
    # 3개 동시 실행
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_to_scraper = {
            executor.submit(run_single_scraper, config, 1): config['key']
            for config in scraper_configs
        }
        
        results = []
        
        for future in concurrent.futures.as_completed(future_to_scraper):
            scraper_key = future_to_scraper[future]
            try:
                result = future.result()
                results.append(result)
                print(f"✨ {result['name']} 완료!")
            except Exception as e:
                logger.error(f"스크래퍼 {scraper_key} 실행 중 예외 발생: {e}")
    
    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()
    
    print(f"\n🎯 테스트 결과:")
    print(f"  • 전체 실행 시간: {total_duration:.1f}초")
    
    successful = [r for r in results if r['status'] == 'success']
    failed = [r for r in results if r['status'] == 'error']
    
    print(f"  • 성공: {len(successful)}개")
    print(f"  • 실패: {len(failed)}개")
    
    if successful:
        print(f"\n✅ 성공한 스크래퍼들:")
        for result in successful:
            print(f"  • {result['name']}: {result['duration']:.1f}초")
    
    if failed:
        print(f"\n❌ 실패한 스크래퍼들:")
        for result in failed:
            print(f"  • {result['name']}: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    test_concurrent_execution()
    print("\n🎉 테스트 완료!")