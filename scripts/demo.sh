#!/usr/bin/env bash
# A guided tour of the Expense Tracker API: runs the main curl commands from
# docs/commands.html in order and prints each response.
#
# Start the API first (Terminal 1):   uvicorn app.main:app --reload
# Then run this (Terminal 2):          bash scripts/demo.sh
#
# It adds a few example expenses to whichever database the server is using and
# deletes only the one it creates for the update/delete steps. For a throwaway
# database, start the server with:   EXPENSES_DB=data/demo.db uvicorn app.main:app --reload
#
# Generated from the same list of commands as docs/commands.html.

if ! curl -s -o /dev/null http://127.0.0.1:8000/; then
  echo "The API is not running at http://127.0.0.1:8000"
  echo "Start it in another terminal with:  uvicorn app.main:app --reload"
  exit 1
fi

BOLD=$(printf "\033[1m"); DIM=$(printf "\033[2m"); RESET=$(printf "\033[0m")
step() { printf "\n%s== %s ==%s\n%s$ %s%s\n" "$BOLD" "$1" "$RESET" "$DIM" "$2" "$RESET"; }


# ---------------- Check the server ----------------
step "Check the server: Is the server up?" "curl -s http://127.0.0.1:8000/"
curl -s http://127.0.0.1:8000/
echo
step "Check the server: List every route the API exposes" "curl -s http://127.0.0.1:8000/openapi.json | python3 -c 'import sys, json; [print(m.upper().ljust(7), p) for p, ops in json.load(sys.stdin)[\"paths\"].items() for m in ops]'"
curl -s http://127.0.0.1:8000/openapi.json | python3 -c 'import sys, json; [print(m.upper().ljust(7), p) for p, ops in json.load(sys.stdin)["paths"].items() for m in ops]'
echo

