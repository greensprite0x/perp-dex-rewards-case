#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Выгрузка лидерборда Arcus Points (Season 1) и расчёт распределения.

Запуск:  python arcus_leaderboard.py
Результат: arcus_leaderboard.csv в той же папке + сводка в окне.

Источник: https://points-api.arcus.xyz/v1/leaderboard (публичный, без ключа)
"""

import csv
import json
import sys
import time
import urllib.error
import urllib.request

BASE = "https://points-api.arcus.xyz/v1/leaderboard"
SEASON = "Season+1"
LIMIT = 100
PAUSE = 0.3          # пауза между запросами, секунды
MAX_RETRIES = 3

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
    "Origin": "https://app.arcus.xyz",
    "Referer": "https://app.arcus.xyz/",
}


def fetch(offset):
    """Одна страница лидерборда. Возвращает (список записей, total)."""
    url = f"{BASE}?season={SEASON}&limit={LIMIT}&offset={offset}"
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.load(resp)
            return data.get("entries", []), data.get("total")
        except urllib.error.HTTPError as e:
            last_error = f"HTTP {e.code}"
            # 429 — слишком частые запросы: ждём дольше и пробуем снова
            time.sleep(2 * attempt)
        except Exception as e:  # обрыв связи, таймаут и прочее
            last_error = str(e)
            time.sleep(2 * attempt)

    raise RuntimeError(f"не удалось получить offset={offset}: {last_error}")


def main():
    rows = []
    offset = 0
    total = None

    print("Выгрузка лидерборда Arcus Points, Season 1\n")

    while True:
        entries, reported_total = fetch(offset)
        if total is None and reported_total is not None:
            total = reported_total
            print(f"Сервер сообщает участников: {total}\n")

        if not entries:
            break

        rows.extend(entries)
        shown = f"{len(rows)}" + (f" из {total}" if total else "")
        print(f"  снято {shown}")

        offset += LIMIT
        time.sleep(PAUSE)

        if total and len(rows) >= total:
            break

    if not rows:
        print("Ничего не получено. Возможно, структура ответа изменилась.")
        sys.exit(1)

    # ---------- сохранение ----------
    with open("arcus_leaderboard.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["rank", "name", "tier", "points"])
        for e in rows:
            writer.writerow([
                e.get("rank"),
                e.get("name"),
                e.get("tier"),
                e.get("points"),
            ])

    # ---------- расчёт ----------
    pts = sorted((float(e.get("points") or 0) for e in rows), reverse=True)
    n = len(pts)
    summa = sum(pts)
    median = pts[n // 2] if n % 2 else (pts[n // 2 - 1] + pts[n // 2]) / 2
    zeros = sum(1 for p in pts if p == 0)

    print("\n" + "=" * 46)
    print("РАСПРЕДЕЛЕНИЕ ПОИНТОВ")
    print("=" * 46)
    print(f"Участников выгружено:   {n:,}".replace(",", " "))
    if total:
        print(f"Заявлено сервером:      {total:,}".replace(",", " "))
    print(f"Сумма поинтов:          {summa:,.2f}".replace(",", " "))
    print(f"Среднее на участника:   {summa / n:,.2f}".replace(",", " "))
    print(f"Медиана:                {median:,.2f}".replace(",", " "))
    print(f"Максимум (1-е место):   {pts[0]:,.2f}".replace(",", " "))
    print(f"Участников с нулём:     {zeros:,}".replace(",", " "))

    print("\nДоля верхушки в общей сумме:")
    for k in (10, 100, 1000, 5000):
        if n >= k:
            print(f"  топ-{k:<5} {sum(pts[:k]) / summa * 100:6.2f}%")

    # распределение по тирам, если поле есть
    tiers = {}
    for e in rows:
        t = e.get("tier") or "(не указан)"
        tiers[t] = tiers.get(t, 0) + 1
    if len(tiers) > 1 or "(не указан)" not in tiers:
        print("\nУчастников по уровням:")
        for t, c in sorted(tiers.items(), key=lambda x: -x[1]):
            print(f"  {t:<14} {c:,}".replace(",", " "))

    print("\nФайл сохранён: arcus_leaderboard.csv")


if __name__ == "__main__":
    main()
