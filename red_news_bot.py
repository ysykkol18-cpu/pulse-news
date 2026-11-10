"""Бот красных новостей для Discord.
Берёт бесплатную ленту календаря Forex Factory и шлёт в Discord только события
с высокой важностью (красные папки). Работает через вебхук, токен бота не нужен.

Настройки (переменные окружения):
  DISCORD_WEBHOOK_URL  ссылка вебхука (обязательно)
  CURRENCIES           валюты через запятую, по умолчанию USD. ALL = все
  AHEAD_MIN            за сколько минут до события предупреждать, по умолчанию 30
  LATE_MIN             сколько минут после выхода ещё отправлять, по умолчанию 10
  NEWS_TZ              часовой пояс в сообщениях, по умолчанию America/Chicago
  LOOP                 если задано, бот работает постоянно и проверяет раз в 5 минут
Запуск теста: python3 red_news_bot.py test
"""
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

FEED = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
HOOK = os.environ.get("DISCORD_WEBHOOK_URL", "")
CUR = [c.strip().upper() for c in os.environ.get("CURRENCIES", "USD").split(",") if c.strip()]
AHEAD = int(os.environ.get("AHEAD_MIN", "30"))
LATE = int(os.environ.get("LATE_MIN", "10"))
TZ = ZoneInfo(os.environ.get("NEWS_TZ", "America/Chicago"))
STATE = "sent.json"


def http(url, body=None):
    headers = {"User-Agent": "Mozilla/5.0 red-news-bot"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers)
    return urllib.request.urlopen(req, timeout=30).read()


def post(payload):
    http(HOOK, json.dumps(payload).encode())


def load_state():
    try:
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_state(sent):
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(sent[-300:], f, ensure_ascii=False)


def run_once():
    try:
        events = json.loads(http(FEED))
    except Exception as ex:
        print("Не удалось получить ленту:", ex)
        return
    sent = load_state()
    now = datetime.now(timezone.utc)
    embeds, keys = [], []
    for e in events:
        if e.get("impact") != "High":
            continue
        country = str(e.get("country", "")).upper()
        if "ALL" not in CUR and country not in CUR:
            continue
        try:
            t = datetime.fromisoformat(e["date"])
        except Exception:
            continue
        key = f'{e["date"]}|{country}|{e.get("title", "")}'
        mins = (t - now).total_seconds() / 60
        if key in sent or not (-LATE <= mins <= AHEAD):
            continue
        when = t.astimezone(TZ).strftime("%H:%M")
        note = f"через {round(mins)} мин" if mins > 0 else "только что вышла"
        embeds.append({
            "title": f"🔴 {country}: {e.get('title', '')}",
            "description": f"{when} ({TZ.key}), {note}",
            "color": 0xE74C3C,
            "fields": [
                {"name": "Прогноз", "value": e.get("forecast") or "-", "inline": True},
                {"name": "Прошлое", "value": e.get("previous") or "-", "inline": True},
            ],
        })
        keys.append(key)
    if embeds:
        try:
            post({"embeds": embeds[:10]})
        except Exception as ex:
            print("Не удалось отправить в Discord:", ex)
            return
        sent += keys
        print("Отправлено событий:", len(embeds))
    else:
        print("Новых красных событий нет")
    save_state(sent)


if __name__ == "__main__":
    if not HOOK:
        sys.exit("Не задана переменная DISCORD_WEBHOOK_URL")
    if sys.argv[1:] == ["test"]:
        post({"content": "✅ Бот красных новостей подключён"})
    elif os.environ.get("LOOP"):
        while True:
            run_once()
            time.sleep(300)
    else:
        run_once()
