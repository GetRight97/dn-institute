from pathlib import Path
from datetime import datetime, timezone
import csv

from polymarket import PublicClient

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = RAW_DIR / "market_dates.csv"

START_DATE = datetime(2025, 11, 1, tzinfo=timezone.utc)
END_DATE = datetime(2026, 5, 1, tzinfo=timezone.utc)
TARGET_MARKETS = 20


def get_volume(market):
    metrics = getattr(market, "metrics", None)
    if metrics is None:
        return 0.0

    volume = getattr(metrics, "volume", None)
    if volume is None:
        volume = getattr(metrics, "volume_num", None)

    if volume is None:
        return 0.0

    try:
        return float(volume)
    except (TypeError, ValueError):
        return 0.0


def has_binary_winner(market):
    state = getattr(market, "state", None)
    outcomes = getattr(market, "outcomes", None)

    if (
        state is None
        or outcomes is None
        or not bool(getattr(state, "closed", False))
    ):
        return False

    yes_outcome = getattr(outcomes, "yes", None)
    no_outcome = getattr(outcomes, "no", None)

    if yes_outcome is None or no_outcome is None:
        return False

    try:
        yes_price = float(yes_outcome.price)
        no_price = float(no_outcome.price)
    except (TypeError, ValueError, AttributeError):
        return False

    return (
        (yes_price == 1.0 and no_price == 0.0)
        or (no_price == 1.0 and yes_price == 0.0)
    )


def collect_markets():
    selected_markets = []
    seen_condition_ids = set()

    with PublicClient() as client:
        paginator = client.list_markets(
            closed=True,
            end_date_min=START_DATE,
            end_date_max=END_DATE,
            order="volume",
            ascending=False,
            page_size=100,
        )

        for page_number, page in enumerate(paginator, start=1):
            print(
                "Page:",
                page_number,
                "| API markets:",
                len(page.items),
                "| selected:",
                len(selected_markets),
            )

            for market in page.items:
                condition_id = getattr(market, "condition_id", None)
                if not condition_id:
                    continue

                condition_id = str(condition_id)

                if condition_id in seen_condition_ids:
                    continue

                state = getattr(market, "state", None)
                if state is None:
                    continue

                start_date = getattr(state, "start_date", None)
                end_date = getattr(state, "end_date", None)

                if (
                    start_date is None
                    or end_date is None
                    or start_date >= end_date
                ):
                    continue

                if not (START_DATE <= end_date < END_DATE):
                    continue

                # Skip disputed/pending/50-50/etc. closed markets.
                if not has_binary_winner(market):
                    continue

                seen_condition_ids.add(condition_id)
                selected_markets.append(market)

                if len(selected_markets) == TARGET_MARKETS:
                    return selected_markets

    raise RuntimeError(
        "Market selection incomplete: "
        f"expected exactly {TARGET_MARKETS} valid resolved markets, "
        f"found {len(selected_markets)} after pagination exhausted."
    )


def write_csv(markets):
    if len(markets) != TARGET_MARKETS:
        raise RuntimeError(
            "Refusing to write market_dates.csv: "
            f"expected {TARGET_MARKETS}, got {len(markets)}."
        )

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "condition_id",
                "title",
                "start_date",
                "end_date",
                "volume",
            ]
        )

        for market in markets:
            writer.writerow(
                [
                    str(market.condition_id),
                    market.question or "",
                    market.state.start_date.isoformat(),
                    market.state.end_date.isoformat(),
                    get_volume(market),
                ]
            )


def main():
    markets = collect_markets()

    print()
    print("======================================")
    print("DONE")
    print("======================================")
    print("Selected markets:", len(markets))

    volumes = [get_volume(market) for market in markets]
    print("Highest volume:", max(volumes))
    print("Lowest volume in sample:", min(volumes))

    write_csv(markets)
    print("Created:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
