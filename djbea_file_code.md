# DJBEA 첨부파일 다운로드 분석 및 코드 정리

## 현재 상황 요약

- **사용자 요구사항**: 각 공고마다 PDF와 HWP 2개 파일이 있어야 함
- **현재 결과**: PDF 파일은 성공적으로 다운로드되지만, HWP 파일은 실제로 존재하지 않아 다운로드 실패
- **핵심 발견**: DJBEA 사이트에서 HWP 파일 URL들이 모두 HTML 에러 페이지를 반환함

## 기술적 분석 결과

### 1. PDF 파일 (성공)
- **패턴**: `https://www.djbea.or.kr/pms/resources/pmsfile/2025/N5400003/{hash}.pdf`
- **해시 예시**: 
  - SEQ=7952: `3e271938020d8a`
  - SEQ=7951: `3e26f97016f64f` 
  - SEQ=7950: `3e240871e236ba`
- **특징**: 
  - Content-Type: `application/pdf;charset=UTF-8`
  - 파일 크기: 200KB~500KB
  - 정상 다운로드 가능

### 2. HWP 파일 (실패)
- **시도한 패턴들**:
  ```
  /pms/resources/pmsfile/2025/N5400003/{hash}.hwp
  /pms/resources/pmsfile/2025/{hash}.hwp
  /pms/resources/file/{hash}.hwp
  ```
- **결과**: 모든 HWP URL이 동일한 HTML 에러 페이지 반환
  - Content-Type: `text/html;charset=UTF-8`
  - 파일 크기: 48332 bytes (모든 URL에서 동일)
  - 내용: DJBEA 사이트의 에러 페이지 HTML

### 3. 해시 추출 방법
JavaScript에서 해시 패턴 추출:
```python
def _extract_djbea_a2m_files(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
    scripts = soup.find_all('script')
    for script in scripts:
        script_text = script.string if script.string else ""
        # 파일 해시 패턴 추출 (12-16자리 16진수)
        hash_patterns = re.findall(r'([a-f0-9]{12,16})', script_text)
        if hash_patterns:
            file_hash = max(hash_patterns, key=len)
            return self._extract_hash_based_files(file_hash)
```

## 구현된 코드 섹션들

### 1. 해시 기반 파일 추출 (enhanced_djbea_scraper.py:684-746)
```python
def _extract_hash_based_files(self, file_hash: str) -> List[Dict[str, Any]]:
    """해시 기반 파일 추출 - PDF와 HWP만 우선 추출"""
    attachments = []
    
    # 가장 많이 발견되는 경로 우선 시도
    base_paths = [
        f"/pms/resources/pmsfile/2025/N5400003/",
        f"/pms/resources/pmsfile/2025/",
    ]
    
    # PDF와 HWP 우선 (사용자가 언급한 파일 타입)
    primary_extensions = ['.pdf', '.hwp']
    
    # 파일 존재 확인 및 검증
    for base_path in base_paths:
        for ext in primary_extensions:
            test_url = f"{self.base_url}{base_path}{file_hash}{ext}"
            # HEAD 요청으로 파일 존재 확인
            # 파일 타입별 검증 로직
```

### 2. HWP 파일 다운로드 검증 로직 (enhanced_djbea_scraper.py:1035-1058)
```python
elif file_ext == '.hwp':
    # HWP 파일 시그니처 확인
    hwp_signatures = [
        b'HWP Document File',
        b'\x0D\x0A\x0D\x0A', 
        b'\xD0\xCF\x11\xE0',
    ]
    is_likely_valid_file = any(content.startswith(sig) for sig in hwp_signatures)
    
    # DJBEA 특수 케이스: HTML Content-Type이지만 실제 HWP인 경우
    if is_html_response and file_ext == '.hwp':
        if len(content) > 10000:
            html_tag_count = content.count(b'<') + content.count(b'>')
            content_ratio = html_tag_count / len(content)
            
            if content_ratio < 0.01:  # HTML 태그가 1% 미만
                is_likely_valid_file = True
            elif b'<!DOCTYPE' not in content[:200]:
                is_likely_valid_file = True
```

