#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup

with open('ccei_detail_fresh.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')

# Find the download area
download_area = soup.find('div', class_='vw_download')
if download_area:
    print("Found download area!")
    print("\nParent structure:")
    
    # Get parent and siblings
    parent = download_area.parent
    if parent:
        print(f"Parent tag: {parent.name}")
        print(f"Parent classes: {parent.get('class')}")
        
        # Show all children of parent
        print("\nSiblings and content:")
        for child in parent.children:
            if hasattr(child, 'name') and child.name:
                classes = child.get('class', [])
                print(f"\n- {child.name} class='{classes}'")
                print(f"  Text: {child.get_text(strip=True)[:200]}")
                
                # If it's the download div, show its onclick
                if child == download_area:
                    onclick = child.get('onclick')
                    if onclick:
                        print(f"  Onclick: {onclick}")
                    
                    # Check for child elements
                    links = child.find_all('a')
                    for link in links:
                        print(f"  Link: {link.get_text(strip=True)}")
                        print(f"    href: {link.get('href')}")
                        print(f"    onclick: {link.get('onclick')}")

# Also look for the actual file data being passed to downloadAll
print("\n\nSearching for downloadAll calls...")
import re

# Find all script tags
scripts = soup.find_all('script')
for script in scripts:
    if script.string and 'downloadAll' in script.string:
        # Extract the call
        matches = re.findall(r'downloadAll\([^)]+\)', script.string)
        for match in matches:
            print(f"Found call: {match}")
        
        # Also look for FILE variable assignments
        file_matches = re.findall(r'FILE["\']?\s*[:=]\s*["\']([^"\']+)["\']', script.string)
        for fm in file_matches:
            print(f"FILE data: {fm}")