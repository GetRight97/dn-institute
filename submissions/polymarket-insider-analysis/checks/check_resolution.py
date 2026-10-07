import csv
import requests
import json


# --------------------------------------------------
# 1. Берём первый condition_id из market_dates.csv
# --------------------------------------------------

with open(
        "data/raw/market_dates.csv",
    "r",
    encoding="utf-8"
) as file:

    reader = csv.DictReader(file)

    first_market = next(reader)

condition_id = first_market["condition_id"]

print("Condition ID:")
print(condition_id)


# --------------------------------------------------
# 2. Запрашиваем рынок через Gamma API
# --------------------------------------------------

url = "https://gamma-api.polymarket.com/markets"

params = {
    "conditionId": condition_id
}

response = requests.get(
    url,
    params=params
)

print()
print("HTTP:", response.status_code)


# --------------------------------------------------
# 3. Показываем ответ
# --------------------------------------------------

data = response.json()

print()
print("Ответ API:")

print(
    json.dumps(
        data,
        indent=2,
        ensure_ascii=False
    )
)