# ---------------- Add expenses ----------------
step "Add expenses: Add an expense" "curl -s -X POST http://127.0.0.1:8000/expenses -H \"Content-Type: application/json\" -d '{\"title\": \"Groceries\", \"amount\": 42.50, \"category\": \"food\", \"spent_on\": \"2026-10-05\"}' | python3 -m json.tool"
curl -s -X POST http://127.0.0.1:8000/expenses -H "Content-Type: application/json" -d '{"title": "Groceries", "amount": 42.50, "category": "food", "spent_on": "2026-10-05"}' | python3 -m json.tool
echo
step "Add expenses: Add one with a note" "curl -s -X POST http://127.0.0.1:8000/expenses -H \"Content-Type: application/json\" -d '{\"title\": \"MetroCard refill\", \"amount\": 34, \"category\": \"transport\", \"spent_on\": \"2026-09-28\", \"note\": \"Unlimited 7-day\"}' | python3 -m json.tool"
curl -s -X POST http://127.0.0.1:8000/expenses -H "Content-Type: application/json" -d '{"title": "MetroCard refill", "amount": 34, "category": "transport", "spent_on": "2026-09-28", "note": "Unlimited 7-day"}' | python3 -m json.tool
echo
step "Add expenses: Messy input gets cleaned up" "curl -s -X POST http://127.0.0.1:8000/expenses -H \"Content-Type: application/json\" -d '{\"title\": \"  Coffee  \", \"amount\": 4.75, \"category\": \"  FOOD \", \"spent_on\": \"2026-10-07\", \"note\": \"   \"}' | python3 -m json.tool"
curl -s -X POST http://127.0.0.1:8000/expenses -H "Content-Type: application/json" -d '{"title": "  Coffee  ", "amount": 4.75, "category": "  FOOD ", "spent_on": "2026-10-07", "note": "   "}' | python3 -m json.tool
echo
step "Add expenses: Money is stored exactly" "curl -s -X POST http://127.0.0.1:8000/expenses -H \"Content-Type: application/json\" -d '{\"title\": \"Notebook\", \"amount\": 19.99, \"category\": \"education\", \"spent_on\": \"2026-09-15\"}' | python3 -m json.tool"
curl -s -X POST http://127.0.0.1:8000/expenses -H "Content-Type: application/json" -d '{"title": "Notebook", "amount": 19.99, "category": "education", "spent_on": "2026-09-15"}' | python3 -m json.tool
echo
step "Add expenses: Add one and save its id for later commands" "ID=\$(curl -s -X POST http://127.0.0.1:8000/expenses -H \"Content-Type: application/json\" -d '{\"title\": \"Concert ticket\", \"amount\": 85, \"category\": \"entertainment\", \"spent_on\": \"2026-10-08\"}' | python3 -c 'import sys, json; print(json.load(sys.stdin)[\"id\"])') && echo \"New expense id: \$ID\""
ID=$(curl -s -X POST http://127.0.0.1:8000/expenses -H "Content-Type: application/json" -d '{"title": "Concert ticket", "amount": 85, "category": "entertainment", "spent_on": "2026-10-08"}' | python3 -c 'import sys, json; print(json.load(sys.stdin)["id"])') && echo "New expense id: $ID"
echo
step "Add expenses: Add several in a loop" "for day in 01 02 03; do curl -s -o /dev/null -w \"%{http_code} \" -X POST http://127.0.0.1:8000/expenses -H \"Content-Type: application/json\" -d \"{\\\"title\\\": \\\"Lunch\\\", \\\"amount\\\": 12.50, \\\"category\\\": \\\"food\\\", \\\"spent_on\\\": \\\"2026-10-\$day\\\"}\"; done; echo"
for day in 01 02 03; do curl -s -o /dev/null -w "%{http_code} " -X POST http://127.0.0.1:8000/expenses -H "Content-Type: application/json" -d "{\"title\": \"Lunch\", \"amount\": 12.50, \"category\": \"food\", \"spent_on\": \"2026-10-$day\"}"; done; echo
echo
step "Add expenses: See the status line and headers too" "curl -s -i -X POST http://127.0.0.1:8000/expenses -H \"Content-Type: application/json\" -d '{\"title\": \"Phone bill\", \"amount\": 35, \"category\": \"utilities\", \"spent_on\": \"2026-09-01\"}'"
curl -s -i -X POST http://127.0.0.1:8000/expenses -H "Content-Type: application/json" -d '{"title": "Phone bill", "amount": 35, "category": "utilities", "spent_on": "2026-09-01"}'
echo

# ---------------- Validation errors ----------------
step "Validation errors: Amount of zero" "curl -s -X POST http://127.0.0.1:8000/expenses -H \"Content-Type: application/json\" -d '{\"title\": \"Free sample\", \"amount\": 0, \"category\": \"food\", \"spent_on\": \"2026-10-05\"}' -w \"\\nHTTP %{http_code}\\n\""
curl -s -X POST http://127.0.0.1:8000/expenses -H "Content-Type: application/json" -d '{"title": "Free sample", "amount": 0, "category": "food", "spent_on": "2026-10-05"}' -w "\nHTTP %{http_code}\n"
echo
step "Validation errors: Title that is only spaces" "curl -s -X POST http://127.0.0.1:8000/expenses -H \"Content-Type: application/json\" -d '{\"title\": \"   \", \"amount\": 5, \"category\": \"food\", \"spent_on\": \"2026-10-05\"}' -w \"\\nHTTP %{http_code}\\n\""
curl -s -X POST http://127.0.0.1:8000/expenses -H "Content-Type: application/json" -d '{"title": "   ", "amount": 5, "category": "food", "spent_on": "2026-10-05"}' -w "\nHTTP %{http_code}\n"
echo
step "Validation errors: Date in the future" "curl -s -X POST http://127.0.0.1:8000/expenses -H \"Content-Type: application/json\" -d '{\"title\": \"Flight\", \"amount\": 300, \"category\": \"travel\", \"spent_on\": \"2030-01-01\"}' -w \"\\nHTTP %{http_code}\\n\""
curl -s -X POST http://127.0.0.1:8000/expenses -H "Content-Type: application/json" -d '{"title": "Flight", "amount": 300, "category": "travel", "spent_on": "2030-01-01"}' -w "\nHTTP %{http_code}\n"
echo
step "Validation errors: Missing required fields" "curl -s -X POST http://127.0.0.1:8000/expenses -H \"Content-Type: application/json\" -d '{\"title\": \"No amount\"}' -w \"\\nHTTP %{http_code}\\n\""
curl -s -X POST http://127.0.0.1:8000/expenses -H "Content-Type: application/json" -d '{"title": "No amount"}' -w "\nHTTP %{http_code}\n"
echo

# ---------------- List and filter ----------------
step "List and filter: Every expense" "curl -s \"http://127.0.0.1:8000/expenses\" | python3 -m json.tool"
curl -s "http://127.0.0.1:8000/expenses" | python3 -m json.tool
echo
step "List and filter: Every expense as a compact table" "curl -s \"http://127.0.0.1:8000/expenses\" | python3 -c 'import sys, json; rows = json.load(sys.stdin); [print(\"%4d  %s  %-13s %8.2f  %s\" % (e[\"id\"], e[\"spent_on\"], e[\"category\"], e[\"amount\"], e[\"title\"])) for e in rows]'"
curl -s "http://127.0.0.1:8000/expenses" | python3 -c 'import sys, json; rows = json.load(sys.stdin); [print("%4d  %s  %-13s %8.2f  %s" % (e["id"], e["spent_on"], e["category"], e["amount"], e["title"])) for e in rows]'
echo
step "List and filter: Only one category" "curl -s \"http://127.0.0.1:8000/expenses?category=food\" | python3 -c 'import sys, json; rows = json.load(sys.stdin); [print(\"%4d  %s  %-13s %8.2f  %s\" % (e[\"id\"], e[\"spent_on\"], e[\"category\"], e[\"amount\"], e[\"title\"])) for e in rows]'"
curl -s "http://127.0.0.1:8000/expenses?category=food" | python3 -c 'import sys, json; rows = json.load(sys.stdin); [print("%4d  %s  %-13s %8.2f  %s" % (e["id"], e["spent_on"], e["category"], e["amount"], e["title"])) for e in rows]'
echo
step "List and filter: First page of 3" "curl -s \"http://127.0.0.1:8000/expenses?limit=3&offset=0\" | python3 -c 'import sys, json; rows = json.load(sys.stdin); [print(\"%4d  %s  %-13s %8.2f  %s\" % (e[\"id\"], e[\"spent_on\"], e[\"category\"], e[\"amount\"], e[\"title\"])) for e in rows]'"
curl -s "http://127.0.0.1:8000/expenses?limit=3&offset=0" | python3 -c 'import sys, json; rows = json.load(sys.stdin); [print("%4d  %s  %-13s %8.2f  %s" % (e["id"], e["spent_on"], e["category"], e["amount"], e["title"])) for e in rows]'
echo
step "List and filter: Second page of 3" "curl -s \"http://127.0.0.1:8000/expenses?limit=3&offset=3\" | python3 -c 'import sys, json; rows = json.load(sys.stdin); [print(\"%4d  %s  %-13s %8.2f  %s\" % (e[\"id\"], e[\"spent_on\"], e[\"category\"], e[\"amount\"], e[\"title\"])) for e in rows]'"
curl -s "http://127.0.0.1:8000/expenses?limit=3&offset=3" | python3 -c 'import sys, json; rows = json.load(sys.stdin); [print("%4d  %s  %-13s %8.2f  %s" % (e["id"], e["spent_on"], e["category"], e["amount"], e["title"])) for e in rows]'
echo

# ---------------- View one expense ----------------
step "View one expense: View by id" "curl -s \"http://127.0.0.1:8000/expenses/\$ID\" | python3 -m json.tool"
curl -s "http://127.0.0.1:8000/expenses/$ID" | python3 -m json.tool
echo
step "View one expense: Id that does not exist" "curl -s -w \"\\nHTTP %{http_code}\\n\" http://127.0.0.1:8000/expenses/99999"
curl -s -w "\nHTTP %{http_code}\n" http://127.0.0.1:8000/expenses/99999
echo

# ---------------- Update an expense ----------------
step "Update an expense: Update every field" "curl -s -X PUT \"http://127.0.0.1:8000/expenses/\$ID\" -H \"Content-Type: application/json\" -d '{\"title\": \"Concert ticket (balcony)\", \"amount\": 65, \"category\": \"entertainment\", \"spent_on\": \"2026-10-08\", \"note\": \"Swapped seats\"}' | python3 -m json.tool"
curl -s -X PUT "http://127.0.0.1:8000/expenses/$ID" -H "Content-Type: application/json" -d '{"title": "Concert ticket (balcony)", "amount": 65, "category": "entertainment", "spent_on": "2026-10-08", "note": "Swapped seats"}' | python3 -m json.tool
echo
step "Update an expense: Leaving fields out is rejected" "curl -s -w \"\\nHTTP %{http_code}\\n\" -X PUT \"http://127.0.0.1:8000/expenses/\$ID\" -H \"Content-Type: application/json\" -d '{\"amount\": 70}'"
curl -s -w "\nHTTP %{http_code}\n" -X PUT "http://127.0.0.1:8000/expenses/$ID" -H "Content-Type: application/json" -d '{"amount": 70}'
echo

# ---------------- Delete an expense ----------------
step "Delete an expense: Delete by id" "curl -i -X DELETE \"http://127.0.0.1:8000/expenses/\$ID\""
curl -i -X DELETE "http://127.0.0.1:8000/expenses/$ID"
echo
step "Delete an expense: It is gone" "curl -s -w \"\\nHTTP %{http_code}\\n\" \"http://127.0.0.1:8000/expenses/\$ID\""
curl -s -w "\nHTTP %{http_code}\n" "http://127.0.0.1:8000/expenses/$ID"
echo

# ---------------- Summaries ----------------
step "Summaries: Totals per month" "curl -s \"http://127.0.0.1:8000/expenses/summary?by=month\" | python3 -m json.tool"
curl -s "http://127.0.0.1:8000/expenses/summary?by=month" | python3 -m json.tool
echo
step "Summaries: Totals per category, biggest first" "curl -s \"http://127.0.0.1:8000/expenses/summary?by=category\" | python3 -m json.tool"
curl -s "http://127.0.0.1:8000/expenses/summary?by=category" | python3 -m json.tool
echo
step "Summaries: Category spending as a text bar chart" "curl -s \"http://127.0.0.1:8000/expenses/summary?by=category\" | python3 -c 'import sys, json; d = json.load(sys.stdin); [print(\"%-14s %9.2f  %s\" % (r[\"group\"], r[\"total\"], \"#\" * round(r[\"total\"] / d[\"grand_total\"] * 40))) for r in d[\"rows\"]]'"
curl -s "http://127.0.0.1:8000/expenses/summary?by=category" | python3 -c 'import sys, json; d = json.load(sys.stdin); [print("%-14s %9.2f  %s" % (r["group"], r["total"], "#" * round(r["total"] / d["grand_total"] * 40))) for r in d["rows"]]'
echo

# ---------------- Headers, timing and CORS ----------------
step "Headers, timing and CORS: Status line and all response headers" "curl -i \"http://127.0.0.1:8000/expenses?limit=1\""
curl -i "http://127.0.0.1:8000/expenses?limit=1"
echo
step "Headers, timing and CORS: Choose your own request id" "curl -s -i -H \"X-Request-ID: demo1234\" \"http://127.0.0.1:8000/expenses?limit=1\" | grep -i \"x-request-id\""
curl -s -i -H "X-Request-ID: demo1234" "http://127.0.0.1:8000/expenses?limit=1" | grep -i "x-request-id"
echo
step "Headers, timing and CORS: Time a request" "curl -s -o /dev/null -w \"status %{http_code} in %{time_total}s\\n\" \"http://127.0.0.1:8000/expenses/summary?by=category\""
curl -s -o /dev/null -w "status %{http_code} in %{time_total}s\n" "http://127.0.0.1:8000/expenses/summary?by=category"
echo
step "Headers, timing and CORS: A browser call from the front-end is allowed" "curl -s -i -H \"Origin: http://127.0.0.1:5500\" \"http://127.0.0.1:8000/expenses?limit=1\" | grep -i \"access-control\""
curl -s -i -H "Origin: http://127.0.0.1:5500" "http://127.0.0.1:8000/expenses?limit=1" | grep -i "access-control"
echo
step "Headers, timing and CORS: A call from any other site is not" "curl -s -i -H \"Origin: http://evil.example\" \"http://127.0.0.1:8000/expenses?limit=1\" | grep -i \"access-control-allow-origin\" || echo \"No CORS headers, so a browser on that site would block the response\""
curl -s -i -H "Origin: http://evil.example" "http://127.0.0.1:8000/expenses?limit=1" | grep -i "access-control-allow-origin" || echo "No CORS headers, so a browser on that site would block the response"
echo
step "Headers, timing and CORS: The preflight a browser sends before a POST" "curl -s -i -X OPTIONS \"http://127.0.0.1:8000/expenses\" -H \"Origin: http://127.0.0.1:5500\" -H \"Access-Control-Request-Method: POST\" -H \"Access-Control-Request-Headers: content-type,x-request-id\""
curl -s -i -X OPTIONS "http://127.0.0.1:8000/expenses" -H "Origin: http://127.0.0.1:5500" -H "Access-Control-Request-Method: POST" -H "Access-Control-Request-Headers: content-type,x-request-id"
echo

# ---------------- Look inside the database ----------------
step "Look inside the database: Tables in the database" "python3 scripts/sql.py --tables"
python3 scripts/sql.py --tables
echo
step "Look inside the database: Latest rows exactly as stored" "python3 scripts/sql.py \"SELECT id, spent_on, title, category, amount_cents FROM expenses ORDER BY id DESC LIMIT 5\""
python3 scripts/sql.py "SELECT id, spent_on, title, category, amount_cents FROM expenses ORDER BY id DESC LIMIT 5"
echo
step "Look inside the database: The monthly summary query" "python3 scripts/sql.py \"SELECT strftime('%Y-%m', spent_on) AS month, COUNT(*) AS n, SUM(amount_cents) / 100.0 AS total FROM expenses GROUP BY month ORDER BY month\""
python3 scripts/sql.py "SELECT strftime('%Y-%m', spent_on) AS month, COUNT(*) AS n, SUM(amount_cents) / 100.0 AS total FROM expenses GROUP BY month ORDER BY month"
echo

printf "\n%sDone: 36 steps.%s Watch Terminal 1 to see each request the API received.\n" "$BOLD" "$RESET"
