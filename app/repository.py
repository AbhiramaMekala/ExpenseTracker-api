"""Repository layer: every SQL statement in the project lives here.

All queries use ? placeholders (never string formatting with user input), so
values are passed to SQLite separately from the SQL text and cannot inject SQL.
"""

import sqlite3
from datetime import date

from .database import Database
from .models import Expense, ExpenseData, SummaryRow


class ExpenseRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    # ---------- helpers ----------

    @staticmethod
    def _to_expense(row: sqlite3.Row) -> Expense:
        return Expense(
            id=row["id"],
            title=row["title"],
            amount_cents=row["amount_cents"],
            category=row["category"],
            spent_on=date.fromisoformat(row["spent_on"]),
            note=row["note"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    # ---------- CRUD ----------

    def add(self, data: ExpenseData) -> Expense:
        with self.db.connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO expenses (title, amount_cents, category, spent_on, note)
                VALUES (?, ?, ?, ?, ?)
                """,
                (data.title, data.amount_cents, data.category,
                 data.spent_on.isoformat(), data.note),
            )
            new_id = cur.lastrowid
        return self.get(new_id)  # type: ignore[return-value]

    def get(self, expense_id: int) -> Expense | None:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT * FROM expenses WHERE id = ?", (expense_id,)
            ).fetchone()
        return self._to_expense(row) if row else None

    def list_expenses(
        self,
        category: str | None = None,
        month: str | None = None,       # "YYYY-MM"
        limit: int = 100,
        offset: int = 0,
    ) -> list[Expense]:
        clauses, params = [], []
        if category:
            clauses.append("category = ?")
            params.append(category)
        if month:
            clauses.append("strftime('%Y-%m', spent_on) = ?")
            params.append(month)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"""
            SELECT * FROM expenses
            {where}
            ORDER BY spent_on DESC, id DESC
            LIMIT ? OFFSET ?
        """
        with self.db.connection() as conn:
            rows = conn.execute(sql, (*params, limit, offset)).fetchall()
        return [self._to_expense(r) for r in rows]

    def update(self, expense_id: int, data: ExpenseData) -> Expense | None:
        with self.db.connection() as conn:
            cur = conn.execute(
                """
                UPDATE expenses
                SET title = ?, amount_cents = ?, category = ?, spent_on = ?,
                    note = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (data.title, data.amount_cents, data.category,
                 data.spent_on.isoformat(), data.note, expense_id),
            )
            changed = cur.rowcount
        return self.get(expense_id) if changed else None

    def delete(self, expense_id: int) -> bool:
        with self.db.connection() as conn:
            cur = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
            return cur.rowcount > 0

    # ---------- summaries ----------

    def monthly_summary(self, year: int | None = None) -> list[SummaryRow]:
        """Total, count and average spend per calendar month."""
        sql = """
            SELECT strftime('%Y-%m', spent_on)     AS grp,
                   COUNT(*)                        AS cnt,
                   SUM(amount_cents)               AS total,
                   CAST(ROUND(AVG(amount_cents)) AS INTEGER) AS avg
            FROM expenses
            {where}
            GROUP BY grp
            ORDER BY grp
        """
        params: tuple = ()
        where = ""
        if year is not None:
            where = "WHERE strftime('%Y', spent_on) = ?"
            params = (f"{year:04d}",)
        with self.db.connection() as conn:
            rows = conn.execute(sql.format(where=where), params).fetchall()
        return [SummaryRow(r["grp"], r["cnt"], r["total"], r["avg"]) for r in rows]

    def category_summary(self, month: str | None = None) -> list[SummaryRow]:
        """Total, count and average spend per category, biggest first."""
        sql = """
            SELECT category                        AS grp,
                   COUNT(*)                        AS cnt,
                   SUM(amount_cents)               AS total,
                   CAST(ROUND(AVG(amount_cents)) AS INTEGER) AS avg
            FROM expenses
            {where}
            GROUP BY category
            ORDER BY total DESC, category
        """
        params: tuple = ()
        where = ""
        if month:
            where = "WHERE strftime('%Y-%m', spent_on) = ?"
            params = (month,)
        with self.db.connection() as conn:
            rows = conn.execute(sql.format(where=where), params).fetchall()
        return [SummaryRow(r["grp"], r["cnt"], r["total"], r["avg"]) for r in rows]
