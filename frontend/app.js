// Expense Tracker front-end.
// Plain JavaScript, no build step. Every call to the API goes through api(),
// which also records the request and response in the network panel.

const $ = (sel) => document.querySelector(sel);
const PAGE_SIZE = 10;
const MAX_CALLS = 200;
const SUGGESTED = ["food", "transport", "rent", "utilities", "education", "entertainment", "health", "shopping"];

const state = {
  base: "http://127.0.0.1:8000",
  filters: { category: "", month: "" },
  offset: 0,
  summaryBy: "month",
  editingId: null,
  confirmDeleteId: null,
  expenses: [],
  calls: [],
  openCallId: null,
};

const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });
const fmtMoney = (n) => money.format(n);
const today = () => {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
};
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function store(key, value) {
  try {
    if (value === undefined) return localStorage.getItem(key);
    localStorage.setItem(key, value);
  } catch { return null; }
}

// ------------------------------------------------------------------ API client

class ApiError extends Error {
  constructor(status, body, message) {
    super(message || `HTTP ${status}`);
    this.status = status;
    this.body = body;
  }
}

function requestId() {
  const bytes = new Uint8Array(4);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

async function api(method, path, { query, body } = {}) {
  const url = new URL(path, state.base);
  for (const [k, v] of Object.entries(query || {})) {
    if (v !== "" && v !== null && v !== undefined) url.searchParams.set(k, v);
  }
  const id = requestId();
  const headers = { "X-Request-ID": id };
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const call = {
    id, method, url: url.toString(), path: url.pathname + url.search,
    reqHeaders: headers, reqBody: body, at: new Date(), status: null,
  };
  addCall(call);

  const started = performance.now();
  let res;
  try {
    res = await fetch(url, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  } catch (err) {
    call.ms = performance.now() - started;
    call.status = 0;
    call.error = "The request never got a response. The API is not running at this address, or it refused this page's origin (CORS).";
    updateCall(call);
    throw new ApiError(0, null, call.error);
  }
  call.ms = performance.now() - started;
  call.status = res.status;
  call.statusText = res.statusText;
  call.resHeaders = {};
  for (const name of ["content-type", "content-length", "x-request-id", "x-response-time-ms"]) {
    const v = res.headers.get(name);
    if (v !== null) call.resHeaders[name] = v;
  }
  const text = await res.text();
  let data = null;
  if (text) {
    try { data = JSON.parse(text); } catch { data = text; }
  }
  call.resBody = data;
  updateCall(call);
  if (!res.ok) throw new ApiError(res.status, data);
  return data;
}

// ------------------------------------------------------------------ network panel

function addCall(call) {
  state.calls.unshift(call);
  if (state.calls.length > MAX_CALLS) state.calls.pop();
  const li = document.createElement("li");
  li.className = "call fresh";
  li.dataset.id = call.id;
  $("#calls").prepend(li);
  while ($("#calls").children.length > MAX_CALLS) $("#calls").lastElementChild.remove();
  renderCall(li, call);
  setTimeout(() => li.classList.remove("fresh"), 1300);
  updateWireMeta();
}

function updateCall(call) {
  const li = $(`#calls li[data-id="${call.id}"]`);
  if (li) renderCall(li, call);
}

function statusClass(code) {
  if (code === null) return "pending";
  return "s" + String(code)[0];
}

function shellQuote(s) {
  return "'" + s.replace(/'/g, "'\\''") + "'";
}

function curlFor(call) {
  const parts = ["curl -s"];
  if (call.method !== "GET") parts.push(`-X ${call.method}`);
  parts.push(`"${call.url}"`);
  if (call.reqBody !== undefined) {
    parts.push('-H "Content-Type: application/json"');
    parts.push(`-d ${shellQuote(JSON.stringify(call.reqBody))}`);
  }
  return parts.join(" ");
}

function pretty(v) {
  if (v === null || v === undefined) return "(empty)";
  return typeof v === "string" ? v : JSON.stringify(v, null, 2);
}

function renderCall(li, call) {
  const open = state.openCallId === call.id;
  li.classList.toggle("open", open);
  const code = call.status === null ? "…" : call.status === 0 ? "failed" : call.status;
  const serverMs = call.resHeaders?.["x-response-time-ms"];
  const time = call.at.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });

  li.innerHTML = `
    <button type="button" aria-expanded="${open}">
      <span class="method m-${call.method}">${call.method}</span>
      <span class="path">${esc(call.path)}</span>
      <span class="code ${statusClass(call.status)}">${code}</span>
      <span class="meta">
        <span>[${call.id}]</span>
        <span>${time}</span>
        ${call.ms !== undefined ? `<span>round trip ${call.ms.toFixed(0)} ms</span>` : ""}
        ${serverMs ? `<span>server ${serverMs} ms</span>` : ""}
      </span>
    </button>
    ${open ? detailHtml(call) : ""}`;
  li.querySelector("button").addEventListener("click", () => {
    state.openCallId = open ? null : call.id;
    for (const c of state.calls) updateCall(c);
  });
  const copy = li.querySelector(".copy-curl");
  if (copy) copy.addEventListener("click", () => copyText(curlFor(call), copy));
}

function detailHtml(call) {
  const reqHead = Object.entries(call.reqHeaders).map(([k, v]) => `${k}: ${v}`).join("\n");
  const resHead = call.resHeaders ? Object.entries(call.resHeaders).map(([k, v]) => `${k}: ${v}`).join("\n") : "";
  const response = call.status === null ? "Waiting…"
    : call.status === 0 ? call.error
    : `HTTP ${call.status} ${call.statusText || ""}\n${resHead}\n\n${pretty(call.resBody)}`;
  // Every call sends X-Request-ID, a custom header, so browsers may preflight any of them.
  const preflight = `<p class="hint">Because this request sends a custom header (X-Request-ID), the browser may first send an OPTIONS "preflight" request asking the API for permission. Pages can't see preflights, but the API's terminal prints them.</p>`;
  return `
    <div class="detail">
      <div>
        <h3>Request</h3>
        <pre>${esc(`${call.method} ${call.url}\n${reqHead}${call.reqBody !== undefined ? "\n\n" + pretty(call.reqBody) : ""}`)}</pre>
      </div>
      <div>
        <h3>Response</h3>
        <pre>${esc(response)}</pre>
      </div>
      <div>
        <div class="curl-row"><h3>Same request from the terminal</h3><button type="button" class="btn btn-wire copy-curl">Copy</button></div>
        <pre>${esc(curlFor(call))}</pre>
      </div>
      ${preflight}
    </div>`;
}

function updateWireMeta() {
  const n = state.calls.length;
  $("#call-count").textContent = `${n} call${n === 1 ? "" : "s"}`;
  $("#wire-empty").hidden = n > 0;
}

async function copyText(text, button) {
  try {
    await navigator.clipboard.writeText(text);
    button.textContent = "Copied";
  } catch {
    button.textContent = "Select and copy";
    const pre = button.closest(".detail").querySelector(".curl-row + pre");
    const range = document.createRange();
    range.selectNodeContents(pre);
    getSelection().removeAllRanges();
    getSelection().addRange(range);
  }
  setTimeout(() => (button.textContent = "Copy"), 1500);
}

// ------------------------------------------------------------------ connection

async function connect() {
  const status = $("#api-status");
  status.dataset.state = "checking";
  status.textContent = "Checking…";
  hideNotice();
  try {
    await api("GET", "/");
    status.dataset.state = "up";
    status.textContent = "Connected";
    await refreshAll();
  } catch {
    status.dataset.state = "down";
    status.textContent = "Not reachable";
    showConnectionHelp();
  }
}

function showConnectionHelp() {
  const onFile = location.protocol === "file:";
  const n = $("#notice");
  n.innerHTML = `
    <h2>Can't reach the API at ${esc(state.base)}</h2>
    <ol>
      <li>Start it in Terminal 1, inside the project folder: <code>uvicorn app.main:app --reload</code></li>
      ${onFile
        ? `<li>This page is open as a file. Serve it instead, in Terminal 2: <code>python3 -m http.server 5500 --directory frontend</code>, then open <code>http://127.0.0.1:5500</code></li>`
        : `<li>Check that this page's address (<code>${esc(location.origin)}</code>) is allowed. The API accepts <code>http://127.0.0.1:5500</code> and <code>http://localhost:5500</code> by default.</li>`}
      <li>Then press Reconnect.</li>
    </ol>`;
  n.hidden = false;
}
function hideNotice() { $("#notice").hidden = true; }

// ------------------------------------------------------------------ data loading

async function refreshAll() {
  await Promise.all([loadExpenses(), loadSummary()]);
}

async function loadExpenses() {
  try {
    const rows = await api("GET", "/expenses", {
      query: { category: state.filters.category, month: state.filters.month, limit: PAGE_SIZE, offset: state.offset },
    });
    state.expenses = rows;
    renderRows();
    rememberCategories(rows.map((r) => r.category));
  } catch (err) {
    renderRowsError(err);
  }
}

async function loadSummary() {
  const query = { by: state.summaryBy };
  if (state.summaryBy === "category") query.month = state.filters.month;
  try {
    const data = await api("GET", "/expenses/summary", { query });
    renderSummary(data);
    if (state.summaryBy === "category") rememberCategories(data.rows.map((r) => r.group));
  } catch (err) {
    $("#bars").innerHTML = `<li class="bars-empty">${esc(errorText(err))}</li>`;
  }
}

const knownCategories = new Set(SUGGESTED);
function rememberCategories(list) {
  let changed = false;
  for (const c of list) if (c && !knownCategories.has(c)) { knownCategories.add(c); changed = true; }
  if (changed || !$("#category-options").children.length) {
    $("#category-options").innerHTML = [...knownCategories].sort().map((c) => `<option value="${esc(c)}">`).join("");
  }
}

function errorText(err) {
  if (!(err instanceof ApiError)) return String(err);
  const d = err.body?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((e) => `${e.loc?.at(-1)}: ${e.msg}`).join("; ");
  return err.message;
}

// ------------------------------------------------------------------ rendering

function renderRows() {
  const tbody = $("#rows");
  if (!state.expenses.length) {
    const filtered = state.filters.category || state.filters.month;
    tbody.innerHTML = `<tr class="empty-row"><td colspan="5">${
      state.offset > 0 ? "No more expenses." : filtered ? "Nothing matches these filters." : "No expenses yet. Add your first one above."
    }</td></tr>`;
  } else {
    tbody.innerHTML = state.expenses.map(rowHtml).join("");
  }
  const from = state.expenses.length ? state.offset + 1 : 0;
  $("#page-info").textContent = state.expenses.length ? `Showing ${from}–${state.offset + state.expenses.length}` : "";
  $("#prev-page").disabled = state.offset === 0;
  $("#next-page").disabled = state.expenses.length < PAGE_SIZE;
}

function rowHtml(e) {
  const actions = state.confirmDeleteId === e.id
    ? `<span class="confirm">Delete this?
         <button type="button" class="btn btn-danger" data-action="confirm-delete" data-id="${e.id}">Delete</button>
         <button type="button" class="btn btn-quiet" data-action="keep" data-id="${e.id}">Keep</button></span>`
    : `<button type="button" class="link-btn" data-action="edit" data-id="${e.id}">Edit</button>
       <button type="button" class="link-btn danger" data-action="delete" data-id="${e.id}">Delete</button>`;
  return `<tr class="${state.editingId === e.id ? "is-editing" : ""}">
    <td class="date">${esc(e.spent_on)}</td>
    <td>${esc(e.title)}${e.note ? `<span class="note">${esc(e.note)}</span>` : ""}</td>
    <td><span class="chip">${esc(e.category)}</span></td>
    <td class="num">${fmtMoney(e.amount)}</td>
    <td class="actions">${actions}</td>
  </tr>`;
}

function renderRowsError(err) {
  $("#rows").innerHTML = `<tr class="empty-row"><td colspan="5">Couldn't load expenses: ${esc(errorText(err))}</td></tr>`;
}

