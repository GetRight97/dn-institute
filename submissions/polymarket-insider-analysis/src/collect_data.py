from pathlib import Path
from datetime import datetime, timezone
import csv
import os
import time

import requests


BASE_DIR = Path(__file__).resolve().parents[1]

RAW_DIR = BASE_DIR / "data" / "raw"
RAW_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

MARKETS_FILE = RAW_DIR / "market_dates.csv"
OUTPUT_FILE = RAW_DIR / "trades.csv"
TEMP_OUTPUT_FILE = RAW_DIR / "trades.csv.tmp"

EXPECTED_MARKETS = 20

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

TRADES_URL = (
    "https://data-api.polymarket.com/v2/trades"
)

TIMEOUT = 30
MAX_RETRIES = 8
REQUEST_DELAY = 0.2


def get_json(url, params=None):
    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):
        try:
            response = requests.get(
                url,
                params=params,
                timeout=TIMEOUT,
            )

            if response.status_code == 429:
                retry_after = response.headers.get(
                    "Retry-After"
                )

                try:
                    wait_seconds = (
                        float(retry_after)
                        if retry_after
                        else min(
                            2 ** attempt,
                            60,
                        )
                    )
                except ValueError:
                    wait_seconds = min(
                        2 ** attempt,
                        60,
                    )

                print(
                    f"Rate limited. "
                    f"Waiting {wait_seconds}s..."
                )

                time.sleep(
                    wait_seconds
                )

                continue

            if response.status_code >= 500:
                wait_seconds = min(
                    2 ** attempt,
                    60,
                )

                print(
                    f"HTTP {response.status_code}. "
                    f"Waiting {wait_seconds}s..."
                )

                time.sleep(
                    wait_seconds
                )

                continue

            response.raise_for_status()

            return response.json()

        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
        ) as error:

            if attempt == MAX_RETRIES:
                raise RuntimeError(
                    f"Request failed after "
                    f"{MAX_RETRIES} attempts"
                ) from error

            wait_seconds = min(
                2 ** attempt,
                60,
            )

            print(
                f"Network error. "
                f"Waiting {wait_seconds}s..."
            )

            time.sleep(
                wait_seconds
            )

        except requests.exceptions.RequestException as error:
            raise RuntimeError(
                f"HTTP request failed: {url}"
            ) from error

        except ValueError as error:
            raise RuntimeError(
                f"Invalid JSON response from: {url}"
            ) from error

    raise RuntimeError(
        f"Request failed after "
        f"{MAX_RETRIES} attempts"
    )


def load_markets():
    """
    Read and validate the fixed scoped market universe.

    Every row must contain a condition_id. The final universe
    must contain exactly EXPECTED_MARKETS unique markets.
    """

    markets = []
    seen_condition_ids = set()

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

            if condition_id in seen_condition_ids:
                raise RuntimeError(
                    "Invalid market_dates.csv: "
                    f"duplicate condition_id at row {row_number}: "
                    f"{condition_id}"
                )

            seen_condition_ids.add(
                condition_id
            )

            markets.append(
                {
                    "condition_id":
                        condition_id,
                    "title":
                        row.get(
                            "title",
                            "",
                        ),
                }
            )

    if len(markets) != EXPECTED_MARKETS:
        raise RuntimeError(
            "Invalid fixed market universe: "
            f"expected exactly {EXPECTED_MARKETS} markets, "
            f"found {len(markets)}."
        )

    print(
        "Loaded markets:",
        len(markets),
    )

    return markets


def collect_trades_for_market(
    condition_id,
):
    """
    Collect complete trade history for one selected market.

    Pagination metadata is mandatory. Missing pagination or
    missing has_more is treated as an incomplete API response
    rather than as end-of-history.
    """

    all_market_trades = []

    params = {
        "condition":
            condition_id,
        "limit":
            1000,
    }

    previous_cursor = None
    page_number = 0

    while True:
        data = get_json(
            TRADES_URL,
            params=params,
        )

        if not isinstance(
            data,
            dict,
        ):
            raise RuntimeError(
                "Unexpected trade API response "
                f"for {condition_id}"
            )

        if "data" not in data:
            raise RuntimeError(
                "Missing data field "
                f"for {condition_id}"
            )

        trades = data[
            "data"
        ]

        if not isinstance(
            trades,
            list,
        ):
            raise RuntimeError(
                "Unexpected trade data format "
                f"for {condition_id}"
            )

        if "pagination" not in data:
            raise RuntimeError(
                "Missing pagination metadata "
                f"for {condition_id}"
            )

        pagination = data[
            "pagination"
        ]

        if not isinstance(
            pagination,
            dict,
        ):
            raise RuntimeError(
                "Unexpected pagination format "
                f"for {condition_id}"
            )

        if "has_more" not in pagination:
            raise RuntimeError(
                "Missing pagination.has_more "
                f"for {condition_id}"
            )

        has_more = pagination[
            "has_more"
        ]

        if not isinstance(
            has_more,
            bool,
        ):
            raise RuntimeError(
                "Invalid pagination.has_more "
                f"for {condition_id}: {has_more!r}"
            )

        page_number += 1

        all_market_trades.extend(
            trades
        )

        if (
            page_number == 1
            or page_number % 10 == 0
        ):
            print(
                "   Page:",
                page_number,
                "| trades collected:",
                len(
                    all_market_trades
                ),
            )

        if not has_more:
            break

        next_cursor = pagination.get(
            "next_cursor"
        )

        if not next_cursor:
            raise RuntimeError(
                "has_more=True but "
                "next_cursor is missing "
                f"for {condition_id}"
            )

        if next_cursor == previous_cursor:
            raise RuntimeError(
                "Trade API returned "
                "the same cursor twice "
                f"for {condition_id}"
            )

        previous_cursor = (
            next_cursor
        )

        params[
            "cursor"
        ] = next_cursor

        time.sleep(
            REQUEST_DELAY
        )

    return all_market_trades


