"""API layer: HTTP routes. Run with `uvicorn app.main:app --reload`.

Endpoints
---------
POST   /expenses                 add an expense
GET    /expenses                 list expenses (filter by category / month, paginate)
GET    /expenses/summary         monthly or category-wise totals
GET    /expenses/{id}            view one expense
PUT    /expenses/{id}            update an expense
DELETE /expenses/{id}            delete an expense

A separate browser front-end lives in frontend/ and talks to these endpoints
over HTTP; see app/middleware.py for how cross-origin calls are allowed and logged.
"""

import os
from typing import Literal

from fastapi import Depends, FastAPI, Query, Request, status
from fastapi.responses import JSONResponse, Response

from . import middleware
from .database import Database
from .repository import ExpenseRepository
from .schemas import ExpenseIn, ExpenseOut, SummaryOut, SummaryResponse
from .service import ExpenseNotFound, ExpenseService, InvalidExpense

DEFAULT_DB_PATH = os.getenv("EXPENSES_DB", "data/expenses.db")


def create_app(db_path: str = DEFAULT_DB_PATH) -> FastAPI:
    """Build the app. Tests call this with a temporary database file."""
    db = Database(db_path)
    db.init_schema()

    app = FastAPI(
        title="Expense Tracker API",
        version="1.0.0",
        description="Track personal expenses and see monthly and category-wise summaries.",
    )
    app.state.service = ExpenseService(ExpenseRepository(db))
    middleware.install(app)  # CORS for the browser front-end + request log

    # ----- map domain errors to HTTP responses -----

    @app.exception_handler(ExpenseNotFound)
    async def not_found_handler(_: Request, exc: ExpenseNotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(InvalidExpense)
    async def invalid_handler(_: Request, exc: InvalidExpense) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    def get_service(request: Request) -> ExpenseService:
        return request.app.state.service

    # ----- routes -----

    @app.get("/", include_in_schema=False)
    def root() -> dict:
        return {"message": "Expense Tracker API. Open /docs for the interactive docs."}

    @app.post("/expenses", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED,
              tags=["expenses"])
    def add_expense(body: ExpenseIn, svc: ExpenseService = Depends(get_service)) -> ExpenseOut:
        data = svc.build_data(body.title, body.amount, body.category, body.spent_on, body.note)
        return ExpenseOut.from_expense(svc.create(data))

    @app.get("/expenses", response_model=list[ExpenseOut], tags=["expenses"])
    def list_expenses(
        category: str | None = Query(None, description="e.g. food"),
        month: str | None = Query(None, description="YYYY-MM, e.g. 2026-09"),
        limit: int = Query(100, ge=1, le=500),
        offset: int = Query(0, ge=0),
        svc: ExpenseService = Depends(get_service),
    ) -> list[ExpenseOut]:
        return [ExpenseOut.from_expense(e) for e in svc.list_expenses(category, month, limit, offset)]

    # Declared before /expenses/{expense_id} so "summary" is not read as an id.
    @app.get("/expenses/summary", response_model=SummaryResponse, tags=["summaries"])
    def summary(
        by: Literal["month", "category"] = Query("month"),
        year: int | None = Query(None, ge=1900, le=2100, description="only for by=month"),
        month: str | None = Query(None, description="YYYY-MM, only for by=category"),
        svc: ExpenseService = Depends(get_service),
    ) -> SummaryResponse:
        rows = svc.summary(by, year=year, month=month)
        grand_total = sum(r.total_cents for r in rows) / 100
        return SummaryResponse(by=by, grand_total=grand_total,
                               rows=[SummaryOut.from_row(r) for r in rows])

    @app.get("/expenses/{expense_id}", response_model=ExpenseOut, tags=["expenses"])
    def get_expense(expense_id: int, svc: ExpenseService = Depends(get_service)) -> ExpenseOut:
        return ExpenseOut.from_expense(svc.get(expense_id))

    @app.put("/expenses/{expense_id}", response_model=ExpenseOut, tags=["expenses"])
    def update_expense(expense_id: int, body: ExpenseIn,
                       svc: ExpenseService = Depends(get_service)) -> ExpenseOut:
        data = svc.build_data(body.title, body.amount, body.category, body.spent_on, body.note)
        return ExpenseOut.from_expense(svc.update(expense_id, data))

    @app.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT,
                tags=["expenses"])
    def delete_expense(expense_id: int, svc: ExpenseService = Depends(get_service)) -> Response:
        svc.delete(expense_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return app


app = create_app()
