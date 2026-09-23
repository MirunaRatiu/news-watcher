"""
UBB Watcher
Citeste feed-ul RSS al Facultatii UBB si afiseaza anunturile in formatul pe care il va primi agentul.
"""
import html
import re

import feedparser
import requests

FEED_URL = "https://www.cs.ubbcluj.ro/feed/"
HEADERS = {
    "User-Agent": "UBB-Watcher/0.1 (proiect student; github.com/MirunaRatiu/news-watcher)"
}


def clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_announcements() -> list[dict]:
    response = requests.get(FEED_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()
    feed = feedparser.parse(response.content)

    announcements = []
    for entry in feed.entries:
        announcements.append({
            "id": entry.get("id") or entry.get("link"),
            "titlu": entry.get("title", "").strip(),
            "link": entry.get("link", ""),
            "data": entry.get("published", ""),
            "text": clean_html(entry.get("summary", ""))[:1500],
        })
    return announcements


def format_for_agent(a: dict) -> str:
    return f"Titlu: {a['titlu']}\nLink: {a['link']}\nText: {a['text']}"


if __name__ == "__main__":
    anunturi = fetch_announcements()
    print(f"Am gasit {len(anunturi)} anunturi in feed.\n")
    for a in anunturi:
        print(f"[ID] {a['id']}")
        print(f"[Data] {a['data']}")
        print(format_for_agent(a))
        print("-" * 70)
