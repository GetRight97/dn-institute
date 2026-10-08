from pathlib import Path
from datetime import datetime, timezone
import csv
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
    Read the fixed scoped market universe from market_dates.csv.
    """

    markets = []

    with open(
        MARKETS_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        reader = csv.DictReader(
            file
        )

        for row in reader:
            condition_id = row.get(
                "condition_id",
                "",
            ).strip()

            if not condition_id:
                continue

            markets.append(
                {
                    "condition_id": condition_id,
                    "title": row.get(
                        "title",
                        "",
                    ),
                }
            )

    if not markets:
        raise RuntimeError(
            "market_dates.csv contains no markets."
        )

    print(
        "Loaded markets:",
        len(markets),
    )

    return markets


def collect_trades_for_market(condition_id):
    """
    Collect all available trade pages for one market
    with visible progress.
    """

    all_market_trades = []

    params = {
        "condition": condition_id,
        "limit": 1000,
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
                f"Unexpected trade API response "
                f"for {condition_id}"
            )

        trades = data.get(
            "data"
        )

        if trades is None:
            raise RuntimeError(
                f"Missing data field "
                f"for {condition_id}"
            )

        if not isinstance(
            trades,
            list,
        ):
            raise RuntimeError(
                f"Unexpected trade data format "
                f"for {condition_id}"
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
                len(all_market_trades),
            )

        pagination = data.get(
            "pagination",
            {},
        )

        if not isinstance(
            pagination,
            dict,
        ):
            raise RuntimeError(
                f"Unexpected pagination format "
                f"for {condition_id}"
            )

        if not pagination.get(
            "has_more",
            False,
        ):
            break

        next_cursor = pagination.get(
            "next_cursor"
        )

        if not next_cursor:
            raise RuntimeError(
                f"has_more=True but "
                f"next_cursor is missing "
                f"for {condition_id}"
            )

        if next_cursor == previous_cursor:
            raise RuntimeError(
                f"Trade API returned "
                f"the same cursor twice "
                f"for {condition_id}"
            )

        previous_cursor = next_cursor
        params["cursor"] = next_cursor

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


def main():
    markets = load_markets()

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

    with open(
        OUTPUT_FILE,
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
            condition_id = (
                market[
                    "condition_id"
                ]
            )

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

            total_api_trades += (
                len(trades)
            )

            period_trade_count = 0

            for trade in trades:
                timestamp = get_trade_value(
                    trade,
                    "timestamp",
                )

                if timestamp in (
                    "",
                    None,
                ):
                    continue

                try:
                    trade_date = (
                        datetime.fromtimestamp(
                            int(timestamp),
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

                trade_condition_id = (
                    get_trade_value(
                        trade,
                        "condition_id",
                        "conditionId",
                        condition_id,
                    )
                )

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
                        "condition_id": (
                            trade_condition_id
                            or condition_id
                        ),
                        "proxy_wallet": (
                            proxy_wallet
                        ),
                        "side": get_trade_value(
                            trade,
                            "side",
                        ),
                        "size": get_trade_value(
                            trade,
                            "size",
                        ),
                        "price": get_trade_value(
                            trade,
                            "price",
                        ),
                        "timestamp": timestamp,
                        "trade_date": (
                            trade_date.isoformat()
                        ),
                        "outcome": get_trade_value(
                            trade,
                            "outcome",
                        ),
                        "title": (
                            get_trade_value(
                                trade,
                                "title",
                            )
                            or market.get(
                                "title",
                                "",
                            )
                        ),
                        "transaction_hash": (
                            transaction_hash
                        ),
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