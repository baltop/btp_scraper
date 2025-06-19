# "지원사업 공고 수집" Project Guidelines

## 목표
주어진 URL의 사이트에 접속하여 사이트에 공지된 지원사업 공고문을 수집하고 첨부파일을 다운로드 하여 로컬디렉토리에 저장한다.
사이트의 공고는 대부분 pagination 기반의 BBS 형태로 되어 있다.
주어진 URL은 1 페이지의  목록 페이지 이다. 목록들은 대부분 10개에서 30개 내외이다.
수집을 위해 목록 상의 첫번째 공고의 링크를 타고 상세 페이지로 이동하여, 상세페이지에서 공고 내용을 markdown 방식으로 저장한다.
공고 본문이 있는 상세페이지에는 공고본문과 첨부파일 링크가 있다. 첨부파일 링크가 있는 경우 첨부파일들을 다운로드 하여 로컬에 저장한다.
각 공고 별로 본문 파일과 첨부파일은 분리되어 저장되어야 한다.

## 세부 단계
- 주어진 URL을 접속하여 html을 다운로드 받는다.
- html의 태그와 엘레멘트를 분석하여 DOM 구조를 파악한다.
- 공고 목록을 파악하여 각 공고의 세부페이지로 이동할 수 있는 링크나 javacript 방법을 찾아낸다.
- 첫번째 공고 상세 페이지로 이동한다.
- 상세페이지의 html를 분석하여 헤더 제목 등은 제외하고 공고 본문만 추려 낼수 있는 태그, 엘레멘트를 찾아내서 해당 부분만을 markdown으로 변환하여 파일로 저장한다.
- 상세패이지의 html을 분석하여 첨부파일이 있으면 첨부파일을 다운로드 받는다.
- 다시 목록 페이지로 되돌아 가서 다음 공고를 위와 같은 방식으로 처리하고 목록의 전체 공고가 처리될때까지 반복한다.
- 주어진 URL의 공고들을 전부 처리했으면 하단의 pagination bar를 분석하여 다음 페이지로 이동한다.
- 다음 페이지도 공고들이 있으므로 이것들으 처리하고 전부 처리되고 나면 다시 다음 페이지로 이동한다.
- 4페이지까지만 반복하고 4페이지가 끝나면 프로그램을 중단한다.

## 새로운 사이트 추가 시 주의사항

### 1. 사이트 구조 분석
새로운 사이트를 추가하기 전에 반드시 다음 사항들을 확인해야 합니다:

#### 1.1 페이지 구조 확인
- **목록 페이지 URL 패턴**: 페이지네이션이 어떻게 구현되어 있는지 확인
  - GET 파라미터 방식: `?page=2`, `?p=2`, `?pageNo=2` 등
  - POST 요청 방식: AJAX/JSON으로 데이터를 가져오는 경우
  - JavaScript 함수 호출: `onclick="goPage(2)"` 등

- **상세 페이지 접근 방식**:
  - 직접 링크: `<a href="/board/view?id=123">`
  - JavaScript 함수: `onclick="viewDetail(123)"`
  - POST 요청: 폼 전송으로 상세 페이지 접근

#### 1.2 HTML 구조 파악
- **목록 페이지 구조**:
  - 테이블 기반: `<table>`, `<tr>`, `<td>`
  - 리스트 기반: `<ul>`, `<li>` 또는 `<div>` 반복
  - 공고 제목, 날짜, 조회수, 첨부파일 여부 등의 위치 확인

- **상세 페이지 구조**:
  - 본문 영역: 공고 내용이 들어있는 컨테이너 찾기
  - 첨부파일 영역: 파일 다운로드 링크가 있는 위치
  - 메타 정보: 작성자, 작성일, 조회수 등

### 2. 기술적 고려사항

#### 2.1 정적 vs 동적 사이트
- **정적 HTML**: BeautifulSoup으로 파싱 가능
- **JavaScript 렌더링**: Playwright나 Selenium 필요
- **AJAX/JSON API**: requests로 직접 API 호출

#### 2.2 인증 및 보안
- **세션 관리**: 로그인이 필요한 경우 세션 유지
- **CSRF 토큰**: POST 요청 시 토큰 처리
- **User-Agent**: 일부 사이트는 브라우저 User-Agent 필요
- **SSL 인증서**: `verify=False` 옵션 필요할 수 있음

#### 2.3 첨부파일 다운로드
- **직접 링크**: `<a href="/download/file.pdf">`
- **JavaScript 함수**: `onclick="download(123)"`
- **인증 필요**: 세션 쿠키나 토큰이 필요한 경우
- **리다이렉트**: 여러 단계의 리다이렉트를 거치는 경우

