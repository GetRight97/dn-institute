import csv
import requests

# Берём наши рынки
with open("data/raw/market_dates.csv", "r", encoding="utf-8") as file:
    reader = csv.DictReader(file)

    for number, row in enumerate(reader, start=1):

        condition_id = row["condition_id"]

        url = "https://gamma-api.polymarket.com/markets"

        params = {
            "conditionId": condition_id
        }

        response = requests.get(url, params=params)

        if response.status_code != 200:
            print("Ошибка:", response.status_code)
            continue

        data = response.json()

        if not data:
            continue

        market = data[0]

        if market.get("closed") is True:

            print()
            print("==============================")
            print("НАЙДЕН ЗАКРЫТЫЙ РЫНОК")
            print("==============================")

            print("Номер:", number)
            print("Question:", market.get("question"))
            print("Condition ID:", market.get("conditionId"))
            print("Closed:", market.get("closed"))
            print("Active:", market.get("active"))
            print("Outcomes:", market.get("outcomes"))
            print("Outcome prices:", market.get("outcomePrices"))
            print("Resolved by:", market.get("resolvedBy"))
            print("UMA status:", market.get("umaResolutionStatuses"))
            print("End date:", market.get("endDate"))

            break

        if number % 100 == 0:
            print("Проверено рынков:", number)

print()
print("Готово!")