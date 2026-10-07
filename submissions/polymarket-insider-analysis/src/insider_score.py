import csv
import math
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
RESULTS_DIR = BASE_DIR / "results"

RESULTS_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# --------------------------------------------------
# 1. Загружаем trader_market_signals.csv
# --------------------------------------------------

traders = []

with open(
    RESULTS_DIR / "trader_market_signals.csv",
    "r",
    encoding="utf-8"
) as file:

    reader = csv.DictReader(file)

    for row in reader:

        trader = {
            "wallet": row["wallet"],

            "markets":
                int(row["markets"]),

            "total_buy_count":
                int(row["total_buy_count"]),

            "total_buy_volume":
                float(row["total_buy_volume"]),

            "profit_proxy":
                float(row["profit_proxy"]),

            "profitable_markets":
                int(row["profitable_markets"]),

            "profitable_market_ratio":
                float(row["profitable_market_ratio"]),

            "low_price_win_markets":
                int(row["low_price_win_markets"]),

            "very_low_price_win_markets":
                int(row["very_low_price_win_markets"]),

            "late_low_price_win_markets":
                int(row["late_low_price_win_markets"])
        }

        traders.append(trader)


print(
    "Загружено трейдеров:",
    len(traders)
)


# --------------------------------------------------
# 2. Вспомогательная функция
# --------------------------------------------------

def cap_ratio(value, target):

    """
    Если value >= target:
        возвращает 1

    Если меньше:
        пропорционально 0..1
    """

    if target <= 0:
        return 0

    return min(
        value / target,
        1
    )


# --------------------------------------------------
# 3. Рассчитываем score
# --------------------------------------------------

results = []


for trader in traders:

    markets = trader["markets"]

    very_low_markets = trader[
        "very_low_price_win_markets"
    ]

    late_markets = trader[
        "late_low_price_win_markets"
    ]

    profitable_ratio = trader[
        "profitable_market_ratio"
    ]

    profit_proxy = trader[
        "profit_proxy"
    ]

    volume = trader[
        "total_buy_volume"
    ]


    # --------------------------------------------------
    # A. Very-low-price wins
    # max 25
    #
    # 10 таких рынков = максимум
    # --------------------------------------------------

    very_low_score = (
        cap_ratio(
            very_low_markets,
            10
        )
        * 25
    )


    # --------------------------------------------------
    # B. Late low-price wins
    # max 20
    #
    # 5 рынков = максимум
    # --------------------------------------------------

    late_score = (
        cap_ratio(
            late_markets,
            5
        )
        * 20
    )


    # --------------------------------------------------
    # C. Profitable market ratio
    # max 20
    #
    # 80%+ = максимум
    # --------------------------------------------------

    profitable_score = (
        cap_ratio(
            profitable_ratio,
            0.80
        )
        * 20
    )


    # --------------------------------------------------
    # D. Profit proxy
    # max 15
    #
    # Используем log,
    # чтобы один огромный трейдер
    # не уничтожил весь рейтинг
    # --------------------------------------------------

    positive_profit = max(
        profit_proxy,
        0
    )

    profit_score = (
        cap_ratio(
            math.log1p(
                positive_profit
            ),
            math.log1p(
                50000
            )
        )
        * 15
    )


    # --------------------------------------------------
    # E. Повторяемость по рынкам
    # max 10
    #
    # 30 рынков = максимум
    # --------------------------------------------------

    market_score = (
        cap_ratio(
            markets,
            30
        )
        * 10
    )


    # --------------------------------------------------
    # F. BUY volume
    # max 10
    #
    # $100k+ = максимум
    # --------------------------------------------------

    volume_score = (
        cap_ratio(
            math.log1p(
                volume
            ),
            math.log1p(
                100000
            )
        )
        * 10
    )


    # --------------------------------------------------
    # Итоговый score
    # --------------------------------------------------

    insider_score = (
        very_low_score
        + late_score
        + profitable_score
        + profit_score
        + market_score
        + volume_score
    )


    # --------------------------------------------------
    # Категория риска
    # --------------------------------------------------

    if insider_score >= 80:

        risk_level = "VERY HIGH"

    elif insider_score >= 65:

        risk_level = "HIGH"

    elif insider_score >= 50:

        risk_level = "ELEVATED"

    elif insider_score >= 35:

        risk_level = "MODERATE"

    else:

        risk_level = "LOW"


    results.append({

        **trader,

        "very_low_score":
            very_low_score,

        "late_score":
            late_score,

        "profitable_score":
            profitable_score,

        "profit_score":
            profit_score,

        "market_score":
            market_score,

        "volume_score":
            volume_score,

        "insider_score":
            insider_score,

        "risk_level":
            risk_level
    })