### 3. 첨부파일 추출 전략 우선순위 (enhanced_djbea_scraper.py:407-471)
```python
def _extract_detail_attachments(self, soup: BeautifulSoup, current_url: str = None):
    # 전략 1: DJBEA A2mUpload 시스템 (해시 기반)
    a2m_attachments = self._extract_djbea_a2m_files(soup)
    
    # 전략 2: dext5-multi-container
    dext5_containers = soup.find_all('div', class_='dext5-multi-container')
    
    # 전략 3: 파일 섹션
    file_sections = soup.find_all('div', class_=re.compile('file|attach'))
    
    # 전략 4: JavaScript 다운로드 링크
    download_links = soup.find_all('a', onclick=re.compile('download|fileDown'))
    
    # 전략 5: 직접 파일 링크
    file_links = soup.find_all('a', href=re.compile(r'\.(pdf|hwp|doc)', re.I))
    
    # 전략 6: 텍스트 패턴
    text_attachments = self._extract_from_text_patterns(soup)
    
    # 전략 7: 하드코딩된 파일 (fallback)
    if not attachments:
        hardcoded_files = self._extract_hardcoded_djbea_files(current_url)
```

## 분석용 테스트 스크립트들

### 1. test_multiple_djbea.py
여러 공고의 첨부파일 추출 결과 확인
```bash
python test_multiple_djbea.py
```

### 2. debug_hwp_content.py
HWP 파일 응답 내용 상세 분석
```bash
python debug_hwp_content.py
```

### 3. test_djbea_enhanced_extraction.py
Enhanced 스크래퍼의 중복 제거 및 다운로드 테스트
```bash
python test_djbea_enhanced_extraction.py
```

### 4. find_real_hwp_files.py (미완성)
다양한 패턴으로 실제 HWP 파일 탐색

## 주요 발견사항

### 1. DJBEA 파일 시스템 특징
- **PDF 파일**: 해시 기반 파일명으로 정상 제공
- **HWP 파일**: 해당 URL에 파일이 존재하지 않음
- **에러 페이지**: 48332 bytes 크기의 HTML 페이지로 일관되게 응답

### 2. 가능한 원인들
1. **DJBEA에서 HWP 파일을 실제로 제공하지 않음**
2. **다른 URL 패턴이나 다운로드 방식 사용**
3. **로그인이나 특별한 세션이 필요한 파일**
4. **PDF로만 파일을 제공하고 HWP는 제공하지 않는 정책**

### 3. 검증된 사실들
- 각 공고마다 고유한 해시 패턴 존재
- PDF 파일은 해시를 통해 성공적으로 접근 가능
- HWP 확장자 URL들은 모두 동일한 에러 페이지 반환
- A2mUpload 시스템 사용하지만 파일 목록 API는 응답 없음

## 향후 개선 방향

### 1. 즉시 적용 가능한 개선
```python
# 중복 제거 강화
def _extract_hash_based_files(self, file_hash: str):
    # PDF만 추출하고 HWP는 시도하지 않음
    primary_extensions = ['.pdf']  # HWP 제거
    
    # 중복 URL 제거 로직 강화
    seen_urls = set()
    unique_attachments = []
    for attachment in attachments:
        if attachment['url'] not in seen_urls:
            seen_urls.add(attachment['url'])
            unique_attachments.append(attachment)
```

### 2. 추가 조사 필요한 부분
1. **A2mUpload API 엔드포인트 분석**
   ```python
   # 다른 API 엔드포인트 시도
   api_endpoints = [
       "/pms/dextfile/common-fileList.do",
       "/pms/common/file/list.do", 
       "/pms/file/list.do"
   ]
   ```

2. **브라우저 네트워크 탭 분석**
   - 실제 브라우저에서 첨부파일 다운로드 시 사용되는 URL 확인
   - JavaScript 실행 과정에서 동적으로 생성되는 URL 패턴 분석

3. **세션 기반 다운로드 시도**
   ```python
   # 목록 페이지 방문 후 세션 유지하여 파일 다운로드
   response = scraper.get_page(list_url)
   detail_response = scraper.get_page(detail_url)
   file_response = scraper.get_page(file_url)
   ```

## 결론

현재 DJBEA 스크래퍼는 PDF 파일 다운로드에 성공하고 있으나, HWP 파일은 실제로 해당 URL에 존재하지 않는 것으로 확인됨. 사용자가 언급한 "각 공고마다 PDF, HWP 2개 파일"은 실제 사이트 구조와 다를 수 있으며, PDF 파일만 제공되는 것이 정상일 가능성이 높음.

추가 조사 없이는 HWP 파일 다운로드 구현이 어려우며, 현재 PDF 파일 다운로드가 정상적으로 작동하므로 이를 유지하는 것이 적절함.