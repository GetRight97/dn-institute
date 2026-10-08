import csv
from collections import defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]

PROCESSED_DIR = BASE_DIR / "data" / "processed"
RESULTS_DIR = BASE_DIR / "results"

RESULTS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

INPUT_FILE = (
    PROCESSED_DIR
    / "trades_with_outcome.csv"
)

OUTPUT_FILE = (
    RESULTS_DIR
    / "trader_edge.csv"
)

MIN_BUYS = 20

LOW_PRICE_THRESHOLD = 0.50
VERY_LOW_PRICE_THRESHOLD = 0.25
LATE_HOURS = 24


traders = defaultdict(
    lambda: {
        "buy_count": 0,
        "winning_buy_count": 0,

        "buy_volume": 0.0,

        # BUY-only hold-to-resolution proxy.
        # This is NOT realized P&L.
        "profit_proxy": 0.0,

        "winning_price_sum": 0.0,

        "low_price_wins": 0,
        "very_low_price_wins": 0,
        "late_low_price_wins": 0,

        "markets": set(),

        "max_profit_trade": 0.0,
    }
)


total_buy_count = 0
total_winning_buy_count = 0


with open(
    INPUT_FILE,
    "r",
    encoding="utf-8",
) as file:

    reader = csv.DictReader(
        file
    )

    for trade in reader:

        side = trade.get(
            "side",
            "",
        ).upper()

        if side != "BUY":
            continue

        winning_outcome = trade.get(
            "winning_outcome",
            "",
        )

        if not winning_outcome:
            continue

        wallet = trade.get(
            "proxy_wallet",
            "",
        ).strip()

        if not wallet:
            continue

        try:
            size = float(
                trade.get(
                    "size",
                    0,
                )
            )

            price = float(
                trade.get(
                    "price",
                    0,
                )
            )

        except (
            ValueError,
            TypeError,
        ):
            continue

        if size < 0:
            continue

        if not (
            0 <= price <= 1
        ):
            continue

        volume = (
            size
            * price
        )

        is_winner = (
            trade.get(
                "is_winning_buy",
                "",
            )
            == "1"
        )

        hours_raw = trade.get(
            "hours_before_close",
            "",
        )

        hours = None

        if hours_raw not in (
            "",
            None,
        ):
            try:
                hours = float(
                    hours_raw
                )
            except (
                ValueError,
                TypeError,
            ):
                hours = None

        stats = traders[
            wallet
        ]

        stats[
            "buy_count"
        ] += 1

        stats[
            "buy_volume"
        ] += volume

        condition_id = trade.get(
            "condition_id",
            "",
        )

        if condition_id:
            stats[
                "markets"
            ].add(
                condition_id
            )

        total_buy_count += 1

        if is_winner:

            total_winning_buy_count += 1

            stats[
                "winning_buy_count"
            ] += 1

            stats[
                "winning_price_sum"
            ] += price

            # If held to settlement:
            # cost = size * price
            # payout = size
            # proxy profit = size * (1 - price)
            profit = (
                size
                * (1 - price)
            )

            stats[
                "profit_proxy"
            ] += profit

            if (
                profit
                > stats[
                    "max_profit_trade"
                ]
            ):
                stats[
                    "max_profit_trade"
                ] = profit

            if (
                price
                <= LOW_PRICE_THRESHOLD
            ):
                stats[
                    "low_price_wins"
                ] += 1

            if (
                price
                <= VERY_LOW_PRICE_THRESHOLD
            ):
                stats[
                    "very_low_price_wins"
                ] += 1

            if (
                price
                <= LOW_PRICE_THRESHOLD
                and hours is not None
                and 0
                <= hours
                <= LATE_HOURS
            ):
                stats[
                    "late_low_price_wins"
                ] += 1

        else:

            # If held to settlement:
            # losing BUY expires worthless.
            loss = (
                size
                * price
            )

            stats[
                "profit_proxy"
            ] -= loss


baseline_hit_rate = (
    total_winning_buy_count
    / total_buy_count
    if total_buy_count > 0
    else 0
)


results = []


