#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from ccei_scraper import CCEIScraper
import requests
import json

# Create scraper instance
scraper = CCEIScraper()

# Test various API endpoints for file information
seq = '35464'

print("Testing potential file API endpoints...")

# Possible endpoints
endpoints = [
    f"/chungbuk/json/common/fileList.json?seq={seq}",
    f"/chungbuk/custom/fileList.json?no={seq}",
    f"/chungbuk/json/notice/fileList.do?seq={seq}",
    f"/chungbuk/json/common/getFileList.json?seq={seq}",
]

for endpoint in endpoints:
    url = scraper.base_url + endpoint
    print(f"\nTrying: {url}")
    
    try:
        response = scraper.session.get(url)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"JSON response: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
            except:
                print(f"Response (not JSON): {response.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")

# Also try POST requests
print("\n\nTrying POST requests...")

post_endpoints = [
    "/chungbuk/json/common/fileList.json",
    "/chungbuk/custom/fileList.json",
]

for endpoint in post_endpoints:
    url = scraper.base_url + endpoint
    print(f"\nPOST to: {url}")
    
    data = {'seq': seq, 'no': seq}
    
    try:
        response = scraper.session.post(url, data=data)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"JSON response: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
            except:
                print(f"Response (not JSON): {response.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")