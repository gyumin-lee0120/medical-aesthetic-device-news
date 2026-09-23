"""해외 RSS 수집기.
현재 Global Cosmetics News를 보조 소스로 연결합니다.
의료미용 장비 직접 관련성이 낮은 기사는 국내 수집기와 동일한 태깅 기준으로 걸러집니다.
"""
import os, sys, time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
from utils import classify_categories, classify_segments, find_mentions, load_config, save_news, strip_html

def relevant(text, cfg):
    lowered = text.lower()
    terms = []
    terms += cfg.get("search_keywords", [])
    terms += cfg.get("brand", {}).get("own_company", [])
    terms += cfg.get("brand", {}).get("own_products", [])
    terms += cfg.get("brand", {}).get("competitor_companies", [])
    terms += cfg.get("brand", {}).get("competitor_products", [])
    return any(t and t.lower() in lowered for t in terms)

def run():
    cfg = load_config()
    src = cfg.get("sources", {}).get("overseas_rss", {})
    if not src.get("enabled", False):
        print("overseas_rss 비활성화")
        return
    items=[]
    for feed in src.get("feeds", []):
        print("RSS:", feed.get("name"))
        d=feedparser.parse(feed.get("url"))
        for e in d.entries[:80]:
            title=strip_html(e.get("title",""))
            summary=strip_html(e.get("summary",""))
            text=f"{title} {summary}"
            if not relevant(text,cfg):
                continue
            link=e.get("link")
            if not link: continue
            pub=e.get("published") or e.get("updated") or ""
            mentions=find_mentions(text,cfg)
            item={
                "title":title,"summary":summary,"link":link,"source":feed.get("name","해외 RSS"),
                "pub_date":pub,"matched_keyword":"RSS","categories":classify_categories(text,cfg),
                "segments":classify_segments(text,cfg),"is_overseas":True,**mentions
            }
            item["own_brand_mentions"]=mentions["own_company_mentions"]+mentions["own_product_mentions"]
            item["competitor_mentions"]=mentions["competitor_company_mentions"]+mentions["competitor_product_mentions"]
            items.append(item)
        time.sleep(.2)
    merged=save_news(items)
    print(f"완료: 해외 RSS {len(items)}건 / 누적 {len(merged)}건")

if __name__=="__main__":
    run()
