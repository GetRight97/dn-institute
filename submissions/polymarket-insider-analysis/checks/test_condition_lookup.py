import requests

condition_id = "0x24aba6bd6e6278069b57911685b30ef58b7227c3345794848641148e015e109d"

url = "https://gamma-api.polymarket.com/markets"


print("TEST 1: condition_id")

response = requests.get(
    url,
    params={
        "condition_id": condition_id
    },
    timeout=20
)

print("URL:", response.url)
print("HTTP:", response.status_code)

data = response.json()

print("Количество рынков:", len(data))

if data:
    print("Получили conditionId:")
    print(data[0].get("conditionId"))


print()
print("====================================")
print()


print("TEST 2: condition_ids")

response = requests.get(
    url,
    params={
        "condition_ids": condition_id
    },
    timeout=20
)

print("URL:", response.url)
print("HTTP:", response.status_code)

data = response.json()

print("Количество рынков:", len(data))

if data:
    print("Получили conditionId:")
    print(data[0].get("conditionId"))