#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from gsif_scraper import GSIFScraper
import sys

def test_single_announcement():
    """단일 공고를 테스트"""
    scraper = GSIFScraper()
    
    # 목록 페이지 가져오기
    print("Getting list page...")
    response = scraper.get_page(scraper.list_url)
    if not response:
        print("Failed to get list page")
        return
    
    # 목록 파싱
    announcements = scraper.parse_list_page(response.text)
    if not announcements:
        print("No announcements found")
        return
    
    # HTML에서 실제 링크 확인
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')
    first_link = soup.find('a', text=lambda t: t and '창업보육센터' in t)
    if first_link:
        print(f"\nActual href in HTML: {first_link.get('href', 'No href')}")
        print(f"Onclick: {first_link.get('onclick', 'No onclick')}")
    
    # 첫 번째 공고 테스트
    print(f"\nTesting first announcement: {announcements[0]['title']}")
    print(f"URL: {announcements[0]['url']}")
    
    # 상세 페이지 가져오기
    print(f"\nTrying to fetch detail page...")
    detail_response = scraper.get_page(announcements[0]['url'])
    if not detail_response:
        print("Failed to get detail page")
        # 직접 시도해보기
        import requests
        try:
            test_response = requests.get(announcements[0]['url'], headers=scraper.headers, verify=False, timeout=30)
            print(f"Direct request status: {test_response.status_code}")
            print(f"Response length: {len(test_response.text)}")
        except Exception as e:
            print(f"Direct request error: {e}")
        return
    
    # 상세 페이지 파싱
    detail = scraper.parse_detail_page(detail_response.text)
    
    print(f"\nContent length: {len(detail['content'])} characters")
    print(f"First 200 chars of content: {detail['content'][:200]}...")
    print(f"\nAttachments found: {len(detail['attachments'])}")
    for i, att in enumerate(detail['attachments']):
        print(f"  {i+1}. {att['name']}")
        print(f"     URL: {att['url']}")
    
    # 실제로 처리해보기
    print("\n" + "="*50)
    print("Processing announcement...")
    scraper.process_announcement(announcements[0], 1, 'test_output')

if __name__ == "__main__":
    test_single_announcement()