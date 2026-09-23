# WONTECH Medical Aesthetic Device News

기존 Cosmetics News Clipping 구조를 기반으로 만든 의료·에스테틱 장비 내부용 뉴스클리핑 V1입니다.

## V1 기능
- 네이버 뉴스 평일 자동 수집
- WONTECH / 자사 제품 언급 분류
- 주요 경쟁사 / 경쟁제품 언급 분류
- RF / HIFU / Laser·Pico / RF Microneedling / Surgical / 인허가 / 학회·임상 등 태깅
- 전체 시장 / WONTECH / 주요 경쟁사별 대시보드
- 경쟁제품 Quick Filter
- 뉴스 모멘텀 / 경쟁사 언급 / 기술군 구성 지표
- 학회·전시회 캘린더
- Telegram Daily Brief 발송 모듈 (설정 전까지 비활성)

## 자동 실행
`.github/workflows/collect.yml`
- KST 월~금 오전 7:30 자동 실행
- 뉴스 수집 → JSON 갱신/Push → Telegram 브리핑 순서

## 필요한 GitHub Secrets
새 저장소의 `Settings > Secrets and variables > Actions`에서 등록합니다.

- `NAVER_CLIENT_ID`
- `NAVER_CLIENT_SECRET`
- `TELEGRAM_BOT_TOKEN` (Telegram 연결 시)
- `TELEGRAM_CHAT_ID` (Telegram 연결 시)

## Telegram
초기에는 `config.yaml`의 `telegram.enabled: false`입니다.
Bot과 국내영업용 Telegram 방을 만든 뒤 두 Secret을 등록하고 `true`로 변경합니다.

## GitHub Pages
`Settings > Pages > Deploy from a branch > main /docs`로 설정합니다.
예상 URL:
`https://gyumin-lee0120.github.io/medical-aesthetic-device-news/`

## V2 후보
- 해외 전문매체 / 경쟁사 Newsroom 자동수집
- MFDS / FDA / NMPA 인허가 지표
- 수출입·시장 규모 등 외부 정량지표
- AI 자연어 주간 인사이트
- 카카오톡 채널 또는 WONTECH Aesthetic Weekly 연동
