#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from ccei_scraper_improved import CCEIScraper
import os
import shutil

# Clean up previous test output
if os.path.exists('output/ccei'):
    shutil.rmtree('output/ccei')

# Create scraper instance
scraper = CCEIScraper()

# Test scraping just the first page
print("Testing improved CCEI scraper...")
scraper.scrape_pages(max_pages=1, output_base='output')

# Check results
output_dir = 'output/ccei'
if os.path.exists(output_dir):
    print(f"\nOutput directory created: {output_dir}")
    
    # List all subdirectories (announcements)
    subdirs = [d for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d))]
    print(f"Found {len(subdirs)} announcements")
    
    # Check first announcement with attachments
    for subdir in sorted(subdirs)[:3]:
        announcement_dir = os.path.join(output_dir, subdir)
        print(f"\n{subdir}:")
        
        # Check for content.md
        content_file = os.path.join(announcement_dir, 'content.md')
        if os.path.exists(content_file):
            print(f"  - content.md exists ({os.path.getsize(content_file)} bytes)")
        
        # Check for attachments
        attachments_dir = os.path.join(announcement_dir, 'attachments')
        if os.path.exists(attachments_dir):
            files = os.listdir(attachments_dir)
            print(f"  - {len(files)} attachments:")
            for f in files[:3]:
                size = os.path.getsize(os.path.join(attachments_dir, f))
                print(f"    * {f} ({size:,} bytes)")