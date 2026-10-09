"""Service layer: business rules that sit between the API and the database.

The API layer turns HTTP requests into calls on ExpenseService; the service
cleans up input, applies rules, and raises domain errors that the API maps to
HTTP status codes. It never touches SQL directly.
"""

import re
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from .models import Expense, ExpenseData, SummaryRow
from .repository import ExpenseRepository

MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
MAX_AMOUNT_CENTS = 100_000_000  # $1,000,000 cap guards against typos


class ExpenseNotFound(Exception):
    def __init__(self, expense_id: int) -> None:
        super().__init__(f"Expense {expense_id} not found")
        self.expense_id = expense_id


class InvalidExpense(ValueError):
    """Input that is well-formed but breaks a business rule."""


def to_cents(amount: float | Decimal | str) -> int:
    """Convert a money amount to integer cents without float rounding errors.

    19.99 as a float is 19.989999..., so int(19.99 * 100) would give 1998.
    Going through Decimal(str(...)) keeps it exactly 1999.
    """
    value = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(value * 100)


class ExpenseService:
    def __init__(self, repo: ExpenseRepository) -> None:
        self.repo = repo

    # ---------- input cleanup ----------

    @staticmethod
    def build_data(
        title: str,
        amount: float | Decimal | str,
        category: str,
        spent_on: date,
        note: str | None = None,
    ) -> ExpenseData:
        title = (title or "").strip()
        category = (category or "").strip().lower()
        note = note.strip() if note and note.strip() else None
        cents = to_cents(amount)

        if not title:
            raise InvalidExpense("title must not be empty")
        if not category:
            raise InvalidExpense("category must not be empty")
        if cents <= 0:
            raise InvalidExpense("amount must be greater than 0")
        if cents > MAX_AMOUNT_CENTS:
            raise InvalidExpense("amount must be at most 1,000,000.00")
        if spent_on > date.today():
            raise InvalidExpense("spent_on cannot be in the future")

        return ExpenseData(title, cents, category, spent_on, note)

    @staticmethod
    def check_month(month: str | None) -> None:
        if month is not None and not MONTH_PATTERN.match(month):
            raise InvalidExpense("month must look like YYYY-MM, e.g. 2026-09")

    # ---------- operations ----------

    def create(self, data: ExpenseData) -> Expense:
        return self.repo.add(data)

    def get(self, expense_id: int) -> Expense:
        expense = self.repo.get(expense_id)
        if expense is None:
            raise ExpenseNotFound(expense_id)
        return expense

    def list_expenses(self, category: str | None = None, month: str | None = None,
                      limit: int = 100, offset: int = 0) -> list[Expense]:
        self.check_month(month)
        if category:
            category = category.strip().lower()
        return self.repo.list_expenses(category, month, limit, offset)

    def update(self, expense_id: int, data: ExpenseData) -> Expense:
        expense = self.repo.update(expense_id, data)
        if expense is None:
            raise ExpenseNotFound(expense_id)
        return expense

    def delete(self, expense_id: int) -> None:
        if not self.repo.delete(expense_id):
            raise ExpenseNotFound(expense_id)

    def summary(self, by: str, year: int | None = None,
                month: str | None = None) -> list[SummaryRow]:
        if by == "month":
            return self.repo.monthly_summary(year)
        if by == "category":
            self.check_month(month)
            return self.repo.category_summary(month)
        raise InvalidExpense("by must be 'month' or 'category'")
