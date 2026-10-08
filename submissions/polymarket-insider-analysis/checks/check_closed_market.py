from pathlib import Path
import csv

import requests


BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "raw"
    / "market_dates.csv"
)

GAMMA_MARKETS_URL = (
    "https://gamma-api.polymarket.com/markets"
)

TIMEOUT = 30


def main():
    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        reader = csv.DictReader(file)

        for number, row in enumerate(
            reader,
            start=1,
        ):
            condition_id = row.get(
                "condition_id",
                "",
            ).strip()

            if not condition_id:
                continue

            params = {
                "conditionId": condition_id
            }

            try:
                response = requests.get(
                    GAMMA_MARKETS_URL,
                    params=params,
                    timeout=TIMEOUT,
                )

                response.raise_for_status()

                data = response.json()

            except requests.exceptions.RequestException as error:
                print(
                    "Request error:",
                    condition_id,
                    error,
                )
                continue

            except ValueError as error:
                print(
                    "Invalid JSON:",
                    condition_id,
                    error,
                )
                continue

            if not isinstance(
                data,
                list,
            ):
                print(
                    "Unexpected API response:",
                    condition_id,
                )
                continue

            if not data:
                continue

            market = data[0]

            if not isinstance(
                market,
                dict,
            ):
                continue

            if market.get("closed") is True:
                print()
                print(
                    "=============================="
                )
                print(
                    "FOUND CLOSED MARKET"
                )
                print(
                    "=============================="
                )

                print(
                    "Number:",
                    number,
                )
                print(
                    "Question:",
                    market.get(
                        "question"
                    ),
                )
                print(
                    "Condition ID:",
                    market.get(
                        "conditionId"
                    ),
                )
                print(
                    "Closed:",
                    market.get(
                        "closed"
                    ),
                )
                print(
                    "Active:",
                    market.get(
                        "active"
                    ),
                )
                print(
                    "Outcomes:",
                    market.get(
                        "outcomes"
                    ),
                )
                print(
                    "Outcome prices:",
                    market.get(
                        "outcomePrices"
                    ),
                )
                print(
                    "Resolved by:",
                    market.get(
                        "resolvedBy"
                    ),
                )
                print(
                    "UMA status:",
                    market.get(
                        "umaResolutionStatuses"
                    ),
                )
                print(
                    "End date:",
                    market.get(
                        "endDate"
                    ),
                )

                break

            if number % 100 == 0:
                print(
                    "Checked markets:",
                    number,
                )

    print()
    print("Done")


if __name__ == "__main__":
    main()