### 3. 구현 체크리스트

#### 3.1 새 스크래퍼 클래스 생성
```python
from base_scraper import BaseScraper

class NewSiteScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://example.com"
        self.list_url = "https://example.com/board/list"
    
    def get_list_url(self, page_num):
        # 페이지별 URL 생성 로직
        pass
    
    def parse_list_page(self, html_content):
        # 목록 페이지 파싱 로직
        pass
    
    def parse_detail_page(self, html_content):
        # 상세 페이지 파싱 로직
        pass
```

#### 3.2 tp_scraper.py에 추가
- 새 스크래퍼 import
- argparse choices에 추가
- 실행 로직에 새 사이트 처리 추가

### 4. 일반적인 문제 해결 방법

#### 4.1 페이지 로드 실패
- User-Agent 헤더 추가
- SSL 인증서 검증 비활성화
- 타임아웃 값 증가
- 쿠키/세션 처리

#### 4.2 파싱 실패
- HTML 구조 재확인
- JavaScript 렌더링 필요 여부 확인
- 인코딩 문제 확인 (UTF-8, EUC-KR 등)

#### 4.3 첨부파일 다운로드 실패
- 다운로드 URL 패턴 분석
- Referer 헤더 추가
- 세션 쿠키 확인
- JavaScript 실행 필요 여부

### 5. 테스트 방법

1. **단계별 테스트**:
   ```bash
   # 1. 목록 페이지 접근 테스트
   curl -s "목록URL" | grep "공고제목"
   
   # 2. 상세 페이지 접근 테스트
   python3 -c "from new_scraper import NewSiteScraper; ..."
   
   # 3. 첨부파일 다운로드 테스트
   # 개별 파일 다운로드 테스트
   ```

2. **전체 실행 테스트**:
   ```bash
   # 1페이지만 테스트
   python tp_scraper.py --site newsite --pages 1
   ```

### 6. 현재 구현된 사이트별 특징 요약

- **BTP**: 표준적인 게시판, 직접 링크 방식
- **ITP**: JavaScript 함수 기반, 파일 다운로드 제한
- **CCEI**: AJAX/JSON API, POST 요청 방식, 파일 정보가 목록 API에 포함
- **KIDP**: JavaScript 렌더링, 복잡한 URL 파라미터
- **GSIF**: Base64 인코딩된 파라미터, 특수한 테이블 구조
- **DJBEA**: SSL 인증서 문제, JavaScript 기반 네비게이션
- **MIRE**: PHP 세션 기반, EUC-KR 인코딩, 특수한 테이블 구조
- **DCB**: 표준 테이블 구조, 다양한 파일 다운로드 패턴

새로운 사이트를 추가할 때는 위 사이트들 중 가장 유사한 구조를 가진 스크래퍼를 참고하여 구현하면 됩니다.

### 7. 주요 개발 인사이트

#### 7.1 인코딩 처리
웹 스크래핑 시 인코딩 문제는 매우 흔합니다. 특히 한국 사이트들은 다양한 인코딩을 사용합니다:

1. **페이지 인코딩**:
   - UTF-8이 기본이지만, 일부 사이트는 EUC-KR 사용
   - `response.encoding` 설정으로 해결
   ```python
   response = self.session.get(url)
   response.encoding = 'euc-kr'  # 또는 'utf-8'
   ```

2. **파일명 인코딩**:
   - Content-Disposition 헤더의 파일명이 잘못 인코딩된 경우가 많음
   - latin-1로 디코딩 후 실제 인코딩으로 재디코딩 필요
   ```python
   filename = filename.encode('latin-1').decode('euc-kr')
   ```

3. **RFC 5987 형식 처리**:
   - 최신 표준은 `filename*=UTF-8''%ED%95%9C%EA%B8%80.hwp` 형식
   - 인코딩과 파일명을 분리하여 처리 필요

#### 7.2 파일 다운로드 패턴
각 사이트마다 다른 파일 다운로드 방식을 사용합니다:

1. **직접 링크 방식**: 
   - 가장 단순, href 속성에 파일 URL 포함

2. **JavaScript 함수 방식**:
   - `onclick="download('file_id')"` 형태
   - 정규표현식으로 파라미터 추출 필요

3. **UUID/ID 기반 방식**:
   - CCEI처럼 파일 정보가 별도 API나 목록에 포함
   - 파일 UUID로 다운로드 URL 구성

4. **세션 기반 방식**:
   - MIRE처럼 PHP 세션 ID가 필요한 경우
   - 초기 접속 시 세션 ID 획득 후 재사용

