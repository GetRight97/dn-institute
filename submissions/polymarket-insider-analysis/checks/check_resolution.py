from pathlib import Path
import csv
import json

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
    # --------------------------------------------------
    # 1. Берём первый condition_id
    # --------------------------------------------------

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        reader = csv.DictReader(file)

        first_market = next(
            reader,
            None,
        )

    if first_market is None:
        raise RuntimeError(
            "market_dates.csv contains no markets"
        )

    condition_id = first_market.get(
        "condition_id",
        "",
    ).strip()

    if not condition_id:
        raise RuntimeError(
            "First row contains no condition_id"
        )

    print("Condition ID:")
    print(condition_id)

    # --------------------------------------------------
    # 2. Запрашиваем Gamma API
    # --------------------------------------------------

    params = {
        "conditionId": condition_id
    }

    try:
        response = requests.get(
            GAMMA_MARKETS_URL,
            params=params,
            timeout=TIMEOUT,
        )

        print()
        print(
            "HTTP:",
            response.status_code,
        )

        response.raise_for_status()

        data = response.json()

    except requests.exceptions.RequestException as error:
        raise RuntimeError(
            f"Gamma API request failed "
            f"for {condition_id}"
        ) from error

    except ValueError as error:
        raise RuntimeError(
            "Gamma API returned invalid JSON"
        ) from error

    # --------------------------------------------------
    # 3. Проверяем формат и показываем ответ
    # --------------------------------------------------

    if not isinstance(
        data,
        list,
    ):
        raise RuntimeError(
            "Unexpected Gamma API response format"
        )

    if not data:
        raise RuntimeError(
            f"No market returned for "
            f"{condition_id}"
        )

    print()
    print("API response:")

    print(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()