def get_trade_value(
    trade,
    snake_name,
    camel_name=None,
    default="",
):
    if snake_name in trade:
        return trade.get(
            snake_name,
            default,
        )

    if camel_name:
        return trade.get(
            camel_name,
            default,
        )

    return default


def write_trades_atomically(
    markets,
):
    """
    Write to a temporary file first.

    OUTPUT_FILE is replaced only after all selected markets
    are collected successfully, so failures cannot leave a
    partial trades.csv that looks complete.
    """

    fieldnames = [
        "condition_id",
        "proxy_wallet",
        "side",
        "size",
        "price",
        "timestamp",
        "trade_date",
        "outcome",
        "title",
        "transaction_hash",
    ]

    total_api_trades = 0
    total_period_trades = 0

    try:
        with open(
            TEMP_OUTPUT_FILE,
            "w",
            newline="",
            encoding="utf-8",
        ) as csv_file:

            writer = csv.DictWriter(
                csv_file,
                fieldnames=fieldnames,
            )

            writer.writeheader()

            for number, market in enumerate(
                markets,
                start=1,
            ):
                condition_id = market[
                    "condition_id"
                ]

                print()
                print(
                    number,
                    "/",
                    len(markets),
                    "| Market:",
                    condition_id,
                )

                trades = (
                    collect_trades_for_market(
                        condition_id
                    )
                )

                total_api_trades += len(
                    trades
                )

                period_trade_count = 0

                for trade_index, trade in enumerate(
                    trades,
                    start=1,
                ):
                    if not isinstance(
                        trade,
                        dict,
                    ):
                        raise RuntimeError(
                            "Invalid trade row "
                            f"for market {condition_id}, "
                            f"index {trade_index}: expected object."
                        )

                    trade_condition_id = (
                        get_trade_value(
                            trade,
                            "condition_id",
                            "conditionId",
                            "",
                        )
                    )

                    if trade_condition_id in (
                        "",
                        None,
                    ):
                        raise RuntimeError(
                            "Trade row is missing condition_id "
                            f"for market {condition_id}, "
                            f"index {trade_index}."
                        )

                    trade_condition_id = str(
                        trade_condition_id
                    )

                    if (
                        trade_condition_id
                        != condition_id
                    ):
                        raise RuntimeError(
                            "Trade row condition_id mismatch: "
                            f"requested {condition_id}, "
                            f"received {trade_condition_id}."
                        )

                    timestamp = (
                        get_trade_value(
                            trade,
                            "timestamp",
                        )
                    )

                    if timestamp in (
                        "",
                        None,
                    ):
                        continue

                    try:
                        trade_date = (
                            datetime.fromtimestamp(
                                int(
                                    timestamp
                                ),
                                timezone.utc,
                            )
                        )

                    except (
                        ValueError,
                        TypeError,
                        OSError,
                    ):
                        continue

                    if not (
                        START_DATE
                        <= trade_date
                        < END_DATE
                    ):
                        continue

                    proxy_wallet = (
                        get_trade_value(
                            trade,
                            "proxy_wallet",
                            "proxyWallet",
                        )
                    )

                    transaction_hash = (
                        get_trade_value(
                            trade,
                            "transaction_hash",
                            "transactionHash",
                        )
                    )

                    writer.writerow(
                        {
                            "condition_id":
                                trade_condition_id,
                            "proxy_wallet":
                                proxy_wallet,
                            "side":
                                get_trade_value(
                                    trade,
                                    "side",
                                ),
                            "size":
                                get_trade_value(
                                    trade,
                                    "size",
                                ),
                            "price":
                                get_trade_value(
                                    trade,
                                    "price",
                                ),
                            "timestamp":
                                timestamp,
                            "trade_date":
                                trade_date.isoformat(),
                            "outcome":
                                get_trade_value(
                                    trade,
                                    "outcome",
                                ),
                            "title":
                                (
                                    get_trade_value(
                                        trade,
                                        "title",
                                    )
                                    or market.get(
                                        "title",
                                        "",
                                    )
                                ),
                            "transaction_hash":
                                transaction_hash,
                        }
                    )

                    period_trade_count += 1
                    total_period_trades += 1

                print(
                    "| API trades:",
                    len(trades),
                    "| period trades:",
                    period_trade_count,
                )

                time.sleep(
                    REQUEST_DELAY
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

    return (
        total_api_trades,
        total_period_trades,
    )


def main():
    markets = load_markets()

    (
        total_api_trades,
        total_period_trades,
    ) = write_trades_atomically(
        markets
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
        "Markets processed:",
        len(markets),
    )

    print(
        "Trades returned by API:",
        total_api_trades,
    )

    print(
        "Trades in analysis period:",
        total_period_trades,
    )

    print(
        "Created:",
        OUTPUT_FILE,
    )


if __name__ == "__main__":
    main()
