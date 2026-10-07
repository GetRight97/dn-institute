import csv
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# --------------------------------------------------
# 1. Загружаем результаты рынков
# --------------------------------------------------

market_results = {}

with open(
    PROCESSED_DIR / "market_outcomes.csv",
    "r",
    encoding="utf-8"
) as file:

    reader = csv.DictReader(file)

    for row in reader:

        condition_id = row["condition_id"]

        market_results[condition_id] = {
            "winning_outcome": row["winning_outcome"],
            "closed_time": row["closed_time"],
            "uma_status": row["uma_status"]
        }


print(
    "Загружено рынков:",
    len(market_results)
)


# --------------------------------------------------
# 2. Открываем trades.csv
# --------------------------------------------------

with open(
    RAW_DIR / "trades.csv",
    "r",
    encoding="utf-8"
) as input_file:

    reader = csv.DictReader(input_file)

    fieldnames = reader.fieldnames + [
        "winning_outcome",
        "uma_status",
        "is_winning_buy",
        "closed_time",
        "hours_before_close"
    ]


    # --------------------------------------------------
    # 3. Создаём новый CSV
    # --------------------------------------------------

    with open(
        PROCESSED_DIR / "trades_with_outcome.csv",
        "w",
        newline="",
        encoding="utf-8"
    ) as output_file:

        writer = csv.DictWriter(
            output_file,
            fieldnames=fieldnames
        )

        writer.writeheader()


        total_trades = 0
        matched_trades = 0
        resolved_trades = 0

        buy_trades = 0
        winning_buy_trades = 0

        timing_available = 0


        # --------------------------------------------------
        # 4. Обрабатываем сделки
        # --------------------------------------------------

        for trade in reader:

            total_trades += 1

            condition_id = trade["condition_id"]


            # --------------------------------------------------
            # Рынок не найден
            # --------------------------------------------------

            if condition_id not in market_results:

                trade["winning_outcome"] = ""
                trade["uma_status"] = ""
                trade["is_winning_buy"] = ""
                trade["closed_time"] = ""
                trade["hours_before_close"] = ""

                writer.writerow(trade)

                continue


            matched_trades += 1

            market = market_results[
                condition_id
            ]


            winning_outcome = market[
                "winning_outcome"
            ]

            closed_time = market[
                "closed_time"
            ]

            uma_status = market[
                "uma_status"
            ]


            trade["winning_outcome"] = (
                winning_outcome
            )

            trade["uma_status"] = (
                uma_status
            )

            trade["closed_time"] = (
                closed_time
            )


            # --------------------------------------------------
            # 5. BUY на победивший outcome
            # --------------------------------------------------

            is_winning_buy = ""


            if winning_outcome:

                resolved_trades += 1


                if trade["side"] == "BUY":

                    buy_trades += 1


                    if (
                        trade["outcome"]
                        == winning_outcome
                    ):

                        is_winning_buy = 1

                        winning_buy_trades += 1

                    else:

                        is_winning_buy = 0


            trade["is_winning_buy"] = (
                is_winning_buy
            )


            # --------------------------------------------------
            # 6. Время сделки до закрытия рынка
            # --------------------------------------------------

            hours_before_close = ""


            if closed_time:

                try:

                    trade_time = datetime.fromisoformat(
                        trade["trade_date"]
                    )

                    close_time = datetime.fromisoformat(
                        closed_time
                    )

                    time_difference = (
                        close_time
                        - trade_time
                    )

                    hours_before_close = (
                        time_difference.total_seconds()
                        / 3600
                    )

                    hours_before_close = round(
                        hours_before_close,
                        4
                    )

                    timing_available += 1


                except ValueError:

                    hours_before_close = ""


            trade[
                "hours_before_close"
            ] = hours_before_close


            # --------------------------------------------------
            # 7. Записываем
            # --------------------------------------------------

            writer.writerow(trade)


            # --------------------------------------------------
            # 8. Прогресс
            # --------------------------------------------------

            if total_trades % 100000 == 0:

                print(
                    "Обработано:",
                    total_trades
                )


# --------------------------------------------------
# 9. Итог
# --------------------------------------------------

print()

print(
    "======================================"
)

print(
    "ГОТОВО"
)

print(
    "======================================"
)

print()

print(
    "Всего сделок:",
    total_trades
)

print(
    "Сопоставлено с рынками:",
    matched_trades
)

print(
    "Сделок на resolved рынках:",
    resolved_trades
)

print(
    "BUY-сделок:",
    buy_trades
)

print(
    "BUY на победивший outcome:",
    winning_buy_trades
)

print(
    "Есть timing:",
    timing_available
)


# --------------------------------------------------
# 10. Общая BUY accuracy
# --------------------------------------------------

if buy_trades > 0:

    accuracy = (
        winning_buy_trades
        / buy_trades
        * 100
    )

    print(
        "Общая BUY accuracy:",
        round(
            accuracy,
            2
        ),
        "%"
    )


print()

print(
    "Создан файл: trades_with_outcome.csv"
)