function monthLabel(ym) {
  const [y, m] = ym.split("-").map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString("en-US", { month: "short", year: "numeric" });
}

function renderSummary(data) {
  $("#grand-total").textContent = fmtMoney(data.grand_total);
  const scope = data.by === "category" && state.filters.month ? `in ${monthLabel(state.filters.month)}` : "in total";
  $("#grand-label").textContent = data.rows.length ? scope : "no spending recorded yet";
  const max = Math.max(...data.rows.map((r) => r.total), 0);
  const rows = data.by === "month" ? [...data.rows].reverse() : data.rows; // newest month first
  $("#bars").innerHTML = rows.length
    ? rows.map((r) => `
      <li>
        <span class="label" title="${esc(r.group)}">${esc(data.by === "month" ? monthLabel(r.group) : r.group)}</span>
        <span class="track"><span class="fill" style="width:${max ? (r.total / max) * 100 : 0}%"></span></span>
        <span class="val">${fmtMoney(r.total)}<small>${r.count} item${r.count === 1 ? "" : "s"}</small></span>
      </li>`).join("")
    : `<li class="bars-empty">Totals appear here once you add expenses.</li>`;
}

// ------------------------------------------------------------------ form

const form = $("#expense-form");

function readForm() {
  const v = (name) => form.elements[name].value;
  const amount = v("amount").trim();
  return {
    title: v("title"),
    amount: amount === "" ? null : Number(amount),
    category: v("category"),
    spent_on: v("spent_on") || null,
    note: v("note").trim() ? v("note") : null,
  };
}

