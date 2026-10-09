# Expense Tracker REST API

A REST API for tracking personal expenses, built with **Python, FastAPI and SQLite**.
It supports full CRUD on expenses plus **monthly** and **category-wise** spending summaries
computed with SQL.

## Features

- 6 endpoints to add, view, update and delete expenses and to summarise spending
- Layered, object-oriented design: API → service → repository → database
- SQL aggregation queries (`GROUP BY`, `strftime`, `SUM`, `AVG`) for summaries
- Money stored as integer cents, so `19.99` never turns into `19.989999…`
- Input validation (Pydantic + business rules) with clear `422` / `404` errors
- Interactive docs generated automatically at `/docs`
- Tested two ways: a **pytest** suite and a **Postman** collection with test scripts

## Project structure

```
expense-tracker-api/
├── app/
│   ├── main.py         # API layer: FastAPI routes, error → HTTP status mapping
│   ├── schemas.py      # Pydantic request/response models
│   ├── service.py      # ExpenseService: validation and business rules
│   ├── repository.py   # ExpenseRepository: every SQL query lives here
│   ├── database.py     # Database: connection handling and schema
│   └── models.py       # Plain dataclasses passed between layers
├── tests/
│   ├── test_service.py # data + business layer tests (no server needed)
│   └── test_api.py     # end-to-end tests of all 6 endpoints
├── postman/
│   └── expense-tracker.postman_collection.json
├── scripts/seed.py     # loads ~3 months of sample data
└── requirements.txt
```

Each layer only talks to the one below it. The routes never write SQL, and the
repository never knows about HTTP, which keeps each class small and testable on its own.

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m scripts.seed             # optional: sample data
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000/docs** to try every endpoint in the browser.
The database file is created at `data/expenses.db` (override with the `EXPENSES_DB` environment variable).

## Endpoints

| Method | Path                  | Description                                             |
|--------|-----------------------|---------------------------------------------------------|
| POST   | `/expenses`           | Add an expense → `201 Created`                          |
| GET    | `/expenses`           | List expenses; filter with `category`, `month`; paginate with `limit`, `offset` |
| GET    | `/expenses/{id}`      | View one expense (`404` if missing)                     |
| PUT    | `/expenses/{id}`      | Update an expense                                       |
| DELETE | `/expenses/{id}`      | Delete an expense → `204 No Content`                    |
| GET    | `/expenses/summary`   | `?by=month[&year=2026]` or `?by=category[&month=2026-09]` |

### Example

```bash
curl -X POST http://127.0.0.1:8000/expenses \
  -H "Content-Type: application/json" \
  -d '{"title": "Groceries", "amount": 42.50, "category": "food", "spent_on": "2026-09-14"}'
```

```json
{"id": 1, "title": "Groceries", "amount": 42.5, "category": "food",
 "spent_on": "2026-09-14", "note": null,
 "created_at": "2026-10-09 14:02:11", "updated_at": "2026-10-09 14:02:11"}
```

```bash
curl "http://127.0.0.1:8000/expenses/summary?by=category&month=2026-09"
```

```json
{"by": "category", "grand_total": 1617.3,
 "rows": [{"group": "rent", "count": 1, "total": 1450.0, "average": 1450.0},
          {"group": "food", "count": 2, "total": 167.3, "average": 83.65}]}
```

### The summary SQL

```sql
SELECT strftime('%Y-%m', spent_on) AS grp,
       COUNT(*)                    AS cnt,
       SUM(amount_cents)           AS total,
       CAST(ROUND(AVG(amount_cents)) AS INTEGER) AS avg
FROM expenses
GROUP BY grp
ORDER BY grp;
```

All queries use `?` placeholders, so user input is never pasted into SQL text.

## Validation rules

| Rule                                   | Response |
|----------------------------------------|----------|
| Title and category must not be blank   | 422 |
| Amount > 0, at most 2 decimals, ≤ 1,000,000 | 422 |
| `spent_on` must be a real date and not in the future | 422 |
| `month` filters must look like `YYYY-MM` | 422 |
| Unknown expense id                     | 404 |

Categories are trimmed and lower-cased, so `" Food "` and `"food"` are grouped together.

## Testing

```bash
python -m pytest -v
```

`test_service.py` covers the database, repository and service layers;
`test_api.py` sends real HTTP requests to every endpoint, including error cases.

**Postman:** import `postman/expense-tracker.postman_collection.json`, start the server,
and run the collection. It walks through create → list → get → update → summaries → delete,
storing the new id in a variable and checking status codes and response bodies.

## Possible next steps

- User accounts with token authentication
- Budgets per category with over-budget alerts
- CSV export of filtered expenses
- Docker image and a hosted deployment
