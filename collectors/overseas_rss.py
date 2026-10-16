"""해외 뉴스 수집기 (Google News RSS 검색).

config.yaml > sources.overseas_rss.google_news 의 영문 검색식으로 최근 기사를 가져옵니다.
- 별도 API 키가 필요 없습니다.
- 관련도 필터(config.yaml > relevance)를 통과한 기사만 저장됩니다.
- 기존 feeds(일반 RSS 주소) 설정도 그대로 지원합니다.
"""
import re
import time
from urllib.parse import quote

import feedparser
from utils import is_relevant, load_config, retag, save_news, strip_html

GOOGLE_NEWS = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def clean_title(title, publisher):
    # Google News 제목 끝의 " - 매체명" 제거
    if publisher and title.endswith(f" - {publisher}"):
        return title[: -len(f" - {publisher}")].strip()
    return re.sub(r"\s+-\s+[^-]{2,60}$", "", title).strip()


def collect(url, label, cfg, limit=60):
    d = feedparser.parse(url)
    out = []
    for e in d.entries[:limit]:
        publisher = ""
        if e.get("source"):
            publisher = e.source.get("title", "") if hasattr(e.source, "get") else ""
        title = clean_title(strip_html(e.get("title", "")), publisher)
        summary = strip_html(e.get("summary", ""))
        if publisher and summary.endswith(publisher):
            summary = summary[: -len(publisher)].strip()
        link = e.get("link")
        if not title or not link:
            continue
        if not is_relevant(f"{title} {summary}", cfg):
            continue
        item = {
            "title": title,
            "summary": summary if summary != title else "",
            "link": link,
            "source": publisher or label,
            "pub_date": e.get("published") or e.get("updated") or "",
            "matched_keyword": label,
            "is_overseas": True,
        }
        out.append(retag(item, cfg))
    return out


def run():
    cfg = load_config()
    src = cfg.get("sources", {}).get("overseas_rss", {})
    if not src.get("enabled", False):
        print("overseas_rss 비활성화")
        return

    items = {}
    for q in src.get("google_news", []):
        url = GOOGLE_NEWS.format(q=quote(q["query"]))
        got = collect(url, f"해외: {q.get('name', '')}", cfg)
        print(f"Google News [{q.get('name')}]: {len(got)}건")
        for it in got:
            items[it["link"]] = it
        time.sleep(1)

    for feed in src.get("feeds", []) or []:
        got = collect(feed["url"], feed.get("name", "해외 RSS"), cfg)
        print(f"RSS [{feed.get('name')}]: {len(got)}건")
        for it in got:
            items[it["link"]] = it

    # 같은 기사가 여러 매체로 중복되면 제목 기준으로 1건만
    by_title = {}
    for it in items.values():
        by_title.setdefault(it["title"].lower(), it)

    merged = save_news(list(by_title.values()))
    print(f"완료: 해외 {len(by_title)}건 / 누적 {len(merged)}건")


if __name__ == "__main__":
    run()
