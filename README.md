# 부산테크노파크 지원사업 공고 수집 프로그램

부산테크노파크(BTP) 웹사이트에서 지원사업 공고를 자동으로 수집하는 Python 프로그램입니다.

## 기능

- 공고 목록 페이지에서 각 공고 정보 수집
- 공고 상세 페이지의 본문을 마크다운으로 변환하여 저장
- 첨부파일 자동 다운로드
- 페이지네이션 처리 (기본 4페이지)
- 공고별로 별도 폴더에 체계적으로 저장

## 설치 방법

1. Python 3.8 이상 설치 필요

2. 가상환경 생성 및 활성화:
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate  # Windows
```

3. 필요한 패키지 설치:
```bash
pip install -r requirements.txt
```

## 사용 방법

### 기본 실행 (4페이지 수집):
```bash
python run_scraper.py
```

### 페이지 수 지정:
```bash
python run_scraper.py --pages 2  # 2페이지만 수집
python run_scraper.py --pages 10 # 10페이지 수집
```

### 직접 스크립트 실행:
```bash
python btp_scraper.py
```

## 출력 구조

수집된 공고는 `output` 폴더에 다음과 같은 구조로 저장됩니다:

```
output/
├── 001_공고제목1/
│   ├── content.md          # 공고 본문 (마크다운)
│   └── attachments/        # 첨부파일 폴더
│       ├── 첨부파일1.pdf
│       └── 첨부파일2.hwp
├── 002_공고제목2/
│   ├── content.md
│   └── attachments/
│       └── 첨부파일.zip
└── ...
```

## 주요 구성 요소

- `btp_scraper.py`: 메인 스크래퍼 클래스
- `run_scraper.py`: 실행 스크립트 (명령행 인터페이스)
- `requirements.txt`: 필요한 Python 패키지 목록

## 주의사항

- 서버 부하를 줄이기 위해 각 요청 사이에 1초의 대기 시간이 있습니다
- 네트워크 상태에 따라 수집 시간이 달라질 수 있습니다
- 첨부파일이 큰 경우 다운로드 시간이 오래 걸릴 수 있습니다