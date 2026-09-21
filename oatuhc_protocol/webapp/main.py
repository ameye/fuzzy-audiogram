"""
OAUTHC FAI validation — web data-entry app.

FastAPI + SQLite. Two-table relational design matching
oatuhc_protocol/data_dictionary.md v1.0:
  - patients      (one row per patient)
  - ear_records   (one row per ear; two rows share patient_id)

Endpoints:
  GET  /                        → data-entry UI
  GET  /api/health              → health check
  GET  /api/patients            → list patients
  POST /api/patients            → create patient
  GET  /api/patients/{id}       → patient + ear records
  POST /api/patients/{id}/ears  → add ear record
  PATCH /api/ears/{id}          → update ear record
  DELETE /api/ears/{id}         → delete ear record
  GET  /api/export.csv          → clean CSV for the FAI pipeline
  GET  /api/qa                  → batch QA flags
"""

from __future__ import annotations

import csv
import hashlib
import hmac
import io
import math
import os
import re
import secrets
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

app = FastAPI(title="OAUTHC FAI Validation — Data Entry", version="1.0.0")

STATIC_DIR = Path(__file__).parent / "static"
DB_PATH = Path(os.environ.get("FAI_DB_PATH", Path(__file__).parent / "data" / "oatuhc_fai.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

THRESH_FIELDS = ["th_250", "th_500", "th_1k", "th_2k", "th_3k", "th_4k", "th_6k", "th_8k"]
BC_FIELDS = ["bc_500", "bc_1k", "bc_2k", "bc_4k"]

# Physiologically plausible range for dB HL (data_dictionary.md v1.0, rule 5).
# Out-of-range thresholds are an exclusion criterion in the protocol, so they are
# rejected at entry rather than being cleaned up later.
THRESH_MIN = -10.0
THRESH_MAX = 120.0

# Frequencies required to compute the WHO PTA-4 reference standard.
PTA4_FIELDS = ("th_500", "th_1k", "th_2k", "th_4k")


def _validate_threshold(v):
    """Reject non-numeric, non-finite and out-of-range dB HL values."""
    if v is None:
        return v
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ValueError("threshold must be a number in dB HL")
    if not math.isfinite(v):
        raise ValueError("threshold must be a finite number")
    if not (THRESH_MIN <= v <= THRESH_MAX):
        raise ValueError(
            f"threshold must be between {THRESH_MIN:g} and {THRESH_MAX:g} dB HL, got {v:g}")
    return float(v)

DIAGNOSES = ["csoM", "otosclerosis", "nihl", "presbyacusis", "ssnhl",
             "ototoxicity", "meniere", "other", "not_documented"]
GRADES = ["normal", "mild", "moderate", "moderately_severe", "severe", "profound"]
SHAPES = ["flat", "sloping", "notched", "rising"]

# ── DB helpers ──────────────────────────────────────────────────────────────

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS patients (
        patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
        age_years INTEGER,
        sex INTEGER,
        created_by TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS ear_records (
        study_id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
        ear TEXT NOT NULL CHECK (ear IN ('left','right')),
        test_month_year TEXT,
        th_250 REAL, th_500 REAL, th_1k REAL, th_2k REAL,
        th_3k REAL, th_4k REAL, th_6k REAL, th_8k REAL,
        bc_500 REAL, bc_1k REAL, bc_2k REAL, bc_4k REAL,
        diagnosis_category TEXT,
        consultant_grade TEXT,
        documented_shape TEXT,
        ear_included INTEGER,
        exclusion_reason TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        UNIQUE (patient_id, ear)
    );
    """)
    conn.commit()
    conn.close()


init_db()

# ── Authentication ──────────────────────────────────────────────────────────
# Credentials come from the environment so no secret lives in the repo:
#   APP_USERNAME / APP_PASSWORD — the owner account
#   APP_USERS   — additional accounts, "user:pass,user:pass" (commas, semicolons
#                 or newlines all work as separators)
#   APP_SECRET  — HMAC key that signs session cookies (any long random string;
#                 changing it invalidates all existing sessions)
#
# FAILS CLOSED: with no accounts configured the app refuses to serve data rather
# than exposing clinical records. Sessions use a signed, HttpOnly cookie; no
# password is ever stored in the database or the repo.

def _load_users() -> dict[str, str]:
    """Collect the configured accounts from the environment."""
    users: dict[str, str] = {}
    single_user = os.environ.get("APP_USERNAME", "").strip()
    single_pass = os.environ.get("APP_PASSWORD", "")
    if single_user and single_pass:
        users[single_user] = single_pass

    for chunk in re.split(r"[,\n;]+", os.environ.get("APP_USERS", "")):
        chunk = chunk.strip()
        if not chunk or ":" not in chunk:
            continue
        name, _, pw = chunk.partition(":")
        name, pw = name.strip(), pw.strip()
        if name and pw:
            users[name] = pw
    return users


USERS = _load_users()
AUTH_SECRET = os.environ.get("APP_SECRET", "").strip() or "change-me-fai-secret"
AUTH_ENABLED = bool(USERS)

COOKIE_NAME = "fai_session"
SESSION_TTL = int(os.environ.get("APP_SESSION_HOURS", "12")) * 3600
PUBLIC_PATHS = {"/login", "/api/health", "/api/auth/login", "/favicon.ico"}

_LOGIN_ATTEMPTS: dict[str, list[float]] = {}
_LOGIN_MAX_ATTEMPTS = 10
_LOGIN_WINDOW = 300  # seconds


def _sign(payload: str) -> str:
    return hmac.new(AUTH_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()


# Server-side session registry. A cookie is only accepted while its token is
# still listed here, so logout genuinely revokes access instead of merely asking
# the browser to drop the cookie. Sessions are in-memory: a restart forces
# everyone to sign in again, which is the safe default for clinical data.
_SESSIONS: dict[str, dict] = {}   # token -> {"user": str, "exp": float}


def _prune_sessions() -> None:
    now = time.time()
    for tok in [t for t, s in _SESSIONS.items() if s["exp"] <= now]:
        _SESSIONS.pop(tok, None)


def make_session(user: str) -> str:
    """Register a session and return a signed '<token>:<hmac>' cookie value."""
    _prune_sessions()
    token = secrets.token_urlsafe(32)
    _SESSIONS[token] = {"user": user, "exp": time.time() + SESSION_TTL}
    return f"{token}:{_sign(token)}"


def session_user(raw: Optional[str]) -> Optional[str]:
    """Return the signed-in username for a valid session, else None."""
    if not raw or ":" not in raw:
        return None
    token, sig = raw.rsplit(":", 1)
    if not hmac.compare_digest(sig, _sign(token)):
        return None
    entry = _SESSIONS.get(token)
    if not entry or entry["exp"] <= time.time():
        _SESSIONS.pop(token, None)
        return None
    return entry["user"]


def verify_session(raw: Optional[str]) -> bool:
    return session_user(raw) is not None


def check_credentials(username: str, password: str) -> Optional[str]:
    """Return the canonical username on success, else None.

    Every account is compared without an early exit so the response time does
    not reveal whether the username or the password was the wrong half.
    """
    matched: Optional[str] = None
    for name, pw in USERS.items():
        name_ok = hmac.compare_digest(username, name)
        pass_ok = hmac.compare_digest(password, pw)
        if name_ok and pass_ok:
            matched = name
    return matched


def invalidate_session(raw: Optional[str]) -> None:
    """Revoke a session server-side."""
    if raw and ":" in raw:
        _SESSIONS.pop(raw.rsplit(":", 1)[0], None)


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if fwd:
        return fwd
    return request.client.host if request.client else "unknown"


def _rate_limited(ip: str) -> bool:
    now = time.time()
    hits = [t for t in _LOGIN_ATTEMPTS.get(ip, []) if now - t < _LOGIN_WINDOW]
    _LOGIN_ATTEMPTS[ip] = hits
    return len(hits) >= _LOGIN_MAX_ATTEMPTS


def _record_attempt(ip: str) -> None:
    _LOGIN_ATTEMPTS.setdefault(ip, []).append(time.time())


def _is_secure_request(request: Request) -> bool:
    fwd = request.headers.get("x-forwarded-proto", "").lower()
    return fwd == "https" or request.url.scheme == "https"


@app.middleware("http")
async def require_auth(request: Request, call_next):
    """Gate every route except the login form, health probe and static assets."""
    path = request.url.path
    if path in PUBLIC_PATHS or path.startswith("/assets/"):
        return await call_next(request)

    if not AUTH_ENABLED:
        return JSONResponse(
            {"error": "Authentication is not configured. Set the APP_USERNAME and "
                      "APP_PASSWORD environment variables and redeploy."},
            status_code=503,
        )

    if verify_session(request.cookies.get(COOKIE_NAME)):
        return await call_next(request)

    if path.startswith("/api/"):
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    nxt = path + (("?" + request.url.query) if request.url.query else "")
    return RedirectResponse("/login?next=" + quote(nxt, safe="/"), status_code=302)


class LoginIn(BaseModel):
    username: str
    password: str


@app.get("/login")
async def login_page():
    return HTMLResponse(LOGIN_PAGE)


@app.post("/api/auth/login")
async def login(request: Request, creds: LoginIn):
    if not AUTH_ENABLED:
        return JSONResponse(
            {"error": "Authentication is not configured on the server."}, status_code=503)

    ip = _client_ip(request)
    if _rate_limited(ip):
        return JSONResponse(
            {"error": "Too many attempts. Try again in a few minutes."}, status_code=429)

    user = check_credentials(creds.username.strip(), creds.password)
    if user is None:
        _record_attempt(ip)
        return JSONResponse({"error": "Invalid username or password"}, status_code=401)

    resp = JSONResponse({"ok": True, "user": user})
    resp.set_cookie(
        COOKIE_NAME, make_session(user),
        httponly=True, samesite="lax", max_age=SESSION_TTL,
        secure=_is_secure_request(request),
    )
    return resp


@app.post("/api/auth/logout")
async def logout(request: Request):
    invalidate_session(request.cookies.get(COOKIE_NAME))
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(COOKIE_NAME, path="/")
    return resp


@app.get("/api/auth/status")
async def auth_status(request: Request):
    raw = request.cookies.get(COOKIE_NAME)
    user = session_user(raw)
    return {
        "auth_enabled": AUTH_ENABLED,
        "logged_in": user is not None,
        "user": user,
    }


LOGIN_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sign in — OAUTHC FAI Validation</title>
<script src="https://cdn.tailwindcss.com/3.4.17"></script>
<style>body{background:#07070d;color:#fff;font-family:Inter,system-ui,sans-serif;margin:0}</style>
</head>
<body class="min-h-screen flex flex-col items-center justify-center p-6 gap-6">
  <form id="f" class="w-full max-w-sm rounded-2xl border border-white/10 bg-white/[0.03] p-7">
    <h1 class="text-lg font-bold mb-1">OAUTHC FAI <span class="text-violet-400">Validation</span></h1>
    <p class="text-xs text-white/40 mb-5">Sign in to continue</p>
    <label class="text-xs text-white/50">Username</label>
    <input id="u" autocomplete="username"
           class="w-full mb-3 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm outline-none focus:border-violet-500/50">
    <label class="text-xs text-white/50">Password</label>
    <input id="p" type="password" autocomplete="current-password"
           class="w-full mb-4 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm outline-none focus:border-violet-500/50">
    <button type="submit"
            class="w-full rounded-lg border border-violet-500/35 bg-violet-500/15 py-2 text-sm font-semibold text-violet-200">
      Sign in
    </button>
    <p id="e" class="mt-3 text-xs text-rose-300" style="display:none"></p>
  </form>
  <p class="text-xs text-white/30">Designed By <span class="text-white/55 font-medium">Dr. Sanyaolu A. Ameye</span></p>
  <script>
    document.getElementById('f').addEventListener('submit', async function (ev) {
      ev.preventDefault();
      var err = document.getElementById('e');
      err.style.display = 'none';
      try {
        var r = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            username: document.getElementById('u').value,
            password: document.getElementById('p').value
          })
        });
        if (r.ok) {
          var q = new URLSearchParams(location.search);
          location.href = q.get('next') || '/';
        } else {
          var d = await r.json().catch(function () { return {}; });
          err.textContent = d.error || ('Sign-in failed (HTTP ' + r.status + ')');
          err.style.display = 'block';
        }
      } catch (e2) {
        err.textContent = 'Network error: ' + e2.message;
        err.style.display = 'block';
      }
    });
  </script>
</body>
</html>"""

# ── Pydantic models ─────────────────────────────────────────────────────────

class PatientIn(BaseModel):
    age_years: Optional[int] = Field(None, ge=18, le=110)
    sex: Optional[int] = Field(None, ge=1, le=2)
    created_by: Optional[str] = None


class EarRecordIn(BaseModel):
    ear: str
    test_month_year: Optional[str] = None
    th_250: Optional[float] = None
    th_500: Optional[float] = None
    th_1k: Optional[float] = None
    th_2k: Optional[float] = None
    th_3k: Optional[float] = None
    th_4k: Optional[float] = None
    th_6k: Optional[float] = None
    th_8k: Optional[float] = None
    bc_500: Optional[float] = None
    bc_1k: Optional[float] = None
    bc_2k: Optional[float] = None
    bc_4k: Optional[float] = None
    diagnosis_category: Optional[str] = None
    consultant_grade: Optional[str] = None
    documented_shape: Optional[str] = None
    ear_included: Optional[int] = Field(None, ge=0, le=1)
    exclusion_reason: Optional[str] = None

    @field_validator(*THRESH_FIELDS, *BC_FIELDS)
    @classmethod
    def threshold_in_range(cls, v):
        """Every air- and bone-conduction threshold must be a finite value in
        −10..120 dB HL (data_dictionary.md v1.0, rule 5)."""
        return _validate_threshold(v)

    @field_validator("ear")
    @classmethod
    def ear_valid(cls, v):
        if v not in ("left", "right"):
            raise ValueError("ear must be 'left' or 'right'")
        return v

    @field_validator("diagnosis_category")
    @classmethod
    def diag_valid(cls, v):
        if v is not None and v not in DIAGNOSES:
            raise ValueError(f"diagnosis_category must be one of {DIAGNOSES}")
        return v

    @field_validator("consultant_grade")
    @classmethod
    def grade_valid(cls, v):
        if v is not None and v not in GRADES:
            raise ValueError(f"consultant_grade must be one of {GRADES}")
        return v

    @field_validator("documented_shape")
    @classmethod
    def shape_valid(cls, v):
        if v is not None and v not in SHAPES:
            raise ValueError(f"documented_shape must be one of {SHAPES}")
        return v


# ── Derived helpers ─────────────────────────────────────────────────────────

def pta4(row: sqlite3.Row) -> Optional[float]:
    vals = [row[k] for k in ("th_500", "th_1k", "th_2k", "th_4k")]
    if all(v is not None for v in vals):
        return round(sum(vals) / 4, 1)
    return None


def who_grade(pta: Optional[float]) -> Optional[str]:
    if pta is None:
        return None
    if pta < 26:
        return "normal"
    if pta < 41:
        return "mild"
    if pta < 61:
        return "moderate"
    if pta < 81:
        return "severe"
    return "profound"


def borderline(pta: Optional[float]) -> Optional[int]:
    if pta is None:
        return None
    return 1 if any(abs(pta - b) <= 5 for b in (25, 40, 60, 80)) else 0


def monotonicity_flag(row: sqlite3.Row) -> int:
    seq = [row[k] for k in THRESH_FIELDS]
    pairs = [(a, b) for a, b in zip(seq[:-1], seq[1:]) if a is not None and b is not None]
    if not pairs:
        return 0
    return 1 if max(abs(a - b) for a, b in pairs) > 40 else 0


def ear_to_dict(r: sqlite3.Row) -> dict:
    d = dict(r)
    d["pta4"] = pta4(r)
    d["who_grade"] = who_grade(d["pta4"])
    d["borderline"] = borderline(d["pta4"])
    d["monotonicity_flag"] = monotonicity_flag(r)
    return d


# ── Routes ──────────────────────────────────────────────────────────────────

if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR)), name="assets")


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/patients")
async def patients_page():
    """Captured-record list and batch QA, on their own page.

    Separate from the entry form so the data-entry screen stays focused. Both
    pages are behind the same auth middleware and share /assets/app.css.
    """
    return FileResponse(STATIC_DIR / "patients.html")


