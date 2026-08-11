"""
Разовая проверка OLX.kz — запускается GitHub Actions по расписанию.
Секреты BOT_TOKEN, CHAT_ID, OLX_URL берутся из переменных окружения.
"""

import os
import json
import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
OLX_URL = os.environ["OLX_URL"]

SEEN_FILE = "seen_ads.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
}


def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_seen(seen):
    trimmed = list(seen)[-500:]
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(trimmed, f)


def send_telegram(text, url):
    api = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    keyboard = {"inline_keyboard": [[{"text": "Открыть объявление", "url": url}]]}
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": json.dumps(keyboard),
    }
    r = requests.post(api, data=payload, timeout=15)
    if not r.ok:
        print("Ошибка отправки в Telegram:", r.text)


def fetch_ads():
    resp = requests.get(OLX_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    ads = []
    cards = soup.find_all(attrs={"data-cy": "l-card"})
    for card in cards:
        ad_id = card.get("id")
        link_tag = card.find("a", href=True)
        if not link_tag:
            continue
        link = link_tag["href"]
        if link.startswith("/"):
            link = "https://www.olx.kz" + link

        title_tag = card.find("h4") or card.find("h6")
        title = title_tag.get_text(strip=True) if title_tag else "Без названия"

        price_tag = card.find(attrs={"data-testid": "ad-price"})
        price = price_tag.get_text(strip=True) if price_tag else "Цена не указана"

        if ad_id:
            ads.append((ad_id, title, price, link))
    return ads


def main():
    seen = load_seen()
    first_run = len(seen) == 0

    ads = fetch_ads()
    print(f"Найдено объявлений на странице: {len(ads)}")

    if first_run:
        # первый запуск - просто запоминаем всё что есть, не спамим
        for ad_id, *_ in ads:
            seen.add(ad_id)
        save_seen(seen)
        print(f"Первый запуск: сохранено {len(seen)} объявлений.")
        return

    new_ads = [a for a in ads if a[0] not in seen]
    for ad_id, title, price, link in reversed(new_ads):
        text = f"🆕 <b>{title}</b>\n💰 {price}"
        send_telegram(text, link)
        seen.add(ad_id)

    if new_ads:
        save_seen(seen)
        print(f"Отправлено новых: {len(new_ads)}")
    else:
        print("Новых объявлений нет.")


if __name__ == "__main__":
    main()
