# 화장품 시장 뉴스 클리핑 자동화 시스템

더마 스킨케어·홈뷰티 디바이스를 메인으로, 화장품 시장 전체를 서브로 매일 자동 수집해
GitHub Pages 대시보드 웹페이지와 이메일로 보여주는 시스템입니다. 비용은 0원(무료 티어)입니다.

## 폴더 구조

```
cosmetics-news-clipping/
├── config.yaml              # 키워드·소스·이메일 설정 (여기부터 채워야 함)
├── requirements.txt
├── collectors/
│   ├── utils.py             # 공용 함수 (분류, 저장, 중복 제거)
│   └── naver_news.py        # 네이버 뉴스 검색 API 수집기 (1차 구현)
├── data/
│   ├── news.json            # 수집된 뉴스 누적 데이터
│   └── exhibitions.json     # 전시회·박람회 일정 (수동 관리)
├── docs/                    # GitHub Pages가 서비스하는 폴더 (대시보드)
│   ├── index.html
│   └── data/                # news.json / exhibitions.json 사본 (대시보드가 여기서 읽음)
├── .github/workflows/collect.yml   # 매일 자동 실행 설정
└── send_email.py            # 이메일 브리핑 발송
```

## 지금 상태로 할 수 있는 것 / 아직 안 되는 것

- 지금 되는 것: 네이버 뉴스 검색 API 수집, 메인/서브·카테고리 자동 분류, 자사/경쟁사 언급 집계, 대시보드 표시, 이메일 발송, 전시회 캘린더
- 아직 안 되는 것 (config.yaml에 `enabled: false`로 표시됨, 다음 단계에서 순차 추가): 빅카인즈, 화장품 전문지 RSS, 식약처 규제/의료기기/생산실적, 키프리스 특허, 해외 매체, 통계청 온라인쇼핑, 관세청 수출입
- 대시보드의 "데이터·트렌드" 3개 차트는 위 통계 소스가 아직 없어 "연동 예정"으로 표시됩니다. 실제 수치가 없는데 있는 것처럼 보여주지 않기 위한 것이니, 소스 연동이 끝나면 채워집니다.

## 처음 시작하는 순서

### 1. GitHub 계정 만들기
1. https://github.com/signup 접속
2. 이메일(gyumin_lee@wtlaser.com 등), 비밀번호, 사용자명 입력 후 가입
3. 이메일 인증 완료

### 2. 저장소 만들기
1. 로그인 후 우측 상단 `+` → `New repository`
2. Repository name: 예) `cosmetics-news-clipping`
3. `Private` 선택 (회사 관련 설정이 담기므로 비공개 권장)
4. `Create repository` 클릭

### 3. 이 폴더 업로드
가장 쉬운 방법 (git 명령어 없이):
1. 방금 만든 저장소 페이지에서 `Add file` → `Upload files`
2. 이 `cosmetics-news-clipping` 폴더 안의 모든 파일·폴더를 통째로 끌어다 놓기
   (`.github` 폴더처럼 점으로 시작하는 폴더도 반드시 포함해야 합니다)
3. `Commit changes` 클릭

### 4. 네이버 오픈API 키 발급
1. https://developers.naver.com 접속 → 로그인(네이버 계정) → `Application` → `애플리케이션 등록`
2. 애플리케이션 이름 자유 입력, 사용 API에서 `검색` 선택
3. 등록 후 발급되는 `Client ID`, `Client Secret` 확인 (무료, 일 25,000회 호출)

### 5. GitHub Secrets 등록 (API 키를 코드에 직접 쓰지 않고 안전하게 보관)
저장소 페이지 → `Settings` → 좌측 `Secrets and variables` → `Actions` → `New repository secret`
다음 4개를 각각 등록:
| Name | 값 |
|---|---|
| `NAVER_CLIENT_ID` | 4번에서 발급받은 Client ID |
| `NAVER_CLIENT_SECRET` | 4번에서 발급받은 Client Secret |
| `GMAIL_ADDRESS` | 이메일 발송에 쓸 Gmail 주소 (선택, 이메일 기능 쓸 때만) |
| `GMAIL_APP_PASSWORD` | 아래 6번 참고 (선택, 이메일 기능 쓸 때만) |

### 6. (선택) 이메일 발송을 쓰려면 — Gmail 앱 비밀번호 발급
1. 발신용 Gmail 계정에서 2단계 인증을 먼저 켜야 합니다 (myaccount.google.com/security)
2. https://myaccount.google.com/apppasswords 접속 → 앱 비밀번호 생성 (일반 로그인 비밀번호 아님)
3. 발급된 16자리 값을 `GMAIL_APP_PASSWORD` secret으로 등록
4. `config.yaml`에서 `email.enabled: true`로 바꾸고 `email.to`에 받는 사람 이메일 입력

### 7. config.yaml 채우기
`config.yaml`을 열어 `TODO`로 표시된 부분을 실제 값으로 수정:
- `brand.own`: 자사 브랜드명
- `brand.competitors`: 추적할 경쟁사명 목록
- `email.to`: 받는사람 이메일 (이메일 기능을 쓸 경우)

### 8. GitHub Pages 켜기 (대시보드 웹페이지 활성화)
1. 저장소 `Settings` → 좌측 `Pages`
2. `Source`: `Deploy from a branch` 선택
3. `Branch`: `main`, 폴더: `/docs` 선택 → `Save`
4. 몇 분 후 `https://<사용자명>.github.io/cosmetics-news-clipping/` 로 접속 가능

### 9. 자동 수집 켜기
1. 저장소 `Actions` 탭 → 처음 접속 시 `I understand my workflows, go ahead and enable them` 클릭
2. `화장품 뉴스 클리핑 수집` 워크플로 선택 → `Run workflow` 버튼으로 수동 실행해 정상 동작 확인
3. 이후 매일 한국시간 오전 7시 30분에 자동 실행됩니다 (`.github/workflows/collect.yml`에서 시간 변경 가능)

## 문제가 생기면
- Actions 탭에서 실행 로그를 열어보면 어느 단계에서 실패했는지 나옵니다 (네이버 API 키 오류, 이메일 인증 오류 등 메시지로 안내됩니다)
- 대시보드에 "아직 수집된 데이터가 없습니다"라고 뜨면 아직 Actions가 한 번도 성공적으로 실행되지 않은 것입니다

## 다음 단계 (로드맵)
1. 화장품 전문지(코스인·코스모닝·CMN·뷰티경제) RSS 확인 및 연동
2. 식약처 화장품 규제정보 / 의료기기 품목허가정보 API 연동
3. 특허청 키프리스(KIPRIS) 오픈API 연동
4. 통계청 온라인쇼핑동향조사, 관세청 수출입통계 연동 → 데이터·트렌드 차트 실제 데이터로 교체
5. 빅카인즈, 해외 매체(Global Cosmetics News, CosmeticsDesign 등) 연동
6. 자연어 기반 브리핑 요약 (현재는 단순 집계 기반 요약)