#### 7.3 AJAX/JSON API 처리
동적 사이트 증가로 AJAX 처리가 중요해졌습니다:

1. **API 엔드포인트 찾기**:
   - 브라우저 개발자 도구의 Network 탭 활용
   - XHR/Fetch 요청 확인

2. **데이터 캐싱**:
   - CCEI처럼 목록 API에 상세 정보가 포함된 경우
   - 리스트 데이터를 캐시하여 재사용

3. **POST 요청 처리**:
   - 필요한 파라미터 확인
   - CSRF 토큰 등 보안 요소 처리

#### 7.4 에러 처리 및 복원력
안정적인 스크래퍼를 위한 필수 요소:

1. **SSL 인증서 문제**:
   - `verify=False` 옵션 사용 (보안상 주의 필요)
   - 특히 정부/공공기관 사이트에서 흔함

2. **동적 세션 관리**:
   - 세션이 만료되는 경우 자동 재획득
   - 쿠키 저장 및 재사용

3. **다단계 폴백**:
   - 파일명 인코딩 시도: EUC-KR → UTF-8 → 원본
   - 본문 추출 시도: 특정 클래스 → 대체 선택자 → 텍스트 길이 기반

4. **메타데이터 보존**:
   - 파일명을 알 수 없는 경우 임시 파일명 사용
   - UUID나 인덱스 기반 파일명 생성

#### 7.5 성능 최적화
대량 스크래핑 시 고려사항:

1. **요청 간격 조절**:
   - `time.sleep(1)` 등으로 서버 부하 방지
   - 페이지별로 다른 대기 시간 설정

2. **스트리밍 다운로드**:
   - 대용량 파일은 청크 단위로 다운로드
   - 메모리 효율성 향상

3. **병렬 처리 고려**:
   - 여러 파일 동시 다운로드 (서버 정책 확인 필요)
   - 비동기 처리 도입 가능

#### 7.6 디버깅 팁
문제 발생 시 효과적인 디버깅 방법:

1. **단계별 테스트**:
   - 목록 파싱 → 상세 페이지 접근 → 파일 다운로드 순서로 테스트
   - 각 단계별 출력 확인

2. **HTML 저장**:
   - 문제가 되는 페이지의 HTML을 파일로 저장
   - 오프라인에서 파싱 로직 테스트

3. **헤더 분석**:
   - Response 헤더 확인 (특히 Content-Type, Content-Disposition)
   - Request 헤더 조정 (User-Agent, Referer 등)

4. **인코딩 테스트**:
   - `chardet` 라이브러리로 인코딩 자동 감지
   - 다양한 인코딩 조합 시도

### 8. Enhanced 스크래퍼 개발 가이드라인

#### 8.1 표준화된 개발 규칙

새로운 Enhanced 스크래퍼 개발 시 반드시 준수해야 할 표준 규칙:

**출력 디렉토리 규칙**:
- 테스트 시 항상 `output/{사이트명}` 형식 사용
- 예: `output/kca`, `output/keit`, `output/djbea`
- 기존 `output_사이트명` 형식은 사용 금지

**테스트 페이지 수**:
- 모든 테스트는 기본적으로 **3페이지**까지 실행
- `test_enhanced_{사이트명}.py`의 기본값을 3으로 설정

**첨부파일 검증 필수**:
- 테스트 완료 후 첨부파일 다운로드 상태 반드시 확인
- 파일 크기, 한글 파일명, 다운로드 성공 여부 검증
- 첨부파일이 없는 공고와 있는 공고 모두 정상 처리 확인

**개발 인사이트 문서**:
- 모든 사이트는 `{사이트명}_code.txt` 형식으로 인사이트 저장
- 예: `kca_code.txt`, `keit_code.txt`, `djbea_code.txt`
- 사이트 특성, 기술적 해결책, 재사용 패턴 등 포함

**테스트 함수 기본값 설정**:
```python
def test_site_scraper(pages=3):  # 기본값을 3으로 설정
    output_dir = "output/사이트명"  # 표준 출력 디렉토리
    # 첨부파일 검증 로직 포함 필수
```

#### 8.2 Enhanced 아키텍처 개요

Enhanced 스크래퍼는 기존 BaseScraper에서 발전된 형태로, 다음과 같은 핵심 개선사항을 제공합니다:

1. **StandardTableScraper 상속**: 공통 기능 재사용
2. **중복 검사 자동화**: 해시 기반 제목 중복 감지  
3. **향상된 로깅**: 구조화된 로그 시스템
4. **Fallback 메커니즘**: 설정 없이도 동작하는 기본 구현
5. **파일명 인코딩 개선**: 다단계 인코딩 복구

