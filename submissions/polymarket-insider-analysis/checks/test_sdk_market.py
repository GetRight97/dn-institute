from polymarket import PublicClient


condition_id = (
    "0x3848f792fcb0c8b760bb665213a5e732"
    "b5b9b530eb0a47cdda3f6b08d4ae9f6f"
)


with PublicClient() as client:

    page = client.list_markets(
        condition_ids=[condition_id],
        closed=True,
        page_size=10
    ).first_page()

    market = page.items[0]

    print("MARKET:")
    print(market)

    print()
    print("===================================")
    print("ТИП:")
    print(type(market))

    print()
    print("===================================")
    print("ATTRIBUTES:")
    print(dir(market))

    print()
    print("===================================")
    print("STATE:")
    print(market.state)

    print()
    print("===================================")
    print("OUTCOMES:")
    print(getattr(market, "outcomes", "НЕТ ПОЛЯ outcomes"))

    print()
    print("===================================")
    print("TOKENS:")
    print(getattr(market, "tokens", "НЕТ ПОЛЯ tokens"))