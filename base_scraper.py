
# do not use this file. use enhanced scraper style.

# import requests
# from bs4 import BeautifulSoup
# import os
# import time
# import html2text
# from urllib.parse import urljoin, urlparse, parse_qs
# import re
# from abc import ABC, abstractmethod

# class BaseScraper(ABC):
#     """테크노파크 스크래퍼의 기본 클래스"""
    
#     def __init__(self):
#         self.headers = {
#             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
#         }
#         self.session = requests.Session()
#         self.session.headers.update(self.headers)
#         self.h = html2text.HTML2Text()
#         self.h.ignore_links = False
#         self.h.ignore_images = False
#         self.verify_ssl = True  # SSL 검증 여부
        
#     @abstractmethod
#     def get_list_url(self, page_num):
#         """페이지 번호에 따른 목록 URL 반환"""
#         pass
        
#     @abstractmethod
#     def parse_list_page(self, html_content):
#         """목록 페이지 파싱"""
#         pass
        
#     @abstractmethod
#     def parse_detail_page(self, html_content):
#         """상세 페이지 파싱"""
#         pass
        
#     def get_page(self, url):
#         """페이지 가져오기"""
#         try:
#             response = self.session.get(url, verify=self.verify_ssl)
#             # 인코딩 자동 감지 또는 기본값 설정
#             if response.encoding is None or response.encoding == 'ISO-8859-1':
#                 # 한국 사이트의 경우 대부분 UTF-8 또는 EUC-KR
#                 try:
#                     response.encoding = response.apparent_encoding
#                 except:
#                     response.encoding = 'utf-8'
#             return response
#         except Exception as e:
#             print(f"Error fetching page {url}: {e}")
#             import traceback
#             traceback.print_exc()
#             return None
            
#     def download_file(self, url, save_path):
#         """파일 다운로드"""
#         try:
#             print(f"Downloading from: {url}")
            
#             # 세션에 Referer 헤더 추가
#             download_headers = self.headers.copy()
#             download_headers['Referer'] = self.base_url
            
#             response = self.session.get(url, headers=download_headers, stream=True, timeout=30, verify=self.verify_ssl)
#             response.raise_for_status()
            
#             # Content-Disposition 헤더에서 실제 파일명 추출 시도
#             content_disposition = response.headers.get('Content-Disposition', '')
#             if content_disposition:
#                 import re
#                 filename_match = re.search(r'filename[^;=\n]*=(([\'"]).*?\2|[^;\n]*)', content_disposition)
#                 if filename_match:
#                     filename = filename_match.group(1).strip('"\'')
#                     # 인코딩 문제 해결
#                     try:
#                         filename = filename.encode('latin-1').decode('utf-8')
#                     except:
#                         pass
                    
#                     # 파일명이 유효하면 save_path 업데이트
#                     if filename and not filename.isspace():
#                         save_dir = os.path.dirname(save_path)
#                         # + 기호를 공백으로 변경
#                         filename = filename.replace('+', ' ')
#                         save_path = os.path.join(save_dir, self.sanitize_filename(filename))
            
#             # 파일 저장
#             with open(save_path, 'wb') as f:
#                 for chunk in response.iter_content(chunk_size=8192):
#                     if chunk:
#                         f.write(chunk)
                        
#             file_size = os.path.getsize(save_path)
#             print(f"Downloaded: {save_path} ({file_size:,} bytes)")
#             return True
            
#         except requests.exceptions.RequestException as e:
#             print(f"Network error downloading {url}: {e}")
#             return False
#         except Exception as e:
#             print(f"Error downloading file {url}: {e}")
#             return False
            
#     def sanitize_filename(self, filename):
#         """파일명 정리"""
#         # URL 디코딩 (퍼센트 인코딩 제거)
#         from urllib.parse import unquote
#         filename = unquote(filename)
        
#         # 특수문자 제거 (파일 시스템에서 허용하지 않는 문자)
#         filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
#         # 연속된 공백을 하나로
#         filename = re.sub(r'\s+', ' ', filename)
        
#         # 너무 긴 파일명 제한
#         if len(filename) > 200:
#             # 확장자 보존
#             name_parts = filename.rsplit('.', 1)
#             if len(name_parts) == 2:
#                 name, ext = name_parts
#                 filename = name[:200-len(ext)-1] + '.' + ext
#             else:
#                 filename = filename[:200]
                