#### 8.2 클래스 구조 패턴

```python
from enhanced_base_scraper import StandardTableScraper

class EnhancedSiteScraper(StandardTableScraper):
    """사이트명 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 하드코딩된 설정들 (설정 파일로 관리되지만 fallback용)
        self.base_url = "https://example.com"
        self.list_url = "https://example.com/board/list"
        
        # 사이트 특화 설정
        self.verify_ssl = True/False  # SSL 인증서 정책
        self.default_encoding = 'utf-8'  # 또는 'euc-kr'
    
    def get_list_url(self, page_num: int) -> str:
        """페이지별 URL 생성 - 설정 주입과 Fallback 패턴"""
        # 설정이 있으면 부모 클래스의 표준 구현 사용
        if self.config and self.config.pagination:
            return super().get_list_url(page_num)
        
        # Fallback: 사이트 특화 로직
        return f"{self.list_url}?page={page_num}"
    
    def parse_list_page(self, html_content: str) -> list:
        """목록 페이지 파싱 - 설정 주입과 Fallback 패턴"""
        # 설정 기반 파싱이 가능하면 사용
        if self.config and self.config.selectors:
            return super().parse_list_page(html_content)
        
        # Fallback: 사이트 특화 로직
        return self._parse_list_fallback(html_content)

# 하위 호환성을 위한 별칭
SiteScraper = EnhancedSiteScraper
```

#### 8.3 중복 검사 시스템

Enhanced 스크래퍼는 자동 중복 검사 기능을 제공합니다:

```python
# 자동으로 수행되는 중복 검사
def filter_new_announcements(self, announcements: List[Dict[str, Any]]) -> tuple:
    """새로운 공고만 필터링 - 중복 임계값 체크 포함"""
    new_announcements = []
    duplicate_count = 0
    
    for ann in announcements:
        title = ann.get('title', '')
        if not self.is_title_processed(title):
            new_announcements.append(ann)
            duplicate_count = 0  # 리셋
        else:
            duplicate_count += 1
            # 연속 3개 중복 시 조기 종료
            if duplicate_count >= self.duplicate_threshold:
                return new_announcements, True
    
    return new_announcements, False
```

**특징**:
- MD5 해시 기반 제목 정규화 및 중복 검사
- `processed_titles_사이트명.json` 파일로 상태 관리
- 연속 3개 중복 발견 시 자동 조기 종료
- 제목 정규화: 공백, 특수문자, 대소문자 통일

#### 8.4 파일명 인코딩 개선

Enhanced 스크래퍼는 다단계 인코딩 복구를 지원합니다:

```python
def _extract_filename(self, response: requests.Response, default_path: str) -> str:
    """향상된 파일명 추출 - 다단계 인코딩 처리"""
    content_disposition = response.headers.get('content-disposition', '')
    
    # RFC 5987 형식 처리 (filename*=UTF-8''%ED%95%9C%EA%B8%80.hwp)
    rfc5987_match = re.search(r"filename\*=([^']*)'([^']*)'(.+)", content_disposition)
    if rfc5987_match:
        encoding, lang, filename = rfc5987_match.groups()
        try:
            filename = unquote(filename)
            decoded = filename.encode('latin-1').decode(encoding or 'utf-8')
            return os.path.join(save_dir, self.sanitize_filename(decoded))
        except:
            pass
    
    # 다양한 인코딩 시도: UTF-8, EUC-KR, CP949
    for encoding in ['utf-8', 'euc-kr', 'cp949']:
        try:
            if encoding == 'utf-8':
                decoded = filename.encode('latin-1').decode('utf-8')
            else:
                decoded = filename.encode('latin-1').decode(encoding)
            
            if decoded and not decoded.isspace():
                clean_filename = self.sanitize_filename(decoded.replace('+', ' '))
                return os.path.join(save_dir, clean_filename)
        except:
            continue
```

#### 8.5 향상된 로깅 시스템

구조화된 로깅으로 디버깅과 모니터링을 개선합니다:

```python
# 정보성 로그 (진행상황)
logger.info(f"테이블에서 {len(tbody.find_all('tr'))}개 행 발견")
logger.info(f"{len(announcements)}개 공고 파싱 완료")
logger.info(f"다운로드 완료: {save_path} ({file_size:,} bytes)")

# 디버그 로그 (상세 정보)
logger.debug(f"본문을 {selector} 선택자로 찾음")
logger.debug(f"JavaScript 파일 다운로드 URL 생성: {file_url}")

# 경고 로그 (주의사항)
logger.warning(f"basic_table 클래스를 가진 테이블을 찾을 수 없습니다")

# 오류 로그 (실패 원인)
logger.error(f"행 파싱 중 오류: {e}")
logger.error(f"파일 다운로드 실패 {url}: {e}")
```

