from polymarket import PublicClient


CONDITION_ID = (
    "0x3848f792fcb0c8b760bb665213a5e732"
    "b5b9b530eb0a47cdda3f6b08d4ae9f6f"
)


def main():

    with PublicClient() as client:

        page = client.list_markets(
            condition_ids=[CONDITION_ID],
            closed=True,
            page_size=10,
        ).first_page()

        if not page.items:
            raise RuntimeError(
                "No market returned for condition_id: "
                f"{CONDITION_ID}"
            )

        market = page.items[0]

        print("MARKET")
        print("===================================")

        print(
            "Condition ID:",
            market.condition_id,
        )

        print(
            "Question:",
            getattr(
                market,
                "question",
                None,
            ),
        )

        print(
            "Closed:",
            getattr(
                market,
                "closed",
                None,
            ),
        )

        print(
            "End date:",
            getattr(
                market,
                "end_date",
                None,
            ),
        )

        print(
            "Closed time:",
            getattr(
                market,
                "closed_time",
                None,
            ),
        )

        print(
            "Outcomes:",
            getattr(
                market,
                "outcomes",
                None,
            ),
        )


if __name__ == "__main__":
    main()