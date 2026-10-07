import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

PROCESSED_DIR = BASE_DIR / "data" / "processed"
RESULTS_DIR = BASE_DIR / "results"

RESULTS_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# --------------------------------------------------
# 1. Берём TOP-10 из insider_ranking.csv
# --------------------------------------------------

top_wallets = set()

with open(
    RESULTS_DIR / "insider_ranking.csv",
    "r",
    encoding="utf-8"
) as file:

    reader = csv.DictReader(file)

    for row in reader:

        rank = int(row["rank"])

        if rank <= 10:
            top_wallets.add(
                row["wallet"]
            )


print("TOP кошельков:", len(top_wallets))


# --------------------------------------------------
# 2. Выбираем интересные сделки
# --------------------------------------------------

interesting_trades = []


with open(
    PROCESSED_DIR / "trades_with_outcome.csv",
    "r",
    encoding="utf-8"
) as file:

    reader = csv.DictReader(file)

    for trade in reader:

        wallet = trade["proxy_wallet"]

        if wallet not in top_wallets:
            continue

        if trade["side"] != "BUY":
            continue

        if trade["is_winning_buy"] != "1":
            continue


        price = float(
            trade["price"]
        )

        size = float(
            trade["size"]
        )

        hours = trade[
            "hours_before_close"
        ]


        # Только интересные входы:
        # победитель был куплен максимум по 50c
        if price > 0.50:
            continue


        volume = (
            size * price
        )

        profit_proxy = (
            size * (1 - price)
        )


        if hours != "":
            hours_value = float(hours)
        else:
            hours_value = None


        interesting_trades.append({

            "wallet":
                wallet,

            "condition_id":
                trade["condition_id"],

            "title":
                trade["title"],

            "trade_date":
                trade["trade_date"],

            "closed_time":
                trade["closed_time"],

            "hours_before_close":
                hours_value,

            "outcome":
                trade["outcome"],

            "winning_outcome":
                trade["winning_outcome"],

            "price":
                price,

            "size":
                size,

            "volume":
                volume,

            "profit_proxy":
                profit_proxy,

            "transaction_hash":
                trade["transaction_hash"]
        })


# --------------------------------------------------
# 3. Сортируем
# --------------------------------------------------

interesting_trades.sort(
    key=lambda trade: (
        trade["wallet"],
        -trade["profit_proxy"]
    )
)


# --------------------------------------------------
# 4. Создаём CSV
# --------------------------------------------------

with open(
    RESULTS_DIR / "candidate_details.csv",
    "w",
    newline="",
    encoding="utf-8"
) as file:

    fieldnames = [
        "wallet",
        "condition_id",
        "title",
        "trade_date",
        "closed_time",
        "hours_before_close",
        "outcome",
        "winning_outcome",
        "price",
        "size",
        "volume",
        "profit_proxy",
        "transaction_hash"
    ]

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames
    )

    writer.writeheader()

    for trade in interesting_trades:
        writer.writerow(trade)


# --------------------------------------------------
# 5. Показываем TOP интересных сделок
# --------------------------------------------------

interesting_trades.sort(
    key=lambda trade:
        trade["profit_proxy"],
    reverse=True
)


print()
print("======================================")
print("TOP-30 ИНТЕРЕСНЫХ СДЕЛОК")
print("======================================")


for trade in interesting_trades[:30]:

    print()

    print(
        "Wallet:",
        trade["wallet"]
    )

    print(
        "Market:",
        trade["title"]
    )

    print(
        "Outcome:",
        trade["outcome"]
    )

    print(
        "Price:",
        trade["price"]
    )

    print(
        "Hours before close:",
        trade["hours_before_close"]
    )

    print(
        "Volume:",
        round(
            trade["volume"],
            2
        )
    )

    print(
        "Profit proxy:",
        round(
            trade["profit_proxy"],
            2
        )
    )


print()
print("======================================")
print(
    "Создан файл: candidate_details.csv"
)
print("======================================")