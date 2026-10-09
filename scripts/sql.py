"""Run a SQL query against the expenses database and print the result as a table.

Usage:
    python3 scripts/sql.py "SELECT * FROM expenses LIMIT 5"
    python3 scripts/sql.py --tables
    python3 scripts/sql.py --schema

The database path comes from EXPENSES_DB (default data/expenses.db), the same
setting the API uses. Uses only Python's built-in sqlite3 module, so it works
anywhere Python does, even without the sqlite3 command-line tool.
"""

import os
import sqlite3
import sys


def print_table(headers: list[str], rows: list[tuple]) -> None:
    cells = [[("" if v is None else str(v)) for v in row] for row in rows]
    widths = [max([len(h)] + [len(r[i]) for r in cells]) for i, h in enumerate(headers)]
    numeric = [all(isinstance(row[i], (int, float)) or row[i] is None for row in rows) and rows
               for i in range(len(headers))]

    def fmt(values: list[str]) -> str:
        return "  ".join(v.rjust(w) if numeric[i] else v.ljust(w)
                         for i, (v, w) in enumerate(zip(values, widths))).rstrip()

    print(fmt(headers))
    print("  ".join("-" * w for w in widths))
    for r in cells:
        print(fmt(r))
    print(f"({len(rows)} row{'s' if len(rows) != 1 else ''})")


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip())
        return 1
    path = os.getenv("EXPENSES_DB", "data/expenses.db")
    if not os.path.exists(path):
        print(f"No database at {path}. Start the API or run: python -m scripts.seed")
        return 1

    conn = sqlite3.connect(path)
    try:
        if argv[0] == "--tables":
            rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' "
                                "AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
            print("\n".join(r[0] for r in rows))
            return 0
        if argv[0] == "--schema":
            for (sql,) in conn.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL "
                                       "AND name NOT LIKE 'sqlite_%'"):
                print(sql.strip() + ";")
            return 0
        cur = conn.execute(" ".join(argv))
        if cur.description is None:
            conn.commit()
            print(f"OK, {cur.rowcount} row(s) changed")
        else:
            print_table([d[0] for d in cur.description], cur.fetchall())
        return 0
    except sqlite3.Error as exc:
        print(f"SQL error: {exc}")
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
