import requests
from bs4 import BeautifulSoup

# 인천테크노파크 사업공고 페이지
url = "https://itp.or.kr/intro.asp?tmid=13"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

response = requests.get(url, headers=headers, verify=False)  # SSL 인증서 검증 비활성화
response.encoding = 'utf-8'

soup = BeautifulSoup(response.text, 'html.parser')

print("=== PAGE TITLE ===")
print(soup.title.string if soup.title else "No title found")

print("\n=== TABLE STRUCTURE ===")
tables = soup.find_all('table')
for i, table in enumerate(tables):
    print(f"\nTable {i+1}:")
    print(f"Class: {table.get('class')}")
    print(f"ID: {table.get('id')}")
    print(f"Summary: {table.get('summary')}")
    
print("\n=== BOARD LIST ITEMS ===")
# 다양한 패턴으로 게시판 항목 찾기
board_items = soup.select('tr[onclick]') or soup.select('tr[style*="cursor"]') or soup.select('td.subject a')
print(f"Found {len(board_items)} board items")

if board_items:
    first_item = board_items[0]
    print(f"\nFirst item: {first_item}")

print("\n=== LINKS ===")
# 게시글 링크 찾기
links = soup.select('a[href*="mode=view"]') or soup.select('a[href*="boardView"]') or soup.select('td.subject a')
print(f"Found {len(links)} board links")
if links:
    print(f"First link: {links[0].get('href')}")
    print(f"First link text: {links[0].get_text(strip=True)}")

print("\n=== PAGINATION ===")
# 페이지네이션 찾기
pagination = soup.select('.paging') or soup.select('.pagination') or soup.select('[class*="page"]')
for p in pagination:
    print(f"Pagination element: {p.get('class')}")

print("\n=== SPECIFIC SELECTORS ===")
# 인천테크노파크 특유의 선택자 찾기
bbs_list = soup.select('.bbs_list') or soup.select('.board_list')
print(f"BBS list elements: {len(bbs_list)}")

# td.subject 찾기 (제목 컬럼)
subjects = soup.select('td.subject')
print(f"\nFound {len(subjects)} subject cells")
if subjects:
    print(f"First subject: {subjects[0].get_text(strip=True)[:100]}")