# --------------------------------------------------
# 4. Сортируем
# --------------------------------------------------

results.sort(
    key=lambda trader:
        trader["insider_score"],
    reverse=True
)


# --------------------------------------------------
# 5. TOP-30
# --------------------------------------------------

print()
print(
    "======================================"
)

print(
    "TOP-30 POTENTIALLY INFORMED TRADERS"
)

print(
    "======================================"
)


for trader in results[:30]:

    print()

    print(
        "Wallet:",
        trader["wallet"]
    )

    print(
        "Score:",
        round(
            trader["insider_score"],
            2
        ),
        "/ 100"
    )

    print(
        "Risk:",
        trader["risk_level"]
    )

    print(
        "Markets:",
        trader["markets"]
    )

    print(
        "Profitable ratio:",
        round(
            trader[
                "profitable_market_ratio"
            ] * 100,
            2
        ),
        "%"
    )

    print(
        "Very-low-price win markets:",
        trader[
            "very_low_price_win_markets"
        ]
    )

    print(
        "Late low-price win markets:",
        trader[
            "late_low_price_win_markets"
        ]
    )

    print(
        "Profit proxy:",
        round(
            trader["profit_proxy"],
            2
        )
    )

    print(
        "BUY volume:",
        round(
            trader["total_buy_volume"],
            2
        )
    )


# --------------------------------------------------
# 6. Сохраняем insider_ranking.csv
# --------------------------------------------------

with open(
    RESULTS_DIR / "insider_ranking.csv",
    "w",
    newline="",
    encoding="utf-8"
) as file:

    fieldnames = [
        "rank",
        "wallet",
        "insider_score",
        "risk_level",

        "markets",
        "total_buy_count",
        "total_buy_volume",
        "profit_proxy",

        "profitable_markets",
        "profitable_market_ratio",

        "low_price_win_markets",
        "very_low_price_win_markets",
        "late_low_price_win_markets",

        "very_low_score",
        "late_score",
        "profitable_score",
        "profit_score",
        "market_score",
        "volume_score"
    ]

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames
    )

    writer.writeheader()


    for rank, trader in enumerate(
        results,
        start=1
    ):

        writer.writerow({

            "rank":
                rank,

            "wallet":
                trader["wallet"],

            "insider_score":
                round(
                    trader[
                        "insider_score"
                    ],
                    4
                ),

            "risk_level":
                trader["risk_level"],

            "markets":
                trader["markets"],

            "total_buy_count":
                trader[
                    "total_buy_count"
                ],

            "total_buy_volume":
                trader[
                    "total_buy_volume"
                ],

            "profit_proxy":
                trader[
                    "profit_proxy"
                ],

            "profitable_markets":
                trader[
                    "profitable_markets"
                ],

            "profitable_market_ratio":
                trader[
                    "profitable_market_ratio"
                ],

            "low_price_win_markets":
                trader[
                    "low_price_win_markets"
                ],

            "very_low_price_win_markets":
                trader[
                    "very_low_price_win_markets"
                ],

            "late_low_price_win_markets":
                trader[
                    "late_low_price_win_markets"
                ],

            "very_low_score":
                trader[
                    "very_low_score"
                ],

            "late_score":
                trader[
                    "late_score"
                ],

            "profitable_score":
                trader[
                    "profitable_score"
                ],

            "profit_score":
                trader[
                    "profit_score"
                ],

            "market_score":
                trader[
                    "market_score"
                ],

            "volume_score":
                trader[
                    "volume_score"
                ]
        })


print()

print(
    "======================================"
)

print(
    "Создан файл: insider_ranking.csv"
)

print(
    "======================================"
)