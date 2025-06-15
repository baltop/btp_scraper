#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
전체 main.py 테스트 (6개 스크래퍼)
"""

import os
import sys
import logging
import concurrent.futures
from datetime import datetime
import time

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 테스트용 Enhanced 스크래퍼들 import (6개만)
from enhanced_gsif_scraper import EnhancedGSIFScraper
from enhanced_jbf_scraper import EnhancedJBFScraper
from enhanced_koema_scraper import EnhancedKOEMAScraper
from enhanced_cci_scraper import EnhancedCCIScraper
from enhanced_dcb_scraper import EnhancedDCBScraper
from enhanced_djbea_scraper import EnhancedDJBEAScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 테스트용 6개 스크래퍼 정의
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
    },
    'cci': {
        'class': EnhancedCCIScraper,
        'name': 'CCI (창조경제혁신센터)',
        'output_dir': 'cci_enhanced'
    },
    'dcb': {
        'class': EnhancedDCBScraper,
        'name': 'DCB (대구디지털산업진흥원)',
        'output_dir': 'dcb_enhanced'
    },
    'djbea': {
        'class': EnhancedDJBEAScraper,
        'name': 'DJBEA (대전바이오진흥원)',
        'output_dir': 'djbea_enhanced'
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
        
        # 결과 통계 수집
        stats = collect_scraper_stats(output_dir)
        
        logger.info(f"✅ [{scraper_key.upper()}] 완료 - {duration:.1f}초, 공고 {stats['announcements']}개, 파일 {stats['files']}개")
        
        return {
            'scraper': scraper_key,
            'name': scraper_info['name'],
            'status': 'success',
            'duration': duration,
            'announcements': stats['announcements'],
            'files': stats['files'],
            'total_size': stats['total_size'],
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
            'duration': duration,
            'announcements': 0,
            'files': 0,
            'total_size': 0
        }

def collect_scraper_stats(output_dir):
    """스크래퍼 실행 결과 통계 수집"""
    stats = {
        'announcements': 0,
        'files': 0,
        'total_size': 0
    }
    
    try:
        if not os.path.exists(output_dir):
            return stats
        
        # 공고 폴더들 찾기
        announcement_folders = [
            item for item in os.listdir(output_dir)
            if os.path.isdir(os.path.join(output_dir, item)) and 
               any(item.startswith(prefix) for prefix in ['001_', '002_', '003_', '004_', '005_', '006_', '007_', '008_', '009_'])
        ]
        
        stats['announcements'] = len(announcement_folders)
        
        # 첨부파일 통계
        for folder in announcement_folders:
            attachments_dir = os.path.join(output_dir, folder, 'attachments')
            if os.path.exists(attachments_dir):
                for file in os.listdir(attachments_dir):
                    file_path = os.path.join(attachments_dir, file)
                    if os.path.isfile(file_path):
                        stats['files'] += 1
                        stats['total_size'] += os.path.getsize(file_path)
        
    except Exception as e:
        logger.error(f"통계 수집 중 오류: {e}")
    
    return stats

def run_scrapers_batch(scraper_batch, max_pages=1):
    """스크래퍼 배치 실행 (최대 3개 동시)"""
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_to_scraper = {
            executor.submit(run_single_scraper, config, max_pages): config['key']
            for config in scraper_batch
        }
        
        results = []
        
        for future in concurrent.futures.as_completed(future_to_scraper):
            scraper_key = future_to_scraper[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"스크래퍼 {scraper_key} 실행 중 예외 발생: {e}")
                results.append({
                    'scraper': scraper_key,
                    'status': 'exception',
                    'error': str(e),
                    'duration': 0,
                    'announcements': 0,
                    'files': 0,
                    'total_size': 0
                })
        
        return results

def format_size(size_bytes):
    """바이트를 읽기 쉬운 형태로 변환"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def test_main_pattern():
    """main.py 패턴 테스트 (6개 스크래퍼)"""
    print("🚀 Enhanced 스크래퍼 통합 실행기 테스트 (6개)")
    print("="*60)
    
    start_time = datetime.now()
    
    # 스크래퍼 설정 준비
    scraper_configs = []
    for key, info in TEST_SCRAPERS.items():
        scraper_configs.append({
            'key': key,
            'info': info
        })
    
    print(f"📋 총 {len(scraper_configs)}개 Enhanced 스크래퍼 실행 예정")
    print("   3개씩 동시 실행하여 전체 스크래핑 수행")
    print()
    
    # 3개씩 배치로 나누기
    batch_size = 3
    all_results = []
    
    for i in range(0, len(scraper_configs), batch_size):
        batch = scraper_configs[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        
        print(f"🔄 배치 {batch_num} 실행 중 ({len(batch)}개 스크래퍼):")
        for config in batch:
            print(f"   • {config['info']['name']}")
        print()
        
        # 배치 실행
        batch_results = run_scrapers_batch(batch, max_pages=1)
        all_results.extend(batch_results)
        
        print(f"✨ 배치 {batch_num} 완료\n")
    
    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()
    
    # 결과 요약
    print("="*80)
    print("🎯 Enhanced 스크래퍼 테스트 결과 요약")
    print("="*80)
    
    successful = [r for r in all_results if r['status'] == 'success']
    failed = [r for r in all_results if r['status'] in ['error', 'exception']]
    
    total_announcements = sum(r['announcements'] for r in successful)
    total_files = sum(r['files'] for r in successful)
    total_size = sum(r['total_size'] for r in successful)
    
    print(f"📊 전체 통계:")
    print(f"  • 총 스크래퍼: {len(all_results)}개")
    print(f"  • 성공: {len(successful)}개")
    print(f"  • 실패: {len(failed)}개")
    print(f"  • 전체 실행 시간: {total_duration:.1f}초")
    print(f"  • 총 수집 공고: {total_announcements}개")
    print(f"  • 총 다운로드 파일: {total_files}개")
    print(f"  • 총 파일 크기: {format_size(total_size)}")
    
    if successful:
        print(f"\n✅ 성공한 스크래퍼들:")
        for result in successful:
            print(f"  • {result['name']}: {result['announcements']}개 공고, {result['files']}개 파일, {result['duration']:.1f}초")
    
    if failed:
        print(f"\n❌ 실패한 스크래퍼들:")
        for result in failed:
            print(f"  • {result['name']}: {result.get('error', 'Unknown error')}")
    
    print("\n" + "="*80)
    print(f"⏰ 전체 실행 시간: {total_duration:.1f}초")
    print(f"📅 실행 완료 시각: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    test_main_pattern()
    print("\n🎉 테스트 완료!")