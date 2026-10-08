from pathlib import Path
import csv
import json
import time

from polymarket import PublicClient


BASE_DIR = Path(__file__).resolve().parents[1]

RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

MARKETS_FILE = RAW_DIR / "market_dates.csv"
OUTPUT_FILE = PROCESSED_DIR / "market_outcomes.csv"

MAX_RETRIES = 5


def load_condition_ids():
    """
    Read the fixed market universe from market_dates.csv.

    This ensures market metadata is collected for all markets
    selected by market_dates.py, including markets that had
    zero trades during the analysis period.
    """

    condition_ids = []

    with open(
        MARKETS_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:
            condition_id = row.get(
                "condition_id",
                "",
            ).strip()

            if condition_id:
                condition_ids.append(
                    condition_id
                )

    # Remove duplicates while preserving order
    condition_ids = list(
        dict.fromkeys(
            condition_ids
        )
    )

    if not condition_ids:
        raise RuntimeError(
            "market_dates.csv contains no condition IDs."
        )

    print(
        "Markets in fixed universe:",
        len(condition_ids),
    )

    return condition_ids


def fetch_market(
    client,
    condition_id,
):
    """
    Fetch one historical market.

    Transient API/SDK errors are retried.
    A failed lookup is never silently ignored.
    """

    last_error = None

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):
        try:
            paginator = client.list_markets(
                condition_ids=[
                    condition_id
                ],
                closed=True,
                page_size=10,
            )

            page = paginator.first_page()

            if not page.items:
                raise RuntimeError(
                    f"No market returned for "
                    f"condition_id={condition_id}"
                )

            market = next(
                (
                    item
                    for item in page.items
                    if str(item.condition_id)
                    == condition_id
                ),
                None,
            )

            if market is None:
                raise RuntimeError(
                    "Returned markets do not contain "
                    f"condition_id={condition_id}"
                )

            return market

        except Exception as error:
            last_error = error

            if attempt == MAX_RETRIES:
                break

            wait_seconds = min(
                2 ** attempt,
                30,
            )

            print(
                f"Lookup failed for {condition_id}. "
                f"Retry {attempt}/{MAX_RETRIES} "
                f"in {wait_seconds}s..."
            )

            time.sleep(
                wait_seconds
            )

    raise RuntimeError(
        f"Failed to fetch market "
        f"{condition_id} after "
        f"{MAX_RETRIES} attempts"
    ) from last_error


def collect_markets(
    condition_ids,
):
    """
    Retrieve metadata for every market
    in the fixed universe.

    The pipeline fails if even one lookup fails.
    """

    found_markets = {}
    failed_ids = []

    with PublicClient() as client:

        for number, condition_id in enumerate(
            condition_ids,
            start=1,
        ):
            try:
                market = fetch_market(
                    client,
                    condition_id,
                )

                found_markets[
                    condition_id
                ] = market

            except Exception as error:
                print()
                print(
                    "ERROR:",
                    condition_id,
                )
                print(error)

                failed_ids.append(
                    condition_id
                )

            print(
                "Checked:",
                number,
                "/",
                len(condition_ids),
                "| found:",
                len(found_markets),
                "| failed:",
                len(failed_ids),
            )

    if failed_ids:
        print()
        print(
            "Failed market lookups:"
        )

        for condition_id in failed_ids:
            print(
                condition_id
            )

        raise RuntimeError(
            f"{len(failed_ids)} market lookup(s) "
            f"failed. market_outcomes.csv was not "
            f"created because downstream analysis "
            f"would be incomplete."
        )

    if len(found_markets) != len(
        condition_ids
    ):
        raise RuntimeError(
            "Market coverage check failed: "
            f"{len(found_markets)} found "
            f"for {len(condition_ids)} "
            f"condition IDs."
        )

    return found_markets


