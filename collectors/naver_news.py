"""원텍 Medical Aesthetic Device News - 네이버 뉴스 수집기."""
import os
import sys
import time

import requests

from utils import classify_categories, find_mentions, load_config, save_news, strip_html

API_URL = "https://openapi.naver.com/v1/search/news.json"


def fetch_keyword(keyword, client_id, client_secret, display, max_pages):
    headers = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
    results = []
    for page in range(max_pages):
        start = 1 + page * display
        if start > 1000:
            break
        params = {"query": keyword, "display": display, "start": start, "sort": "date"}
        resp = requests.get(API_URL, headers=headers, params=params, timeout=15)
        if resp.status_code != 200:
            print(f"[경고] '{keyword}' 요청 실패: {resp.status_code} {resp.text[:200]}", file=sys.stderr)
            break
        items = resp.json().get("items", [])
        if not items:
            break
        results.extend(items)
        time.sleep(0.1)
    return results


def run():
    cfg = load_config()
    src_cfg = cfg["sources"]["naver_news"]
    if not src_cfg.get("enabled", False):
        print("naver_news 비활성화")
        return

    client_id = os.environ.get("NAVER_CLIENT_ID")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("[오류] NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수가 없습니다.", file=sys.stderr)
        sys.exit(1)

    keywords = list(dict.fromkeys(cfg.get("search_keywords", [])))
    display = src_cfg.get("display", 100)
    max_pages = src_cfg.get("max_pages", 2)

    collected = {}
    for kw in keywords:
        print(f"수집 중: {kw}")
        for raw in fetch_keyword(kw, client_id, client_secret, display, max_pages):
            title = strip_html(raw.get("title", ""))
            description = strip_html(raw.get("description", ""))
            link = raw.get("originallink") or raw.get("link")
            if not link:
                continue
            combined = f"{title} {description}"
            if kw.lower() not in combined.lower():
                continue

            mentions = find_mentions(combined, cfg)
            item = {
                "title": title,
                "summary": description,
                "link": link,
                "source": "네이버 뉴스",
                "pub_date": raw.get("pubDate", ""),
                "matched_keyword": kw,
                "categories": classify_categories(combined, cfg),
                "is_overseas": False,
                **mentions,
            }
            # 기존 대시보드/후속 코드 호환용 필드
            item["own_brand_mentions"] = mentions["own_company_mentions"] + mentions["own_product_mentions"]
            item["competitor_mentions"] = mentions["competitor_company_mentions"] + mentions["competitor_product_mentions"]
            collected[link] = item

    merged = save_news(list(collected.values()))
    print(f"완료: 이번 실행 {len(collected)}건 / 누적 {len(merged)}건")


if __name__ == "__main__":
    run()
