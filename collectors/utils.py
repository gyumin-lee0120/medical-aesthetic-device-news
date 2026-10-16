"""공용 유틸리티: 설정 로드, 카테고리/영역/회사/제품 분류, 중복 제거, JSON 저장."""
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


def classify_segments(text, cfg):
    lowered = text.lower()
    matched = []
    for seg, keywords in cfg.get("segments", {}).items():
        if any(kw.lower() in lowered for kw in keywords):
            matched.append(seg)
    return matched or ["에스테틱"]


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


def is_relevant(text, cfg):
    """관련도 필터: 주제어가 하나 이상 있고, 제외어가 없어야 통과."""
    rel = cfg.get("relevance", {})
    lowered = (text or "").lower()
    excludes = [t.lower() for t in rel.get("exclude_terms", []) if t]
    if any(t in lowered for t in excludes):
        return False
    contexts = [t.lower() for t in rel.get("context_terms", []) if t]
    if contexts and not any(t in lowered for t in contexts):
        return False
    return True


def retag(item, cfg):
    """현재 config 기준으로 카테고리·영역·언급 정보를 다시 계산 (기존 누적 기사 포함)."""
    text = f"{item.get('title', '')} {item.get('summary', '')}"
    mentions = find_mentions(text, cfg)
    item.update(mentions)
    item["categories"] = classify_categories(text, cfg)
    item["segments"] = classify_segments(text, cfg)
    item["own_brand_mentions"] = mentions["own_company_mentions"] + mentions["own_product_mentions"]
    item["competitor_mentions"] = mentions["competitor_company_mentions"] + mentions["competitor_product_mentions"]
    return item


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

    cfg = load_config()

    def sort_key(item):
        try:
            dt = parsedate_to_datetime(item.get("pub_date", ""))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            return datetime(1970, 1, 1, tzinfo=timezone.utc)

    # 기간 내 + 관련도 통과 기사만 남기고, 최신 기준으로 태그 재계산
    merged = sorted(
        (retag(v, cfg) for v in by_link.values()
         if is_recent(v) and is_relevant(f"{v.get('title', '')} {v.get('summary', '')}", cfg)),
        key=sort_key,
        reverse=True,
    )

    for path in (DATA_PATH, DOCS_DATA_PATH):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
    return merged
