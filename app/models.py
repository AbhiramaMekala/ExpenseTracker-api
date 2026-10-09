"""Domain objects used between the repository and the service layers.

These are plain dataclasses (no FastAPI or Pydantic dependency) so the data
and business layers can be used and tested on their own.
"""

from dataclasses import dataclass
from datetime import date


@dataclass
class ExpenseData:
    """The editable fields of an expense (what a client sends in)."""

    title: str
    amount_cents: int
    category: str
    spent_on: date
    note: str | None = None


@dataclass
class Expense(ExpenseData):
    """A stored expense, including server-managed fields."""

    id: int = 0
    created_at: str = ""
    updated_at: str = ""

    @property
    def amount(self) -> float:
        return self.amount_cents / 100


@dataclass
class SummaryRow:
    """One line of a monthly or category-wise summary."""

    group: str           # "2026-09" for months, "food" for categories
    count: int
    total_cents: int
    average_cents: int
