import csv
import os
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

MARKET_OUTCOMES_FILE = PROCESSED_DIR / "market_outcomes.csv"
TRADES_FILE = RAW_DIR / "trades.csv"
OUTPUT_FILE = PROCESSED_DIR / "trades_with_outcome.csv"
TEMP_OUTPUT_FILE = PROCESSED_DIR / "trades_with_outcome.csv.tmp"


def load_market_results():
    market_results = {}

    with open(
        MARKET_OUTCOMES_FILE,
        "r",
        encoding="utf-8",
    ) as file:
        reader = csv.DictReader(file)

        for row_number, row in enumerate(reader, start=2):
            condition_id = row.get("condition_id", "").strip()

            if not condition_id:
                raise RuntimeError(
                    "Invalid market_outcomes.csv: "
                    f"row {row_number} is missing condition_id."
                )

            winning_outcome = row.get(
                "winning_outcome",
                "",
            ).strip()

            closed_time = row.get(
                "closed_time",
                "",
            ).strip()

            if not winning_outcome:
                raise RuntimeError(
                    "Invalid market_outcomes.csv: "
                    f"{condition_id} has no winning_outcome."
                )

            if not closed_time:
                raise RuntimeError(
                    "Invalid market_outcomes.csv: "
                    f"{condition_id} has no closed_time."
                )

            market_results[condition_id] = {
                "winning_outcome": winning_outcome,
                "closed_time": closed_time,
                "uma_status": row.get("uma_status", ""),
            }

    if not market_results:
        raise RuntimeError(
            "market_outcomes.csv contains no markets."
        )

    print("Loaded market outcomes:", len(market_results))
    return market_results


def parse_datetime(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except (ValueError, AttributeError):
        return None


def enrich_to_temp_file(market_results):
    total_trades = 0
    matched_trades = 0
    resolved_trades = 0
    buy_trades = 0
    winning_buy_trades = 0
    timing_available = 0
    negative_timing = 0

    unmatched_condition_ids = set()
    trade_market_ids = set()

    try:
        with open(
            TRADES_FILE,
            "r",
            encoding="utf-8",
        ) as input_file:
            reader = csv.DictReader(input_file)

            if reader.fieldnames is None:
                raise RuntimeError(
                    "trades.csv has no header."
                )

            fieldnames = list(reader.fieldnames) + [
                "winning_outcome",
                "uma_status",
                "is_winning_buy",
                "closed_time",
                "hours_before_close",
            ]

            with open(
                TEMP_OUTPUT_FILE,
                "w",
                newline="",
                encoding="utf-8",
            ) as output_file:
                writer = csv.DictWriter(
                    output_file,
                    fieldnames=fieldnames,
                )
                writer.writeheader()

                for trade in reader:
                    total_trades += 1

                    condition_id = trade.get(
                        "condition_id",
                        "",
                    ).strip()

                    if not condition_id:
                        raise RuntimeError(
                            "Trade row is missing condition_id "
                            f"at input row {total_trades + 1}."
                        )

                    trade_market_ids.add(condition_id)
                    market = market_results.get(condition_id)

                    if market is None:
                        unmatched_condition_ids.add(
                            condition_id
                        )
                        continue

                    matched_trades += 1

                    winning_outcome = market[
                        "winning_outcome"
                    ]
                    closed_time = market[
                        "closed_time"
                    ]
                    uma_status = market[
                        "uma_status"
                    ]

                    trade["winning_outcome"] = winning_outcome
                    trade["uma_status"] = uma_status
                    trade["closed_time"] = closed_time

                    is_winning_buy = ""
                    resolved_trades += 1

                    side = trade.get("side", "").upper()

                    if side == "BUY":
                        buy_trades += 1
                        trade_outcome = trade.get(
                            "outcome",
                            "",
                        )

                        if trade_outcome == winning_outcome:
                            is_winning_buy = 1
                            winning_buy_trades += 1
                        else:
                            is_winning_buy = 0

                    trade["is_winning_buy"] = is_winning_buy

                    trade_time = parse_datetime(
                        trade.get(
                            "trade_date",
                            "",
                        )
                    )
                    close_time = parse_datetime(
                        closed_time
                    )

                    if (
                        trade_time is None
                        or close_time is None
                    ):
                        raise RuntimeError(
                            "Invalid timing data for "
                            f"condition_id={condition_id}, "
                            f"input row {total_trades + 1}."
                        )

                    hours_before_close = round(
                        (
                            close_time
                            - trade_time
                        ).total_seconds()
                        / 3600,
                        4,
                    )

                    timing_available += 1

                    if hours_before_close < 0:
                        negative_timing += 1

                    trade[
                        "hours_before_close"
                    ] = hours_before_close

                    writer.writerow(trade)

                    if total_trades % 100000 == 0:
                        print(
                            "Processed:",
                            total_trades,
                        )

        if unmatched_condition_ids:
            print()
            print("Unmatched condition IDs:")

            for condition_id in sorted(
                unmatched_condition_ids
            ):
                print(condition_id)

            raise RuntimeError(
                f"{len(unmatched_condition_ids)} "
                "condition ID(s) from trades.csv "
                "were not found in market_outcomes.csv."
            )

        os.replace(
            TEMP_OUTPUT_FILE,
            OUTPUT_FILE,
        )

    except Exception:
        try:
            TEMP_OUTPUT_FILE.unlink(
                missing_ok=True
            )
        except OSError:
            pass
        raise

    return {
        "total_trades": total_trades,
        "trade_markets": len(trade_market_ids),
        "matched_trades": matched_trades,
        "resolved_trades": resolved_trades,
        "buy_trades": buy_trades,
        "winning_buy_trades": winning_buy_trades,
        "timing_available": timing_available,
        "negative_timing": negative_timing,
    }


def main():
    market_results = load_market_results()
    stats = enrich_to_temp_file(
        market_results
    )

    print()
    print("======================================")
    print("DONE")
    print("======================================")
    print("Total trades:", stats["total_trades"])
    print("Trade markets:", stats["trade_markets"])
    print("Matched trades:", stats["matched_trades"])
    print(
        "Trades on resolved markets:",
        stats["resolved_trades"],
    )
    print("BUY trades:", stats["buy_trades"])
    print(
        "BUY on winning outcome:",
        stats["winning_buy_trades"],
    )
    print(
        "Timing available:",
        stats["timing_available"],
    )
    print(
        "Trades after closed_time:",
        stats["negative_timing"],
    )

    if stats["buy_trades"] > 0:
        hit_rate = (
            stats["winning_buy_trades"]
            / stats["buy_trades"]
            * 100
        )
        print(
            "BUY outcome hit rate:",
            round(hit_rate, 2),
            "%",
        )

    print()
    print("Created:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
