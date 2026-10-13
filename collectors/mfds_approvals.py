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

TARGET_PRODUCTS = {
    "RF": ["범용전기수술기"],
    "HIFU": ["집속형초음파자극시스템"],
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
    session = requests.Session()

    while True:
        params = {
            "serviceKey": API_KEY,
            "pageNo": page,
            "numOfRows": rows,
            "type": "xml",
            "prduct": product,
        }

        r = session.get(API_URL, params=params, timeout=(10, 60))
        r.raise_for_status()

        root = ET.fromstring(r.text)

        result_code = root.findtext("./header/resultCode")
        result_msg = root.findtext("./header/resultMsg")

        if result_code != "00":
            raise RuntimeError(
                f"MFDS API 오류: {result_code} {result_msg}"
            )

        total = int(root.findtext("./body/totalCount") or 0)

        print(f"[수집] {category} / {product} → totalCount={total}")

        # 필터가 또 무시되면 즉시 중단
        if total > 5000:
            raise RuntimeError(
                f"품목명 필터 미적용 의심: {product} totalCount={total}"
            )

        items = root.findall("./body/items/item")

        for item in items:
            raw = {
                child.tag: (child.text or "").strip()
                for child in list(item)
            }

            permit_date = (
                raw.get("PRMSN_YMD")
                or raw.get("PRMISN_DT")
                or raw.get("PRMISN_DE")
                or raw.get("PERMIT_DT")
                or ""
            )

            permit_no = (
                raw.get("PRODUCT_PRMISN_NO")
                or raw.get("PERMIT_NO")
                or raw.get("PRMISN_NO")
                or ""
            )

            year = permit_date[:4]

            if year.isdigit() and int(year) >= 2024:
                results.append({
                    "category": category,
                    "query_product": product,
                    "permit_date": permit_date,
                    "permit_no": permit_no,
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
            rows = fetch_product(category, product)
            all_rows.extend(rows)

    # 허가번호 중복 제거
    dedup = {}

    for row in all_rows:
        key = row["permit_no"] or (
            f"{row['category']}|"
            f"{row['product']}|"
            f"{row['permit_date']}|"
            f"{row['company']}"
        )
        dedup[key] = row

    rows = list(dedup.values())

    yearly = {
        "2024": {"RF": 0, "HIFU": 0, "LASER": 0},
        "2025": {"RF": 0, "HIFU": 0, "LASER": 0},
        "2026": {"RF": 0, "HIFU": 0, "LASER": 0},
    }

    for row in rows:
        year = row["permit_date"][:4]

        if year in yearly:
            yearly[year][row["category"]] += 1

    for year in yearly:
        yearly[year]["total_candidates"] = (
            yearly[year]["RF"]
            + yearly[year]["HIFU"]
            + yearly[year]["LASER"]
        )

    output = {
        "purpose": "에스테틱 RF/HIFU/Laser 최신 품목허가 후보",
        "period": "2024~현재",
        "source": "식품의약품안전처 의료기기 품목허가 정보",
        "yearly_candidates": yearly,
        "records": sorted(
            rows,
            key=lambda x: x["permit_date"],
            reverse=True,
        ),
    }

    for path in OUT_FILES:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(output, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print("[완료]")
    print(json.dumps(yearly, ensure_ascii=False))


if __name__ == "__main__":
    run()