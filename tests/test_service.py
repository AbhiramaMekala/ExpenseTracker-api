"""Tests for the database, repository and service layers (no web server needed).

Run with:  python -m pytest   (or)   python -m unittest discover tests
"""

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from app.database import Database
from app.repository import ExpenseRepository
from app.service import ExpenseNotFound, ExpenseService, InvalidExpense, to_cents


class ServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        db = Database(Path(self._tmp.name) / "test.db")
        db.init_schema()
        self.svc = ExpenseService(ExpenseRepository(db))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def add(self, title="Lunch", amount="12.50", category="food",
            spent_on=date(2026, 9, 3), note=None):
        return self.svc.create(self.svc.build_data(title, amount, category, spent_on, note))


class TestMoney(unittest.TestCase):
    def test_to_cents_avoids_float_error(self):
        self.assertEqual(to_cents(19.99), 1999)
        self.assertEqual(to_cents("0.1"), 10)
        self.assertEqual(to_cents(2.675), 268)  # rounds half up


class TestCrud(ServiceTestCase):
    def test_add_and_get(self):
        e = self.add(title="  Coffee ", category=" Food ", note="  ")
        got = self.svc.get(e.id)
        self.assertEqual(got.title, "Coffee")
        self.assertEqual(got.category, "food")      # normalised
        self.assertIsNone(got.note)                 # blank note becomes None
        self.assertEqual(got.amount, 12.5)

    def test_list_filters(self):
        self.add(category="food", spent_on=date(2026, 8, 30))
        self.add(category="food", spent_on=date(2026, 9, 2))
        self.add(category="travel", spent_on=date(2026, 9, 5))
        self.assertEqual(len(self.svc.list_expenses()), 3)
        self.assertEqual(len(self.svc.list_expenses(category="FOOD")), 2)
        self.assertEqual(len(self.svc.list_expenses(month="2026-09")), 2)
        self.assertEqual(len(self.svc.list_expenses(category="food", month="2026-09")), 1)

    def test_list_newest_first_and_paging(self):
        for d in (1, 2, 3):
            self.add(title=f"day {d}", spent_on=date(2026, 9, d))
        titles = [e.title for e in self.svc.list_expenses(limit=2)]
        self.assertEqual(titles, ["day 3", "day 2"])
        self.assertEqual([e.title for e in self.svc.list_expenses(limit=2, offset=2)], ["day 1"])

    def test_update(self):
        e = self.add()
        new = self.svc.build_data("Dinner", "30", "food", date(2026, 9, 4))
        updated = self.svc.update(e.id, new)
        self.assertEqual(updated.title, "Dinner")
        self.assertEqual(updated.amount_cents, 3000)

    def test_delete(self):
        e = self.add()
        self.svc.delete(e.id)
        with self.assertRaises(ExpenseNotFound):
            self.svc.get(e.id)

    def test_missing_ids_raise_not_found(self):
        data = self.svc.build_data("x", "1", "misc", date(2026, 9, 1))
        with self.assertRaises(ExpenseNotFound):
            self.svc.get(999)
        with self.assertRaises(ExpenseNotFound):
            self.svc.update(999, data)
        with self.assertRaises(ExpenseNotFound):
            self.svc.delete(999)


class TestValidation(ServiceTestCase):
    def test_rejects_bad_input(self):
        today = date.today()
        bad = [
            ("", "5", "food", today),
            ("x", "0", "food", today),
            ("x", "-3", "food", today),
            ("x", "5", "  ", today),
            ("x", "1000000.01", "food", today),
            ("x", "5", "food", today + timedelta(days=1)),
        ]
        for args in bad:
            with self.subTest(args=args), self.assertRaises(InvalidExpense):
                self.svc.build_data(*args)

    def test_rejects_bad_month(self):
        for m in ("2026-13", "2026-9", "Sept"):
            with self.subTest(m=m), self.assertRaises(InvalidExpense):
                self.svc.list_expenses(month=m)


class TestSummaries(ServiceTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.add(amount="10.00", category="food", spent_on=date(2026, 8, 10))
        self.add(amount="20.00", category="food", spent_on=date(2026, 9, 1))
        self.add(amount="5.00", category="travel", spent_on=date(2026, 9, 2))
        self.add(amount="100.00", category="rent", spent_on=date(2026, 9, 3))
        self.add(amount="7.00", category="food", spent_on=date(2025, 12, 31))

    def test_monthly(self):
        rows = self.svc.summary("month")
        self.assertEqual([r.group for r in rows], ["2025-12", "2026-08", "2026-09"])
        sept = rows[-1]
        self.assertEqual((sept.count, sept.total_cents, sept.average_cents), (3, 12500, 4167))

    def test_monthly_filtered_by_year(self):
        rows = self.svc.summary("month", year=2026)
        self.assertEqual([r.group for r in rows], ["2026-08", "2026-09"])

    def test_category_sorted_by_total(self):
        rows = self.svc.summary("category")
        self.assertEqual([(r.group, r.total_cents) for r in rows],
                         [("rent", 10000), ("food", 3700), ("travel", 500)])

    def test_category_for_one_month(self):
        rows = self.svc.summary("category", month="2026-09")
        self.assertEqual({r.group: r.count for r in rows}, {"rent": 1, "food": 1, "travel": 1})

    def test_bad_group(self):
        with self.assertRaises(InvalidExpense):
            self.svc.summary("week")


if __name__ == "__main__":
    unittest.main()
