import csv
import math
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
RESULTS_DIR = BASE_DIR / "results"

RESULTS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

INPUT_FILE = (
    RESULTS_DIR
    / "trader_market_signals.csv"
)

FULL_OUTPUT_FILE = (
    RESULTS_DIR
    / "insider_ranking.csv"
)

TOP100_OUTPUT_FILE = (
    RESULTS_DIR
    / "insider_ranking_top100.csv"
)

TOP_N = 100


def cap_ratio(value, target):
    if target <= 0:
        return 0.0

    return min(
        max(
            value / target,
            0.0,
        ),
        1.0,
    )


# --------------------------------------------------
# 1. Load wallet-level market signals
# --------------------------------------------------

traders = []


with open(
    INPUT_FILE,
    "r",
    encoding="utf-8",
) as file:

    reader = csv.DictReader(
        file
    )

    for row in reader:

        wallet = row.get(
            "wallet",
            "",
        ).strip()

        if not wallet:
            continue

        trader = {
            "wallet":
                wallet,

            "markets":
                int(
                    row[
                        "markets"
                    ]
                ),

            "total_buy_count":
                int(
                    row[
                        "total_buy_count"
                    ]
                ),

            "total_winning_buy_count":
                int(
                    row[
                        "total_winning_buy_count"
                    ]
                ),

            "hit_rate":
                float(
                    row[
                        "hit_rate"
                    ]
                ),

            "total_buy_volume":
                float(
                    row[
                        "total_buy_volume"
                    ]
                ),

            "profit_proxy":
                float(
                    row[
                        "profit_proxy"
                    ]
                ),

            "profitable_markets":
                int(
                    row[
                        "profitable_markets"
                    ]
                ),

            "profitable_market_ratio":
                float(
                    row[
                        "profitable_market_ratio"
                    ]
                ),

            "low_price_win_markets":
                int(
                    row[
                        "low_price_win_markets"
                    ]
                ),

            "low_price_win_market_ratio":
                float(
                    row[
                        "low_price_win_market_ratio"
                    ]
                ),

            "very_low_price_win_markets":
                int(
                    row[
                        "very_low_price_win_markets"
                    ]
                ),

            "very_low_price_win_market_ratio":
                float(
                    row[
                        "very_low_price_win_market_ratio"
                    ]
                ),

            "late_low_price_win_markets":
                int(
                    row[
                        "late_low_price_win_markets"
                    ]
                ),

            "late_low_price_win_market_ratio":
                float(
                    row[
                        "late_low_price_win_market_ratio"
                    ]
                ),
        }

        traders.append(
            trader
        )


if not traders:
    raise RuntimeError(
        "trader_market_signals.csv contains no traders."
    )


print(
    "Loaded traders:",
    len(traders),
)


# --------------------------------------------------
# 2. Global BUY baseline
# --------------------------------------------------

global_buy_count = sum(
    trader[
        "total_buy_count"
    ]
    for trader in traders
)

global_winning_buy_count = sum(
    trader[
        "total_winning_buy_count"
    ]
    for trader in traders
)


