#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from ccei_scraper import CCEIScraper
from bs4 import BeautifulSoup
import re

# Create scraper instance
scraper = CCEIScraper()

# Fetch a detail page
seq = '35464'
detail_url = f'{scraper.base_url}/chungbuk/custom/notice_view.do?no={seq}'

print(f"Fetching: {detail_url}")
response = scraper.session.get(detail_url)

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Save for inspection
    with open('ccei_detail_fresh.html', 'w', encoding='utf-8') as f:
        f.write(response.text)
    
    print("\nSearching for file-related elements...")
    
    # Look for any links
    all_links = soup.find_all('a', href=True)
    print(f"\nTotal links found: {len(all_links)}")
    
    # Filter for potential download links
    download_links = []
    for link in all_links:
        href = link.get('href', '')
        text = link.get_text(strip=True)
        onclick = link.get('onclick', '')
        
        if any(pattern in href.lower() for pattern in ['download', 'file', '.hwp', '.pdf', '.docx']):
            download_links.append({'text': text, 'href': href, 'onclick': onclick})
        elif any(pattern in onclick.lower() for pattern in ['download', 'file']):
            download_links.append({'text': text, 'href': href, 'onclick': onclick})
    
    print(f"\nPotential download links: {len(download_links)}")
    for dl in download_links:
        print(f"- Text: {dl['text']}")
        print(f"  Href: {dl['href']}")
        if dl['onclick']:
            print(f"  Onclick: {dl['onclick']}")
    
    # Look for file information in scripts
    print("\n\nSearching scripts for file data...")
    scripts = soup.find_all('script')
    for i, script in enumerate(scripts):
        if script.string and ('file' in script.string.lower() or 'download' in script.string.lower()):
            lines = script.string.split('\n')
            for line in lines:
                if 'file' in line.lower() or 'uuid' in line.lower():
                    print(f"Script {i}: {line.strip()}")
    
    # Look for specific areas that might contain files
    print("\n\nSearching for file areas...")
    
    # Common file area classes/ids
    file_patterns = ['file', 'attach', 'download', '첨부']
    
    for pattern in file_patterns:
        # Search by class
        elements = soup.find_all(class_=re.compile(pattern, re.I))
        if elements:
            print(f"\nElements with '{pattern}' in class:")
            for elem in elements[:3]:
                print(f"- {elem.name} class='{elem.get('class')}'")
                print(f"  Content: {elem.get_text(strip=True)[:100]}")
        
        # Search by id
        elements = soup.find_all(id=re.compile(pattern, re.I))
        if elements:
            print(f"\nElements with '{pattern}' in id:")
            for elem in elements[:3]:
                print(f"- {elem.name} id='{elem.get('id')}'")
                print(f"  Content: {elem.get_text(strip=True)[:100]}")