#### 8.6 Fallback 메커니즘 패턴

Enhanced 스크래퍼는 설정 없이도 동작하는 Fallback 패턴을 구현합니다:

```python
def parse_list_page(self, html_content: str) -> list:
    """목록 페이지 파싱"""
    # 1단계: 설정 기반 파싱 시도
    if self.config and self.config.selectors:
        return super().parse_list_page(html_content)
    
    # 2단계: Fallback - 사이트 특화 로직
    return self._parse_list_fallback(html_content)

def _parse_list_fallback(self, html_content: str) -> list:
    """사이트별 특화된 파싱 로직"""
    # 여러 선택자를 순차적으로 시도
    for selector in ['.basic_table', '.board_table', 'table']:
        table = soup.find('table', class_=selector)
        if table:
            break
    
    # 본문 추출도 다단계 시도
    for selector in ['.table_con', '.view_con', '.board_view']:
        content_area = soup.select_one(selector)
        if content_area:
            break
```

#### 8.7 사이트별 특화 처리 예시

**GSIF (Base64 인코딩 파라미터)**:
```python
def get_list_url(self, page_num: int) -> str:
    if page_num == 1:
        return self.list_url
    else:
        start_page = (page_num - 1) * 15
        params = f"startPage={start_page}&listNo=&table=cs_bbs_data..."
        encoded = base64.b64encode(params.encode('utf-8')).decode('utf-8')
        return f"{self.base_url}/gsipa/bbs_list.do?bbs_data={encoded}||"
```

**JBF (JavaScript 파일 다운로드)**:
```python
def _extract_attachments(self, soup: BeautifulSoup) -> list:
    # JavaScript 함수에서 파일 다운로드 파라미터 추출
    # 예: fn_fileDown('파일ID')
    match = re.search(r"fn_fileDown\\('([^']+)'\\)", onclick)
    if match:
        file_id = match.group(1)
        file_url = f"{self.base_url}/main/fileDown.action?file_id={file_id}"
```

#### 8.8 테스트 및 검증 패턴

Enhanced 스크래퍼의 표준 테스트 방법:

```python
def verify_results(output_dir):
    """결과 검증 - 표준 패턴"""
    # 1. 원본 URL 포함 확인
    if '**원본 URL**:' in content and 'site_domain' in content:
        url_check_passed += 1
    
    # 2. 한글 파일명 확인
    has_korean = any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename)
    
    # 3. 파일 크기 확인
    file_size = os.path.getsize(att_path)
    
    # 4. 성공률 계산
    success_rate = (successful_items / total_items) * 100
```

#### 8.9 성능 최적화 패턴

**스트리밍 다운로드**:
```python
def download_file(self, url: str, save_path: str) -> bool:
    response = self.session.get(url, stream=True, verify=self.verify_ssl)
    with open(save_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
```

**세션 재사용**:
```python
self.session = requests.Session()
self.session.headers.update(self.headers)
# 모든 요청에서 세션 재사용으로 성능 개선
```

#### 8.10 Enhanced 스크래퍼 장점 요약

1. **개발 효율성**: 공통 기능 재사용으로 개발 시간 단축
2. **안정성**: 중복 검사와 조기 종료로 안정적인 실행
3. **디버깅**: 구조화된 로깅으로 문제 진단 용이
4. **호환성**: 기존 코드와 하위 호환성 유지
5. **확장성**: 설정 주입으로 향후 YAML 설정 지원 준비
6. **복원력**: 다단계 Fallback으로 파싱 실패 최소화
7. **인코딩**: 한글 파일명 처리 개선
8. **성능**: 스트리밍 다운로드와 세션 재사용


# pip install  대신에 uv add를 사용할 것.

# robots.txt는 무시할 것.

## 9. 새로운 사이트 추가 시 실전 개발 프로세스

### 9.1 개발 단계별 체크리스트

#### 1단계: 사이트 분석 및 기본 구조 파악
```bash
# Playwright로 사이트 구조 분석
python -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto('사이트URL')
    input('Press Enter after analysis...')
    browser.close()
"
```

**체크 포인트**:
- [ ] 목록 페이지 테이블/리스트 구조 확인
- [ ] 페이지네이션 방식 확인 (GET/POST/JavaScript)
- [ ] 상세 페이지 링크 패턴 확인
- [ ] 첨부파일 다운로드 링크 패턴 확인
- [ ] SSL 인증서 상태 확인
- [ ] 인코딩 방식 확인 (UTF-8/EUC-KR)

