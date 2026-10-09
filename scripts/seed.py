"""Fill the database with ~3 months of realistic sample expenses.

Usage:  python -m scripts.seed            (writes to data/expenses.db)
        EXPENSES_DB=other.db python -m scripts.seed
"""

import os
import random
from datetime import date, timedelta

from app.database import Database
from app.repository import ExpenseRepository
from app.service import ExpenseService

CATALOGUE = {
    "food": [("Groceries", 25, 90), ("Lunch", 8, 18), ("Coffee", 3, 7)],
    "transport": [("MetroCard refill", 20, 34), ("Uber", 12, 40)],
    "rent": [("Monthly rent", 1450, 1450)],
    "utilities": [("Electricity", 45, 80), ("Phone bill", 35, 35)],
    "education": [("Textbook", 30, 120), ("Online course", 15, 50)],
    "entertainment": [("Movie", 14, 22), ("Concert", 40, 110)],
}


def main(n_days: int = 90, seed: int = 7) -> None:
    rng = random.Random(seed)
    db = Database(os.getenv("EXPENSES_DB", "data/expenses.db"))
    db.init_schema()
    svc = ExpenseService(ExpenseRepository(db))

    start = date.today() - timedelta(days=n_days)
    count = 0
    for offset in range(n_days + 1):
        day = start + timedelta(days=offset)
        if day.day == 1:
            svc.create(svc.build_data("Monthly rent", 1450, "rent", day))
            count += 1
        for _ in range(rng.randint(0, 3)):
            category = rng.choice([c for c in CATALOGUE if c != "rent"])
            title, low, high = rng.choice(CATALOGUE[category])
            amount = round(rng.uniform(low, high), 2)
            svc.create(svc.build_data(title, amount, category, day))
            count += 1
    print(f"Inserted {count} expenses into {db.path}")


if __name__ == "__main__":
    main()
