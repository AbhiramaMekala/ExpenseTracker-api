"""Database layer: owns the SQLite connection and the schema.

Nothing outside this module opens a connection directly. The repository asks
the Database object for a connection, which keeps SQL setup in one place and
makes it easy to point the app at a different file (e.g. a temp file in tests).
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS expenses (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT    NOT NULL,
    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
    category     TEXT    NOT NULL,
    spent_on     TEXT    NOT NULL,          -- ISO date, YYYY-MM-DD
    note         TEXT,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_expenses_spent_on ON expenses (spent_on);
CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses (category);
"""


class Database:
    """Thin wrapper around a SQLite database file."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row  # rows behave like dicts
        return conn

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Yield a connection; commit on success, roll back on error, always close."""
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_schema(self) -> None:
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as conn:
            conn.executescript(SCHEMA)
