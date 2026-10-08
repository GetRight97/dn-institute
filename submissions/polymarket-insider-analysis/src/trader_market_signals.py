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
    / "trader_market_signals.csv"
)


LOW_PRICE_THRESHOLD = 0.50
VERY_LOW_PRICE_THRESHOLD = 0.25
LATE_HOURS = 24

MIN_MARKETS = 3


# --------------------------------------------------
# 1. Aggregate wallet + market
# --------------------------------------------------

post_close_buy_excluded = 0
missing_timing_buy_excluded = 0

trader_markets = defaultdict(
    lambda: {
        "buy_count": 0,
        "buy_volume": 0.0,

        "winning_buy_count": 0,
        "winning_volume": 0.0,

        # BUY-only hold-to-resolution proxy.
        # NOT realized P&L.
        "profit_proxy": 0.0,

        "min_winning_price": None,

        "low_price_win": False,
        "very_low_price_win": False,
        "late_low_price_win": False,
    }
)


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

        condition_id = trade.get(
            "condition_id",
            "",
        ).strip()

        if not condition_id:
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

        # Keep post-close rows in the enriched input for
        # diagnostics, but exclude them from predictive
        # wallet-market aggregates to prevent outcome leakage.
        if hours_raw in (
            "",
            None,
        ):
            missing_timing_buy_excluded += 1
            continue

        try:
            hours = float(
                hours_raw
            )

        except (
            ValueError,
            TypeError,
        ):
            missing_timing_buy_excluded += 1
            continue

        if hours < 0:
            post_close_buy_excluded += 1
            continue

        key = (
            wallet,
            condition_id,
        )

        stats = trader_markets[
            key
        ]

        stats[
            "buy_count"
        ] += 1

        stats[
            "buy_volume"
        ] += volume

        # --------------------------------------------------
        # Winning BUY
        # --------------------------------------------------

        if is_winner:

            stats[
                "winning_buy_count"
            ] += 1

            stats[
                "winning_volume"
            ] += volume

            # BUY-only hold-to-resolution
            # proxy profit.
            profit = (
                size
                * (1 - price)
            )

            stats[
                "profit_proxy"
            ] += profit

            current_min = stats[
                "min_winning_price"
            ]

            if (
                current_min is None
                or price < current_min
            ):
                stats[
                    "min_winning_price"
                ] = price

            if (
                price
                <= LOW_PRICE_THRESHOLD
            ):
                stats[
                    "low_price_win"
                ] = True

            if (
                price
                <= VERY_LOW_PRICE_THRESHOLD
            ):
                stats[
                    "very_low_price_win"
                ] = True

            if (
                price
                <= LOW_PRICE_THRESHOLD
                and hours is not None
                and 0
                <= hours
                <= LATE_HOURS
            ):
                stats[
                    "late_low_price_win"
                ] = True

        # --------------------------------------------------
        # Losing BUY
        # --------------------------------------------------

        else:

            loss = (
                size
                * price
            )

            stats[
                "profit_proxy"
            ] -= loss


# --------------------------------------------------
# 2. Aggregate across markets by wallet
# --------------------------------------------------

traders = defaultdict(
    lambda: {
        "markets": 0,

        "profitable_markets": 0,

        "low_price_win_markets": 0,
        "very_low_price_win_markets": 0,
        "late_low_price_win_markets": 0,

        "profit_proxy": 0.0,

        "total_buy_volume": 0.0,
        "total_buy_count": 0,
        "total_winning_buy_count": 0,
    }
)


for (
    wallet,
    condition_id,
), stats in trader_markets.items():

    trader = traders[
        wallet
    ]

    trader[
        "markets"
    ] += 1

    trader[
        "profit_proxy"
    ] += stats[
        "profit_proxy"
    ]

    trader[
        "total_buy_volume"
    ] += stats[
        "buy_volume"
    ]

    trader[
        "total_buy_count"
    ] += stats[
        "buy_count"
    ]

    trader[
        "total_winning_buy_count"
    ] += stats[
        "winning_buy_count"
    ]

    if (
        stats[
            "profit_proxy"
        ] > 0
    ):
        trader[
            "profitable_markets"
        ] += 1

    if stats[
        "low_price_win"
    ]:
        trader[
            "low_price_win_markets"
        ] += 1

    if stats[
        "very_low_price_win"
    ]:
        trader[
            "very_low_price_win_markets"
        ] += 1

    if stats[
        "late_low_price_win"
    ]:
        trader[
            "late_low_price_win_markets"
        ] += 1


# --------------------------------------------------
# 3. Build result table
# --------------------------------------------------

results = []


