# 복지넷(bokji.net) 스크래퍼 개발 인사이트

## 사이트 개요
- **사이트명**: 복지넷 (한국사회복지협의회)
- **URL**: https://www.bokji.net/not/nti/01.bokji
- **사이트 유형**: 표준 HTML 게시판 + POST 기반 상세 페이지
- **주요 특징**: 공지사항을 포함한 복지 분야 지원사업 공고

## 기술적 구현 특징

### 1. 게시판 구조 분석
```html
<!-- 목록 페이지: 표준 HTML 테이블 -->
<table class="board_list_type1">
  <tbody>
    <tr class="notice">  <!-- 공지 공고 -->
      <td class="no"><span>공지</span></td>
      <td class="subject">
        <a href="javascript:goView('30659')">[필독] 공고 제목</a>
        <img src="/images/bbs/icon_disk.png" alt="파일" />  <!-- 첨부파일 표시 -->
      </td>
    </tr>
    <tr>  <!-- 일반 공고 -->
      <td class="no">5336</td>
      <td class="subject">
        <a href="javascript:goView('30809')">공고 제목</a>
      </td>
    </tr>
  </tbody>
</table>
```

### 2. 페이지네이션 방식
- **1페이지**: GET 요청
- **2페이지 이상**: POST 요청으로 페이지 파라미터 전송
```python
# 2페이지부터는 POST 데이터
data = {
    'PG': str(page_num),
    'SEARCH_GUBUN': '',
    'SEARCH_KEYWORD': ''
}
```

### 3. 상세 페이지 접근 방식
- **목록 링크**: `javascript:goView('boardidx')`
- **실제 접근**: POST 요청 필요
```python
# 상세 페이지 POST 요청
data = {
    'BOARDIDX': boardidx,
    'PG': '1'
}
response = session.post("https://www.bokji.net/not/nti/01_01.bokji", data=data)
```

### 4. 첨부파일 다운로드 시스템
- **파일 링크**: `javascript:down('boardidx','fileseq')`  
- **다운로드 방식**: POST 요청
```python
# 파일 다운로드 POST 요청
data = {
    'BOARDIDX': boardidx,
    'FILESEQ': fileseq
}
response = session.post("https://www.bokji.net/not/nti/01_02.bokji", data=data)
```

## 주요 해결 과제

### 1. 공지 공고 처리
- **문제**: 번호 대신 "공지" span 태그
- **해결책**: 
```python
is_notice = False
if number_cell.find('span'):
    span_text = number_cell.find('span').get_text(strip=True)
    if span_text == '공지':
        is_notice = True
        number = "공지"
```

### 2. JavaScript 링크 처리
- **문제**: href="javascript:goView('30809')" 형태
- **해결책**: 정규표현식으로 boardidx 추출
```python
boardidx_match = re.search(r"goView\('(\d+)'\)", href)
```

### 3. POST 기반 상세 페이지 접근
- **문제**: GET 요청으로는 상세 페이지 접근 불가
- **해결책**: Enhanced Base Scraper의 `process_announcement` 메서드 오버라이드
```python
def process_announcement(self, announcement, index, output_base):
    # POST 요청으로 상세 페이지 가져오기
    if boardidx:
        data = {'BOARDIDX': boardidx, 'PG': '1'}
        response = self.post_page(self.detail_url, data=data)
```

### 4. 첨부파일 파싱 개선
- **문제**: HTML에 많은 공백과 개행 포함
- **해결책**: 텍스트 정규화 후 파싱
```python
# 공백 정리 후 파싱
link_text = re.sub(r'\s+', ' ', link_elem.get_text()).strip()
size_match = re.search(r'\((\d+)\s*bytes\)', link_text)
```

### 5. 한국어 파일명 처리
- **인코딩**: Content-Disposition 헤더에서 latin-1 → euc-kr/utf-8 변환
- **특수문자**: 파일시스템 호환성을 위한 특수문자 치환

## 성능 및 수집 결과

### 테스트 결과 (3페이지)
- **총 수집 공고**: 30개
- **공지 공고**: 2개 (번호 "공지")
- **일반 공고**: 28개 (번호 5336~5309)
- **첨부파일**: PDF, JPG, HWP 등 다양한 형식

### 수집 성공률
- **목록 파싱**: 100% (30/30)
- **본문 추출**: 100% (30/30)  
- **첨부파일 파싱**: 100% (첨부파일 있는 공고 모두)
- **첨부파일 다운로드**: ~95% (일부 특수문자 파일명 이슈)

## 재사용 가능한 패턴

### 1. POST 기반 게시판 패턴
복지넷과 유사한 구조를 가진 사이트들에 적용 가능:
- 목록: GET 요청
- 상세: POST 요청 (BOARDIDX 파라미터)
- 파일: POST 요청 (BOARDIDX, FILESEQ 파라미터)

### 2. JavaScript 링크 처리 패턴
```python
# JavaScript 함수에서 ID 추출
link_match = re.search(r"goView\('(\d+)'\)", href)
download_match = re.search(r"down\('(\d+)','(\d+)'\)", href)
```

### 3. Enhanced Base Scraper 확장 패턴
```python
class CustomScraper(EnhancedBaseScraper):
    def process_announcement(self, announcement, index, output_base):
        # 사이트별 특화 로직 구현
        # POST 요청, 특수 인증 등
```

## 개발 도전과 해결책

### 1. 동적 vs 정적 콘텐츠
- **도전**: 첫 페이지는 GET, 나머지는 POST
- **해결**: `_get_page_announcements` 메서드 오버라이드

### 2. Enhanced Base Scraper 활용
- **도전**: 기본 클래스는 GET 요청 기반
- **해결**: 필요한 메서드만 선택적 오버라이드하여 하위 호환성 유지

### 3. 첨부파일 링크 추출
- **도전**: HTML 중첩 구조와 공백 처리
- **해결**: BeautifulSoup + 정규표현식 조합

## 기술적 권장사항

### 1. 신규 유사 사이트 개발 시
1. **구조 분석**: 브라우저 개발자 도구로 Network 탭 확인
2. **POST 요청 확인**: AJAX 호출이나 폼 전송 방식 파악
3. **Enhanced Base Scraper 활용**: 기본 기능 최대 활용 후 필요시 오버라이드

### 2. 성능 최적화
- **요청 간격**: 1초 (서버 부하 고려)
- **페이지 간격**: 2초 (안정성 확보)
- **오류 처리**: 개별 공고 실패가 전체 스크래핑을 중단하지 않도록

### 3. 유지보수 고려사항
- **사이트 구조 변경**: 선택자나 URL 패턴 변경 대응
- **인코딩 변화**: 다양한 인코딩 방식 대응
- **보안 정책**: SSL, CSRF 토큰 등의 변화 대응

## 결론

복지넷 스크래퍼는 Enhanced Base Scraper의 확장성을 잘 보여주는 사례입니다. POST 기반 접근과 JavaScript 링크 처리가 핵심이며, 이는 많은 한국 정부/공공기관 사이트에서 재사용할 수 있는 패턴입니다.

**핵심 성공 요인**:
1. 사이트별 특화와 기본 클래스 활용의 균형
2. 단계별 디버깅을 통한 문제 해결
3. 한국어 환경 특성 고려 (인코딩, 파일명)
4. 안정적인 오류 처리 및 로깅

이 패턴은 향후 유사한 구조의 사이트들 (상공회의소, 지역개발공사 등)에서 바로 적용 가능할 것으로 예상됩니다.