import csv


count_total = 0

count_10_min = 0
count_1_hour = 0
count_6_hours = 0
count_24_hours = 0

count_negative = 0

min_minutes = None
max_minutes = None


with open(
    "trades_with_timing.csv",
    "r",
    encoding="utf-8"
) as file:

    reader = csv.DictReader(file)

    for trade in reader:

        count_total += 1

        minutes = float(trade["minutes_to_end"])


        # ------------------------------------------
        # Отрицательное время
        # ------------------------------------------

        if minutes < 0:
            count_negative += 1


        # ------------------------------------------
        # Время до окончания
        # ------------------------------------------

        if 0 <= minutes <= 10:
            count_10_min += 1

        if 0 <= minutes <= 60:
            count_1_hour += 1

        if 0 <= minutes <= 360:
            count_6_hours += 1

        if 0 <= minutes <= 1440:
            count_24_hours += 1


        # ------------------------------------------
        # Минимум / максимум
        # ------------------------------------------

        if min_minutes is None or minutes < min_minutes:
            min_minutes = minutes

        if max_minutes is None or minutes > max_minutes:
            max_minutes = minutes


print()
print("======================================")
print("ПРОВЕРКА ВРЕМЕНИ")
print("======================================")

print()
print("Всего сделок:", count_total)

print()
print("Сделок за 10 минут до конца:", count_10_min)

print("Сделок за 1 час до конца:", count_1_hour)

print("Сделок за 6 часов до конца:", count_6_hours)

print("Сделок за 24 часа до конца:", count_24_hours)

print()
print("Сделок после market_end:", count_negative)

print()
print("Минимальное minutes_to_end:", min_minutes)

print("Максимальное minutes_to_end:", max_minutes)