"""End-to-end tests for all 6 HTTP endpoints, using FastAPI's TestClient.

Run with:  python -m pytest -v
"""

from datetime import date, timedelta

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import create_app  # noqa: E402


@pytest.fixture()
def client(tmp_path):
    return TestClient(create_app(str(tmp_path / "test.db")))


def new_expense(client, **overrides):
    body = {"title": "Lunch", "amount": 12.5, "category": "food",
            "spent_on": "2026-09-03", "note": None}
    body.update(overrides)
    return client.post("/expenses", json=body)


# ---------- POST /expenses ----------

def test_create_returns_201_and_body(client):
    r = new_expense(client, title="Coffee", amount=4.75, category="Food")
    assert r.status_code == 201
    body = r.json()
    assert body["id"] > 0
    assert body["title"] == "Coffee"
    assert body["amount"] == 4.75
    assert body["category"] == "food"


@pytest.mark.parametrize("override", [
    {"title": ""},
    {"amount": 0},
    {"amount": -5},
    {"amount": 1.234},             # more than 2 decimal places
    {"spent_on": "not-a-date"},
    {"spent_on": (date.today() + timedelta(days=2)).isoformat()},
])
def test_create_rejects_invalid(client, override):
    assert new_expense(client, **override).status_code == 422


# ---------- GET /expenses ----------

def test_list_and_filters(client):
    new_expense(client, category="food", spent_on="2026-08-30")
    new_expense(client, category="food", spent_on="2026-09-02")
    new_expense(client, category="travel", spent_on="2026-09-05")

    assert len(client.get("/expenses").json()) == 3
    assert len(client.get("/expenses", params={"category": "food"}).json()) == 2
    assert len(client.get("/expenses", params={"month": "2026-09"}).json()) == 2
    assert client.get("/expenses", params={"month": "2026-9"}).status_code == 422


# ---------- GET /expenses/{id} ----------

def test_get_one_and_404(client):
    created = new_expense(client).json()
    assert client.get(f"/expenses/{created['id']}").json() == created
    assert client.get("/expenses/9999").status_code == 404


# ---------- PUT /expenses/{id} ----------

def test_update(client):
    eid = new_expense(client).json()["id"]
    r = client.put(f"/expenses/{eid}", json={
        "title": "Dinner", "amount": 30, "category": "food", "spent_on": "2026-09-04"})
    assert r.status_code == 200
    assert r.json()["title"] == "Dinner"
    assert r.json()["amount"] == 30.0
    missing = client.put("/expenses/9999", json={
        "title": "x", "amount": 1, "category": "misc", "spent_on": "2026-09-04"})
    assert missing.status_code == 404


# ---------- DELETE /expenses/{id} ----------

def test_delete(client):
    eid = new_expense(client).json()["id"]
    assert client.delete(f"/expenses/{eid}").status_code == 204
    assert client.get(f"/expenses/{eid}").status_code == 404
    assert client.delete(f"/expenses/{eid}").status_code == 404


# ---------- GET /expenses/summary ----------

def test_summaries(client):
    new_expense(client, amount=10, category="food", spent_on="2026-08-10")
    new_expense(client, amount=20, category="food", spent_on="2026-09-01")
    new_expense(client, amount=100, category="rent", spent_on="2026-09-03")

    monthly = client.get("/expenses/summary", params={"by": "month"}).json()
    assert monthly["grand_total"] == 130.0
    assert [(r["group"], r["total"]) for r in monthly["rows"]] == [
        ("2026-08", 10.0), ("2026-09", 120.0)]

    by_cat = client.get("/expenses/summary",
                        params={"by": "category", "month": "2026-09"}).json()
    assert [(r["group"], r["count"]) for r in by_cat["rows"]] == [("rent", 1), ("food", 1)]

    assert client.get("/expenses/summary", params={"by": "week"}).status_code == 422