@app.get("/api/health")
async def health():
    return {"status": "ok", "db": str(DB_PATH)}


@app.get("/api/patients")
async def list_patients():
    conn = get_db()
    rows = conn.execute("""
        SELECT p.*, COUNT(e.study_id) AS ear_count,
               SUM(CASE WHEN e.ear_included = 1 THEN 1 ELSE 0 END) AS included_ears
        FROM patients p LEFT JOIN ear_records e ON p.patient_id = e.patient_id
        GROUP BY p.patient_id ORDER BY p.patient_id DESC LIMIT 200
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/patients", status_code=201)
async def create_patient(p: PatientIn):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO patients (age_years, sex, created_by) VALUES (?,?,?)",
        (p.age_years, p.sex, p.created_by))
    conn.commit()
    pid = cur.lastrowid
    conn.close()
    return {"patient_id": pid, "age_years": p.age_years, "sex": p.sex}


@app.patch("/api/patients/{pid}")
async def update_patient(pid: int, p: PatientIn):
    conn = get_db()
    existing = conn.execute("SELECT patient_id FROM patients WHERE patient_id=?", (pid,)).fetchone()
    if existing is None:
        conn.close()
        raise HTTPException(404, "Patient not found")
    conn.execute("UPDATE patients SET age_years=?, sex=?, created_by=? WHERE patient_id=?",
                 (p.age_years, p.sex, p.created_by, pid))
    conn.commit()
    row = conn.execute("SELECT * FROM patients WHERE patient_id=?", (pid,)).fetchone()
    conn.close()
    return dict(row)


# ── Single-form entry: demographics + both ears in ONE submission ───────────

class PatientFullIn(BaseModel):
    """One patient with both ears, exactly as the single-page form submits it."""
    age_years: Optional[int] = Field(None, ge=18, le=110)
    sex: Optional[int] = Field(None, ge=1, le=2)
    created_by: Optional[str] = None
    ears: list[EarRecordIn] = []


EAR_PAYLOAD_COLS = [
    "test_month_year", *THRESH_FIELDS, *BC_FIELDS,
    "diagnosis_category", "consultant_grade", "documented_shape",
    "ear_included", "exclusion_reason",
]


def _write_ear(conn: sqlite3.Connection, pid: int, e: EarRecordIn) -> int:
    """Insert or update the record for this (patient_id, ear). Returns study_id."""
    row = conn.execute(
        "SELECT study_id FROM ear_records WHERE patient_id=? AND ear=?",
        (pid, e.ear)).fetchone()
    vals = [getattr(e, c) for c in EAR_PAYLOAD_COLS]
    if row is None:
        cur = conn.execute(
            f"INSERT INTO ear_records (patient_id, ear, {','.join(EAR_PAYLOAD_COLS)}) "
            f"VALUES (?,?,{','.join('?' * len(EAR_PAYLOAD_COLS))})",
            [pid, e.ear, *vals])
        return cur.lastrowid
    conn.execute(
        f"UPDATE ear_records SET {','.join(c + '=?' for c in EAR_PAYLOAD_COLS)} "
        f"WHERE study_id=?", [*vals, row["study_id"]])
    return row["study_id"]


@app.post("/api/patients/full", status_code=201)
async def create_patient_full(p: PatientFullIn):
    """Create a patient and both ear records from the single-page form."""
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO patients (age_years, sex, created_by) VALUES (?,?,?)",
        (p.age_years, p.sex, p.created_by))
    pid = cur.lastrowid
    ids = [_write_ear(conn, pid, e) for e in p.ears]
    conn.commit()
    conn.close()
    return {"patient_id": pid, "study_ids": ids, "ears": len(ids)}


@app.put("/api/patients/{pid}/full")
async def update_patient_full(pid: int, p: PatientFullIn):
    """Update demographics and upsert both ear records for an existing patient."""
    conn = get_db()
    if conn.execute("SELECT patient_id FROM patients WHERE patient_id=?",
                    (pid,)).fetchone() is None:
        conn.close()
        raise HTTPException(404, "Patient not found")
    conn.execute(
        "UPDATE patients SET age_years=?, sex=?, created_by=? WHERE patient_id=?",
        (p.age_years, p.sex, p.created_by, pid))
    ids = [_write_ear(conn, pid, e) for e in p.ears]
    conn.commit()
    conn.close()
    return {"patient_id": pid, "study_ids": ids, "ears": len(ids)}


@app.get("/api/patients/{pid}")
async def get_patient(pid: int):
    conn = get_db()
    p = conn.execute("SELECT * FROM patients WHERE patient_id=?", (pid,)).fetchone()
    if p is None:
        conn.close()
        raise HTTPException(404, "Patient not found")
    ears = conn.execute(
        "SELECT * FROM ear_records WHERE patient_id=? ORDER BY ear", (pid,)).fetchall()
    conn.close()
    return {"patient": dict(p), "ears": [ear_to_dict(e) for e in ears]}


@app.post("/api/patients/{pid}/ears", status_code=201)
async def add_ear(pid: int, e: EarRecordIn):
    conn = get_db()
    p = conn.execute("SELECT patient_id FROM patients WHERE patient_id=?", (pid,)).fetchone()
    if p is None:
        conn.close()
        raise HTTPException(404, "Patient not found")
    dup = conn.execute(
        "SELECT study_id FROM ear_records WHERE patient_id=? AND ear=?",
        (pid, e.ear)).fetchone()
    if dup:
        conn.close()
        raise HTTPException(409, f"{e.ear} ear already recorded for this patient")
    vals = {f: getattr(e, f) for f in THRESH_FIELDS + BC_FIELDS}
    cur = conn.execute("""
        INSERT INTO ear_records
        (patient_id, ear, test_month_year,
         th_250, th_500, th_1k, th_2k, th_3k, th_4k, th_6k, th_8k,
         bc_500, bc_1k, bc_2k, bc_4k,
         diagnosis_category, consultant_grade, documented_shape,
         ear_included, exclusion_reason)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (pid, e.ear, e.test_month_year,
          vals["th_250"], vals["th_500"], vals["th_1k"], vals["th_2k"],
          vals["th_3k"], vals["th_4k"], vals["th_6k"], vals["th_8k"],
          vals["bc_500"], vals["bc_1k"], vals["bc_2k"], vals["bc_4k"],
          e.diagnosis_category, e.consultant_grade, e.documented_shape,
          e.ear_included, e.exclusion_reason))
    conn.commit()
    sid = cur.lastrowid
    conn.close()
    return {"study_id": sid, "ear": e.ear}


