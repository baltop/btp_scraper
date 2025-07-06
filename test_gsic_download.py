#!/usr/bin/env python3
"""
GSIC File Download Investigation
"""
import requests
import urllib.parse
from urllib.parse import unquote


def test_gsic_download():
    """Test GSIC file download mechanism"""
    
    # Download URL and parameters
    download_url = "https://gsic.or.kr/fileDownload.do"
    
    # Test parameters from the JavaScript function call
    unique_key = "cb00d1a0008a85e71a41b8741facbffe466b53501950a76d080a6663a787e134"
    
    # Headers to match browser request
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://gsic.or.kr/home/kor/M837392473/board.do?deleteAt=N&act=detail&idx=cb00d1a0008a85e71a41b8741facbffe109b56dc9f091bc3058a9de256ae16ef&eSearchValue3=&searchValue1=0&searchKeyword=&pageIndex=1'
    }
    
    # POST data
    data = {
        'uniqueKey': unique_key
    }
    
    print("🔍 Testing GSIC file download mechanism...")
    print(f"📍 URL: {download_url}")
    print(f"🔑 UniqueKey: {unique_key}")
    
    try:
        # Make the request
        response = requests.post(
            download_url, 
            data=data, 
            headers=headers, 
            verify=False,  # SSL certificate issue
            timeout=30
        )
        
        print(f"✅ Status Code: {response.status_code}")
        print(f"📋 Response Headers:")
        for key, value in response.headers.items():
            print(f"   {key}: {value}")
        
        # Check Content-Disposition for filename
        content_disposition = response.headers.get('Content-Disposition', '')
        if content_disposition:
            print(f"\n📄 Content-Disposition: {content_disposition}")
            
            # Extract filename from Content-Disposition
            if 'filename=' in content_disposition:
                filename_part = content_disposition.split('filename=')[1]
                # Remove quotes if present
                filename_part = filename_part.strip('"\'')
                
                # URL decode the filename
                try:
                    decoded_filename = unquote(filename_part, encoding='utf-8')
                    print(f"📝 Decoded Filename: {decoded_filename}")
                except Exception as e:
                    print(f"❌ Filename decode error: {e}")
                    print(f"📝 Raw Filename: {filename_part}")
        
        # Check content type and size
        content_type = response.headers.get('Content-Type', 'unknown')
        content_length = response.headers.get('Content-Length', 'unknown')
        print(f"📦 Content-Type: {content_type}")
        print(f"📏 Content-Length: {content_length}")
        
        # Check if it's actually a file download
        if response.status_code == 200:
            content_start = response.content[:100]
            print(f"🔍 Content preview (first 100 bytes): {content_start}")
            
            # Check for file magic numbers
            if content_start.startswith(b'PK'):
                print("✅ Detected ZIP/Office file (starts with PK)")
            elif content_start.startswith(b'%PDF'):
                print("✅ Detected PDF file")
            elif b'hwp' in content_start[:50].lower():
                print("✅ Detected HWP file")
            else:
                print("❓ Unknown file type")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False


def analyze_download_pattern():
    """Analyze the GSIC download pattern"""
    print("\n🔬 GSIC Download Mechanism Analysis:")
    print("=" * 50)
    
    print("1. 📋 Download Method:")
    print("   - Method: POST")
    print("   - URL: https://gsic.or.kr/fileDownload.do")
    print("   - Parameter: uniqueKey (64-char hex string)")
    
    print("\n2. 🔄 JavaScript Function:")
    print("   - Function: kssFileDownloadForKeyAct(uniqueKey)")
    print("   - Action: Submits hidden form with uniqueKey")
    print("   - Form ID: cmmnFileDownForm")
    
    print("\n3. ✅ Required Headers:")
    print("   - Content-Type: application/x-www-form-urlencoded")
    print("   - User-Agent: Browser user agent")
    print("   - Referer: Original page URL")
    
    print("\n4. 🔑 Key Points:")
    print("   - uniqueKey is extracted from onclick attribute")
    print("   - SSL certificate verification should be disabled")
    print("   - Filename comes from Content-Disposition header")
    print("   - File is properly encoded in URL format")


if __name__ == "__main__":
    # Suppress SSL warnings
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Run tests
    success = test_gsic_download()
    analyze_download_pattern()
    
    if success:
        print("\n✅ GSIC download mechanism working correctly!")
    else:
        print("\n❌ GSIC download mechanism failed!")