import requests


CONDITION_ID = (
    "0x24aba6bd6e6278069b57911685b30ef5"
    "8b7227c3345794848641148e015e109d"
)

GAMMA_MARKETS_URL = (
    "https://gamma-api.polymarket.com/markets"
)

TIMEOUT = 20


def fetch(params):
    try:
        response = requests.get(
            GAMMA_MARKETS_URL,
            params=params,
            timeout=TIMEOUT,
        )

        print("URL:", response.url)
        print("HTTP:", response.status_code)

        response.raise_for_status()

        data = response.json()

    except requests.exceptions.RequestException as error:
        raise RuntimeError(
            "Gamma API request failed"
        ) from error

    except ValueError as error:
        raise RuntimeError(
            "Gamma API returned invalid JSON"
        ) from error

    if not isinstance(
        data,
        list,
    ):
        raise RuntimeError(
            "Unexpected Gamma API response format"
        )

    return data


def show_result(data):
    print(
        "Количество рынков:",
        len(data),
    )

    if data:
        print("Получили conditionId:")
        print(
            data[0].get(
                "conditionId"
            )
        )


def main():
    print("TEST 1: condition_id")

    data = fetch(
        {
            "condition_id":
                CONDITION_ID
        }
    )

    show_result(data)

    print()
    print(
        "===================================="
    )
    print()

    print("TEST 2: condition_ids")

    data = fetch(
        {
            "condition_ids":
                CONDITION_ID
        }
    )

    show_result(data)


if __name__ == "__main__":
    main()
