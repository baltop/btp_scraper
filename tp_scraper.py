#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
지원사업 공고 수집 프로그램
여러 기관의 지원사업 공고를 수집하여 로컬에 저장

지원 사이트:
    - btp: 부산테크노파크
    - itp: 인천테크노파크
    - ccei: 충북창조경제혁신센터
    - kidp: 한국디자인진흥원
    - gsif: 강릉과학산업진흥원
    - djbea: 대전일자리경제진흥원
    - mire: 환동해산업연구원
    - dcb: 부산디자인진흥원
    - all: 모든 사이트

사용법:
    python tp_scraper.py --site btp           # 부산테크노파크 수집 (기본값)
    python tp_scraper.py --site all           # 모든 사이트 수집
    python tp_scraper.py --site btp --pages 2 # 2페이지만 수집
"""

import argparse
import sys
import os
from btp_scraper import BTPScraper
from itp_scraper import ITPScraper
from ccei_scraper import CCEIScraper
from kidp_scraper import KIDPScraper
from gsif_scraper import GSIFScraper
from djbea_scraper import DJBEAScraper
from mire_scraper import MIREScraper
from site_scrapers import (
    DCBScraper, JBFScraper, CEPAScraper, CheongjuCCIScraper,
    GIBScraper, GBTPScraper, DGDPScraper, GEPAScraper
)

def main():
    parser = argparse.ArgumentParser(
        description='테크노파크 지원사업 공고 수집 프로그램',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  python tp_scraper.py                      # 부산테크노파크 4페이지 수집 (기본값)
  python tp_scraper.py --site itp           # 인천테크노파크 4페이지 수집
  python tp_scraper.py --site ccei          # 충북창조경제혁신센터 4페이지 수집
  python tp_scraper.py --site kidp          # 한국디자인진흥원 4페이지 수집
  python tp_scraper.py --site all           # 모든 사이트 4페이지씩 수집
  python tp_scraper.py --site btp --pages 2 # 부산테크노파크 2페이지만 수집
        """
    )
    
    parser.add_argument(
        '--site', 
        choices=['btp', 'itp', 'ccei', 'kidp', 'gsif', 'djbea', 'mire', 'dcb', 'all'],
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
        sites_to_scrape = ['btp', 'itp', 'ccei', 'kidp', 'gsif', 'djbea', 'mire', 'dcb']
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
                    
        elif site == 'ccei':
            print(f"\n{'='*60}")
            print("충북창조경제혁신센터 지원사업 공고 수집을 시작합니다.")
            print(f"수집할 페이지 수: {args.pages}")
            print(f"{'='*60}")
            
            output_dir = os.path.join(args.output, 'ccei')
            os.makedirs(output_dir, exist_ok=True)
            
            try:
                scraper = CCEIScraper()
                scraper.scrape_pages(max_pages=args.pages, output_base=output_dir)
                
                print(f"\n충북창조경제혁신센터 수집이 완료되었습니다.")
                print(f"결과는 '{output_dir}' 폴더에 저장되었습니다.")
                
            except KeyboardInterrupt:
                print("\n\n사용자에 의해 중단되었습니다.")
                sys.exit(0)
            except Exception as e:
                print(f"\n충북창조경제혁신센터 수집 중 오류가 발생했습니다: {e}")
                if len(sites_to_scrape) == 1:
                    sys.exit(1)
                    
        elif site == 'kidp':
            print(f"\n{'='*60}")
            print("한국디자인진흥원 지원사업 공고 수집을 시작합니다.")
            print(f"수집할 페이지 수: {args.pages}")
            print(f"{'='*60}")
            
            output_dir = os.path.join(args.output, 'kidp')
            os.makedirs(output_dir, exist_ok=True)
            
            try:
                scraper = KIDPScraper()
                scraper.scrape_pages(max_pages=args.pages, output_base=output_dir)
                
                print(f"\n한국디자인진흥원 수집이 완료되었습니다.")
                print(f"결과는 '{output_dir}' 폴더에 저장되었습니다.")
                
            except KeyboardInterrupt:
                print("\n\n사용자에 의해 중단되었습니다.")
                sys.exit(0)
            except Exception as e:
                print(f"\n한국디자인진흥원 수집 중 오류가 발생했습니다: {e}")
                if len(sites_to_scrape) == 1:
                    sys.exit(1)
                    
        elif site == 'gsif':
            print(f"\n{'='*60}")
            print("강릉과학산업진흥원 지원사업 공고 수집을 시작합니다.")
            print(f"수집할 페이지 수: {args.pages}")
            print(f"{'='*60}")
            
            output_dir = os.path.join(args.output, 'gsif')
            os.makedirs(output_dir, exist_ok=True)
            
            try:
                scraper = GSIFScraper()
                scraper.scrape_pages(max_pages=args.pages, output_base=output_dir)
                
                print(f"\n강릉과학산업진흥원 수집이 완료되었습니다.")
                print(f"결과는 '{output_dir}' 폴더에 저장되었습니다.")
                
            except KeyboardInterrupt:
                print("\n\n사용자에 의해 중단되었습니다.")
                sys.exit(0)
            except Exception as e:
                print(f"\n강릉과학산업진흥원 수집 중 오류가 발생했습니다: {e}")
                if len(sites_to_scrape) == 1:
                    sys.exit(1)
                    
        elif site == 'djbea':
            print(f"\n{'='*60}")
            print("대전일자리경제진흥원 지원사업 공고 수집을 시작합니다.")
            print(f"수집할 페이지 수: {args.pages}")
            print(f"{'='*60}")
            
            output_dir = os.path.join(args.output, 'djbea')
            os.makedirs(output_dir, exist_ok=True)
            
            try:
                scraper = DJBEAScraper()
                scraper.scrape_pages(max_pages=args.pages, output_base=output_dir)
                
                print(f"\n대전일자리경제진흥원 수집이 완료되었습니다.")
                print(f"결과는 '{output_dir}' 폴더에 저장되었습니다.")
                
            except KeyboardInterrupt:
                print("\n\n사용자에 의해 중단되었습니다.")
                sys.exit(0)
            except Exception as e:
                print(f"\n대전일자리경제진흥원 수집 중 오류가 발생했습니다: {e}")
                if len(sites_to_scrape) == 1:
                    sys.exit(1)
                    
        elif site == 'mire':
            print(f"\n{'='*60}")
            print("환동해산업연구원 지원사업 공고 수집을 시작합니다.")
            print(f"수집할 페이지 수: {args.pages}")
            print(f"{'='*60}")
            
            output_dir = os.path.join(args.output, 'mire')
            os.makedirs(output_dir, exist_ok=True)
            
            try:
                scraper = MIREScraper()
                scraper.scrape_pages(max_pages=args.pages, output_base=output_dir)
                
                print(f"\n환동해산업연구원 수집이 완료되었습니다.")
                print(f"결과는 '{output_dir}' 폴더에 저장되었습니다.")
                
            except KeyboardInterrupt:
                print("\n\n사용자에 의해 중단되었습니다.")
                sys.exit(0)
            except Exception as e:
                print(f"\n환동해산업연구원 수집 중 오류가 발생했습니다: {e}")
                if len(sites_to_scrape) == 1:
                    sys.exit(1)
                    
        elif site == 'dcb':
            print(f"\n{'='*60}")
            print("부산디자인진흥원 지원사업 공고 수집을 시작합니다.")
            print(f"수집할 페이지 수: {args.pages}")
            print(f"{'='*60}")
            
            output_dir = os.path.join(args.output, 'dcb')
            os.makedirs(output_dir, exist_ok=True)
            
            try:
                scraper = DCBScraper()
                scraper.scrape_pages(max_pages=args.pages, output_base=output_dir)
                
                print(f"\n부산디자인진흥원 수집이 완료되었습니다.")
                print(f"결과는 '{output_dir}' 폴더에 저장되었습니다.")
                
            except KeyboardInterrupt:
                print("\n\n사용자에 의해 중단되었습니다.")
                sys.exit(0)
            except Exception as e:
                print(f"\n부산디자인진흥원 수집 중 오류가 발생했습니다: {e}")
                if len(sites_to_scrape) == 1:
                    sys.exit(1)
    
    print(f"\n{'='*60}")
    print("모든 수집이 완료되었습니다.")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()