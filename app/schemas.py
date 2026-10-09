"""Pydantic models that define the JSON shapes of requests and responses."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from .models import Expense, SummaryRow


class ExpenseIn(BaseModel):
    """Body for POST /expenses and PUT /expenses/{id}."""

    title: str = Field(..., min_length=1, max_length=100, examples=["Groceries"])
    amount: Decimal = Field(..., gt=0, max_digits=9, decimal_places=2, examples=[42.50])
    category: str = Field(..., min_length=1, max_length=40, examples=["food"])
    spent_on: date = Field(..., examples=["2026-09-14"])
    note: str | None = Field(None, max_length=500, examples=["Trader Joe's"])


class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    amount: float
    category: str
    spent_on: date
    note: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_expense(cls, e: Expense) -> "ExpenseOut":
        return cls(
            id=e.id, title=e.title, amount=e.amount, category=e.category,
            spent_on=e.spent_on, note=e.note,
            created_at=e.created_at, updated_at=e.updated_at,
        )


class SummaryOut(BaseModel):
    group: str
    count: int
    total: float
    average: float

    @classmethod
    def from_row(cls, r: SummaryRow) -> "SummaryOut":
        return cls(group=r.group, count=r.count,
                   total=r.total_cents / 100, average=r.average_cents / 100)


class SummaryResponse(BaseModel):
    by: str
    grand_total: float
    rows: list[SummaryOut]
