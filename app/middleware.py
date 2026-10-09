"""Cross-cutting HTTP concerns: CORS and a request log.

CORS
    Browsers block a page on one origin (the front-end at http://127.0.0.1:5500)
    from reading responses from another (the API at http://127.0.0.1:8000)
    unless the API says that origin is allowed. curl and Postman are not
    browsers, so they never need this.

Request log
    Every request gets a short id. If the caller sends an X-Request-ID header
    (the front-end does) that id is reused, so the same id shows up in the
    browser's network panel and in this terminal. The id and the server-side
    processing time are sent back as response headers.
"""

import json
import logging
import os
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

log = logging.getLogger("uvicorn.error")  # prints alongside uvicorn's own lines

DEFAULT_ORIGINS = "http://127.0.0.1:5500,http://localhost:5500"
EXPOSED_HEADERS = ["X-Request-ID", "X-Response-Time-ms"]

# ANSI colours for the terminal (ignored by terminals that do not support them)
_C = {"GET": "\033[34m", "POST": "\033[32m", "PUT": "\033[33m",
      "DELETE": "\033[31m", "OPTIONS": "\033[90m"}
_DIM, _RESET = "\033[2m", "\033[0m"


def allowed_origins() -> list[str]:
    raw = os.getenv("EXPENSES_CORS_ORIGINS", DEFAULT_ORIGINS)
    return [o.strip() for o in raw.split(",") if o.strip()]


def _status_colour(code: int) -> str:
    return "\033[32m" if code < 300 else "\033[33m" if code < 500 else "\033[31m"


def install(app: FastAPI) -> None:
    """Attach CORS and request logging to the app."""

    # Our log line below replaces uvicorn's shorter access line, so hide that
    # one to keep exactly one line per request in the terminal.
    logging.getLogger("uvicorn.access").disabled = True

    # Added first, so it sits *inside* the logger below: preflight (OPTIONS)
    # requests that CORS answers on its own are still logged.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins(),
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "X-Request-ID"],
        expose_headers=EXPOSED_HEADERS,
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:8]
        started = time.perf_counter()

        body_note = ""
        if request.method in ("POST", "PUT"):
            raw = await request.body()  # cached by Starlette, the route still sees it
            try:
                body_note = " " + json.dumps(json.loads(raw), separators=(",", ":"))[:160]
            except ValueError:
                body_note = f" <{len(raw)} bytes>"

        response = await call_next(request)
        ms = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-ms"] = f"{ms:.1f}"

        origin = request.headers.get("origin")
        if request.method == "OPTIONS":
            source = f"CORS preflight from {origin}"
        else:
            source = f"from {origin}" if origin else "from terminal/no origin"
        path = request.url.path + (f"?{request.url.query}" if request.url.query else "")
        log.info(
            "%s[%s]%s %s%-6s%s %s%s %s%d%s %.1fms  %s%s%s",
            _DIM, request_id, _RESET,
            _C.get(request.method, ""), request.method, _RESET,
            path, body_note,
            _status_colour(response.status_code), response.status_code, _RESET,
            ms, _DIM, source, _RESET,
        )
        return response
