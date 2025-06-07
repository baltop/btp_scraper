#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
테크노파크 지원사업 공고 수집 프로그램
부산테크노파크(BTP)와 인천테크노파크(ITP) 지원

사용법:
    python tp_scraper.py --site btp           # 부산테크노파크 수집 (기본값)
    python tp_scraper.py --site itp           # 인천테크노파크 수집
    python tp_scraper.py --site all           # 모든 사이트 수집
    python tp_scraper.py --site btp --pages 2 # 2페이지만 수집
"""

import argparse
import sys
import os
from btp_scraper import BTPScraper
from itp_scraper import ITPScraper

def main():
    parser = argparse.ArgumentParser(
        description='테크노파크 지원사업 공고 수집 프로그램',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  python tp_scraper.py                     # 부산테크노파크 4페이지 수집 (기본값)
  python tp_scraper.py --site itp          # 인천테크노파크 4페이지 수집
  python tp_scraper.py --site all          # 모든 사이트 4페이지씩 수집
  python tp_scraper.py --site btp --pages 2  # 부산테크노파크 2페이지만 수집
        """
    )
    
    parser.add_argument(
        '--site', 
        choices=['btp', 'itp', 'all'],
        default='btp',
        help='수집할 사이트 선택 (기본값: btp)'
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
    
    args = parser.parse_args()
    
    if args.pages < 1:
        print("Error: 페이지 수는 1 이상이어야 합니다.")
        sys.exit(1)
        
    # 수집할 사이트 목록 결정
    sites_to_scrape = []
    if args.site == 'all':
        sites_to_scrape = ['btp', 'itp']
    else:
        sites_to_scrape = [args.site]
    
    # 각 사이트별로 수집
    for site in sites_to_scrape:
        if site == 'btp':
            print(f"\n{'='*60}")
            print("부산테크노파크 지원사업 공고 수집을 시작합니다.")
            print(f"수집할 페이지 수: {args.pages}")
            print(f"{'='*60}")
            
            output_dir = os.path.join(args.output, 'btp')
            os.makedirs(output_dir, exist_ok=True)
            
            try:
                scraper = BTPScraper()
                scraper.scrape_pages(max_pages=args.pages, output_base=output_dir)
                
                print(f"\n부산테크노파크 수집이 완료되었습니다.")
                print(f"결과는 '{output_dir}' 폴더에 저장되었습니다.")
                
            except KeyboardInterrupt:
                print("\n\n사용자에 의해 중단되었습니다.")
                sys.exit(0)
            except Exception as e:
                print(f"\n부산테크노파크 수집 중 오류가 발생했습니다: {e}")
                if len(sites_to_scrape) == 1:
                    sys.exit(1)
                    
        elif site == 'itp':
            print(f"\n{'='*60}")
            print("인천테크노파크 지원사업 공고 수집을 시작합니다.")
            print(f"수집할 페이지 수: {args.pages}")
            print(f"{'='*60}")
            
            output_dir = os.path.join(args.output, 'itp')
            os.makedirs(output_dir, exist_ok=True)
            
            try:
                scraper = ITPScraper()
                scraper.scrape_pages(max_pages=args.pages, output_base=output_dir)
                
                print(f"\n인천테크노파크 수집이 완료되었습니다.")
                print(f"결과는 '{output_dir}' 폴더에 저장되었습니다.")
                
            except KeyboardInterrupt:
                print("\n\n사용자에 의해 중단되었습니다.")
                sys.exit(0)
            except Exception as e:
                print(f"\n인천테크노파크 수집 중 오류가 발생했습니다: {e}")
                if len(sites_to_scrape) == 1:
                    sys.exit(1)
    
    print(f"\n{'='*60}")
    print("모든 수집이 완료되었습니다.")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()