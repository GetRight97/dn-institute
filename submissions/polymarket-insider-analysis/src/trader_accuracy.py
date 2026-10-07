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
# 1. Настройки
# --------------------------------------------------

LATE_HOURS = 24


# --------------------------------------------------
# 2. Статистика трейдеров
# --------------------------------------------------

traders = defaultdict(lambda: {
    "buy_count": 0,
    "winning_buy_count": 0,

    "buy_volume": 0,
    "winning_buy_volume": 0,

    "late_buy_count": 0,
    "late_winning_buy_count": 0,

    "markets": set(),

    "max_buy_volume": 0
})


# --------------------------------------------------
# 3. Читаем сделки
# --------------------------------------------------

with open(
    PROCESSED_DIR / "trades_with_outcome.csv",
    "r",
    encoding="utf-8"
) as file:

    reader = csv.DictReader(file)

    for trade in reader:

        # Нас интересуют только BUY
        if trade["side"] != "BUY":
            continue

        # Только рынки, где победитель определён
        if trade["winning_outcome"] == "":
            continue

        wallet = trade["proxy_wallet"]

        size = float(trade["size"])
        price = float(trade["price"])

        volume = size * price

        is_winning_buy = (
            trade["is_winning_buy"] == "1"
        )

        hours_before_close = trade[
            "hours_before_close"
        ]

        # --------------------------------------------------
        # Общая BUY статистика
        # --------------------------------------------------

        traders[wallet]["buy_count"] += 1

        traders[wallet]["buy_volume"] += volume

        traders[wallet]["markets"].add(
            trade["condition_id"]
        )

        if volume > traders[wallet]["max_buy_volume"]:
            traders[wallet]["max_buy_volume"] = volume

        # --------------------------------------------------
        # Выигрышная BUY
        # --------------------------------------------------

        if is_winning_buy:

            traders[wallet][
                "winning_buy_count"
            ] += 1

            traders[wallet][
                "winning_buy_volume"
            ] += volume

        # --------------------------------------------------
        # Поздняя BUY
        # --------------------------------------------------

        if hours_before_close != "":

            hours = float(hours_before_close)

            if 0 <= hours <= LATE_HOURS:

                traders[wallet][
                    "late_buy_count"
                ] += 1

                if is_winning_buy:

                    traders[wallet][
                        "late_winning_buy_count"
                    ] += 1


# --------------------------------------------------
# 4. Формируем результаты
# --------------------------------------------------

results = []


for wallet, stats in traders.items():

    buy_count = stats["buy_count"]

    winning_buy_count = stats[
        "winning_buy_count"
    ]

    buy_volume = stats[
        "buy_volume"
    ]

    winning_buy_volume = stats[
        "winning_buy_volume"
    ]

    late_buy_count = stats[
        "late_buy_count"
    ]

    late_winning_buy_count = stats[
        "late_winning_buy_count"
    ]

    # --------------------------------------------------
    # Accuracy
    # --------------------------------------------------

    accuracy = (
        winning_buy_count
        / buy_count
        if buy_count > 0
        else 0
    )

    # --------------------------------------------------
    # Доля выигрышного объёма
    # --------------------------------------------------

    winning_volume_ratio = (
        winning_buy_volume
        / buy_volume
        if buy_volume > 0
        else 0
    )

    # --------------------------------------------------
    # Late accuracy
    # --------------------------------------------------

    late_accuracy = (
        late_winning_buy_count
        / late_buy_count
        if late_buy_count > 0
        else 0
    )

    # --------------------------------------------------
    # Средний BUY
    # --------------------------------------------------

    average_buy = (
        buy_volume
        / buy_count
        if buy_count > 0
        else 0
    )

    results.append({
        "wallet": wallet,

        "buy_count": buy_count,

        "winning_buy_count":
            winning_buy_count,

        "accuracy":
            accuracy,

        "buy_volume":
            buy_volume,

        "winning_buy_volume":
            winning_buy_volume,

        "winning_volume_ratio":
            winning_volume_ratio,

        "average_buy":
            average_buy,

        "max_buy_volume":
            stats["max_buy_volume"],

        "markets":
            len(stats["markets"]),

        "late_buy_count":
            late_buy_count,

        "late_winning_buy_count":
            late_winning_buy_count,

        "late_accuracy":
            late_accuracy
    })


# --------------------------------------------------
# 5. Сортируем
# --------------------------------------------------

# Чтобы не ловить трейдеров,
# которые сделали 1 сделку и случайно угадали,
# покажем сначала тех, у кого хотя бы 20 BUY.

filtered_results = [
    trader
    for trader in results
    if trader["buy_count"] >= 20
]


filtered_results.sort(
    key=lambda trader: (
        trader["accuracy"],
        trader["buy_count"]
    ),
    reverse=True
)


# --------------------------------------------------
# 6. TOP-30
# --------------------------------------------------

print()
print("======================================")
print("TOP-30 ПО BUY ACCURACY")
print("минимум 20 BUY")
print("======================================")


for trader in filtered_results[:30]:

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
        "Winning BUY:",
        trader["winning_buy_count"]
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
        "BUY volume:",
        round(
            trader["buy_volume"],
            2
        )
    )

    print(
        "Winning volume ratio:",
        round(
            trader["winning_volume_ratio"] * 100,
            2
        ),
        "%"
    )

    print(
        "Average BUY:",
        round(
            trader["average_buy"],
            2
        )
    )

    print(
        "Max BUY:",
        round(
            trader["max_buy_volume"],
            2
        )
    )

    print(
        "Markets:",
        trader["markets"]
    )

    print(
        "Late BUY:",
        trader["late_buy_count"]
    )

    print(
        "Late accuracy:",
        round(
            trader["late_accuracy"] * 100,
            2
        ),
        "%"
    )


# --------------------------------------------------
# 7. Сохраняем CSV
# --------------------------------------------------

with open(
    RESULTS_DIR / "trader_accuracy.csv",
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
        "winning_buy_volume",
        "winning_volume_ratio",
        "average_buy",
        "max_buy_volume",
        "markets",
        "late_buy_count",
        "late_winning_buy_count",
        "late_accuracy"
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
print("Готово!")
print("Создан файл: trader_accuracy.csv")
print("======================================")