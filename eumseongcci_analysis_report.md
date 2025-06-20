# 음성상공회의소 사이트 완전 분석 보고서

## 사이트 정보
- **URL**: https://eumseongcci.korcham.net/front/board/boardContentsListPage.do?boardId=10585&menuId=871
- **사이트 유형**: AJAX 기반 동적 로딩 사이트
- **기술 스택**: JSP + jQuery + AJAX

## 1. 목록 페이지 구조

### 1.1 초기 페이지 로딩
- 메인 페이지에는 실제 공고 목록이 포함되어 있지 않음
- JavaScript로 AJAX 요청을 통해 동적으로 목록 데이터 로드
- `boardLiat()` 함수가 실제 목록 데이터를 가져옴 (함수명에 오타 있음)

### 1.2 AJAX 목록 요청
```javascript
function boardLiat(){
    $.ajax({
        url: boardContentsListUrl,  // "/front/board/boardContentsList.do"
        dataType: "html",
        type:"post",
        data: jQuery("#listFrm").serialize(),
        success: function(data) {
            $(".contents_detail").html(data);
        }
    });
}
```

### 1.3 목록 AJAX 요청 방법
- **URL**: `https://eumseongcci.korcham.net/front/board/boardContentsList.do`
- **Method**: POST
- **필수 POST 데이터**:
```python
{
    'miv_pageNo': '1',
    'miv_pageSize': '15', 
    'total_cnt': '',
    'LISTOP': '',
    'mode': 'W',
    'contId': '',
    'delYn': 'N',
    'menuId': '871',
    'boardId': '10585',
    'readRat': 'A',
    'boardCd': 'N',
    'searchKey': 'A',
    'searchTxt': '',
    'pageSize': '15'
}
```

## 2. 상세 페이지 접근 방법

### 2.1 JavaScript 함수 분석
```javascript
function contentsView(contentsid){
    var f = document.listFrm;
    $("#contId").val(contentsid);
    if('A'=='A'){
        // 접근 권한 체크 (현재는 모든 사용자 허용)
    }
    f.target = "_self";
    f.action = boardContentsViewUrl;  // "/front/board/boardContentsView.do"
    f.submit();
}
```

### 2.2 상세 페이지 접근 성공 방법
- **URL**: `https://eumseongcci.korcham.net/front/board/boardContentsView.do`
- **Method**: POST
- **최소한의 POST 데이터** (성공 확인):
```python
{
    'contId': '117426',  # 공고 ID
    'boardId': '10585'   # 게시판 ID
}
```

### 2.3 GET 요청 실패 이유
- GET 요청으로 직접 접근 시 500 에러 발생
- 서버에서 POST 폼 제출만 허용하는 것으로 보임
- 세션 상태와 폼 데이터 검증 필요

## 3. 본문 내용 구조

### 3.1 HTML 구조
```html
<div class="boardveiw">
    <table cellspacing="0" cellpadding="0">
        <tbody>
            <tr>
                <th>제목</th>
                <td colspan="3">게시글 제목</td>
            </tr>
            <tr>
                <th>작성자</th>
                <td>작성자명</td>
                <th>작성일</th>
                <td>작성일</td>
            </tr>
            <tr>
                <td scope="row" colspan="4" class="td_p">
                    <!-- 실제 본문 내용 (이미지, 텍스트 등) -->
                    <p><img src="/../../../../../../file/dext5editordata/2025/20250605_162242585_57482.jpeg"></p>
                </td>
            </tr>
        </tbody>
    </table>
</div>
```

### 3.2 본문 추출 선택자
- **컨테이너**: `div.boardveiw table tbody`
- **본문 내용**: `td.td_p` (class="td_p"인 td 요소)
- **제목**: 첫 번째 `tr`의 `td` (colspan="3")

## 4. 첨부파일 처리

