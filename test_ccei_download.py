#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from ccei_scraper import CCEIScraper
import requests

# Create scraper instance
scraper = CCEIScraper()

# Get list data to find file UUIDs
print("Getting list data...")
data = scraper.get_list_data(1)

if data and 'result' in data:
    items = data['result']['list']
    
    # Find first item with files
    for item in items:
        if item.get('FILE'):
            print(f"\nItem: {item.get('TITLE')[:50]}...")
            print(f"SEQ: {item.get('SEQ')}")
            
            # Parse file UUIDs
            file_uuids = item.get('FILE').split(',')
            print(f"\nFile UUIDs ({len(file_uuids)}):")
            
            for i, uuid in enumerate(file_uuids[:3]):
                print(f"{i+1}. {uuid}")
            
            # Test the standard download URL
            test_uuid = file_uuids[0]
            url = f"{scraper.base_url}/chungbuk/json/common/fileDown.download?uuid={test_uuid}"
            
            print(f"\nTesting download URL: {url}")
            
            # Try GET request
            response = scraper.session.get(url)
            print(f"Status: {response.status_code}")
            print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
            print(f"Content-Length: {response.headers.get('Content-Length', 'N/A')}")
            
            # If successful, check for filename
            if response.status_code == 200:
                content_disp = response.headers.get('Content-Disposition', '')
                print(f"Content-Disposition: {content_disp}")
                
                # Extract filename from Content-Disposition
                import re
                filename_match = re.search(r'filename="([^"]+)"', content_disp)
                if filename_match:
                    raw_filename = filename_match.group(1)
                    # Try to decode the filename
                    try:
                        # First try UTF-8
                        filename = raw_filename.encode('iso-8859-1').decode('utf-8')
                    except:
                        # If that fails, use the raw filename
                        filename = raw_filename
                    print(f"Extracted filename: {filename}")
                
                # Save a sample file
                if len(response.content) > 0:
                    print(f"\nFile size: {len(response.content)} bytes")
                    with open('test_download.hwp', 'wb') as f:
                        f.write(response.content)
                    print("Saved to test_download.hwp")
            else:
                print("\nResponse preview:")
                print(response.text[:500])
            
            break