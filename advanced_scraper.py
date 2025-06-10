#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
고도화된 지원사업 공고 수집 프로그램
설정 기반 스크래핑 엔진을 사용한 확장 가능한 스크래퍼

주요 특징:
- 설정 파일 기반 사이트 관리 (sites_config.yaml)
- 플러그인 방식의 스크래퍼 아키텍처
- 향상된 오류 처리 및 로깅
- 100+ 사이트 확장을 위한 최적화된 구조
"""

import argparse
import sys
import os
import logging
from pathlib import Path
from typing import List

from scraping_engine import ScrapingEngine, create_engine
from site_registry import get_registry

def setup_logging(verbose: bool = False):
    """로깅 설정"""
    level = logging.DEBUG if verbose else logging.INFO
    
    # 로그 포맷
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    
    # 파일 핸들러
    file_handler = logging.FileHandler('scraping.log', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

def validate_sites(engine: ScrapingEngine, sites: List[str]) -> List[str]:
    """사이트 코드 유효성 검증"""
    validation = engine.validate_sites(sites)
    
    if validation['invalid']:
        print(f"❌ 알 수 없는 사이트: {', '.join(validation['invalid'])}")
        print(f"✅ 사용 가능한 사이트: {', '.join(engine.registry.get_site_codes())}")
        return validation['valid']
    
    return sites

def print_available_sites(engine: ScrapingEngine):
    """사용 가능한 사이트 목록 출력"""
    registry = engine.registry
    
    print("\n📋 사용 가능한 사이트 목록:")
    print("=" * 60)
    
    # 타입별로 그룹화
    types = {}
    for site_code in registry.get_site_codes():
        config = registry.get_site_config(site_code)
        site_type = config.type
        if site_type not in types:
            types[site_type] = []
        types[site_type].append((site_code, config.name))
    
    for site_type, sites in types.items():
        type_desc = registry.scraper_types.get(site_type, {}).get('description', site_type)
        print(f"\n🔧 {site_type.upper()} ({type_desc}):")
        for site_code, site_name in sorted(sites):
            print(f"  • {site_code:12} - {site_name}")
    
    print("\n" + "=" * 60)

def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(
        description='고도화된 지원사업 공고 수집 프로그램',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예제:
  %(prog)s btp                           # 부산테크노파크 4페이지 수집
  %(prog)s btp itp ccei                  # 여러 사이트 동시 수집  
  %(prog)s --all                         # 모든 사이트 수집
  %(prog)s --type standard_table         # 특정 타입 사이트들만 수집
  %(prog)s btp --pages 2                 # 2페이지만 수집
  %(prog)s --list                        # 사용 가능한 사이트 목록 출력
  %(prog)s --validate btp invalid_site   # 사이트 코드 유효성 검증
        """
    )
    
    # 위치 인수 - 사이트 코드들
    parser.add_argument(
        'sites',
        nargs='*',
        help='수집할 사이트 코드 (예: btp itp ccei)'
    )
    
    # 선택 인수들
    parser.add_argument(
        '--all',
        action='store_true',
        help='모든 등록된 사이트 수집'
    )
    
    parser.add_argument(
        '--type',
        type=str,
        help='특정 타입의 사이트들만 수집 (standard_table, ajax_api, javascript, session_based, playwright)'
    )
    
    parser.add_argument(
        '--pages',
        type=int,
        default=4,
        help='수집할 페이지 수 (기본값: 4)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='output',
        help='출력 디렉토리 (기본값: output)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='sites_config.yaml',
        help='설정 파일 경로 (기본값: sites_config.yaml)'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='사용 가능한 사이트 목록 출력'
    )
    
    parser.add_argument(
        '--validate',
        action='store_true',
        help='사이트 코드 유효성만 검증'
    )
    
    parser.add_argument(
        '--continue-on-error',
        action='store_true',
        default=True,
        help='오류 발생 시 계속 진행 (기본값: True)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='상세 로그 출력'
    )
    
    args = parser.parse_args()
    
    # 로깅 설정
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    try:
        # 스크래핑 엔진 생성
        engine = create_engine(args.config)
        engine.set_continue_on_error(args.continue_on_error)
        
        logger.info(f"스크래핑 엔진 초기화 완료: {len(engine.registry.get_site_codes())}개 사이트 등록")
        
        # 사이트 목록 출력
        if args.list:
            print_available_sites(engine)
            return 0
        
        # 수집할 사이트 결정
        sites_to_scrape = []
        
        if args.all:
            sites_to_scrape = engine.registry.get_site_codes()
            logger.info("모든 사이트 수집 모드")
        elif args.type:
            sites_to_scrape = engine.registry.get_sites_by_type(args.type)
            if not sites_to_scrape:
                print(f"❌ 타입 '{args.type}'에 해당하는 사이트가 없습니다")
                return 1
            logger.info(f"타입별 수집 모드: {args.type}")
        elif args.sites:
            sites_to_scrape = args.sites
            logger.info(f"지정된 사이트 수집: {', '.join(sites_to_scrape)}")
        else:
            print("❌ 수집할 사이트를 지정해주세요")
            print("사용법: %(prog)s <사이트코드1> [사이트코드2] ... 또는 --all 또는 --type <타입>" % {'prog': sys.argv[0]})
            print("자세한 도움말: %(prog)s --help" % {'prog': sys.argv[0]})
            return 1
        
        # 사이트 유효성 검증
        if args.validate:
            valid_sites = validate_sites(engine, sites_to_scrape)
            print(f"✅ 유효한 사이트: {', '.join(valid_sites)}")
            return 0
        
        sites_to_scrape = validate_sites(engine, sites_to_scrape)
        if not sites_to_scrape:
            print("❌ 유효한 사이트가 없습니다")
            return 1
        
        # 페이지 수 검증
        if args.pages < 1:
            print("❌ 페이지 수는 1 이상이어야 합니다")
            return 1
        
        # 스크래핑 실행
        print(f"\n🚀 스크래핑 시작")
        print(f"📍 대상 사이트: {', '.join(sites_to_scrape)}")
        print(f"📄 페이지 수: {args.pages}")
        print(f"📁 출력 디렉토리: {args.output}")
        print(f"⚙️  설정 파일: {args.config}")
        print()
        
        # 실제 스크래핑 실행
        if len(sites_to_scrape) == 1:
            # 단일 사이트
            result = engine.scrape_site(
                sites_to_scrape[0], 
                max_pages=args.pages, 
                output_dir=os.path.join(args.output, sites_to_scrape[0])
            )
        else:
            # 다중 사이트
            results = engine.scrape_sites(
                sites_to_scrape,
                max_pages=args.pages,
                output_base=args.output
            )
        
        # 결과 요약 출력
        engine.print_summary()
        
        # 성공한 사이트가 있는지 확인
        results = engine.get_results()
        successful = sum(1 for r in results.values() if r['status'] == 'completed')
        
        if successful > 0:
            print(f"\n✅ 스크래핑 완료: {successful}/{len(sites_to_scrape)} 사이트 성공")
            return 0
        else:
            print(f"\n❌ 모든 사이트 스크래핑 실패")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단되었습니다")
        return 130
    except FileNotFoundError as e:
        print(f"❌ 설정 파일을 찾을 수 없습니다: {e}")
        return 2
    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())