import csv
import requests
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"

RAW_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# Период исследования
start_date = datetime(2025, 11, 1, tzinfo=timezone.utc)
end_date = datetime(2026, 5, 1, tzinfo=timezone.utc)


# API Polymarket
url = "https://gamma-api.polymarket.com/markets"


# Сюда будем складывать подходящие рынки
matching_markets = []

offset = 0


while True:

    params = {
        "limit": 100,
        "offset": offset,
        "closed": True,
        "order": "endDate",
        "ascending": False
    }

    response = requests.get(url, params=params)

    print(
        "Offset:",
        offset,
        "| HTTP:",
        response.status_code
    )

    data = response.json()

    # Проверяем, что API действительно вернуло список
    if not isinstance(data, list):
        print("API вернуло неожиданный формат данных:")
        print(data)
        break

    markets = data

    print(
        "Получили рынков:",
        len(markets)
    )

    # Если рынков больше нет — заканчиваем
    if not markets:
        break

    for market in markets:

        # На всякий случай проверяем структуру элемента
        if not isinstance(market, dict):
            continue

        if not market.get("startDate") or not market.get("endDate"):
            continue

        market_start = datetime.fromisoformat(
            market["startDate"].replace("Z", "+00:00")
        )

        market_end = datetime.fromisoformat(
            market["endDate"].replace("Z", "+00:00")
        )

        # Рынок пересекается с нашим исследуемым периодом
        if market_start < end_date and market_end > start_date:

            matching_markets.append(market)

    # Если получили меньше 100 рынков,
    # скорее всего это последняя страница
    if len(markets) < 100:
        break

    offset += 100


print()
print("Всего подходящих рынков:", len(matching_markets))


# Создаём CSV
with open(
    RAW_DIR / "market_dates.csv",
    "w",
    newline="",
    encoding="utf-8"
) as file:

    writer = csv.writer(file)

    writer.writerow([
        "condition_id",
        "title",
        "start_date",
        "end_date"
    ])

    for market in matching_markets:

        condition_id = market.get("conditionId")

        if not condition_id:
            continue

        writer.writerow([
            condition_id,
            market.get("question", ""),
            market.get("startDate", ""),
            market.get("endDate", "")
        ])


print("Файл market_dates.csv создан.")