import requests
from bs4 import BeautifulSoup
import re

url = "https://itp.or.kr/intro.asp?tmid=13"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

response = requests.get(url, headers=headers, verify=False)
response.encoding = 'utf-8'

soup = BeautifulSoup(response.text, 'html.parser')

print("=== ANALYZING JAVASCRIPT FUNCTIONS ===")
scripts = soup.find_all('script')
for script in scripts:
    if script.string and 'fncShow' in script.string:
        print("Found fncShow function:")
        print(script.string[:500])

print("\n=== ANALYZING TABLE ROWS ===")
table = soup.find('table', class_='list')
if table:
    tbody = table.find('tbody')
    if tbody:
        rows = tbody.find_all('tr')
        print(f"Found {len(rows)} rows")
        
        if rows:
            first_row = rows[0]
            print(f"\nFirst row HTML:\n{first_row}")
            
            # 각 컬럼 분석
            tds = first_row.find_all('td')
            for i, td in enumerate(tds):
                print(f"\nColumn {i}: {td.get('class')}")
                print(f"Text: {td.get_text(strip=True)[:50]}")
                
                # 링크 찾기
                link = td.find('a')
                if link:
                    print(f"Link href: {link.get('href')}")
                    
print("\n=== FORM ANALYSIS ===")
forms = soup.find_all('form')
for form in forms:
    print(f"Form name: {form.get('name')}")
    print(f"Form action: {form.get('action')}")
    print(f"Form method: {form.get('method')}")

# 상세 페이지 URL 패턴 분석
print("\n=== TRYING DETAIL PAGE ===")
# fncShow('9642') 형태에서 9642가 게시글 번호로 보임
detail_url = "https://itp.or.kr/intro.asp?tmid=13&mode=view&no=9642"
print(f"Trying URL: {detail_url}")

detail_response = requests.get(detail_url, headers=headers, verify=False)
print(f"Response status: {detail_response.status_code}")
print(f"Response length: {len(detail_response.text)}")

# 다른 패턴도 시도
detail_url2 = "https://itp.or.kr/intro_view.asp?tmid=13&no=9642"
print(f"\nTrying URL: {detail_url2}")
detail_response2 = requests.get(detail_url2, headers=headers, verify=False)
print(f"Response status: {detail_response2.status_code}")