@app.patch("/api/ears/{sid}")
async def update_ear(sid: int, e: EarRecordIn):
    conn = get_db()
    existing = conn.execute("SELECT * FROM ear_records WHERE study_id=?", (sid,)).fetchone()
    if existing is None:
        conn.close()
        raise HTTPException(404, "Ear record not found")
    sets, vals = [], []
    for f in ["ear", "test_month_year", *THRESH_FIELDS, *BC_FIELDS,
              "diagnosis_category", "consultant_grade", "documented_shape",
              "ear_included", "exclusion_reason"]:
        v = getattr(e, f)
        if v is not None:
            sets.append(f"{f}=?")
            vals.append(v)
    if sets:
        vals.append(sid)
        conn.execute(f"UPDATE ear_records SET {','.join(sets)} WHERE study_id=?", vals)
        conn.commit()
    row = conn.execute("SELECT * FROM ear_records WHERE study_id=?", (sid,)).fetchone()
    conn.close()
    return ear_to_dict(row)


@app.delete("/api/ears/{sid}")
async def delete_ear(sid: int):
    conn = get_db()
    conn.execute("DELETE FROM ear_records WHERE study_id=?", (sid,))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.get("/api/export.csv")
async def export_csv():
    """Clean CSV for the FAI pipeline — matches data_dictionary column order."""
    conn = get_db()
    rows = conn.execute("""
        SELECT e.study_id, e.patient_id, e.ear, e.test_month_year,
               p.age_years, p.sex,
               e.th_250, e.th_500, e.th_1k, e.th_2k, e.th_3k, e.th_4k, e.th_6k, e.th_8k,
               e.bc_500, e.bc_1k, e.bc_2k, e.bc_4k,
               e.diagnosis_category, e.consultant_grade, e.documented_shape,
               e.ear_included, e.exclusion_reason
        FROM ear_records e JOIN patients p ON e.patient_id = p.patient_id
        WHERE e.ear_included = 1
        ORDER BY e.study_id
    """).fetchall()
    conn.close()

    buf = io.StringIO()
    if rows:
        writer = csv.writer(buf)
        writer.writerow(rows[0].keys())
        for r in rows:
            writer.writerow([r[k] for k in r.keys()])
    else:
        # Header-only export with the expected columns
        cols = ["study_id", "patient_id", "ear", "test_month_year", "age_years",
                "sex", *THRESH_FIELDS, *BC_FIELDS, "diagnosis_category",
                "consultant_grade", "documented_shape", "ear_included",
                "exclusion_reason"]
        writer = csv.writer(buf)
        writer.writerow(cols)

    fname = f"oatuhc_fai_export_{datetime.now():%Y%m%d_%H%M}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@app.get("/api/qa")
