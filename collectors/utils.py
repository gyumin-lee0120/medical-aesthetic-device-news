"""공용 유틸리티: 설정 로드, 주제/카테고리 분류, 중복 제거, JSON 저장."""
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

# 뉴스 보관 기간 (일). 이보다 오래된 기사는 저장소 용량을 위해 정리합니다.
RETENTION_DAYS = 90


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def strip_html(text):
    """네이버 API가 <b>태그</b>로 감싸서 주는 검색어 강조 표시 제거."""
    text = re.sub(r"<.*?>", "", text or "")
    return html.unescape(text).strip()


def classify_topic(text, cfg):
    """본문(제목+요약)에 main/sub 키워드가 있는지로 메인/서브 주제 분류. main 우선."""
    lowered = text.lower()
    for kw in cfg["topics"]["main"]:
        if kw.lower() in lowered:
            return "main"
    for kw in cfg["topics"]["sub"]:
        if kw.lower() in lowered:
            return "sub"
    return "sub"  # 메인 키워드가 전혀 없으면 서브로 분류 (보수적 기본값)


def classify_categories(text, cfg):
    """매칭되는 모든 카테고리를 리스트로 반환 (다중 태그 가능)."""
    lowered = text.lower()
    matched = []
    for cat, keywords in cfg["categories"].items():
        if any(kw.lower() in lowered for kw in keywords):
            matched.append(cat)
    return matched or ["미분류"]


def find_brand_mentions(text, cfg):
    """자사/경쟁사 언급 여부 판정. TODO 값이 남아있으면 빈 리스트 반환."""
    lowered = text.lower()
    own_hits = [b for b in cfg["brand"]["own"] if not b.startswith("TODO") and b.lower() in lowered]
    competitor_hits = [c for c in cfg["brand"]["competitors"] if not c.startswith("TODO") and c.lower() in lowered]
    return own_hits, competitor_hits


def load_existing():
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_news(items):
    """기존 데이터와 병합, link 기준 중복 제거 후 저장. docs/data에도 복사."""
    existing = load_existing()
    by_link = {item["link"]: item for item in existing}
    for item in items:
        by_link[item["link"]] = item  # 새 데이터로 덮어쓰기 (최신 정보 유지)

    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)

    def is_recent(item):
        try:
            return parsedate_to_datetime(item["pub_date"]) >= cutoff
        except (KeyError, TypeError, ValueError):
            return True  # 날짜 파싱 실패 시 보수적으로 유지

    merged = sorted(
        (v for v in by_link.values() if is_recent(v)),
        key=lambda x: x.get("pub_date", ""),
        reverse=True,
    )

    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    os.makedirs(os.path.dirname(DOCS_DATA_PATH), exist_ok=True)
    with open(DOCS_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    return merged
