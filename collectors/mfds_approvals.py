import os
import json
import requests
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

API_URL = (
    "https://apis.data.go.kr/1471000/"
    "MdeqStdCdPrdtInfoService03/"
    "getMdeqStdCdPrdtInfoInq03"
)

API_KEY = os.environ.get("MFDS_API_KEY")

# 식약처 공식 품목명 기준
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


def pick(raw, *keys):
    for key in keys:
        value = raw.get(key, "")
        if value:
            return value
    return ""


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

            # 공식 명세의 품목명 요청변수
            "PRDLST_NM": product,
        }

        r = session.get(
            API_URL,
            params=params,
            timeout=(10, 60),
        )
        r.raise_for_status()

        root = ET.fromstring(r.text)

        result_code = root.findtext("./header/resultCode")

        if result_code != "00":
            raise RuntimeError(
                f"MFDS API 오류: {result_code} "
                f"{root.findtext('./header/resultMsg')}"
            )

        total = int(root.findtext("./body/totalCount") or 0)

        print(
            f"[수집] {category} / {product} "
            f"→ totalCount={total}"
        )

        # 품목 필터가 안 먹는 경우 즉시 중단
        if total > 10000:
            raise RuntimeError(
                f"품목 필터가 적용되지 않은 것으로 보입니다. "
                f"{product} totalCount={total}"
            )

        items = root.findall("./body/items/item")

        for item in items:
            raw = {}

            for child in list(item):
                raw[child.tag] = (child.text or "").strip()

            permit_no = pick(
                raw,
                "PERMIT_NO",
                "PRMISN_NO",
                "PRODUCT_PRMISN_NO",
            )

            permit_date = pick(
                raw,
                "PERMIT_DT",
                "PRMISN_DT",
                "PRMSN_YMD",
                "PRMSN_DT",
            )

            product_name = pick(
                raw,
                "PRDLST_NM",
                "PRDUCT",
            )

            class_no = pick(
                raw,
                "MDEQ_CLSF_NO",
                "CLSF_NO",
            )

            company = pick(
                raw,
                "MNET_IPRT_ENTP_NM",
                "ENTRPS",
            )

            use_purpose = pick(
                raw,
                "USE_PURPS",
                "USE_PURPOSE",
                "USE_MTH",
            )

            results.append({
                "category": category,
                "query_product": product,
                "product": product_name,
                "class_no": class_no,
                "permit_no": permit_no,
                "permit_date": permit_date,
                "company": company,
                "use_purpose": use_purpose,
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

    # 동일 허가번호/UDI 제품 중복 정리
    dedup = {}

    for row in all_rows:
        key = row["permit_no"]

        if not key:
            key = (
                f"{row['category']}|"
                f"{row['product']}|"
                f"{row['class_no']}|"
                f"{row['company']}|"
                f"{row['permit_date']}"
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
        "purpose": "에스테틱 RF/HIFU/Laser 허가 범위 검증",
        "source": "식품의약품안전처 의료기기 표준코드별 제품정보",
        "candidate_summary": summary,
        "records": rows,
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