baseline_hit_rate = (
    global_winning_buy_count
    / global_buy_count
    if global_buy_count > 0
    else 0.0
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


# --------------------------------------------------
# 3. Calculate candidate score
# --------------------------------------------------

results = []


for trader in traders:

    markets = trader[
        "markets"
    ]

    buy_count = trader[
        "total_buy_count"
    ]

    hit_rate = trader[
        "hit_rate"
    ]

    very_low_markets = trader[
        "very_low_price_win_markets"
    ]

    very_low_ratio = trader[
        "very_low_price_win_market_ratio"
    ]

    late_markets = trader[
        "late_low_price_win_markets"
    ]

    late_ratio = trader[
        "late_low_price_win_market_ratio"
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

    edge_vs_baseline = (
        hit_rate
        - baseline_hit_rate
    )


    # --------------------------------------------------
    # A. Very-low-price evidence
    # max 25
    # --------------------------------------------------

    very_low_count_score = (
        cap_ratio(
            very_low_markets,
            4,
        )
        * 15
    )

    very_low_ratio_score = (
        cap_ratio(
            very_low_ratio,
            0.75,
        )
        * 10
    )

    very_low_score = (
        very_low_count_score
        + very_low_ratio_score
    )


    # --------------------------------------------------
    # B. Late low-price evidence
    # max 20
    # --------------------------------------------------

    late_count_score = (
        cap_ratio(
            late_markets,
            3,
        )
        * 10
    )

    late_ratio_score = (
        cap_ratio(
            late_ratio,
            0.25,
        )
        * 10
    )

    late_score = (
        late_count_score
        + late_ratio_score
    )


    # --------------------------------------------------
    # C. Hit-rate edge
    # max 20
    # --------------------------------------------------

    positive_edge = max(
        edge_vs_baseline,
        0.0,
    )

    hit_edge_score = (
        cap_ratio(
            positive_edge,
            0.25,
        )
        * 20
    )


    # --------------------------------------------------
    # D. Profitable market ratio
    # max 15
    # --------------------------------------------------

    profitable_score = (
        cap_ratio(
            profitable_ratio,
            0.80,
        )
        * 15
    )


    # --------------------------------------------------
    # E. BUY-only profit proxy
    # max 10
    # --------------------------------------------------

    positive_profit = max(
        profit_proxy,
        0.0,
    )

    profit_score = (
        cap_ratio(
            math.log1p(
                positive_profit
            ),
            math.log1p(
                100000
            ),
        )
        * 10
    )


    # --------------------------------------------------
    # F. Market breadth
    # max 5
    # --------------------------------------------------

    market_score = (
        cap_ratio(
            markets,
            8,
        )
        * 5
    )


    # --------------------------------------------------
    # G. BUY volume
    # max 5
    # --------------------------------------------------

    positive_volume = max(
        volume,
        0.0,
    )

    volume_score = (
        cap_ratio(
            math.log1p(
                positive_volume
            ),
            math.log1p(
                100000
            ),
        )
        * 5
    )


    raw_candidate_score = (
        very_low_score
        + late_score
        + hit_edge_score
        + profitable_score
        + profit_score
        + market_score
        + volume_score
    )


    # --------------------------------------------------
    # Reliability adjustment
    # --------------------------------------------------

    buy_reliability = (
        0.5
        + 0.5
        * cap_ratio(
            buy_count,
            100,
        )
    )

    market_reliability = (
        0.6
        + 0.4
        * cap_ratio(
            markets,
            6,
        )
    )

    reliability_factor = (
        buy_reliability
        * market_reliability
    )

    candidate_score = (
        raw_candidate_score
        * reliability_factor
    )


    # --------------------------------------------------
    # Signal level
    # --------------------------------------------------

    if candidate_score >= 75:
        signal_level = (
            "VERY HIGH"
        )

    elif candidate_score >= 60:
        signal_level = (
            "HIGH"
        )

    elif candidate_score >= 45:
        signal_level = (
            "ELEVATED"
        )

    elif candidate_score >= 30:
        signal_level = (
            "MODERATE"
        )

    else:
        signal_level = (
            "LOW"
        )


    results.append(
        {
            **trader,

            "baseline_hit_rate":
                baseline_hit_rate,

            "edge_vs_baseline":
                edge_vs_baseline,

            "very_low_count_score":
                very_low_count_score,

            "very_low_ratio_score":
                very_low_ratio_score,

            "very_low_score":
                very_low_score,

            "late_count_score":
                late_count_score,

            "late_ratio_score":
                late_ratio_score,

            "late_score":
                late_score,

            "hit_edge_score":
                hit_edge_score,

            "profitable_score":
                profitable_score,

            "profit_score":
                profit_score,

            "market_score":
                market_score,

            "volume_score":
                volume_score,

            "raw_candidate_score":
                raw_candidate_score,

            "reliability_factor":
                reliability_factor,

            "candidate_score":
                candidate_score,

            "signal_level":
                signal_level,
        }
    )


# --------------------------------------------------
# 4. Sort ranking
# --------------------------------------------------

results.sort(
    key=lambda trader: (
        trader[
            "candidate_score"
        ],
        trader[
            "raw_candidate_score"
        ],
        trader[
            "total_buy_count"
        ],
    ),
    reverse=True,
)


# --------------------------------------------------
# 5. Display TOP-30
# --------------------------------------------------

print()
print(
    "======================================"
)
print(
    "TOP-30 POTENTIALLY INFORMED "
    "TRADING CANDIDATES"
)
print(
    "======================================"
)


for rank, trader in enumerate(
    results[:30],
    start=1,
):

    print()

    print(
        "Rank:",
        rank,
    )

    print(
        "Wallet:",
        trader[
            "wallet"
        ],
    )

    print(
        "Candidate score:",
        round(
            trader[
                "candidate_score"
            ],
            2,
        ),
        "/ 100",
    )

    print(
        "Signal level:",
        trader[
            "signal_level"
        ],
    )

    print(
        "Reliability:",
        round(
            trader[
                "reliability_factor"
            ]
            * 100,
            2,
        ),
        "%",
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
        "BUY-only profit proxy:",
        round(
            trader[
                "profit_proxy"
            ],
            2,
        ),
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


# --------------------------------------------------
# 6. CSV field order
# --------------------------------------------------

fieldnames = [
    "rank",
    "wallet",

    "candidate_score",
    "raw_candidate_score",
    "reliability_factor",
    "signal_level",

    "markets",
    "total_buy_count",
    "total_winning_buy_count",

    "hit_rate",
    "baseline_hit_rate",
    "edge_vs_baseline",

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

    "very_low_count_score",
    "very_low_ratio_score",
    "very_low_score",

    "late_count_score",
    "late_ratio_score",
    "late_score",

    "hit_edge_score",
    "profitable_score",
    "profit_score",
    "market_score",
    "volume_score",
]


def write_ranking_csv(
    output_file,
    rows,
):
    with open(
        output_file,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for rank, trader in enumerate(
            rows,
            start=1,
        ):

            row = {
                key: trader[key]
                for key in fieldnames
                if key != "rank"
            }

            row[
                "rank"
            ] = rank

            writer.writerow(
                row
            )


# --------------------------------------------------
# 7. Save full ranking
# --------------------------------------------------

write_ranking_csv(
    FULL_OUTPUT_FILE,
    results,
)


# --------------------------------------------------
# 8. Save compact TOP-100 ranking
# --------------------------------------------------

write_ranking_csv(
    TOP100_OUTPUT_FILE,
    results[:TOP_N],
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
    "Traders ranked:",
    len(results),
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
    "Full ranking:",
    FULL_OUTPUT_FILE,
)

print(
    f"TOP-{TOP_N} ranking:",
    TOP100_OUTPUT_FILE,
)