function clearErrors() {
  form.querySelectorAll(".err").forEach((p) => (p.textContent = ""));
  form.querySelectorAll("[aria-invalid]").forEach((i) => i.removeAttribute("aria-invalid"));
}

function showErrors(err) {
  const detail = err.body?.detail;
  if (Array.isArray(detail)) {
    for (const e of detail) {
      const field = e.loc?.[0] === "body" ? e.loc[1] : null;
      const slot = field && form.querySelector(`.err[data-for="${field}"]`);
      if (slot) {
        slot.textContent = friendly(e);
        form.elements[field]?.setAttribute("aria-invalid", "true");
      } else {
        $("#form-error").textContent = e.msg;
      }
    }
  } else {
    // Business-rule errors come back as one sentence; point at the field it names.
    const text = errorText(err);
    const field = ["title", "amount", "category", "spent_on", "month"].find((f) => text.startsWith(f));
    const slot = field && form.querySelector(`.err[data-for="${field}"]`);
    (slot || $("#form-error")).textContent = text;
    if (slot) form.elements[field]?.setAttribute("aria-invalid", "true");
  }
}

// An empty box reaches the API as "" or null; say "Required" instead of the raw type error.
function friendly(e) {
  const blank = e.input === "" || e.input === null || e.type === "missing";
  return blank ? "Required" : e.msg;
}

