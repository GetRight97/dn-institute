from pathlib import Path
from datetime import datetime, timezone
import csv

from polymarket import PublicClient


BASE_DIR = Path(__file__).resolve().parents[1]

RAW_DIR = BASE_DIR / "data" / "raw"
RAW_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT_FILE = RAW_DIR / "market_dates.csv"

START_DATE = datetime(
    2025,
    11,
    1,
    tzinfo=timezone.utc,
)

END_DATE = datetime(
    2026,
    5,
    1,
    tzinfo=timezone.utc,
)

TARGET_MARKETS = 20


def get_volume(market):
    """
    Read numeric market volume from the SDK MarketMetrics object.
    """

    metrics = getattr(
        market,
        "metrics",
        None,
    )

    if metrics is None:
        return 0.0

    volume = getattr(
        metrics,
        "volume",
        None,
    )

    if volume is None:
        volume = getattr(
            metrics,
            "volume_num",
            None,
        )

    if volume is None:
        return 0.0

    try:
        return float(volume)

    except (
        TypeError,
        ValueError,
    ):
        return 0.0


def collect_markets():
    """
    Dataset scope:

    - closed Polymarket markets
    - scheduled end date:
      2025-11-01 <= end_date < 2026-05-01
    - ordered by trading volume descending
    - first 1,000 unique markets

    The Polymarket SDK handles keyset pagination.
    """

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

        for page_number, page in enumerate(
            paginator,
            start=1,
        ):
            print(
                "Page:",
                page_number,
                "| API markets:",
                len(page.items),
                "| selected:",
                len(selected_markets),
            )

            for market in page.items:

                condition_id = (
                    market.condition_id
                )

                if not condition_id:
                    continue

                condition_id = str(
                    condition_id
                )

                # Avoid duplicate markets
                if condition_id in seen_condition_ids:
                    continue

                end_date = (
                    market.state.end_date
                )

                if end_date is None:
                    continue

                # Local validation of analysis period
                if not (
                    START_DATE
                    <= end_date
                    < END_DATE
                ):
                    continue

                seen_condition_ids.add(
                    condition_id
                )

                selected_markets.append(
                    market
                )

                # Stop as soon as the scoped sample reaches 1,000.
                if (
                    len(selected_markets)
                    >= TARGET_MARKETS
                ):
                    return selected_markets

    return selected_markets


def write_csv(markets):
    """
    Save the fixed market universe used by the rest
    of the analysis pipeline.
    """

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.writer(
            file
        )

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

            start_date = (
                market.state.start_date
            )

            end_date = (
                market.state.end_date
            )

            writer.writerow(
                [
                    str(
                        market.condition_id
                    ),
                    market.question or "",
                    (
                        start_date.isoformat()
                        if start_date is not None
                        else ""
                    ),
                    (
                        end_date.isoformat()
                        if end_date is not None
                        else ""
                    ),
                    get_volume(
                        market
                    ),
                ]
            )


def main():
    markets = collect_markets()

    print()
    print(
        "======================================"
    )
    print("DONE")
    print(
        "======================================"
    )

    print(
        "Selected markets:",
        len(markets),
    )

    if markets:

        volumes = [
            get_volume(market)
            for market in markets
        ]

        print(
            "Highest volume:",
            max(volumes),
        )

        print(
            "Lowest volume in sample:",
            min(volumes),
        )

    write_csv(
        markets
    )

    print(
        "Created:",
        OUTPUT_FILE,
    )


if __name__ == "__main__":
    main()