#### 2단계: Enhanced 스크래퍼 개발
```python
# enhanced_{사이트명}_scraper.py 파일 생성
from enhanced_base_scraper import StandardTableScraper

class Enhanced{사이트명}Scraper(StandardTableScraper):
    """사이트명 전용 스크래퍼 - 향상된 버전"""
    
    def __init__(self):
        super().__init__()
        # 기본 설정
        self.base_url = "https://example.com"
        self.list_url = "https://example.com/board/list"
        
        # 사이트별 특화 설정
        self.verify_ssl = True/False
        self.default_encoding = 'utf-8'/'euc-kr'
        self.timeout = 30/60
        self.delay_between_requests = 1/2
```

**필수 구현 메소드**:
- [ ] `get_list_url()` - 페이지네이션 URL 생성
- [ ] `parse_list_page()` - 목록 페이지 파싱
- [ ] `parse_detail_page()` - 상세 페이지 파싱
- [ ] `_extract_attachments()` - 첨부파일 추출
- [ ] `download_file()` - 파일 다운로드 (필요시 오버라이드)

#### 3단계: 테스트 스크립트 작성
```python
# test_enhanced_{사이트명}.py 파일 생성
def test_{사이트명}_scraper(pages=3):  # 기본값 3페이지
    """사이트명 스크래퍼 테스트"""
    scraper = Enhanced{사이트명}Scraper()
    output_dir = "output/{사이트명}"  # 표준 출력 디렉토리
    os.makedirs(output_dir, exist_ok=True)
    scraper.scrape_pages(max_pages=pages, output_base=output_dir)

def verify_results(output_dir):
    """결과 검증 - 첨부파일 검증 필수"""
    # 1. 공고 수 확인
    # 2. 첨부파일 다운로드 상태 확인
    # 3. 한글 파일명 처리 확인
    # 4. 원본 URL 포함 확인
    # 5. 성공률 계산
```

#### 4단계: 단계별 테스트 실행
```bash
# 1. 단일 페이지 테스트
python test_enhanced_{사이트명}.py --single

# 2. 3페이지 테스트
python test_enhanced_{사이트명}.py --pages 3

# 3. 결과 확인
ls -la output/{사이트명}/
find output/{사이트명} -name "*.pdf" -o -name "*.hwp" | wc -l
```

#### 5단계: 개발 인사이트 문서 작성
```bash
# {사이트명}_code.txt 파일 생성
```

**문서 포함 내용**:
- [ ] 사이트 특성 분석 (URL, 구조, 인코딩)
- [ ] 기술적 구현 특징 (코드 예시 포함)
- [ ] 주요 해결책 (인코딩, 파일다운로드, 특수 처리)
- [ ] 테스트 결과 (성공률, 파일 통계)
- [ ] 재사용 가능한 패턴
- [ ] 특별한 기술적 도전과 해결책

### 9.2 일반적인 개발 패턴별 대응책

#### 표준 HTML 테이블 기반 사이트 (JBBA, BUSANIT 타입)
```python
def parse_list_page(self, html_content: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table')
    tbody = table.find('tbody') or table
    
    for row in tbody.find_all('tr'):
        cells = row.find_all('td')
        if len(cells) < 3:  # 최소 필드 확인
            continue
        
        # 제목 셀 (보통 두 번째)
        title_cell = cells[1]
        link_elem = title_cell.find('a')
        
        if link_elem:
            title = link_elem.get_text(strip=True)
            href = link_elem.get('href', '')
            detail_url = urljoin(self.base_url, href)
```

**적용 사이트**: 대부분의 정부기관, 공공기관 게시판

#### JavaScript 기반 동적 사이트 (KIDP, GSIF 타입)
```python
def get_list_url(self, page_num: int) -> str:
    if page_num == 1:
        return self.list_url
    else:
        # JavaScript 함수 파라미터 분석 후 URL 구성
        params = self._build_page_params(page_num)
        return f"{self.base_url}/api/list?{params}"

def _extract_attachments(self, soup: BeautifulSoup) -> list:
    # JavaScript 함수에서 파일 ID 추출
    onclick_pattern = r"download\('([^']+)'\)"
    for link in soup.find_all('a', onclick=re.compile(onclick_pattern)):
        match = re.search(onclick_pattern, link.get('onclick', ''))
        if match:
            file_id = match.group(1)
            file_url = f"{self.base_url}/download?id={file_id}"
```

**적용 사이트**: 최신 기술 스택을 사용하는 사이트

