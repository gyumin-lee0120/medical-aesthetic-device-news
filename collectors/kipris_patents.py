import json
import os
import time
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict
import yaml

BASE = Path(__file__).resolve().parents[1]

CFG = yaml.safe_load(
    (BASE / "config.yaml").read_text(encoding="utf-8")
)

API_URL = (
    "https://plus.kipris.or.kr/kipo-api/kipi/"
    "patUtiModInfoSearchSevice/getWordSearch"
)

OUTS = [
    BASE / "data" / "patent_trend.json",
    BASE / "docs" / "data" / "patent_trend.json",
]


def fetch_keyword(keyword, api_key):
    page = 1
    rows = 500
    results = []

    while True:
        # ServiceKey를 마지막에 보내도록 순서 유지
        params = [
            ("word", keyword),
            ("year", 10),
            ("patent", "true"),
            ("utility", "false"),
            ("numOfRows", rows),
            ("pageNo", page),
            ("ServiceKey", api_key),
        ]

        r = requests.get(API_URL, params=params, timeout=60)
        r.raise_for_status()

        root = ET.fromstring(r.text)

        result_code = root.findtext(".//resultCode")
        if result_code and result_code not in ("00", "0"):
            raise RuntimeError(
                f"KIPRIS API 오류: {result_code} "
                f"{root.findtext('.//resultMsg')}"
            )

        items = root.findall(".//items/item")

        for item in items:
            results.append({
                "applicationNumber":
                    item.findtext("applicationNumber") or "",
                "applicationDate":
                    item.findtext("applicationDate") or "",
                "title":
                    item.findtext("inventionTitle") or "",
            })

        total = int(root.findtext(".//count/totalCount") or 0)

        if page * rows >= total:
            break

        page += 1
        time.sleep(0.25)

    return results


def run():
    src = CFG.get("sources", {}).get("kipris_patents", {})

    if not src.get("enabled", False):
        print("KIPRIS 특허 수집 비활성화")
        return

    api_key = os.environ.get("KIPRIS_API_KEY")

    if not api_key:
        raise RuntimeError("KIPRIS_API_KEY가 없습니다.")

    keywords = src.get("keywords", [])

    if not keywords:
        raise RuntimeError("config.yaml에 특허 검색 키워드가 없습니다.")

    # 출원번호 기준 중복 제거
    patents = {}

    for keyword in keywords:
        print(f"[수집] {keyword}")

        rows = fetch_keyword(keyword, api_key)

        for item in rows:
            app_no = item["applicationNumber"]

            if app_no:
                patents[app_no] = item

        time.sleep(0.4)

    yearly = defaultdict(int)

    for item in patents.values():
        dt = item["applicationDate"]

        if len(dt) >= 4 and dt[:4].isdigit():
            year = int(dt[:4])

            if 2021 <= year <= 2026:
                yearly[year] += 1

    output = [
        {
            "year": year,
            "count": yearly.get(year, 0)
        }
        for year in range(2021, 2027)
    ]

    for path in OUTS:
        path.write_text(
            json.dumps(output, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    print(f"[완료] 중복 제거 특허 {len(patents)}건")
    print(output)


if __name__ == "__main__":
    run()