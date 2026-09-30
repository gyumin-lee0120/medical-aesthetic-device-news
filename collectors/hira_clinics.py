import os
import json
import requests
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

API_URL = "https://apis.data.go.kr/B551182/hospInfoServicev2/getHospBasisList"
API_KEY = os.environ.get("HIRA_API_KEY")

OUT_FILES = [
    BASE / "data" / "market_metrics.json",
    BASE / "docs" / "data" / "market_metrics.json",
]

TARGET_SUBJECTS = {
    "피부과": "14",
    "성형외과": "08",
}


def fetch_hospitals(subject_code):
    page = 1
    rows = 100
    hospitals = {}

    while True:
        params = {
            "ServiceKey": API_KEY,
            "pageNo": page,
            "numOfRows": rows,
            "dgsbjtCd": subject_code,
        }

        r = requests.get(API_URL, params=params, timeout=30)
        r.raise_for_status()

        root = ET.fromstring(r.text)

        result_code = root.findtext("./header/resultCode")
        if result_code not in ("00", "0"):
            raise RuntimeError(
                f"HIRA API 오류: {result_code} "
                f"{root.findtext('./header/resultMsg')}"
            )

        total = int(root.findtext("./body/totalCount") or 0)
        items = root.findall("./body/items/item")

        for item in items:
            ykiho = item.findtext("ykiho") or item.findtext("YKIHO")
            name = item.findtext("yadmNm") or item.findtext("YADM_NM") or ""

            if ykiho:
                hospitals[ykiho] = name

        if page * rows >= total:
            break

        page += 1

    return hospitals


def run():
    if not API_KEY:
        raise RuntimeError("HIRA_API_KEY가 없습니다.")

    subject_hospitals = {}

    for name, code in TARGET_SUBJECTS.items():
        print(f"[수집] {name}")
        subject_hospitals[name] = fetch_hospitals(code)

    dermatology = subject_hospitals["피부과"]
    plastic = subject_hospitals["성형외과"]

    all_ids = set(dermatology) | set(plastic)
    overlap = set(dermatology) & set(plastic)

    total = len(all_ids)

    for path in OUT_FILES:
        data = json.loads(path.read_text(encoding="utf-8"))

        data["clinic"] = {
            "label": "피부과·성형외과 진료 의료기관 수",
            "unit": "개소",
            "latest_year": 2026,
            "latest_value": total,
            "source": "HIRA",
            "scope": "피부과·성형외과 진료과목 신고 의료기관, 요양기관 중복 제거",
            "detail": {
                "피부과": len(dermatology),
                "성형외과": len(plastic),
                "중복": len(overlap),
                "합계_중복제거": total
            },
            "history": [
                {
                    "year": 2026,
                    "value": total
                }
            ]
        }

        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    print(
        f"[완료] 피부과 {len(dermatology)}개소 / "
        f"성형외과 {len(plastic)}개소 / "
        f"중복 {len(overlap)}개소 / "
        f"중복 제거 합계 {total}개소"
    )


if __name__ == "__main__":
    run()