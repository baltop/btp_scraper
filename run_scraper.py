#!/usr/bin/env python3
"""
부산테크노파크 지원사업 공고 수집 프로그램

사용법:
    python run_scraper.py           # 기본 4페이지 수집
    python run_scraper.py --pages 2 # 2페이지만 수집
"""

import argparse
import sys
import os
from btp_scraper import BTPScraper

def main():
    parser = argparse.ArgumentParser(
        description='부산테크노파크 지원사업 공고 수집 프로그램',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  python run_scraper.py                  # 기본 4페이지 수집
  python run_scraper.py --pages 2        # 2페이지만 수집
  python run_scraper.py --pages 10       # 10페이지 수집
        """
    )
    
    parser.add_argument(
        '--pages', 
        type=int, 
        default=4,
        help='수집할 페이지 수 (기본값: 4)'
    )
    
    args = parser.parse_args()
    
    if args.pages < 1:
        print("Error: 페이지 수는 1 이상이어야 합니다.")
        sys.exit(1)
        
    print(f"부산테크노파크 지원사업 공고 수집을 시작합니다.")
    print(f"수집할 페이지 수: {args.pages}")
    print("-" * 50)
    
    try:
        scraper = BTPScraper()
        scraper.scrape_pages(max_pages=args.pages)
        
        print("\n수집이 완료되었습니다.")
        print(f"결과는 'output' 폴더에 저장되었습니다.")
        
    except KeyboardInterrupt:
        print("\n\n사용자에 의해 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"\n오류가 발생했습니다: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()