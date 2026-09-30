import os
import json
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).resolve().parents[1]

API_URL = (
    "https://apis.data.go.kr/1471000/"
    "MdlpPrdlstPrmisnInfoService06/"
    "getMdlpPrdlstPrmisnList05"
)

API_KEY = os.environ.get("MFDS_API_KEY")

# 에스테틱 장비 관련 식약처 품목명
TARGET_PRODUCTS = [
    "범용전기수술기",
    "집속형초음파자극시스템",
    "레이저수술기",
    "엔디야그레이저수술기",
]

OUT_FILES = [
    BASE / "data" / "market_metrics.json",
    BASE / "docs" / "data" / "market_metrics.json",
]


def fetch_product(product):
    page = 1
    rows = 100
    results = []

    while True:
        params = {
            "serviceKey": API_KEY,
            "pageNo": page,
            "numOfRows": rows,
            "type": "xml",
            "prduct": product,
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
            results.append({
                "product": item.findtext("PRDUCT") or "",
                "permit_no": item.findtext("PRODUCT_PRMISN_NO") or "",
                "permit_date": item.findtext("PRMISN_DT") or "",
            })

        if page * rows >= total:
            break

        page += 1

    return results


def run():
    if not API_KEY:
        raise RuntimeError("MFDS_API_KEY가 없습니다.")

    # 허가번호 기준 중복 제거
    permits = {}

    for product in TARGET_PRODUCTS:
        print(f"[수집] {product}")
        for item in fetch_product(product):
            key = item["permit_no"]

            if not key:
                key = f"{item['product']}-{item['permit_date']}"

            permits[key] = item

    yearly = defaultdict(int)

    for item in permits.values():
        date = item["permit_date"]

        if len(date) >= 4 and date[:4].isdigit():
            yearly[int(date[:4])] += 1

    history = [
        {"year": year, "value": yearly[year]}
        for year in sorted(yearly)
    ]

    if not history:
        raise RuntimeError("집계 가능한 인허가 데이터가 없습니다.")

    latest = history[-1]

    for path in OUT_FILES:
        data = json.loads(path.read_text(encoding="utf-8"))

        data["approval"] = {
            "label": "에스테틱 의료기기 인허가 추이",
            "unit": "건",
            "latest_year": latest["year"],
            "latest_value": latest["value"],
            "source": "식약처",
            "scope": "범용전기수술기·집속형초음파자극시스템·레이저수술기·엔디야그레이저수술기",
            "history": history,
        }

        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print(f"[완료] 총 {len(permits)}건 / 최신 {latest['year']}년 {latest['value']}건")


if __name__ == "__main__":
    run()