#### AJAX/JSON API 기반 사이트 (CCEI 타입)
```python
def fetch_announcements_api(self, page_num: int) -> dict:
    api_url = f"{self.base_url}/api/announcements"
    payload = {
        'page': page_num,
        'size': 20,
        'boardType': 'notice'
    }
    
    response = self.session.post(api_url, json=payload)
    return response.json()

def parse_api_response(self, api_data: dict) -> list:
    announcements = []
    for item in api_data.get('data', []):
        announcement = {
            'title': item.get('title'),
            'url': f"{self.base_url}/view/{item.get('id')}",
            'attachments': item.get('files', [])  # API에 첨부파일 정보 포함
        }
        announcements.append(announcement)
    return announcements
```

**적용 사이트**: 최신 웹 애플리케이션, SPA 기반 사이트

### 9.3 한글 파일명 처리 표준 패턴

#### 다단계 인코딩 처리 패턴
```python
def _extract_filename_from_response(self, response, default_path):
    content_disposition = response.headers.get('Content-Disposition', '')
    
    if content_disposition:
        # 1. RFC 5987 형식 우선 처리
        rfc5987_match = re.search(r"filename\*=([^']*)'([^']*)'(.+)", content_disposition)
        if rfc5987_match:
            encoding, lang, filename = rfc5987_match.groups()
            try:
                filename = unquote(filename, encoding=encoding or 'utf-8')
                return os.path.join(save_dir, self.sanitize_filename(filename))
            except:
                pass
        
        # 2. 일반 filename 파라미터 처리
        filename_match = re.search(r'filename[^;=\n]*=([\'"]*)(.*?)\1', content_disposition)
        if filename_match:
            filename = filename_match.group(2)
            
            # 3. 다양한 인코딩 시도
            for encoding in ['utf-8', 'euc-kr', 'cp949']:
                try:
                    if encoding == 'utf-8':
                        decoded = filename.encode('latin-1').decode('utf-8')
                    else:
                        decoded = filename.encode('latin-1').decode(encoding)
                    
                    if decoded and not decoded.isspace():
                        clean_filename = self.sanitize_filename(decoded.replace('+', ' '))
                        return os.path.join(save_dir, clean_filename)
                except:
                    continue
    
    return default_path
```

### 9.4 성능 최적화 및 안정성 패턴

#### 네트워크 안정성 강화
```python
def robust_request(self, url: str, max_retries: int = 3) -> requests.Response:
    """견고한 요청 처리"""
    for attempt in range(max_retries):
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response
        except (requests.Timeout, requests.ConnectionError) as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2  # 지수 백오프
                logger.warning(f"재시도 {attempt + 1}/{max_retries}: {wait_time}초 대기")
                time.sleep(wait_time)
            else:
                logger.error(f"최대 재시도 횟수 초과: {e}")
                raise
```

#### 메모리 효율적 대용량 파일 처리
```python
def download_large_file(self, url: str, save_path: str) -> bool:
    """대용량 파일 스트리밍 다운로드"""
    try:
        response = self.session.get(url, stream=True, timeout=120)
        total_size = int(response.headers.get('content-length', 0))
        
        with open(save_path, 'wb') as f:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # 진행률 로깅 (10% 단위)
                    if total_size > 0 and downloaded % (total_size // 10) < 8192:
                        progress = (downloaded / total_size) * 100
                        logger.info(f"다운로드 진행률: {progress:.1f}%")
        
        return True
    except Exception as e:
        logger.error(f"대용량 파일 다운로드 실패: {e}")
        return False
```

### 9.5 테스트 및 검증 자동화 패턴

#### 표준 검증 함수
```python
def verify_results(output_dir):
    """표준 결과 검증 패턴"""
    announcement_folders = [d for d in os.listdir(output_dir) 
                          if os.path.isdir(os.path.join(output_dir, d))]
    
    total_items = len(announcement_folders)
    successful_items = 0
    total_attachments = 0
    korean_files = 0
    file_size_total = 0
    
    for folder_name in announcement_folders:
        folder_path = os.path.join(output_dir, folder_name)
        
        # content.md 파일 확인
        content_file = os.path.join(folder_path, 'content.md')
        if os.path.exists(content_file):
            successful_items += 1
            
            # 원본 URL 포함 확인
            with open(content_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if '**원본 URL**:' in content:
                    url_check_passed += 1
        
        # 첨부파일 검증
        attachments_dir = os.path.join(folder_path, 'attachments')
        if os.path.exists(attachments_dir):
            for filename in os.listdir(attachments_dir):
                total_attachments += 1
                
                # 한글 파일명 검증
                if any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in filename):
                    korean_files += 1
                
                # 파일 크기 검증
                file_path = os.path.join(attachments_dir, filename)
                file_size = os.path.getsize(file_path)
                file_size_total += file_size
    
    # 성공률 계산 및 리포트
    success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
    
    logger.info("=== 검증 결과 요약 ===")
    logger.info(f"총 공고 수: {total_items}")
    logger.info(f"성공적 처리: {successful_items} ({success_rate:.1f}%)")
    logger.info(f"총 첨부파일: {total_attachments}")
    logger.info(f"한글 파일명: {korean_files}")
    logger.info(f"총 파일 용량: {file_size_total:,} bytes")
    
    return success_rate >= 80  # 80% 이상 성공 시 통과
```