### 4.1 첨부파일 다운로드 함수
```javascript
function down(url,ofn){
    var sp = url.split('|');
    url2 = sp[0]
    for ( var i in sp ) {
        if (i>0 && i<sp.length-1){
            url2 += '/'+sp[i];
        }else{
            fn = sp[i];
        }
    }
    
    var f = document.writeFrm;
    $("#file_path").val(url);
    $("#orignl_file_nm").val(ofn);
    $("#file_nm").val(ofn);

    f.target = "_open";
    f.action = '/downloadUrl.do';
    f.submit();
}
```

### 4.2 첨부파일 링크 패턴
- JavaScript 함수 호출: `javascript:down('파일경로|파일명', '원본파일명')`
- 다운로드 URL: `/downloadUrl.do`
- POST 방식으로 파일 다운로드

## 5. 페이지네이션

### 5.1 페이지 이동 함수
```javascript
function go_Page(page){
    $("#miv_pageNo").val(page);
    search();  // search() -> boardLiat() 호출
}
```

### 5.2 페이지 요청 방법
- 동일한 AJAX 요청에서 `miv_pageNo` 값만 변경
- `miv_pageSize`로 페이지당 항목 수 조절 (기본 15개)

## 6. 스크래핑 구현 방법

### 6.1 세션 생성 및 초기화
```python
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

# 초기 페이지 접근으로 세션 생성
list_url = "https://eumseongcci.korcham.net/front/board/boardContentsListPage.do?boardId=10585&menuId=871"
response = session.get(list_url, verify=False)
```

### 6.2 목록 데이터 가져오기
```python
ajax_url = "https://eumseongcci.korcham.net/front/board/boardContentsList.do"
post_data = {
    'miv_pageNo': str(page_num),
    'miv_pageSize': '15',
    'menuId': '871',
    'boardId': '10585',
    'readRat': 'A',
    'boardCd': 'N',
    'searchKey': 'A',
    'searchTxt': '',
    'pageSize': '15'
    # ... 기타 필수 필드
}
response = session.post(ajax_url, data=post_data, verify=False)
```

### 6.3 상세 페이지 접근
```python
detail_url = "https://eumseongcci.korcham.net/front/board/boardContentsView.do"
detail_data = {
    'contId': cont_id,
    'boardId': '10585'
}
response = session.post(detail_url, data=detail_data, verify=False)
```

### 6.4 첨부파일 다운로드
```python
download_url = "https://eumseongcci.korcham.net/downloadUrl.do"
download_data = {
    'file_path': file_path,
    'orignl_file_nm': original_filename,
    'file_nm': filename
}
response = session.post(download_url, data=download_data, verify=False)
```

## 7. 주요 특징 및 주의사항

### 7.1 기술적 특징
- **AJAX 기반**: 모든 목록 데이터가 동적으로 로드됨
- **POST 전용**: 상세 페이지는 POST 요청만 허용
- **세션 기반**: 초기 페이지 방문으로 세션 생성 필요
- **폼 기반**: JavaScript 폼 제출 방식 사용

### 7.2 스크래핑 고려사항
- GET 요청으로는 상세 페이지 접근 불가 (500 에러)
- 반드시 POST 데이터와 함께 요청해야 함
- 세션 유지 필요 (requests.Session 사용)
- SSL 인증서 검증 비활성화 필요 (`verify=False`)

### 7.3 에러 방지
- 첫 번째 메인 페이지 접근으로 세션 생성
- AJAX 요청 전에 세션이 유효한지 확인
- 적절한 User-Agent 헤더 설정
- 요청 간격 조절로 서버 부하 방지

## 8. 결론

음성상공회의소 사이트는 **AJAX 기반의 동적 로딩 사이트**로, 다음과 같은 접근 방법이 필요합니다:

1. **목록 데이터**: POST AJAX 요청 (`/front/board/boardContentsList.do`)
2. **상세 페이지**: POST 요청 (`/front/board/boardContentsView.do`)  
3. **첨부파일**: POST 요청 (`/downloadUrl.do`)

모든 요청이 POST 방식이며, 적절한 폼 데이터와 세션 관리가 필요합니다. GET 요청으로는 접근할 수 없는 구조입니다.