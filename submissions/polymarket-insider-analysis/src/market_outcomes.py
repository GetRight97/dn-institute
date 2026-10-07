import csv
import json
from polymarket import PublicClient
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# --------------------------------------------------
# 1. Получаем уникальные condition_id из trades.csv
# --------------------------------------------------

condition_ids = set()

with open(
    RAW_DIR / "trades.csv",
    "r",
    encoding="utf-8"
) as file:
    reader = csv.DictReader(file)

    for trade in reader:
        condition_id = trade["condition_id"]
        condition_ids.add(condition_id)

condition_ids = sorted(condition_ids)

print("Уникальных рынков:", len(condition_ids))


# --------------------------------------------------
# 2. Получаем рынки через Polymarket SDK
# --------------------------------------------------

found_markets = {}
not_found = []
error_count = 0

with PublicClient() as client:

    for number, condition_id in enumerate(condition_ids, start=1):

        try:
            paginator = client.list_markets(
                condition_ids=[condition_id],
                closed=True,
                page_size=10
            )

            page = paginator.first_page()

            # Проверяем, что рынок найден
            if not page.items:
                not_found.append(condition_id)
                continue

            # Проверяем соответствие condition_id
            market = next(
                (
                    item for item in page.items
                    if item.condition_id == condition_id
                ),
                None
            )

            if market is None:
                not_found.append(condition_id)
                continue

            found_markets[condition_id] = market

        except Exception as error:
            print("Ошибка:", condition_id, error)
            error_count += 1

        if number % 50 == 0:
            print(
                "Проверено:",
                number,
                "/",
                len(condition_ids),
                "| найдено:",
                len(found_markets)
            )


# --------------------------------------------------
# 3. Создаём market_outcomes.csv
# --------------------------------------------------

winner_count = 0
closed_time_count = 0
resolved_count = 0

with open(
    PROCESSED_DIR / "market_outcomes.csv",
    "w",
    newline="",
    encoding="utf-8"
) as output_file:

    fieldnames = [
        "condition_id",
        "title",
        "closed",
        "closed_time",
        "end_date",
        "outcomes",
        "outcome_prices",
        "winning_outcome",
        "uma_status"
    ]

    writer = csv.DictWriter(
        output_file,
        fieldnames=fieldnames
    )

    writer.writeheader()

    for condition_id, market in found_markets.items():

        # --------------------------------------------------
        # 4. Основная информация о рынке
        # --------------------------------------------------

        title = market.question
        closed = market.state.closed

        closed_time = market.state.closed_time
        end_date = market.state.end_date

        if closed_time is not None:
            closed_time_count += 1
            closed_time = closed_time.isoformat()
        else:
            closed_time = ""

        if end_date is not None:
            end_date = end_date.isoformat()
        else:
            end_date = ""

        # --------------------------------------------------
        # 5. Получаем outcomes и цены
        # --------------------------------------------------

        yes_outcome = market.outcomes.yes
        no_outcome = market.outcomes.no

        yes_label = yes_outcome.label
        no_label = no_outcome.label

        yes_price = (
            float(yes_outcome.price)
            if yes_outcome.price is not None
            else None
        )

        no_price = (
            float(no_outcome.price)
            if no_outcome.price is not None
            else None
        )

        outcomes = [
            yes_label,
            no_label
        ]

        outcome_prices = [
            yes_price,
            no_price
        ]

        # --------------------------------------------------
        # 6. Получаем статус разрешения рынка
        # --------------------------------------------------

        uma_status = ""

        if market.resolution is not None:

            status = market.resolution.uma_resolution_status

            if status is not None:
                uma_status = status.value

        is_resolved = uma_status in ("resolved", "settled")

        if is_resolved:
            resolved_count += 1

        # --------------------------------------------------
        # 7. Определяем победивший outcome
        # --------------------------------------------------

        winning_outcome = ""

        if closed and is_resolved:

            if yes_price is not None and no_price is not None:

                if yes_price == 1.0 and no_price == 0.0:
                    winning_outcome = yes_label

                elif no_price == 1.0 and yes_price == 0.0:
                    winning_outcome = no_label

        if winning_outcome:
            winner_count += 1

        # --------------------------------------------------
        # 8. Записываем результаты в CSV
        # --------------------------------------------------

        writer.writerow({
            "condition_id": condition_id,
            "title": title,
            "closed": closed,
            "closed_time": closed_time,
            "end_date": end_date,
            "outcomes": json.dumps(
                outcomes,
                ensure_ascii=False
            ),
            "outcome_prices": json.dumps(
                outcome_prices,
                ensure_ascii=False
            ),
            "winning_outcome": winning_outcome,
            "uma_status": uma_status
        })


# --------------------------------------------------
# 9. Итоговая статистика
# --------------------------------------------------

print()
print("======================================")
print("ГОТОВО")
print("======================================")

print("Всего condition_id:", len(condition_ids))
print("Найдено рынков:", len(found_markets))
print("Не найдено:", len(not_found))
print("Ошибок:", error_count)

print()
print("Есть closed_time:", closed_time_count)
print("Со статусом resolved/settled:", resolved_count)
print("Определён победитель:", winner_count)

print()
print("Создан файл: market_outcomes.csv")

if not_found:
    print()
    print("Примеры ненайденных рынков:")

    for condition_id in not_found[:10]:
        print(condition_id)
