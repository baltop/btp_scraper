#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from ccei_scraper import CCEIScraper
import os

# Create scraper instance
scraper = CCEIScraper()

# Create test output directory
os.makedirs('ccei_test_output', exist_ok=True)

# Test the full scraping process for one announcement
print("Testing CCEI scraper full process...")

# Get list data
announcements = scraper.parse_list_page(1)

if announcements:
    # Process first announcement with files
    for announcement in announcements:
        if announcement.get('has_file'):
            print(f"\nProcessing: {announcement['title']}")
            print(f"URL: {announcement['url']}")
            print(f"Has files: {announcement['has_file']}")
            
            # Get detail page
            print("\nFetching detail page...")
            response = scraper.session.get(announcement['url'])
            
            if response.status_code == 200:
                # Parse detail page
                detail_data = scraper.parse_detail_page(response.text)
                
                print(f"\nContent length: {len(detail_data['content'])} chars")
                print(f"Attachments found: {len(detail_data['attachments'])}")
                
                if detail_data['attachments']:
                    print("\nAttachments:")
                    for i, att in enumerate(detail_data['attachments']):
                        print(f"{i+1}. {att['name']}")
                        print(f"   URL: {att['url']}")
                else:
                    print("\nNo attachments found in detail page!")
                    
                    # Try direct download using FILE data from list
                    seq = announcement.get('seq')
                    if seq:
                        print(f"\nTrying to get files using SEQ: {seq}")
                        
                        # Get the list data again to access FILE field
                        list_data = scraper.get_list_data(1)
                        if list_data and 'result' in list_data:
                            items = list_data['result']['list']
                            for item in items:
                                if str(item.get('SEQ')) == str(seq):
                                    file_uuids = item.get('FILE', '').split(',')
                                    if file_uuids and file_uuids[0]:
                                        print(f"Found {len(file_uuids)} file UUIDs")
                                        
                                        # Test downloading first file
                                        uuid = file_uuids[0]
                                        url = f"{scraper.base_url}/chungbuk/json/common/fileDown.download?uuid={uuid}"
                                        print(f"\nTesting download: {url}")
                                        
                                        response = scraper.session.get(url)
                                        if response.status_code == 200:
                                            print("Download successful!")
                                            print(f"Size: {len(response.content)} bytes")
                                    break
            else:
                print(f"Failed to fetch detail page: {response.status_code}")
            
            # Stop after first announcement with files
            break
else:
    print("No announcements found!")

print("\nTest completed.")