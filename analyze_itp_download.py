import requests
from bs4 import BeautifulSoup
import re

# 상세 페이지 접속
url = "https://itp.or.kr/intro.asp?tmid=13&seq=9642"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

response = requests.get(url, headers=headers, verify=False)
response.encoding = 'utf-8'

soup = BeautifulSoup(response.text, 'html.parser')

print("=== JavaScript Functions ===")
scripts = soup.find_all('script')
for script in scripts:
    if script.string and 'fncFileDownload' in script.string:
        print("Found fncFileDownload function:")
        print(script.string)

print("\n=== File Links ===")
# 파일 링크 찾기
file_links = soup.find_all('a', href=lambda x: x and 'fncFileDownload' in x)
for link in file_links:
    print(f"\nLink text: {link.get_text(strip=True)}")
    print(f"Link href: {link.get('href')}")
    
    # JavaScript 함수에서 파라미터 추출
    href = link.get('href', '')
    match = re.search(r"fncFileDownload\('([^']+)',\s*'([^']+)'\)", href)
    if match:
        param1 = match.group(1)
        param2 = match.group(2)
        print(f"Parameters: {param1}, {param2}")
        
        # 가능한 다운로드 URL 구성
        possible_urls = [
            f"https://itp.or.kr/UploadData/{param1}/{param2}",
            f"https://itp.or.kr/common/fileDownload.asp?fileType={param1}&fileName={param2}",
            f"https://itp.or.kr/download.asp?type={param1}&file={param2}",
            f"https://itp.or.kr/file_down.asp?tb={param1}&fn={param2}"
        ]
        
        print("Trying possible download URLs:")
        for test_url in possible_urls:
            print(f"  - {test_url}")
            try:
                test_response = requests.head(test_url, headers=headers, verify=False, allow_redirects=True)
                print(f"    Status: {test_response.status_code}")
                if test_response.status_code == 200:
                    print(f"    SUCCESS! Content-Type: {test_response.headers.get('Content-Type')}")
                    print(f"    Size: {test_response.headers.get('Content-Length', 'Unknown')}")
                    break
            except Exception as e:
                print(f"    Error: {e}")

# Form 분석
print("\n=== Form Analysis ===")
forms = soup.find_all('form')
for form in forms:
    if 'download' in str(form).lower():
        print(f"Form with download: {form.get('name')}")
        print(f"Action: {form.get('action')}")
        print(f"Method: {form.get('method')}")