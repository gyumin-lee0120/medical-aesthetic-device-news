"""오늘의 브리핑 요약 이메일 발송 스크립트.

config.yaml의 email.enabled 가 true일 때만 동작합니다.
필요 환경변수:
  GMAIL_ADDRESS       (보내는 사람 Gmail 주소)
  GMAIL_APP_PASSWORD  (Gmail 앱 비밀번호 - 일반 로그인 비밀번호 아님, README 참고)
"""
import os
import smtplib
import sys
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "collectors"))
from utils import load_config, load_existing  # noqa: E402

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def build_summary(items, cfg):
    main_items = [i for i in items if i.get("topic") == "main"]
    cat_counts = {}
    for i in main_items:
        for c in i.get("categories", []):
            cat_counts[c] = cat_counts.get(c, 0) + 1
    top_cats = sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)[:3]

    own_hits = [i for i in items if i.get("own_brand_mentions")]
    competitor_hits = [i for i in items if i.get("competitor_mentions")]

    lines = []
    lines.append(f"오늘 수집된 기사: 총 {len(items)}건 (메인 주제 {len(main_items)}건)")
    if top_cats:
        cat_text = ", ".join(f"{c} {n}건" for c, n in top_cats)
        lines.append(f"카테고리 상위: {cat_text}")
    lines.append(f"자사 브랜드 언급: {len(own_hits)}건 / 경쟁사 언급: {len(competitor_hits)}건")
    lines.append("")
    lines.append("주요 기사:")
    for item in main_items[:10]:
        lines.append(f"- {item['title']} ({item['source']})\n  {item['link']}")

    return "\n".join(lines)


def send(subject, body, to_addrs, from_addr, app_password):
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(from_addr, app_password)
        server.sendmail(from_addr, to_addrs, msg.as_string())


def run():
    cfg = load_config()
    email_cfg = cfg.get("email", {})
    if not email_cfg.get("enabled", False):
        print("email.enabled: false — 이메일 발송을 건너뜁니다. (config.yaml에서 설정 후 사용)")
        return

    to_addrs = [addr for addr in email_cfg.get("to", []) if not addr.startswith("TODO")]
    if not to_addrs:
        print("[경고] config.yaml email.to 에 유효한 수신자가 없어 발송을 건너뜁니다.")
        return

    from_addr = os.environ.get("GMAIL_ADDRESS")
    app_password = os.environ.get("GMAIL_APP_PASSWORD")
    if not from_addr or not app_password:
        print(
            "[오류] GMAIL_ADDRESS / GMAIL_APP_PASSWORD 환경변수가 없습니다.\n"
            "README의 'Gmail 앱 비밀번호 발급' 안내를 참고해 발급받고 GitHub secrets에 등록하세요.",
            file=sys.stderr,
        )
        sys.exit(1)

    all_items = load_existing()
    cutoff = datetime.now(timezone.utc) - timedelta(days=1)

    def is_today(item):
        from email.utils import parsedate_to_datetime
        try:
            return parsedate_to_datetime(item["pub_date"]) >= cutoff
        except (KeyError, TypeError, ValueError):
            return False

    today_items = [i for i in all_items if is_today(i)]
    body = build_summary(today_items, cfg)
    today_str = datetime.now().strftime("%Y.%m.%d")
    subject = f"[화장품 뉴스 클리핑] {today_str} 브리핑"

    send(subject, body, to_addrs, from_addr, app_password)
    print(f"이메일 발송 완료 → {', '.join(to_addrs)}")


if __name__ == "__main__":
    run()