#         return filename
        
#     def process_announcement(self, announcement, index, output_base='output'):
#         """개별 공고 처리"""
#         print(f"\nProcessing announcement {index}: {announcement['title']}")
#         print(f"URL: {announcement.get('url', 'NO URL')}")
        
#         # 폴더 생성
#         folder_title = self.sanitize_filename(announcement['title'])[:50]
#         folder_name = f"{index:03d}_{folder_title}"
#         folder_path = os.path.join(output_base, folder_name)
#         os.makedirs(folder_path, exist_ok=True)
        
#         # 상세 페이지 가져오기
#         response = self.get_page(announcement['url'])
#         if not response:
#             print(f"Failed to get detail page for: {announcement['title']}")
#             return
            
#         # 상세 내용 파싱
#         detail = self.parse_detail_page(response.text)
#         print(f"Detail parsed - content length: {len(detail['content'])}, attachments: {len(detail['attachments'])}")
        
#         # 메타 정보 추가
#         meta_info = f"""# {announcement['title']}

# **작성자**: {announcement.get('writer', 'N/A')}  
# **작성일**: {announcement.get('date', 'N/A')}  
# **접수기간**: {announcement.get('period', 'N/A')}  
# **상태**: {announcement.get('status', 'N/A')}  
# **원본 URL**: {announcement['url']}

# ---

# """
        
#         # 본문 저장
#         content_path = os.path.join(folder_path, 'content.md')
#         with open(content_path, 'w', encoding='utf-8') as f:
#             f.write(meta_info + detail['content'])
            
#         print(f"Saved content to: {content_path}")
        
#         # 첨부파일 다운로드
#         if detail['attachments']:
#             print(f"Found {len(detail['attachments'])} attachment(s)")
#             attachments_folder = os.path.join(folder_path, 'attachments')
#             os.makedirs(attachments_folder, exist_ok=True)
            
#             for i, attachment in enumerate(detail['attachments']):
#                 print(f"  Attachment {i+1}: {attachment['name']}")
#                 # 원본 파일명 사용
#                 file_name = attachment['name']
                
#                 # 파일명 정리
#                 file_name = self.sanitize_filename(file_name)
                
#                 # + 기호를 공백으로 변경
#                 file_name = file_name.replace('+', ' ')
                
#                 if not file_name or file_name.isspace():
#                     file_name = f"attachment_{i+1}"
                    
#                 file_path = os.path.join(attachments_folder, file_name)
#                 # GIB 특화 처리: attachment 정보 전체 전달
#                 if hasattr(self, '_download_gib_file') and attachment['url'] == 'gib_download':
#                     self.download_file(attachment['url'], file_path, attachment_info=attachment)
#                 else:
#                     self.download_file(attachment['url'], file_path)
#         else:
#             print("No attachments found")
                
#         # 잠시 대기 (서버 부하 방지)
#         time.sleep(1)
        
#     def scrape_pages(self, max_pages=4, output_base='output'):
#         """여러 페이지 스크래핑"""
#         announcement_count = 0
        
#         for page_num in range(1, max_pages + 1):
#             print(f"\n{'='*50}")
#             print(f"Processing page {page_num}")
#             print(f"{'='*50}")
            
#             # 페이지 URL 구성
#             page_url = self.get_list_url(page_num)
                
#             # 페이지 가져오기
#             response = self.get_page(page_url)
#             if not response:
#                 print(f"Failed to fetch page {page_num}")
#                 break
                
#             # 목록 파싱
#             announcements = self.parse_list_page(response.text)
            
#             if not announcements:
#                 print(f"No announcements found on page {page_num}")
#                 break
                
#             print(f"Found {len(announcements)} announcements on page {page_num}")
            
#             # 각 공고 처리
#             for ann in announcements:
#                 announcement_count += 1
#                 self.process_announcement(ann, announcement_count, output_base)
                
#             # 다음 페이지가 있는지 확인
#             if page_num < max_pages:
#                 time.sleep(2)  # 페이지 간 대기
                
#         print(f"\n{'='*50}")
#         print(f"Scraping completed. Total announcements processed: {announcement_count}")
#         print(f"{'='*50}")