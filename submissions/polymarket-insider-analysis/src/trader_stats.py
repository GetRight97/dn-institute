import csv
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"

traders = defaultdict(lambda: {
    "trade_count": 0,
    "total_volume": 0,
    "markets": set(),
    "buy_count": 0,
    "sell_count": 0
})

with open(
    RAW_DIR / "trades.csv",
    "r",
    encoding="utf-8"
) as file:
    reader = csv.DictReader(file)

    for trade in reader:

        wallet = trade["proxy_wallet"]
        size = float(trade["size"])
        price = float(trade["price"])

        traders[wallet]["trade_count"] += 1
        traders[wallet]["total_volume"] += size * price
        traders[wallet]["markets"].add(trade["condition_id"])

        if trade["side"] == "BUY":
            traders[wallet]["buy_count"] += 1
        elif trade["side"] == "SELL":
            traders[wallet]["sell_count"] += 1


print("Всего трейдеров:", len(traders))

sorted_traders = sorted(
    traders.items(),
    key=lambda item: item[1]["trade_count"],
    reverse=True
)

print()
print("ТОП-20 ТРЕЙДЕРОВ ПО КОЛИЧЕСТВУ СДЕЛОК")

for wallet, stats in sorted_traders[:20]:

    average_trade = (
        stats["total_volume"] / stats["trade_count"]
    )

    print()
    print("Wallet:", wallet)
    print("Сделок:", stats["trade_count"])
    print("Объём:", round(stats["total_volume"], 2))
    print("Средняя сделка:", round(average_trade, 2))
    print("Рынков:", len(stats["markets"]))
    print("BUY:", stats["buy_count"])
    print("SELL:", stats["sell_count"])

print()
print("ТОП-20 ПО ДОЛЕ BUY")

traders_with_buy_ratio = []

for wallet, stats in traders.items():

    if stats["trade_count"] >= 100:

        buy_ratio = stats["buy_count"] / stats["trade_count"]

        traders_with_buy_ratio.append(
            (wallet, stats, buy_ratio)
        )

traders_with_buy_ratio.sort(
    key=lambda item: item[2],
    reverse=True
)

for wallet, stats, buy_ratio in traders_with_buy_ratio[:20]:

    print(
        wallet,
        "| сделок:", stats["trade_count"],
        "| BUY:", stats["buy_count"],
        "| SELL:", stats["sell_count"],
        "| BUY-доля:", round(buy_ratio * 100, 2), "%",
        "| рынков:", len(stats["markets"])
    )