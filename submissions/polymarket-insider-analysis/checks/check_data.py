from pathlib import Path
import csv


BASE_DIR = Path(__file__).resolve().parents[1]

TRADES_FILE = (
    BASE_DIR
    / "data"
    / "raw"
    / "trades.csv"
)


def main():
    trades = []

    with open(
        TRADES_FILE,
        "r",
        encoding="utf-8",
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            trades.append(row)

    print("Всего сделок:", len(trades))

    wallets = set()
    markets = set()

    for trade in trades:
        wallet = trade.get(
            "proxy_wallet",
            "",
        ).strip()

        condition_id = trade.get(
            "condition_id",
            "",
        ).strip()

        if wallet:
            wallets.add(wallet)

        if condition_id:
            markets.add(condition_id)

    print("Уникальных трейдеров:", len(wallets))
    print("Уникальных рынков:", len(markets))


if __name__ == "__main__":
    main()
