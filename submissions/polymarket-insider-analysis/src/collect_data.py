import requests
from datetime import datetime, timezone
import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"

RAW_DIR.mkdir(
    parents=True,
    exist_ok=True
)

url = "https://gamma-api.polymarket.com/markets"

start_date = datetime(2025, 11, 1, tzinfo=timezone.utc)
end_date = datetime(2026, 5, 1, tzinfo=timezone.utc)

offset = 0

matching_markets = []

while offset <= 2000:

    params = {
        "limit": 100,
        "offset": offset,
        "closed": True,
        "order": "endDate",
        "ascending": False
    }

    response = requests.get(url, params=params)

    markets = response.json()

    print("Offset:", offset, "| Получили:", len(markets))

    if not markets:
        break

    for market in markets:

        market_start = datetime.fromisoformat(
            market["startDate"].replace("Z", "+00:00")
        )

        market_end = datetime.fromisoformat(
            market["endDate"].replace("Z", "+00:00")
        )

        if market_start < end_date and market_end > start_date:

            matching_markets.append(market)

    offset += 100

print()
print("Всего подходящих рынков:", len(matching_markets))

condition_ids = []

for market in matching_markets:
    condition_id = market.get("conditionId")

    if condition_id:
        condition_ids.append(condition_id)

print()
print("Всего conditionId:", len(condition_ids))

all_period_trades = []

csv_file = open(
    RAW_DIR / "trades.csv",
    "w",
    newline="",
    encoding="utf-8"
)

writer = csv.writer(csv_file)

writer.writerow([
    "condition_id",
    "proxy_wallet",
    "side",
    "size",
    "price",
    "timestamp",
    "trade_date",
    "outcome",
    "title",
    "transaction_hash"
])


for number, condition_id in enumerate(condition_ids, start=1):

    url = "https://data-api.polymarket.com/v2/trades"

    params = {
        "condition": condition_id,
        "limit": 100
    }

    all_market_trades = []

    while True:

        response = requests.get(url, params=params)
        data = response.json()

        trades = data["data"]

        all_market_trades.extend(trades)

        if not data["pagination"]["has_more"]:
            break

        params["cursor"] = data["pagination"]["next_cursor"]

    period_trades = []

    for trade in all_market_trades:

        trade_date = datetime.fromtimestamp(
            trade["timestamp"],
            timezone.utc
        )

        if start_date <= trade_date < end_date:
            period_trades.append(trade)
            all_period_trades.append(trade)

            writer.writerow([
                trade["condition_id"],
                trade["proxy_wallet"],
                trade["side"],
                trade["size"],
                trade["price"],
                trade["timestamp"],
                trade_date.isoformat(),
                trade["outcome"],
                trade["title"],
                trade["transaction_hash"]
            ])

            csv_file.flush()

    print(
        number,
        "/",
        len(condition_ids),
        "| Рынок:",
        condition_id,
        "| всего сделок:",
        len(all_market_trades),
        "| сделок в периоде:",
        len(period_trades)
    )
csv_file.close()
print()
print("Всего сделок в периоде:", len(all_period_trades))