async def qa_report():
    """Batch QA flags.

    Protocol rule 7 is explicit: anomalies are flagged for review and never
    auto-corrected. So these are reports, not edits.
    """
    conn = get_db()
    ears = conn.execute("SELECT * FROM ear_records").fetchall()
    conn.close()
    issues = []
    seen = {}
    for e in ears:
        sid = e["study_id"]
        key = (e["patient_id"], e["ear"])
        if key in seen:
            issues.append({"study_id": sid, "issue": "duplicate (patient_id, ear)"})
        seen[key] = True

        if monotonicity_flag(e):
            issues.append({"study_id": sid, "issue": "monotonicity: adjacent jump > 40 dB"})

        # Transcription check: audiometry is conventionally recorded in 5 dB steps.
        off_step = [f for f in THRESH_FIELDS + BC_FIELDS
                    if e[f] is not None and abs(e[f] / 5 - round(e[f] / 5)) > 1e-9]
        if off_step:
            issues.append({"study_id": sid,
                           "issue": "not a 5 dB step: " + ", ".join(off_step)})

        # NOTE (21 Sep 2026): the "impossible air-bone gap" check was REMOVED at the
        # PI's request. Real audiograms produce negative air-bone gaps of 5-10 dB
        # routinely (+/-5 dB test-retest reliability per ANSI S3.21/BSA, bone-vibrator
        # calibration, unmasked BC picking up the contralateral ear, vibrotactile
        # responses, and AC recorded at the audiometer's output ceiling), so the check
        # was flagging valid observations. Air-bone gaps are instead reviewed during
        # the pre-analysis cleaning pass, not at entry.

        # An ear marked eligible must carry the four PTA-4 frequencies, otherwise
        # the WHO reference standard cannot be computed for it.
        if e["ear_included"] == 1:
            missing = [f for f in PTA4_FIELDS if e[f] is None]
            if missing:
                issues.append({
                    "study_id": sid,
                    "issue": "marked included but missing PTA-4 frequency: "
                             + ", ".join(missing)})

    return {"total_ear_records": len(ears), "issues": issues}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