### 9.6 문제 해결 패턴별 대응책

#### SSL 인증서 문제
```python
# 문제: SSL 인증서 검증 실패 (특히 정부기관 사이트)
# 해결: verify_ssl = False 설정
self.verify_ssl = False
response = self.session.get(url, verify=self.verify_ssl)
```

#### 세션 만료 문제
```python
# 문제: 장시간 스크래핑 시 세션 만료
# 해결: 세션 재생성 로직
def refresh_session_if_needed(self):
    try:
        # 테스트 요청으로 세션 상태 확인
        test_response = self.session.get(self.base_url, timeout=10)
        if test_response.status_code == 401:
            self._create_new_session()
    except:
        self._create_new_session()
```

#### 동적 콘텐츠 로딩 문제
```python
# 문제: JavaScript로 동적 로딩되는 콘텐츠
# 해결: Playwright 사용
def fetch_dynamic_content(self, url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        page.wait_for_selector('table', timeout=30000)  # 테이블 로딩 대기
        content = page.content()
        browser.close()
        return content
```

### 9.7 실전 디버깅 체크리스트

#### 목록 페이지 파싱 실패 시
1. [ ] HTML 구조 변경 확인: `soup.find('table')` → `soup.find_all('table')`
2. [ ] 클래스명 변경 확인: `.board_table` → `.table`
3. [ ] JavaScript 렌더링 필요 여부 확인
4. [ ] 헤더 설정 확인: User-Agent, Referer 등

#### 첨부파일 다운로드 실패 시
1. [ ] 다운로드 URL 패턴 분석: `download.php` → `fileDown.do`
2. [ ] 세션 쿠키 필요 여부 확인
3. [ ] Referer 헤더 설정 확인
4. [ ] 파일명 인코딩 문제 확인

#### 한글 파일명 깨짐 시
1. [ ] Content-Disposition 헤더 분석
2. [ ] 인코딩 순서 변경: UTF-8 → EUC-KR → CP949
3. [ ] RFC 5987 형식 지원 확인
4. [ ] URL 디코딩 적용 확인

### 9.8 성공 사례 기반 재사용 패턴

#### JBBA 타입 (표준 HTML 테이블)
- **적용 가능**: 대부분의 정부기관, 공공기관
- **특징**: GET 파라미터 페이지네이션, 직접 링크
- **재사용률**: 95%

#### BUSANIT 타입 (HTTP 사이트)
- **적용 가능**: 구형 ASP/PHP 기반 사이트
- **특징**: HTTP, 상대 URL, 표준 다운로드 패턴
- **재사용률**: 90%

#### CCEI 타입 (AJAX/JSON API)
- **적용 가능**: 최신 웹 애플리케이션
- **특징**: JSON API, 파일 정보 포함, POST 요청
- **재사용률**: 70%

### 9.9 개발 효율성 극대화 팁

#### 1. 유사 사이트 스크래퍼 활용
```bash
# 기존 스크래퍼 중 가장 유사한 것을 복사해서 시작
cp enhanced_jbba_scraper.py enhanced_newssite_scraper.py
cp test_enhanced_jbba.py test_enhanced_newssite.py

# 사이트명, URL만 변경하고 바로 테스트
```

#### 2. 단계별 개발
```python
# 1단계: 기본 구조만 구현 (목록 파싱)
# 2단계: 상세 페이지 파싱 추가
# 3단계: 첨부파일 다운로드 추가
# 4단계: 인코딩 및 예외 처리 강화
```

#### 3. 개발 과정 문서화
```bash
# 개발 중 발견한 특이사항을 즉시 기록
echo "특이사항: JavaScript 렌더링 필요" >> {사이트명}_notes.txt
echo "해결책: Playwright 사용" >> {사이트명}_notes.txt
```

이런 패턴들을 따르면 새로운 사이트 추가 시 개발 시간을 크게 단축하고, 안정적인 스크래퍼를 만들 수 있습니다.