function resetForm() {
  form.reset();
  form.elements.spent_on.value = today();
  state.editingId = null;
  $("#form-title").textContent = "Add an expense";
  $("#submit-btn").textContent = "Add expense";
  $("#cancel-edit").hidden = true;
  $(".add").classList.remove("editing");
  clearErrors();
}

function startEdit(id) {
  const e = state.expenses.find((x) => x.id === id);
  if (!e) return;
  state.editingId = id;
  state.confirmDeleteId = null;
  form.elements.title.value = e.title;
  form.elements.amount.value = e.amount;
  form.elements.category.value = e.category;
  form.elements.spent_on.value = e.spent_on;
  form.elements.note.value = e.note || "";
  $("#form-title").textContent = `Edit expense #${id}`;
  $("#submit-btn").textContent = "Save changes";
  $("#cancel-edit").hidden = false;
  $(".add").classList.add("editing");
  clearErrors();
  renderRows();
  form.elements.title.focus();
  $(".add").scrollIntoView({ block: "nearest", behavior: "smooth" });
}

form.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  clearErrors();
  const button = $("#submit-btn");
  button.disabled = true;
  const editing = state.editingId;
  try {
    if (editing) {
      await api("PUT", `/expenses/${editing}`, { body: readForm() });
    } else {
      await api("POST", "/expenses", { body: readForm() });
      state.offset = 0;
    }
    resetForm();
    await refreshAll();
    form.elements.title.focus();
  } catch (err) {
    if (err.status === 404) {
      $("#form-error").textContent = `Expense #${editing} no longer exists.`;
      resetForm();
      await refreshAll();
    } else if (err.status === 0) {
      $("#form-error").textContent = "Couldn't reach the API. Is the server still running?";
    } else {
      showErrors(err);
    }
  } finally {
    button.disabled = false;
  }
});

