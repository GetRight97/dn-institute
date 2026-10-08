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

RANKING_FILE = (
    RESULTS_DIR
    / "insider_ranking.csv"
)

TRADES_FILE = (
    PROCESSED_DIR
    / "trades_with_outcome.csv"
)

OUTPUT_FILE = (
    RESULTS_DIR
    / "candidate_details.csv"
)

TOP_CANDIDATES = 10
LOW_PRICE_THRESHOLD = 0.50
VERY_LOW_PRICE_THRESHOLD = 0.25
LATE_HOURS = 24


def load_top_candidates():
    top_candidates = {}

    with open(
        RANKING_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        reader = csv.DictReader(
            file
        )

        for row in reader:

            try:
                rank = int(
                    row["rank"]
                )

            except (
                ValueError,
                TypeError,
                KeyError,
            ):
                continue

            if rank > TOP_CANDIDATES:
                continue

            wallet = row.get(
                "wallet",
                "",
            ).strip()

            if not wallet:
                continue

            top_candidates[
                wallet
            ] = {
                "candidate_rank":
                    rank,
                "candidate_score":
                    float(
                        row.get(
                            "candidate_score",
                            0,
                        )
                    ),
                "signal_level":
                    row.get(
                        "signal_level",
                        "",
                    ),
                "candidate_hit_rate":
                    float(
                        row.get(
                            "hit_rate",
                            0,
                        )
                    ),
                "edge_vs_baseline":
                    float(
                        row.get(
                            "edge_vs_baseline",
                            0,
                        )
                    ),
                "candidate_markets":
                    int(
                        row.get(
                            "markets",
                            0,
                        )
                    ),
            }

    if len(
        top_candidates
    ) != TOP_CANDIDATES:
        raise RuntimeError(
            f"Expected {TOP_CANDIDATES} "
            f"top candidates, found "
            f"{len(top_candidates)}."
        )

    return top_candidates


def parse_hours(value):
    if value in (
        "",
        None,
    ):
        return None

    try:
        return float(
            value
        )

    except (
        ValueError,
        TypeError,
    ):
        return None


def main():
    top_candidates = (
        load_top_candidates()
    )

    print(
        "TOP candidates loaded:",
        len(top_candidates),
    )

    interesting_trades = []

    candidate_trade_counts = defaultdict(
        int
    )

    with open(
        TRADES_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        reader = csv.DictReader(
            file
        )

        for trade in reader:

            wallet = trade.get(
                "proxy_wallet",
                "",
            ).strip()

            if wallet not in top_candidates:
                continue

            if (
                trade.get(
                    "side",
                    "",
                ).upper()
                != "BUY"
            ):
                continue

            if (
                trade.get(
                    "is_winning_buy",
                    "",
                )
                != "1"
            ):
                continue

            try:
                price = float(
                    trade.get(
                        "price",
                        0,
                    )
                )

                size = float(
                    trade.get(
                        "size",
                        0,
                    )
                )

            except (
                ValueError,
                TypeError,
            ):
                continue

            if not (
                0 <= price <= 1
            ):
                continue

            if size < 0:
                continue

            if (
                price
                > LOW_PRICE_THRESHOLD
            ):
                continue

            hours_before_close = (
                parse_hours(
                    trade.get(
                        "hours_before_close",
                        "",
                    )
                )
            )

            trade_after_close = (
                hours_before_close is not None
                and hours_before_close < 0
            )

            # Candidate evidence must use the same
            # pre-close population as the ranking.
            if (
                hours_before_close is None
                or trade_after_close
            ):
                continue

            very_low_price = (
                price
                <= VERY_LOW_PRICE_THRESHOLD
            )

            late_low_price = (
                0
                <= hours_before_close
                <= LATE_HOURS
            )

            volume = (
                size
                * price
            )

            profit_proxy = (
                size
                * (1 - price)
            )

            candidate = (
                top_candidates[
                    wallet
                ]
            )

            interesting_trades.append(
                {
                    "candidate_rank":
                        candidate[
                            "candidate_rank"
                        ],
                    "candidate_score":
                        candidate[
                            "candidate_score"
                        ],
                    "signal_level":
                        candidate[
                            "signal_level"
                        ],
                    "candidate_hit_rate":
                        candidate[
                            "candidate_hit_rate"
                        ],
                    "edge_vs_baseline":
                        candidate[
                            "edge_vs_baseline"
                        ],
                    "candidate_markets":
                        candidate[
                            "candidate_markets"
                        ],
                    "wallet":
                        wallet,
                    "condition_id":
                        trade.get(
                            "condition_id",
                            "",
                        ),
                    "title":
                        trade.get(
                            "title",
                            "",
                        ),
                    "trade_date":
                        trade.get(
                            "trade_date",
                            "",
                        ),
                    "closed_time":
                        trade.get(
                            "closed_time",
                            "",
                        ),
                    "hours_before_close":
                        hours_before_close,
                    "outcome":
                        trade.get(
                            "outcome",
                            "",
                        ),
                    "winning_outcome":
                        trade.get(
                            "winning_outcome",
                            "",
                        ),
                    "price":
                        price,
                    "size":
                        size,
                    "volume":
                        volume,
                    "profit_proxy":
                        profit_proxy,
                    "very_low_price":
                        very_low_price,
                    "late_low_price":
                        late_low_price,
                    # Explicit boolean instead of a blank field.
                    "trade_after_close":
                        trade_after_close,
                    "transaction_hash":
                        trade.get(
                            "transaction_hash",
                            "",
                        ),
                }
            )

            candidate_trade_counts[
                wallet
            ] += 1

    interesting_trades.sort(
        key=lambda trade: (
            trade[
                "candidate_rank"
            ],
            -trade[
                "profit_proxy"
            ],
        )
    )

    fieldnames = [
        "candidate_rank",
        "candidate_score",
        "signal_level",
        "candidate_hit_rate",
        "edge_vs_baseline",
        "candidate_markets",
        "wallet",
        "condition_id",
        "title",
        "trade_date",
        "closed_time",
        "hours_before_close",
        "outcome",
        "winning_outcome",
        "price",
        "size",
        "volume",
        "profit_proxy",
        "very_low_price",
        "late_low_price",
        "trade_after_close",
        "transaction_hash",
    ]

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(
            interesting_trades
        )

    print()
    print(
        "======================================"
    )
    print(
        "TOP CANDIDATE TRADE COVERAGE"
    )
    print(
        "======================================"
    )

    for wallet, candidate in sorted(
        top_candidates.items(),
        key=lambda item:
            item[1][
                "candidate_rank"
            ],
    ):
        print(
            "Rank:",
            candidate[
                "candidate_rank"
            ],
            "| Wallet:",
            wallet,
            "| interesting trades:",
            candidate_trade_counts[
                wallet
            ],
        )

    top_trades = sorted(
        interesting_trades,
        key=lambda trade: (
            trade[
                "late_low_price"
            ],
            trade[
                "very_low_price"
            ],
            trade[
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
        "TOP-30 INTERESTING WINNING BUY TRADES"
    )
    print(
        "======================================"
    )

    for trade in top_trades[
        :30
    ]:
        print()

        print(
            "Candidate rank:",
            trade[
                "candidate_rank"
            ],
        )

        print(
            "Wallet:",
            trade[
                "wallet"
            ],
        )

        print(
            "Market:",
            trade[
                "title"
            ],
        )

        print(
            "Outcome:",
            trade[
                "outcome"
            ],
        )

        print(
            "Price:",
            trade[
                "price"
            ],
        )

        print(
            "Very low price:",
            trade[
                "very_low_price"
            ],
        )

        print(
            "Hours before close:",
            trade[
                "hours_before_close"
            ],
        )

        print(
            "Late low price:",
            trade[
                "late_low_price"
            ],
        )

        print(
            "Trade after close:",
            trade[
                "trade_after_close"
            ],
        )

        print(
            "Volume:",
            round(
                trade[
                    "volume"
                ],
                2,
            ),
        )

        print(
            "BUY-only profit proxy:",
            round(
                trade[
                    "profit_proxy"
                ],
                2,
            ),
        )

    print()
    print(
        "======================================"
    )
    print("DONE")
    print(
        "======================================"
    )

    print(
        "Top candidates:",
        len(
            top_candidates
        ),
    )

    print(
        "Interesting trades:",
        len(
            interesting_trades
        ),
    )

    print(
        "Created:",
        OUTPUT_FILE,
    )


if __name__ == "__main__":
    main()
