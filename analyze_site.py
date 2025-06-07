import requests
from bs4 import BeautifulSoup
import json

url = "https://www.btp.or.kr/kor/CMS/Board/Board.do?mCode=MN013"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

response = requests.get(url, headers=headers)
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
    
print("\n=== BOARD LIST ITEMS ===")
board_items = soup.select('tr[onclick], tr[style*="cursor"]')
print(f"Found {len(board_items)} clickable rows")

if board_items:
    first_item = board_items[0]
    print(f"\nFirst item onclick: {first_item.get('onclick')}")
    print(f"First item HTML: {str(first_item)[:500]}...")

print("\n=== PAGINATION ===")
pagination = soup.select('.paging, .pagination, [class*="page"]')
for p in pagination:
    print(f"Pagination element: {p.get('class')}")
    
print("\n=== LINKS ===")
links = soup.select('a[href*="Board.do"], a[onclick*="goPage"]')
print(f"Found {len(links)} board-related links")

print("\n=== FORM ELEMENTS ===")
forms = soup.find_all('form')
for form in forms:
    print(f"Form action: {form.get('action')}")
    print(f"Form method: {form.get('method')}")
    inputs = form.find_all('input', type='hidden')
    for inp in inputs:
        print(f"  Hidden input: {inp.get('name')} = {inp.get('value')}")