for wallet, stats in traders.items():

    buy_count = (
        stats[
            "buy_count"
        ]
    )

    winning_buy_count = (
        stats[
            "winning_buy_count"
        ]
    )

    hit_rate = (
        winning_buy_count
        / buy_count
        if buy_count > 0
        else 0
    )

    edge_vs_baseline = (
        hit_rate
        - baseline_hit_rate
    )

    if winning_buy_count > 0:

        average_winning_price = (
            stats[
                "winning_price_sum"
            ]
            / winning_buy_count
        )

    else:

        average_winning_price = 0.0

    results.append(
        {
            "wallet": wallet,

            "buy_count":
                buy_count,

            "winning_buy_count":
                winning_buy_count,

            "hit_rate":
                hit_rate,

            "baseline_hit_rate":
                baseline_hit_rate,

            "edge_vs_baseline":
                edge_vs_baseline,

            "buy_volume":
                stats[
                    "buy_volume"
                ],

            "profit_proxy":
                stats[
                    "profit_proxy"
                ],

            "average_winning_price":
                average_winning_price,

            "low_price_wins":
                stats[
                    "low_price_wins"
                ],

            "very_low_price_wins":
                stats[
                    "very_low_price_wins"
                ],

            "late_low_price_wins":
                stats[
                    "late_low_price_wins"
                ],

            "max_profit_trade":
                stats[
                    "max_profit_trade"
                ],

            "markets":
                len(
                    stats[
                        "markets"
                    ]
                ),
        }
    )


filtered = [
    trader
    for trader in results
    if trader[
        "buy_count"
    ] >= MIN_BUYS
]


filtered.sort(
    key=lambda trader: (
        trader[
            "very_low_price_wins"
        ],
        trader[
            "late_low_price_wins"
        ],
        trader[
            "profit_proxy"
        ],
    ),
    reverse=True,
)


print()
print(
    "======================================"
)
print(
    "TOP-30 BY UNEXPECTED WINNING BUY SIGNALS"
)
print(
    "======================================"
)

print()
print(
    "Global BUY baseline:",
    round(
        baseline_hit_rate
        * 100,
        2,
    ),
    "%",
)


for trader in filtered[
    :30
]:

    print()

    print(
        "Wallet:",
        trader[
            "wallet"
        ],
    )

    print(
        "BUY:",
        trader[
            "buy_count"
        ],
    )

    print(
        "Hit rate:",
        round(
            trader[
                "hit_rate"
            ]
            * 100,
            2,
        ),
        "%",
    )

    print(
        "Edge vs baseline:",
        round(
            trader[
                "edge_vs_baseline"
            ]
            * 100,
            2,
        ),
        "pp",
    )

    print(
        "Markets:",
        trader[
            "markets"
        ],
    )

    print(
        "BUY volume:",
        round(
            trader[
                "buy_volume"
            ],
            2,
        ),
    )

    print(
        "BUY-only hold-to-resolution "
        "profit proxy:",
        round(
            trader[
                "profit_proxy"
            ],
            2,
        ),
    )

    print(
        "Average winning price:",
        round(
            trader[
                "average_winning_price"
            ],
            4,
        ),
    )

    print(
        "Winning BUY <= 0.50:",
        trader[
            "low_price_wins"
        ],
    )

    print(
        "Winning BUY <= 0.25:",
        trader[
            "very_low_price_wins"
        ],
    )

    print(
        "Late winning BUY <= 0.50:",
        trader[
            "late_low_price_wins"
        ],
    )

    print(
        "Max proxy profit trade:",
        round(
            trader[
                "max_profit_trade"
            ],
            2,
        ),
    )


with open(
    OUTPUT_FILE,
    "w",
    newline="",
    encoding="utf-8",
) as file:

    fieldnames = [
        "wallet",
        "buy_count",
        "winning_buy_count",
        "hit_rate",
        "baseline_hit_rate",
        "edge_vs_baseline",
        "buy_volume",
        "profit_proxy",
        "average_winning_price",
        "low_price_wins",
        "very_low_price_wins",
        "late_low_price_wins",
        "max_profit_trade",
        "markets",
    ]

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames,
    )

    writer.writeheader()

    for trader in results:
        writer.writerow(
            trader
        )


print()
print(
    "======================================"
)
print(
    "DONE"
)
print(
    "======================================"
)

print(
    "Total BUY:",
    total_buy_count,
)

print(
    "Winning BUY:",
    total_winning_buy_count,
)

print(
    "Global BUY baseline:",
    round(
        baseline_hit_rate
        * 100,
        2,
    ),
    "%",
)

print(
    "Wallets analyzed:",
    len(results),
)

print(
    "Wallets with >=",
    MIN_BUYS,
    "BUY:",
    len(filtered),
)

print(
    "Created:",
    OUTPUT_FILE,
)