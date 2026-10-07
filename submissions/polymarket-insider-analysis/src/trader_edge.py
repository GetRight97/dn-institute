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


traders = defaultdict(lambda: {
    "buy_count": 0,
    "winning_buy_count": 0,

    "buy_volume": 0,
    "profit_proxy": 0,

    "winning_price_sum": 0,

    "low_price_wins": 0,
    "very_low_price_wins": 0,

    "late_low_price_wins": 0,

    "markets": set(),

    "max_profit_trade": 0
})


with open(
    PROCESSED_DIR / "trades_with_outcome.csv",
    "r",
    encoding="utf-8"
) as file:

    reader = csv.DictReader(file)

    for trade in reader:

        if trade["side"] != "BUY":
            continue

        if trade["winning_outcome"] == "":
            continue

        wallet = trade["proxy_wallet"]

        size = float(trade["size"])
        price = float(trade["price"])

        volume = size * price

        is_winner = (
            trade["is_winning_buy"] == "1"
        )

        hours = trade["hours_before_close"]

        traders[wallet]["buy_count"] += 1
        traders[wallet]["buy_volume"] += volume

        traders[wallet]["markets"].add(
            trade["condition_id"]
        )

        # ------------------------------------------
        # Выигрышная BUY
        # ------------------------------------------

        if is_winner:

            traders[wallet][
                "winning_buy_count"
            ] += 1

            traders[wallet][
                "winning_price_sum"
            ] += price

            # Profit proxy при удержании до settlement
            profit = size * (1 - price)

            traders[wallet][
                "profit_proxy"
            ] += profit

            if profit > traders[wallet]["max_profit_trade"]:
                traders[wallet]["max_profit_trade"] = profit

            # Победителя купили максимум по 50 центов
            if price <= 0.50:

                traders[wallet][
                    "low_price_wins"
                ] += 1

            # Особенно неожиданная ставка
            if price <= 0.25:

                traders[wallet][
                    "very_low_price_wins"
                ] += 1

            # Выигрышная ставка <= 50c
            # и в течение 24 часов до закрытия
            if (
                price <= 0.50
                and hours != ""
            ):

                hours_value = float(hours)

                if 0 <= hours_value <= 24:

                    traders[wallet][
                        "late_low_price_wins"
                    ] += 1

        # ------------------------------------------
        # Проигрышная BUY
        # ------------------------------------------

        else:

            loss = size * price

            traders[wallet][
                "profit_proxy"
            ] -= loss


# --------------------------------------------------
# Формируем таблицу
# --------------------------------------------------

results = []


for wallet, stats in traders.items():

    buy_count = stats["buy_count"]

    winning_buy_count = stats[
        "winning_buy_count"
    ]

    accuracy = (
        winning_buy_count / buy_count
        if buy_count > 0
        else 0
    )

    if winning_buy_count > 0:

        average_winning_price = (
            stats["winning_price_sum"]
            / winning_buy_count
        )

    else:

        average_winning_price = 0


    results.append({
        "wallet": wallet,

        "buy_count": buy_count,

        "winning_buy_count":
            winning_buy_count,

        "accuracy":
            accuracy,

        "buy_volume":
            stats["buy_volume"],

        "profit_proxy":
            stats["profit_proxy"],

        "average_winning_price":
            average_winning_price,

        "low_price_wins":
            stats["low_price_wins"],

        "very_low_price_wins":
            stats["very_low_price_wins"],

        "late_low_price_wins":
            stats["late_low_price_wins"],

        "max_profit_trade":
            stats["max_profit_trade"],

        "markets":
            len(stats["markets"])
    })


# --------------------------------------------------
# Фильтруем совсем мелких трейдеров
# --------------------------------------------------

filtered = [
    trader
    for trader in results
    if trader["buy_count"] >= 20
]


# Главный ranking пока по low-price wins,
# затем profit proxy
filtered.sort(
    key=lambda trader: (
        trader["low_price_wins"],
        trader["profit_proxy"]
    ),
    reverse=True
)


# --------------------------------------------------
# TOP-30
# --------------------------------------------------

print()
print("======================================")
print("TOP-30 ПО НЕОЖИДАННЫМ ВЫИГРЫШНЫМ BUY")
print("======================================")


for trader in filtered[:30]:

    print()

    print(
        "Wallet:",
        trader["wallet"]
    )

    print(
        "BUY:",
        trader["buy_count"]
    )

    print(
        "Accuracy:",
        round(
            trader["accuracy"] * 100,
            2
        ),
        "%"
    )

    print(
        "Markets:",
        trader["markets"]
    )

    print(
        "BUY volume:",
        round(
            trader["buy_volume"],
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

    print(
        "Average winning price:",
        round(
            trader["average_winning_price"],
            4
        )
    )

    print(
        "Winning BUY <= 0.50:",
        trader["low_price_wins"]
    )

    print(
        "Winning BUY <= 0.25:",
        trader["very_low_price_wins"]
    )

    print(
        "Late winning BUY <= 0.50:",
        trader["late_low_price_wins"]
    )

    print(
        "Max profit trade:",
        round(
            trader["max_profit_trade"],
            2
        )
    )


# --------------------------------------------------
# Сохраняем CSV
# --------------------------------------------------

with open(
        RESULTS_DIR / "trader_edge.csv",
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

    fieldnames = [
        "wallet",
        "buy_count",
        "winning_buy_count",
        "accuracy",
        "buy_volume",
        "profit_proxy",
        "average_winning_price",
        "low_price_wins",
        "very_low_price_wins",
        "late_low_price_wins",
        "max_profit_trade",
        "markets"
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
print("Создан файл: trader_edge.csv")
print("======================================")