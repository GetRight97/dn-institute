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
    / "trader_accuracy.csv"
)

LATE_HOURS = 24
MIN_BUYS_FOR_DISPLAY = 20


traders = defaultdict(
    lambda: {
        "buy_count": 0,
        "winning_buy_count": 0,
        "buy_volume": 0.0,
        "winning_buy_volume": 0.0,
        "late_buy_count": 0,
        "late_winning_buy_count": 0,
        "markets": set(),
        "max_buy_volume": 0.0,
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

        volume = (
            size
            * price
        )

        is_winning_buy = (
            trade.get(
                "is_winning_buy",
                "",
            )
            == "1"
        )

        hours_before_close = (
            trade.get(
                "hours_before_close",
                "",
            )
        )

        stats = traders[
            wallet
        ]

        stats[
            "buy_count"
        ] += 1

        stats[
            "buy_volume"
        ] += volume

        stats[
            "markets"
        ].add(
            trade.get(
                "condition_id",
                "",
            )
        )

        if (
            volume
            > stats[
                "max_buy_volume"
            ]
        ):
            stats[
                "max_buy_volume"
            ] = volume

        total_buy_count += 1

        if is_winning_buy:

            stats[
                "winning_buy_count"
            ] += 1

            stats[
                "winning_buy_volume"
            ] += volume

            total_winning_buy_count += 1

        if hours_before_close not in (
            "",
            None,
        ):
            try:
                hours = float(
                    hours_before_close
                )

            except (
                ValueError,
                TypeError,
            ):
                hours = None

            if (
                hours is not None
                and 0
                <= hours
                <= LATE_HOURS
            ):

                stats[
                    "late_buy_count"
                ] += 1

                if is_winning_buy:

                    stats[
                        "late_winning_buy_count"
                    ] += 1


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

    buy_volume = (
        stats[
            "buy_volume"
        ]
    )

    winning_buy_volume = (
        stats[
            "winning_buy_volume"
        ]
    )

    late_buy_count = (
        stats[
            "late_buy_count"
        ]
    )

    late_winning_buy_count = (
        stats[
            "late_winning_buy_count"
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

    winning_volume_ratio = (
        winning_buy_volume
        / buy_volume
        if buy_volume > 0
        else 0
    )

    late_hit_rate = (
        late_winning_buy_count
        / late_buy_count
        if late_buy_count > 0
        else 0
    )

    average_buy = (
        buy_volume
        / buy_count
        if buy_count > 0
        else 0
    )

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
                buy_volume,

            "winning_buy_volume":
                winning_buy_volume,

            "winning_volume_ratio":
                winning_volume_ratio,

            "average_buy":
                average_buy,

            "max_buy_volume":
                stats[
                    "max_buy_volume"
                ],

            "markets":
                len(
                    stats[
                        "markets"
                    ]
                ),

            "late_buy_count":
                late_buy_count,

            "late_winning_buy_count":
                late_winning_buy_count,

            "late_hit_rate":
                late_hit_rate,
        }
    )


filtered_results = [
    trader
    for trader in results
    if trader[
        "buy_count"
    ] >= MIN_BUYS_FOR_DISPLAY
]


filtered_results.sort(
    key=lambda trader: (
        trader[
            "hit_rate"
        ],
        trader[
            "buy_count"
        ],
    ),
    reverse=True,
)


print()
print(
    "======================================"
)
print(
    "TOP-30 BY BUY OUTCOME HIT RATE"
)
print(
    f"minimum {MIN_BUYS_FOR_DISPLAY} BUY"
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

print(
    "Unique BUY wallets:",
    len(results),
)


for trader in filtered_results[
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
        "Winning BUY:",
        trader[
            "winning_buy_count"
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
        "BUY volume:",
        round(
            trader[
                "buy_volume"
            ],
            2,
        ),
    )

    print(
        "Winning volume ratio:",
        round(
            trader[
                "winning_volume_ratio"
            ]
            * 100,
            2,
        ),
        "%",
    )

    print(
        "Average BUY:",
        round(
            trader[
                "average_buy"
            ],
            2,
        ),
    )

    print(
        "Max BUY:",
        round(
            trader[
                "max_buy_volume"
            ],
            2,
        ),
    )

    print(
        "Markets:",
        trader[
            "markets"
        ],
    )

    print(
        "Late BUY:",
        trader[
            "late_buy_count"
        ],
    )

    print(
        "Late hit rate:",
        round(
            trader[
                "late_hit_rate"
            ]
            * 100,
            2,
        ),
        "%",
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
        "winning_buy_volume",
        "winning_volume_ratio",
        "average_buy",
        "max_buy_volume",
        "markets",
        "late_buy_count",
        "late_winning_buy_count",
        "late_hit_rate",
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
    "Unique BUY wallets:",
    len(results),
)

print(
    "Wallets with >=",
    MIN_BUYS_FOR_DISPLAY,
    "BUY:",
    len(
        filtered_results
    ),
)

print(
    "Created:",
    OUTPUT_FILE,
)