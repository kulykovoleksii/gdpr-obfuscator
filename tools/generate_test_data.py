"""
Generate a CSV with N rows for testing without external libs.
Columns: id, full_name, email, phone, address, age
"""
import csv
import random
import string


def random_name(i: int) -> str:
    return f"User{i} Test"


def random_email(i: int) -> str:
    return f"user{i}@example.com"


def random_phone(i: int) -> str:
    # simple phone
    return f"+44{random.randint(700000000,799999999)}"


def random_address(i: int) -> str:
    return f"{i} Baker St, Town-{i % 1000}"


def generate_csv(path: str, rows: int = 1_000_000, chunk: int = 100_000):
    fieldnames = ["id", "full_name", "email", "phone", "address", "age"]
    with open(path, "w", newline="", encoding="utf-8") as fout:
        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()
        for i in range(1, rows + 1):
            writer.writerow({
                "id": str(i),
                "full_name": random_name(i),
                "email": random_email(i),
                "phone": random_phone(i),
                "address": random_address(i),
                "age": str(random.randint(18, 90)),
            })
            if i % chunk == 0:
                print(f"Generated {i} rows")



if __name__ == "__main__":
    # small safety default if run accidentally
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1000000
    generate_csv("data.csv", rows=n)