def determine_winner(
    market,
):
    """
    Determine the winning binary outcome.

    A winner is accepted only when:
    - market is closed
    - both final outcome prices are available
    - final prices are exactly 1.0 / 0.0

    UMA status is retained as metadata but is not
    required because not every Polymarket market
    type necessarily exposes the same UMA status.
    """

    closed = bool(
        market.state.closed
    )

    yes_outcome = market.outcomes.yes
    no_outcome = market.outcomes.no

    yes_label = (
        yes_outcome.label
    )

    no_label = (
        no_outcome.label
    )

    yes_price = (
        float(
            yes_outcome.price
        )
        if yes_outcome.price
        is not None
        else None
    )

    no_price = (
        float(
            no_outcome.price
        )
        if no_outcome.price
        is not None
        else None
    )

    uma_status = ""

    if market.resolution is not None:

        status = (
            market.resolution
            .uma_resolution_status
        )

        if status is not None:
            try:
                uma_status = status.value
            except AttributeError:
                uma_status = str(
                    status
                )

    winning_outcome = ""

    if (
        closed
        and yes_price is not None
        and no_price is not None
    ):

        if (
            yes_price == 1.0
            and no_price == 0.0
        ):
            winning_outcome = (
                yes_label
            )

        elif (
            no_price == 1.0
            and yes_price == 0.0
        ):
            winning_outcome = (
                no_label
            )

    is_resolved = bool(
        winning_outcome
    )

    return {
        "yes_label": yes_label,
        "no_label": no_label,
        "yes_price": yes_price,
        "no_price": no_price,
        "uma_status": uma_status,
        "is_resolved": is_resolved,
        "winning_outcome": (
            winning_outcome
        ),
    }


def write_market_outcomes(
    found_markets,
):
    """
    Write complete metadata for the fixed market universe.
    """

    winner_count = 0
    closed_time_count = 0
    resolved_count = 0

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8",
    ) as output_file:

        fieldnames = [
            "condition_id",
            "title",
            "closed",
            "closed_time",
            "end_date",
            "outcomes",
            "outcome_prices",
            "winning_outcome",
            "uma_status",
        ]

        writer = csv.DictWriter(
            output_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for (
            condition_id,
            market,
        ) in found_markets.items():

            title = (
                market.question
                or ""
            )

            closed = bool(
                market.state.closed
            )

            closed_time = (
                market.state.closed_time
            )

            end_date = (
                market.state.end_date
            )

            if closed_time is not None:
                closed_time_count += 1

                closed_time_value = (
                    closed_time.isoformat()
                )

            else:
                closed_time_value = ""

            if end_date is not None:
                end_date_value = (
                    end_date.isoformat()
                )

            else:
                end_date_value = ""

            result = determine_winner(
                market
            )

            outcomes = [
                result["yes_label"],
                result["no_label"],
            ]

            outcome_prices = [
                result["yes_price"],
                result["no_price"],
            ]

            if result[
                "is_resolved"
            ]:
                resolved_count += 1

            if result[
                "winning_outcome"
            ]:
                winner_count += 1

            writer.writerow(
                {
                    "condition_id": (
                        condition_id
                    ),
                    "title": title,
                    "closed": closed,
                    "closed_time": (
                        closed_time_value
                    ),
                    "end_date": (
                        end_date_value
                    ),
                    "outcomes": (
                        json.dumps(
                            outcomes,
                            ensure_ascii=False,
                        )
                    ),
                    "outcome_prices": (
                        json.dumps(
                            outcome_prices,
                            ensure_ascii=False,
                        )
                    ),
                    "winning_outcome": (
                        result[
                            "winning_outcome"
                        ]
                    ),
                    "uma_status": (
                        result[
                            "uma_status"
                        ]
                    ),
                }
            )

    return (
        closed_time_count,
        resolved_count,
        winner_count,
    )


def main():
    condition_ids = (
        load_condition_ids()
    )

    found_markets = (
        collect_markets(
            condition_ids
        )
    )

    (
        closed_time_count,
        resolved_count,
        winner_count,
    ) = write_market_outcomes(
        found_markets
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
        "Condition IDs:",
        len(condition_ids),
    )

    print(
        "Markets found:",
        len(found_markets),
    )

    print(
        "Markets with closed_time:",
        closed_time_count,
    )

    print(
        "Resolved markets:",
        resolved_count,
    )

    print(
        "Markets with identified winner:",
        winner_count,
    )

    print()
    print(
        "Created:",
        OUTPUT_FILE,
    )


if __name__ == "__main__":
    main()