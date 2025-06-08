#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sitelist.csv 파일에서 사이트 목록을 읽어 자동으로 스크래핑하는 스크립트

사용법:
    python scrape_from_csv.py                  # 모든 사이트 스크래핑
    python scrape_from_csv.py --pages 2       # 각 사이트 2페이지씩
    python scrape_from_csv.py --site gsif     # 특정 사이트만
"""

import argparse
import csv
import os
import sys

def read_sitelist(filename='sitelist.csv'):
    """CSV 파일에서 사이트 목록 읽기"""
    sites = {}
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                sites[row['site_code']] = {
                    'name': row['site_name'],
                    'url': row['start_url']
                }
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return {}
    return sites

def main():
    parser = argparse.ArgumentParser(
        description='CSV 파일 기반 자동 스크래핑',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--site',
        help='특정 사이트 코드만 처리'
    )
    
    parser.add_argument(
        '--pages',
        type=int,
        default=4,
        help='수집할 페이지 수 (기본값: 4)'
    )
    
    parser.add_argument(
        '--csv',
        default='sitelist.csv',
        help='사이트 목록 CSV 파일 (기본값: sitelist.csv)'
    )
    
    args = parser.parse_args()
    
    # CSV 파일 읽기
    sites = read_sitelist(args.csv)
    if not sites:
        print("No sites found in CSV file")
        sys.exit(1)
    
    # 처리할 사이트 결정
    if args.site:
        if args.site not in sites:
            print(f"Site '{args.site}' not found in CSV")
            print(f"Available sites: {', '.join(sites.keys())}")
            sys.exit(1)
        sites_to_process = {args.site: sites[args.site]}
    else:
        sites_to_process = sites
    
    # 구현된 사이트 코드 목록
    implemented_sites = ['btp', 'itp', 'ccei', 'kidp', 'gsif', 'djbea', 'mire', 'dcb']
    
    print(f"Found {len(sites_to_process)} sites to process")
    print("="*60)
    
    # 각 사이트 처리
    for site_code, site_info in sites_to_process.items():
        print(f"\nSite: {site_code} - {site_info['name']}")
        print(f"URL: {site_info['url']}")
        
        if site_code in implemented_sites:
            # tp_scraper.py 호출
            cmd = f"python tp_scraper.py --site {site_code} --pages {args.pages}"
            print(f"Running: {cmd}")
            result = os.system(cmd)
            
            if result != 0:
                print(f"Error processing {site_code}")
        else:
            print(f"Scraper not implemented for {site_code}")
            print("To implement, create a scraper class following the BaseScraper pattern")
    
    print("\n" + "="*60)
    print("All processing completed")

if __name__ == "__main__":
    main()