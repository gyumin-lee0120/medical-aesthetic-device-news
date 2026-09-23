"""네이버 뉴스 검색 오픈API 수집기.

config.yaml의 topics.main + topics.sub 키워드로 검색해
제목/요약/링크/출처/발행시각을 수집하고, 메인/서브 주제 및 카테고리를 태깅합니다.

필요 환경변수:
  NAVER_CLIENT_ID
  NAVER_CLIENT_SECRET
(네이버 개발자센터 https://developers.naver.com 에서 애플리케이션 등록 후 발급)
"""
import os
import sys
import time

import requests

from utils import (
    classify_categories,
    classify_topic,
    find_brand_mentions,
    load_config,
    save_news,
    strip_html,
)

API_URL = "https://openapi.naver.com/v1/search/news.json"


def fetch_keyword(keyword, client_id, client_secret, display, max_pages):
    """키워드 하나에 대해 최대 max_pages 페이지(페이지당 display건)를 수집."""
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    results = []
    for page in range(max_pages):
        start = 1 + page * display
        if start > 1000:  # 네이버 API 제약: start 최대 1000
            break
        params = {"query": keyword, "display": display, "start": start, "sort": "date"}
        resp = requests.get(API_URL, headers=headers, params=params, timeout=10)
        if resp.status_code != 200:
            print(f"  [경고] '{keyword}' 요청 실패 (page {page}): {resp.status_code} {resp.text[:200]}", file=sys.stderr)
            break
        items = resp.json().get("items", [])
        if not items:
            break
        results.extend(items)
        time.sleep(0.1)  # 초당 호출 제한 여유
    return results


def run():
    cfg = load_config()
    src_cfg = cfg["sources"]["naver_news"]
    if not src_cfg.get("enabled", False):
        print("naver_news 소스가 비활성화되어 있습니다 (config.yaml sources.naver_news.enabled: false).")
        return

    client_id = os.environ.get("NAVER_CLIENT_ID")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        print(
            "[오류] NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수가 없습니다.\n"
            "README의 '네이버 오픈API 키 발급' 안내를 참고해 발급받고,\n"
            "GitHub 저장소 Settings > Secrets and variables > Actions 에 등록하세요.",
            file=sys.stderr,
        )
        sys.exit(1)

    keywords = list(dict.fromkeys(cfg["topics"]["main"] + cfg["topics"]["sub"]))
    display = src_cfg.get("display", 100)
    max_pages = src_cfg.get("max_pages", 2)

    collected = {}
    for kw in keywords:
        print(f"수집 중: {kw}")
        raw_items = fetch_keyword(kw, client_id, client_secret, display, max_pages)
        for raw in raw_items:
            title = strip_html(raw["title"])
            description = strip_html(raw["description"])
            link = raw["link"] or raw["originallink"]
            combined_text = f"{title} {description}"

            # 네이버 검색은 완전 무관한 기사를 섞어서 반환할 때가 있습니다
            # (예: 검색어 "메이크업"으로 모기 물림 기사가 나오는 경우).
            # 실제로 검색 키워드가 제목/요약에 존재하는 기사만 채택합니다.
            if kw.lower() not in combined_text.lower():
                continue

            own_hits, competitor_hits = find_brand_mentions(combined_text, cfg)

            item = {
                "title": title,
                "summary": description,
                "link": link,
                "source": "네이버 뉴스",
                "pub_date": raw.get("pubDate", ""),
                "matched_keyword": kw,
                "topic": classify_topic(combined_text, cfg),
                "categories": classify_categories(combined_text, cfg),
                "own_brand_mentions": own_hits,
                "competitor_mentions": competitor_hits,
                "is_overseas": False,
            }
            collected[link] = item  # link 기준 1차 중복 제거

    merged = save_news(list(collected.values()))
    print(f"완료: 이번 실행 {len(collected)}건 수집, 누적 저장 {len(merged)}건 (data/news.json, docs/data/news.json)")


if __name__ == "__main__":
    run()
