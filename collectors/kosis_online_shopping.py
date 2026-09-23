"""통계청 온라인쇼핑동향조사 - 화장품 거래액 수집기.

KOSIS 공유서비스 오픈API에서 화장품(objL1=010) 합계(objL2=00, "계") 거래액(itmId=T20)을
월별로 가져와 data/trend_online_shopping.json 에 저장합니다.

확인된 값 (2026.07 기준 실제 응답으로 검증됨):
  tblId=DT_1KE10071 (온라인쇼핑동향조사, orgId=101 통계청)
  objL1=010 -> C1_NM: "화장품"
  objL2=00  -> C2_NM: "계" (합계, 모바일+인터넷쇼핑 전체)
  itmId=T20 -> ITM_NM: "거래액" (단위: 백만원)

필요 환경변수:
  KOSIS_API_KEY
(kosis.kr/openapi 에서 회원가입 후 활용신청 메뉴에서 발급)
"""
import os
import sys
from datetime import datetime

import requests

from utils import BASE_DIR

API_URL = "https://kosis.kr/openapi/Param/statisticsParameterData.do"
TREND_PATH = os.path.join(BASE_DIR, "data", "trend_online_shopping.json")
DOCS_TREND_PATH = os.path.join(BASE_DIR, "docs", "data", "trend_online_shopping.json")

MONTHS_BACK = 24  # 최근 24개월치 조회


def month_offset(yyyymm, offset):
    """"YYYYMM" 문자열에서 offset개월 전/후 계산."""
    y, m = int(yyyymm[:4]), int(yyyymm[4:])
    total = y * 12 + (m - 1) + offset
    return f"{total // 12}{(total % 12) + 1:02d}"

def run():
    api_key = os.environ.get("KOSIS_API_KEY")
    if not api_key:
        print(
            "[오류] KOSIS_API_KEY 환경변수가 없습니다.\n"
            "README의 'KOSIS 온라인쇼핑동향조사 연동' 안내를 참고해 발급받고,\n"
            "GitHub 저장소 Settings > Secrets and variables > Actions 에 등록하세요.",
            file=sys.stderr,
        )
        sys.exit(1)

    end_prd = datetime.now().strftime("%Y%m")
    start_prd = month_offset(end_prd, -(MONTHS_BACK - 1))

    from urllib.parse import quote
    encoded_key = quote(api_key, safe="")

    url = (
        f"{API_URL}?method=getList&apiKey={encoded_key}"
        f"&itmId=T20+&objL1=010+&objL2=00+&format=json&jsonVD=Y&prdSe=M"
        f"&startPrdDe={start_prd}&endPrdDe={end_prd}&outputFields=PRD_DE+"
        f"&orgId=101&tblId=DT_1KE10071"
    )

    import time
    resp = None
    last_error = None
    for attempt in range(3):
        try:
            resp = requests.get(url, timeout=30)
            break
        except requests.exceptions.RequestException as e:
            last_error = e
            print(f"[재시도 {attempt + 1}/3] 연결 실패: {e}", file=sys.stderr)
            time.sleep(5)

    if resp is None:
        print(
            f"[오류] KOSIS API 연결 3회 시도 모두 실패: {last_error}\n"
            "타임아웃이 아니라 접속 자체가 막히는 경우, GitHub Actions 서버(해외 IP)를\n"
            "KOSIS가 차단하고 있을 가능성이 있습니다. 이 경우 자동 수집 대신\n"
            "수동 갱신 방식 전환이 필요할 수 있습니다.",
            file=sys.stderr,
        )
        sys.exit(1)

    if resp.status_code != 200:
        print(f"[오류] KOSIS API 요청 실패: {resp.status_code} {resp.text[:300]}", file=sys.stderr)
        sys.exit(1)

    data = resp.json()
    print(f"[디버그] 응답 원문: {str(data)[:500]}", file=sys.stderr)
    if isinstance(data, dict):
        print(f"[오류] KOSIS API 응답 이상: {data}", file=sys.stderr)
        sys.exit(1)

    points = []
    for row in data:
        try:
            points.append({
                "period": f"{row['PRD_DE'][:4]}-{row['PRD_DE'][4:]}",
                "value_million_krw": int(row["DT"]),
            })
        except (KeyError, ValueError):
            continue

    points.sort(key=lambda p: p["period"])

    import json
    os.makedirs(os.path.dirname(TREND_PATH), exist_ok=True)
    with open(TREND_PATH, "w", encoding="utf-8") as f:
        json.dump(points, f, ensure_ascii=False, indent=2)
    os.makedirs(os.path.dirname(DOCS_TREND_PATH), exist_ok=True)
    with open(DOCS_TREND_PATH, "w", encoding="utf-8") as f:
        json.dump(points, f, ensure_ascii=False, indent=2)

    print(f"완료: 화장품 온라인쇼핑 거래액 {len(points)}개월치 저장 (data/trend_online_shopping.json)")

if __name__ == "__main__":
    run()
