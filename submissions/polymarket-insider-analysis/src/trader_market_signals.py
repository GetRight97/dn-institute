import csv
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

PROCESSED_DIR = BASE_DIR / "data" / "processed"
RESULTS_DIR = BASE_DIR / "results"

RESULTS_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# --------------------------------------------------
# 1. Агрегация trader + market
# --------------------------------------------------

trader_markets = defaultdict(lambda: {
    "buy_count": 0,
    "buy_volume": 0,
    "winning_buy_count": 0,
    "winning_volume": 0,
    "profit_proxy": 0,

    "min_winning_price": None,

    "low_price_win": False,
    "very_low_price_win": False,
    "late_low_price_win": False
})

with open(
    PROCESSED_DIR / "trades_with_outcome.csv",
    "r",
    encoding="utf-8"
) as file:


    reader = csv.DictReader(file)

    for trade in reader:

        # Только BUY
        if trade["side"] != "BUY":
            continue

        # Только resolved рынки
        if trade["winning_outcome"] == "":
            continue


        wallet = trade["proxy_wallet"]
        condition_id = trade["condition_id"]

        key = (
            wallet,
            condition_id
        )


        size = float(trade["size"])
        price = float(trade["price"])

        volume = size * price

        is_winner = (
            trade["is_winning_buy"] == "1"
        )

        hours = trade["hours_before_close"]


        stats = trader_markets[key]


        stats["buy_count"] += 1
        stats["buy_volume"] += volume


        # --------------------------------------------------
        # Winning BUY
        # --------------------------------------------------

        if is_winner:

            stats["winning_buy_count"] += 1

            stats["winning_volume"] += volume


            profit = size * (1 - price)

            stats["profit_proxy"] += profit


            # Минимальная цена,
            # по которой трейдер купил победителя
            if (
                stats["min_winning_price"] is None
                or price < stats["min_winning_price"]
            ):

                stats["min_winning_price"] = price


            # Победитель куплен <= 50c
            if price <= 0.50:

                stats["low_price_win"] = True


            # Победитель куплен <= 25c
            if price <= 0.25:

                stats["very_low_price_win"] = True


            # Победитель <= 50c
            # и не более чем за 24 часа до closed_time
            if (
                price <= 0.50
                and hours != ""
            ):

                hours_value = float(hours)

                if 0 <= hours_value <= 24:

                    stats[
                        "late_low_price_win"
                    ] = True


        # --------------------------------------------------
        # Losing BUY
        # --------------------------------------------------

        else:

            loss = size * price

            stats["profit_proxy"] -= loss


# --------------------------------------------------
# 2. Теперь агрегируем по трейдеру
# --------------------------------------------------

traders = defaultdict(lambda: {
    "markets": 0,

    "profitable_markets": 0,

    "low_price_win_markets": 0,
    "very_low_price_win_markets": 0,
    "late_low_price_win_markets": 0,

    "profit_proxy": 0,

    "total_buy_volume": 0,

    "total_buy_count": 0
})


for (
    wallet,
    condition_id
), stats in trader_markets.items():

    trader = traders[wallet]

    trader["markets"] += 1

    trader["profit_proxy"] += (
        stats["profit_proxy"]
    )

    trader["total_buy_volume"] += (
        stats["buy_volume"]
    )

    trader["total_buy_count"] += (
        stats["buy_count"]
    )


    if stats["profit_proxy"] > 0:

        trader[
            "profitable_markets"
        ] += 1


    if stats["low_price_win"]:

        trader[
            "low_price_win_markets"
        ] += 1


    if stats["very_low_price_win"]:

        trader[
            "very_low_price_win_markets"
        ] += 1


    if stats["late_low_price_win"]:

        trader[
            "late_low_price_win_markets"
        ] += 1


# --------------------------------------------------
# 3. Формируем результаты
# --------------------------------------------------

results = []


for wallet, stats in traders.items():

    markets = stats["markets"]

    profitable_ratio = (
        stats["profitable_markets"]
        / markets
        if markets > 0
        else 0
    )


    results.append({

        "wallet":
            wallet,

        "markets":
            markets,

        "total_buy_count":
            stats["total_buy_count"],

        "total_buy_volume":
            stats["total_buy_volume"],

        "profit_proxy":
            stats["profit_proxy"],

        "profitable_markets":
            stats["profitable_markets"],

        "profitable_market_ratio":
            profitable_ratio,

        "low_price_win_markets":
            stats["low_price_win_markets"],

        "very_low_price_win_markets":
            stats[
                "very_low_price_win_markets"
            ],

        "late_low_price_win_markets":
            stats[
                "late_low_price_win_markets"
            ]
    })


# --------------------------------------------------
# 4. Фильтр
# --------------------------------------------------

filtered = [
    trader
    for trader in results
    if trader["markets"] >= 3
]


# Сначала repeated very-low-price wins,
# затем late wins,
# затем profit
filtered.sort(
    key=lambda x: (
        x["very_low_price_win_markets"],
        x["late_low_price_win_markets"],
        x["profit_proxy"]
    ),
    reverse=True
)


# --------------------------------------------------
# 5. TOP 30
# --------------------------------------------------

print()
print("======================================")
print("TOP-30 ПО ПОВТОРЯЕМОСТИ СИГНАЛОВ")
print("минимум 3 рынка")
print("======================================")


for trader in filtered[:30]:

    print()

    print(
        "Wallet:",
        trader["wallet"]
    )

    print(
        "Markets:",
        trader["markets"]
    )

    print(
        "Profitable markets:",
        trader["profitable_markets"]
    )

    print(
        "Profitable market ratio:",
        round(
            trader["profitable_market_ratio"]
            * 100,
            2
        ),
        "%"
    )

    print(
        "Low-price win markets:",
        trader["low_price_win_markets"]
    )

    print(
        "Very-low-price win markets:",
        trader["very_low_price_win_markets"]
    )

    print(
        "Late low-price win markets:",
        trader["late_low_price_win_markets"]
    )

    print(
        "BUY volume:",
        round(
            trader["total_buy_volume"],
            2
        )
    )

    print(
        "Profit proxy:",
        round(
            trader["profit_proxy"],
            2
        )
    )


# --------------------------------------------------
# 6. Сохраняем CSV
# --------------------------------------------------

with open(
    RESULTS_DIR / "trader_market_signals.csv",
    "w",
    newline="",
    encoding="utf-8"
) as file:

    fieldnames = [
        "wallet",
        "markets",
        "total_buy_count",
        "total_buy_volume",
        "profit_proxy",
        "profitable_markets",
        "profitable_market_ratio",
        "low_price_win_markets",
        "very_low_price_win_markets",
        "late_low_price_win_markets"
    ]

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames
    )

    writer.writeheader()

    for trader in results:

        writer.writerow(trader)


print()
print("======================================")
print("Создан файл: trader_market_signals.csv")
print("======================================")