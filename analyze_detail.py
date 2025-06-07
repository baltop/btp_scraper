import requests
from bs4 import BeautifulSoup

url = "https://www.btp.or.kr/kor/CMS/Board/Board.do?mCode=MN013"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

response = requests.get(url, headers=headers)
response.encoding = 'utf-8'

soup = BeautifulSoup(response.text, 'html.parser')

print("=== FINDING BOARD LIST ===")
board_table = soup.find('table', class_='bdListTbl')
if board_table:
    tbody = board_table.find('tbody')
    if tbody:
        rows = tbody.find_all('tr')
        print(f"Found {len(rows)} rows in table body")
        
        if rows:
            first_row = rows[0]
            print(f"\nFirst row HTML:\n{str(first_row)[:1000]}...")
            
            links = first_row.find_all('a')
            for link in links:
                print(f"\nLink found:")
                print(f"  Text: {link.get_text(strip=True)}")
                print(f"  Href: {link.get('href')}")
                print(f"  Onclick: {link.get('onclick')}")
                
print("\n=== JAVASCRIPT FUNCTIONS ===")
scripts = soup.find_all('script')
for script in scripts:
    if script.string and ('goView' in script.string or 'BoardView' in script.string):
        print("Found relevant script:")
        print(script.string[:500])