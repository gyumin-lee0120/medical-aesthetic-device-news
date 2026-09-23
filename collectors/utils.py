"""공용 유틸리티: 설정 로드, 카테고리/회사/제품 분류, 중복 제거, JSON 저장."""
import html
import json
import os
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import yaml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")
DATA_PATH = os.path.join(BASE_DIR, "data", "news.json")
DOCS_DATA_PATH = os.path.join(BASE_DIR, "docs", "data", "news.json")
RETENTION_DAYS = 120


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def strip_html(text):
    text = re.sub(r"<.*?>", "", text or "")
    return html.unescape(text).strip()


def classify_categories(text, cfg):
    lowered = text.lower()
    matched = []
    for cat, keywords in cfg.get("categories", {}).items():
        if any(kw.lower() in lowered for kw in keywords):
            matched.append(cat)
    return matched or ["기타"]


def _hits(text, values):
    lowered = text.lower()
    return [v for v in values if v and not v.startswith("TODO") and v.lower() in lowered]


def find_mentions(text, cfg):
    brand = cfg.get("brand", {})
    return {
        "own_company_mentions": _hits(text, brand.get("own_company", [])),
        "own_product_mentions": _hits(text, brand.get("own_products", [])),
        "competitor_company_mentions": _hits(text, brand.get("competitor_companies", [])),
        "competitor_product_mentions": _hits(text, brand.get("competitor_products", [])),
    }


def load_existing():
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_news(items):
    existing = load_existing()
    by_link = {item["link"]: item for item in existing}
    for item in items:
        by_link[item["link"]] = item

    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)

    def is_recent(item):
        try:
            return parsedate_to_datetime(item["pub_date"]) >= cutoff
        except (KeyError, TypeError, ValueError):
            return True

    merged = sorted(
        (v for v in by_link.values() if is_recent(v)),
        key=lambda x: x.get("pub_date", ""),
        reverse=True,
    )

    for path in (DATA_PATH, DOCS_DATA_PATH):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
    return merged
