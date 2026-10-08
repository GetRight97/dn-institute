from pathlib import Path
import csv
import json
import os
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
TEMP_OUTPUT_FILE = PROCESSED_DIR / "market_outcomes.csv.tmp"

EXPECTED_MARKETS = 20
MAX_RETRIES = 5


def load_condition_ids():
    """
    Read and validate the fixed market universe.

    Exactly 20 unique non-empty condition IDs are required.
    """

    condition_ids = []
    seen = set()

    with open(
        MARKETS_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        reader = csv.DictReader(
            file
        )

        for row_number, row in enumerate(
            reader,
            start=2,
        ):
            condition_id = row.get(
                "condition_id",
                "",
            ).strip()

            if not condition_id:
                raise RuntimeError(
                    "Invalid market_dates.csv: "
                    f"row {row_number} is missing condition_id."
                )

            if condition_id in seen:
                raise RuntimeError(
                    "Invalid market_dates.csv: "
                    f"duplicate condition_id at row {row_number}: "
                    f"{condition_id}"
                )

            seen.add(
                condition_id
            )

            condition_ids.append(
                condition_id
            )

    if len(
        condition_ids
    ) != EXPECTED_MARKETS:
        raise RuntimeError(
            "Invalid fixed market universe: "
            f"expected exactly {EXPECTED_MARKETS} unique "
            f"condition IDs, found {len(condition_ids)}."
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
    """Fetch one historical market with retries."""

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

            page = (
                paginator.first_page()
            )

            if not page.items:
                raise RuntimeError(
                    "No market returned for "
                    f"condition_id={condition_id}"
                )

            market = next(
                (
                    item
                    for item in page.items
                    if str(
                        item.condition_id
                    )
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
        "Failed to fetch market "
        f"{condition_id} after "
        f"{MAX_RETRIES} attempts"
    ) from last_error


def collect_markets(
    condition_ids,
):
    """Retrieve every selected market or fail."""

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
        raise RuntimeError(
            f"{len(failed_ids)} market lookup(s) failed. "
            "Outcome enrichment aborted."
        )

    if len(
        found_markets
    ) != EXPECTED_MARKETS:
        raise RuntimeError(
            "Market coverage check failed: "
            f"expected {EXPECTED_MARKETS}, "
            f"found {len(found_markets)}."
        )

    return found_markets


def determine_winner(
    market,
):
    """Determine a binary winning outcome."""

    state = getattr(
        market,
        "state",
        None,
    )

    if state is None:
        raise RuntimeError(
            f"Market {market.condition_id} has no state object."
        )

    closed = bool(
        state.closed
    )

    yes_outcome = (
        market.outcomes.yes
    )

    no_outcome = (
        market.outcomes.no
    )

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
                uma_status = (
                    status.value
                )
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

    return {
        "closed":
            closed,
        "yes_label":
            yes_label,
        "no_label":
            no_label,
        "yes_price":
            yes_price,
        "no_price":
            no_price,
        "uma_status":
            uma_status,
        "is_resolved":
            bool(
                winning_outcome
            ),
        "winning_outcome":
            winning_outcome,
    }


def build_rows(
    found_markets,
):
    """
    Build and validate every outcome row before writing.

    Every selected market must have closed_time and an
    identifiable winning outcome.
    """

    rows = []
    unresolved_ids = []
    missing_closed_time_ids = []

    for (
        condition_id,
        market,
    ) in found_markets.items():

        state = getattr(
            market,
            "state",
            None,
        )

        if state is None:
            unresolved_ids.append(
                condition_id
            )
            continue

        closed_time = getattr(
            state,
            "closed_time",
            None,
        )

        if closed_time is None:
            missing_closed_time_ids.append(
                condition_id
            )

        end_date = getattr(
            state,
            "end_date",
            None,
        )

        result = determine_winner(
            market
        )

        if not result[
            "is_resolved"
        ]:
            unresolved_ids.append(
                condition_id
            )

        rows.append(
            {
                "condition_id":
                    condition_id,
                "title":
                    market.question or "",
                "closed":
                    result[
                        "closed"
                    ],
                "closed_time":
                    (
                        closed_time.isoformat()
                        if closed_time
                        is not None
                        else ""
                    ),
                "end_date":
                    (
                        end_date.isoformat()
                        if end_date
                        is not None
                        else ""
                    ),
                "outcomes":
                    json.dumps(
                        [
                            result[
                                "yes_label"
                            ],
                            result[
                                "no_label"
                            ],
                        ],
                        ensure_ascii=False,
                    ),
                "outcome_prices":
                    json.dumps(
                        [
                            result[
                                "yes_price"
                            ],
                            result[
                                "no_price"
                            ],
                        ],
                        ensure_ascii=False,
                    ),
                "winning_outcome":
                    result[
                        "winning_outcome"
                    ],
                "uma_status":
                    result[
                        "uma_status"
                    ],
            }
        )

    validation_errors = []

    if missing_closed_time_ids:
        validation_errors.append(
            "missing closed_time: "
            + ", ".join(
                missing_closed_time_ids
            )
        )

    if unresolved_ids:
        validation_errors.append(
            "unresolved/no winner: "
            + ", ".join(
                unresolved_ids
            )
        )

    if len(
        rows
    ) != EXPECTED_MARKETS:
        validation_errors.append(
            "row count mismatch: "
            f"expected {EXPECTED_MARKETS}, "
            f"built {len(rows)}"
        )

    if validation_errors:
        raise RuntimeError(
            "Outcome enrichment incomplete; "
            + " | ".join(
                validation_errors
            )
        )

    return rows


def write_market_outcomes_atomically(
    rows,
):
    """
    Write a validated dataset to a temporary file and atomically
    replace OUTPUT_FILE only after the complete write succeeds.
    """

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

    try:
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
            writer.writerows(
                rows
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


def main():
    condition_ids = (
        load_condition_ids()
    )

    found_markets = (
        collect_markets(
            condition_ids
        )
    )

    rows = build_rows(
        found_markets
    )

    write_market_outcomes_atomically(
        rows
    )

    closed_time_count = sum(
        1
        for row in rows
        if row[
            "closed_time"
        ]
    )

    resolved_count = sum(
        1
        for row in rows
        if row[
            "winning_outcome"
        ]
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
        resolved_count,
    )

    print()
    print(
        "Created:",
        OUTPUT_FILE,
    )


if __name__ == "__main__":
    main()
