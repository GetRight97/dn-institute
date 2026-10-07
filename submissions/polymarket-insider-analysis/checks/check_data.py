import csv

trades = []

with open("data/raw/trades.csv", "r", encoding="utf-8") as file:
    reader = csv.DictReader(file)

    for row in reader:
        trades.append(row)

print("Всего сделок:", len(trades))

wallets = set()
markets = set()

for trade in trades:
    wallets.add(trade["proxy_wallet"])
    markets.add(trade["condition_id"])

print("Уникальных трейдеров:", len(wallets))
print("Уникальных рынков:", len(markets))