$("#cancel-edit").addEventListener("click", () => { resetForm(); renderRows(); });

// ------------------------------------------------------------------ list actions

$("#rows").addEventListener("click", async (ev) => {
  const btn = ev.target.closest("button[data-action]");
  if (!btn) return;
  const id = Number(btn.dataset.id);
  const action = btn.dataset.action;
  if (action === "edit") startEdit(id);
  if (action === "delete") { state.confirmDeleteId = id; renderRows(); }
  if (action === "keep") { state.confirmDeleteId = null; renderRows(); }
  if (action === "confirm-delete") {
    btn.disabled = true;
    try {
      await api("DELETE", `/expenses/${id}`);
    } catch (err) {
      if (err.status !== 404) alertRow(errorText(err));
    }
    state.confirmDeleteId = null;
    if (state.editingId === id) resetForm();
    if (state.expenses.length === 1 && state.offset > 0) state.offset -= PAGE_SIZE;
    await refreshAll();
  }
});

function alertRow(text) {
  $("#page-info").textContent = text;
}

let filterTimer;
function onFilterChange() {
  clearTimeout(filterTimer);
  filterTimer = setTimeout(async () => {
    state.filters.category = $("#filter-category").value.trim();
    state.filters.month = $("#filter-month").value;
    state.offset = 0;
    await refreshAll();
  }, 300);
}
$("#filter-category").addEventListener("input", onFilterChange);
$("#filter-month").addEventListener("change", onFilterChange);
$("#filters").addEventListener("submit", (ev) => ev.preventDefault());
$("#clear-filters").addEventListener("click", () => {
  $("#filter-category").value = "";
  $("#filter-month").value = "";
  onFilterChange();
});

$("#prev-page").addEventListener("click", () => { state.offset = Math.max(0, state.offset - PAGE_SIZE); loadExpenses(); });
$("#next-page").addEventListener("click", () => { state.offset += PAGE_SIZE; loadExpenses(); });

document.querySelectorAll(".seg button").forEach((b) =>
  b.addEventListener("click", () => {
    state.summaryBy = b.dataset.by;
    document.querySelectorAll(".seg button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    loadSummary();
  }));

$("#clear-wire").addEventListener("click", () => {
  state.calls = [];
  state.openCallId = null;
  $("#calls").innerHTML = "";
  updateWireMeta();
});

$("#connection-form").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const value = $("#api-base").value.trim().replace(/\/+$/, "");
  if (value) {
    state.base = value;
    store("expense-api-base", value);
  }
  connect();
});

// ------------------------------------------------------------------ start

state.base = store("expense-api-base") || state.base;
$("#api-base").value = state.base;
form.elements.spent_on.value = today();
form.elements.spent_on.max = today();
rememberCategories([]);
updateWireMeta();
connect();
