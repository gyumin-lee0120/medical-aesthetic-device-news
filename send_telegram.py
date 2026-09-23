"""평일 아침 Medical Aesthetic Device Daily Brief를 Telegram으로 전송합니다.

필요 GitHub Secrets:
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHAT_ID
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import requests

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "collectors"))
from utils import load_config, load_existing  # noqa: E402


def recent(item, hours=24):
    try:
        return parsedate_to_datetime(item["pub_date"]) >= datetime.now(timezone.utc) - timedelta(hours=hours)
    except (KeyError, TypeError, ValueError):
        return False


def score(item):
    s = 0
    if item.get("own_brand_mentions"):
        s += 5
    if item.get("competitor_mentions"):
        s += 3
    cats = set(item.get("categories", []))
    s += 3 * bool(cats & {"인허가·규제", "신제품·출시"})
    s += 2 * bool(cats & {"학회·임상", "글로벌사업"})
    return s


def build_message(items, cfg):
    tg = cfg.get("telegram", {})
    max_items = int(tg.get("max_items", 8))
    dashboard = tg.get("dashboard_url", "")
    items = sorted(items, key=lambda x: (score(x), x.get("pub_date", "")), reverse=True)[:max_items]

    today = datetime.now().strftime("%Y.%m.%d")
    lines = [f"WONTECH Medical Aesthetic Device Daily Brief | {today}", ""]
    if not items:
        lines.append("최근 24시간 내 수집된 주요 뉴스가 없습니다.")
    else:
        lines.append(f"오늘 주요 뉴스 {len(items)}건")
        lines.append("")
        for idx, item in enumerate(items, 1):
            cats = "/".join(item.get("categories", [])[:2]) or "시장"
            lines.append(f"{idx}. [{cats}] {item['title']}")
            lines.append(item["link"])
    if dashboard:
        lines.extend(["", f"대시보드 보기: {dashboard}"])
    return "\n".join(lines)


def run():
    cfg = load_config()
    tg = cfg.get("telegram", {})
    if not tg.get("enabled", False):
        print("telegram.enabled: false — Telegram 발송 건너뜀")
        return

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("[오류] TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID가 없습니다.", file=sys.stderr)
        sys.exit(1)

    items = [i for i in load_existing() if recent(i)]
    text = build_message(items, cfg)
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
        timeout=20,
    )
    if not r.ok:
        print(f"[오류] Telegram 발송 실패: {r.status_code} {r.text[:300]}", file=sys.stderr)
        sys.exit(1)
    print("Telegram 브리핑 발송 완료")


if __name__ == "__main__":
    run()