for wallet, stats in traders.items():

    markets = stats[
        "markets"
    ]

    total_buy_count = stats[
        "total_buy_count"
    ]

    total_winning_buy_count = stats[
        "total_winning_buy_count"
    ]

    profitable_market_ratio = (
        stats[
            "profitable_markets"
        ]
        / markets
        if markets > 0
        else 0
    )

    low_price_win_market_ratio = (
        stats[
            "low_price_win_markets"
        ]
        / markets
        if markets > 0
        else 0
    )

    very_low_price_win_market_ratio = (
        stats[
            "very_low_price_win_markets"
        ]
        / markets
        if markets > 0
        else 0
    )

    late_low_price_win_market_ratio = (
        stats[
            "late_low_price_win_markets"
        ]
        / markets
        if markets > 0
        else 0
    )

    hit_rate = (
        total_winning_buy_count
        / total_buy_count
        if total_buy_count > 0
        else 0
    )

    results.append(
        {
            "wallet":
                wallet,

            "markets":
                markets,

            "total_buy_count":
                total_buy_count,

            "total_winning_buy_count":
                total_winning_buy_count,

            "hit_rate":
                hit_rate,

            "total_buy_volume":
                stats[
                    "total_buy_volume"
                ],

            "profit_proxy":
                stats[
                    "profit_proxy"
                ],

            "profitable_markets":
                stats[
                    "profitable_markets"
                ],

            "profitable_market_ratio":
                profitable_market_ratio,

            "low_price_win_markets":
                stats[
                    "low_price_win_markets"
                ],

            "low_price_win_market_ratio":
                low_price_win_market_ratio,

            "very_low_price_win_markets":
                stats[
                    "very_low_price_win_markets"
                ],

            "very_low_price_win_market_ratio":
                very_low_price_win_market_ratio,

            "late_low_price_win_markets":
                stats[
                    "late_low_price_win_markets"
                ],

            "late_low_price_win_market_ratio":
                late_low_price_win_market_ratio,
        }
    )


# --------------------------------------------------
# 4. Filter
# --------------------------------------------------

filtered = [
    trader
    for trader in results
    if trader[
        "markets"
    ] >= MIN_MARKETS
]


# Prefer repeated cross-market evidence.
filtered.sort(
    key=lambda trader: (
        trader[
            "very_low_price_win_markets"
        ],
        trader[
            "late_low_price_win_markets"
        ],
        trader[
            "profitable_market_ratio"
        ],
        trader[
            "profit_proxy"
        ],
    ),
    reverse=True,
)


# --------------------------------------------------
# 5. TOP 30
# --------------------------------------------------

print()
print(
    "======================================"
)
print(
    "TOP-30 BY CROSS-MARKET SIGNAL REPETITION"
)
print(
    f"minimum {MIN_MARKETS} markets"
)
print(
    "======================================"
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
        "Markets:",
        trader[
            "markets"
        ],
    )

    print(
        "BUY:",
        trader[
            "total_buy_count"
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
        "Profitable markets:",
        trader[
            "profitable_markets"
        ],
    )

    print(
        "Profitable market ratio:",
        round(
            trader[
                "profitable_market_ratio"
            ]
            * 100,
            2,
        ),
        "%",
    )

    print(
        "Low-price win markets:",
        trader[
            "low_price_win_markets"
        ],
        "/",
        trader[
            "markets"
        ],
    )

    print(
        "Very-low-price win markets:",
        trader[
            "very_low_price_win_markets"
        ],
        "/",
        trader[
            "markets"
        ],
    )

    print(
        "Very-low-price market ratio:",
        round(
            trader[
                "very_low_price_win_market_ratio"
            ]
            * 100,
            2,
        ),
        "%",
    )

    print(
        "Late low-price win markets:",
        trader[
            "late_low_price_win_markets"
        ],
        "/",
        trader[
            "markets"
        ],
    )

    print(
        "Late market ratio:",
        round(
            trader[
                "late_low_price_win_market_ratio"
            ]
            * 100,
            2,
        ),
        "%",
    )

    print(
        "BUY volume:",
        round(
            trader[
                "total_buy_volume"
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


# --------------------------------------------------
# 6. Save CSV
# --------------------------------------------------

with open(
    OUTPUT_FILE,
    "w",
    newline="",
    encoding="utf-8",
) as file:

    fieldnames = [
        "wallet",
        "markets",
        "total_buy_count",
        "total_winning_buy_count",
        "hit_rate",
        "total_buy_volume",
        "profit_proxy",
        "profitable_markets",
        "profitable_market_ratio",
        "low_price_win_markets",
        "low_price_win_market_ratio",
        "very_low_price_win_markets",
        "very_low_price_win_market_ratio",
        "late_low_price_win_markets",
        "late_low_price_win_market_ratio",
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
    "Wallets analyzed:",
    len(results),
)

print(
    "Wallets with >=",
    MIN_MARKETS,
    "markets:",
    len(filtered),
)

print(
    "Wallet-market combinations:",
    len(trader_markets),
)

print(
    "Post-close BUY excluded from predictive aggregates:",
    post_close_buy_excluded,
)

print(
    "BUY with missing/invalid timing excluded:",
    missing_timing_buy_excluded,
)

print(
    "Created:",
    OUTPUT_FILE,
)