import os
import json
import requests
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

API_URL = (
    "https://apis.data.go.kr/1471000/"
    "MdlpPrdlstPrmisnInfoService06/"
    "getMdlpPrdlstPrmisnList05"
)

API_KEY = os.environ.get("MFDS_API_KEY")

# 식약처 공식 품목명 기준 후보군
TARGET_PRODUCTS = {
    "RF": [
        "범용전기수술기",
    ],
    "HIFU": [
        "집속형초음파자극시스템",
    ],
    "LASER": [
        "레이저수술기",
        "엔디야그레이저수술기",
        "탄산가스레이저수술기",
    ],
}

OUT_FILES = [
    BASE / "data" / "mfds_aesthetic_candidates.json",
    BASE / "docs" / "data" / "mfds_aesthetic_candidates.json",
]


def fetch_product(category, product):
    page = 1
    rows = 100
    results = []

    while True:
        params = {
            "serviceKey": API_KEY,
            "pageNo": page,
            "numOfRows": rows,
            "type": "xml",
            "PRDUCT": product,
        }

        r = requests.get(API_URL, params=params, timeout=30)
        r.raise_for_status()

        root = ET.fromstring(r.text)

        result_code = root.findtext("./header/resultCode")
        if result_code != "00":
            raise RuntimeError(
                f"MFDS API 오류: {result_code} "
                f"{root.findtext('./header/resultMsg')}"
            )

        total = int(root.findtext("./body/totalCount") or 0)
        items = root.findall("./body/items/item")

        for item in items:
            # 응답 필드를 전부 보존
            raw = {}

            for child in list(item):
                raw[child.tag] = (child.text or "").strip()

            permit_date = raw.get("PRMISN_DT", "")

            # 지금 필요한 최신 구간만 저장
            if (
                len(permit_date) >= 4
                and permit_date[:4].isdigit()
                and int(permit_date[:4]) >= 2024
            ):
                results.append({
                    "category": category,
                    "query_product": product,
                    "permit_date": permit_date,
                    "permit_no": raw.get("PRODUCT_PRMISN_NO", ""),
                    "product": raw.get("PRDUCT", ""),
                    "company": raw.get("ENTRPS", ""),
                    "raw": raw,
                })

        if page * rows >= total:
            break

        page += 1

    return results


def run():
    if not API_KEY:
        raise RuntimeError("MFDS_API_KEY가 없습니다.")

    all_rows = []

    for category, products in TARGET_PRODUCTS.items():
        for product in products:
            print(f"[수집] {category} / {product}")

            rows = fetch_product(category, product)
            all_rows.extend(rows)

            print(f"  → 2024년 이후 {len(rows)}건")

    # 허가번호 기준 중복 제거
    dedup = {}

    for row in all_rows:
        key = row["permit_no"]

        if not key:
            key = (
                f"{row['category']}-"
                f"{row['product']}-"
                f"{row['permit_date']}-"
                f"{row['company']}"
            )

        dedup[key] = row

    rows = list(dedup.values())

    summary = {
        "RF": 0,
        "HIFU": 0,
        "LASER": 0,
    }

    for row in rows:
        summary[row["category"]] += 1

    output = {
        "purpose": "에스테틱 RF/HIFU/Laser 허가 범위 검증용",
        "period": "2024~현재",
        "source": "식품의약품안전처 의료기기 품목허가 정보",
        "candidate_summary": summary,
        "records": sorted(
            rows,
            key=lambda x: x["permit_date"],
            reverse=True,
        ),
    }

    for path in OUT_FILES:
        path.parent.mkdir(parents=True, exist_ok=True)

        path.write_text(
            json.dumps(
                output,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    print("[완료]")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    run()