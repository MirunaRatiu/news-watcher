"""
La fiecare rulare:
    1. Citim feed-ul RSS al facultatii.
    2. Pastram doar anunturile pe care nu le-am mai vazut (seen.json).
    3. Pentru fiecare anunt nou:
         a) il trimitem pe #ubb-all (toate anunturile, fara agent);
         b) il dam agentului, care decide daca e relevant;
         c) daca e relevant, trimitem rezumatul pe #ubb-news.
    4. Memoram anuntul ca „vazut”.
"""
import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

from classifier import classify
from fetch_feed import fetch_announcements

load_dotenv()

SEEN_FILE = Path(__file__).with_name("seen.json")
MAX_SEEN_IDS = 300  

WEBHOOK_ALL = os.environ["DISCORD_WEBHOOK_ALL"]    
WEBHOOK_NEWS = os.environ["DISCORD_WEBHOOK_NEWS"]  

GRAY = 0x95A5A6    # #ubb-al
GREEN = 0x2ECC71   # #ubb-news
ORANGE = 0xE67E22  # #ubb-news


def is_first_run() -> bool:
    return not SEEN_FILE.exists()


def load_seen_ids() -> list[str]:
    return json.loads(SEEN_FILE.read_text(encoding="utf-8"))


def save_seen_ids(seen_ids: list[str]) -> None:
    newest_ids = seen_ids[-MAX_SEEN_IDS:]
    SEEN_FILE.write_text(json.dumps(newest_ids, indent=2), encoding="utf-8")



def send_to_discord(webhook_url: str, title: str, text: str, link: str, date: str, color: int) -> None:
    """Trimite un mesaj pe un canal Discord."""
    message = {
        "embeds": [{
            "title": title[:256],        
            "description": text[:4000],
            "url": link,
            "footer": {"text": date},
            "color": color,
        }]
    }

    response = requests.post(webhook_url, json=message, timeout=30)

    if response.status_code == 429:
        wait_seconds = float(response.json().get("retry_after", 2))
        time.sleep(wait_seconds)
        response = requests.post(webhook_url, json=message, timeout=30)

    response.raise_for_status() 


def notify_all_channel(announcement: dict) -> None:
    preview = announcement["text"][:300] + "…"
    send_to_discord(WEBHOOK_ALL, announcement["titlu"], preview, announcement["link"], announcement["data"], GRAY)



def notify_news_channel(announcement: dict, verdict: dict) -> None:
    relevant = verdict.get("relevant")

    if relevant is True:
        send_to_discord(WEBHOOK_NEWS, announcement["titlu"], verdict.get("rezumat", ""), announcement["link"], announcement["data"], GREEN)


def process_announcement(announcement: dict) -> None:
    notify_all_channel(announcement)

    verdict, tokens = classify(announcement)
    print(f"  relevant={verdict.get('relevant')} | {announcement['titlu']} ({tokens} tokeni)")

    notify_news_channel(announcement, verdict)




def main() -> None:
    announcements = list(reversed(fetch_announcements()))

    if is_first_run():
        save_seen_ids([a["id"] for a in announcements])
        print(f"Prima rulare: am memorat {len(announcements)} anunturi existente, fara notificari.")
        return

    seen_ids = load_seen_ids()
    new_announcements = [a for a in announcements if a["id"] not in seen_ids]
    print(f"Anunturi noi: {len(new_announcements)}")

    for announcement in new_announcements:
        try:
            process_announcement(announcement)
        except requests.RequestException as error:
            print(f"  Eroare Discord pentru '{announcement['titlu']}': {error}")
            continue

        seen_ids.append(announcement["id"])
        save_seen_ids(seen_ids)

        time.sleep(1)  


if __name__ == "__main__":
    main()