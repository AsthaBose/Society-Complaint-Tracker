# Society Complaint Tracker

A full-stack web app for housing societies to replace WhatsApp-group complaint chaos.
Residents report problems; the committee triages them, updates status, and sees how long fixes take.

**Stack:** FastAPI · SQLAlchemy 2 · SQLite (dev) / PostgreSQL (prod) · JWT auth · vanilla JS frontend

## Run it

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                    # then edit SECRET_KEY and COMMITTEE_CODE
export $(grep -v '^#' .env | sed 's/ *#.*//' | xargs)   # or set the variables however you prefer
python -m scripts.seed                                  # optional demo data
uvicorn app.main:app --reload
```

Open http://localhost:8000 (app) or http://localhost:8000/docs (interactive API docs).

Demo logins after seeding (password `password123`): `committee@demo.com`, `resident@demo.com`, `meera@demo.com`.

Run tests: `pytest`

## Features

- Register / log in; two roles: **resident** and **committee**
- Residents submit complaints and see only their own
- Category and urgency are auto-detected when left on "Auto-detect" (keyword rules in `app/triage.py`)
- Committee sees all complaints, filters by status/category, updates status with a note
- Every status change is stored as an append-only history, shown as a timeline
- Dashboard: open / in progress / resolved counts, high-urgency open, average time to resolve

## API

| Method | Path | Who | Purpose |
|---|---|---|---|
| POST | `/api/auth/register` | anyone | Create account (committee code makes you committee) |
| POST | `/api/auth/login` | anyone | Get a JWT |
| GET | `/api/auth/me` | logged in | Current user |
| POST | `/api/complaints` | logged in | Create complaint |
| GET | `/api/complaints?status=&category=` | logged in | Resident: own; committee: all |
| GET | `/api/complaints/{id}` | owner / committee | Detail with history |
| PATCH | `/api/complaints/{id}/status` | committee | Change status, add note |
| GET | `/api/stats` | committee | Dashboard numbers |

## Design decisions (and why)

- **Role is read from the database on every request, not stored in the JWT.** Demoting a user takes effect immediately instead of when their token expires.
- **A resident requesting someone else's complaint gets 404, not 403,** so the API doesn't reveal which ids exist.
- **Passwords use PBKDF2-SHA256 (600k iterations) with a per-user salt**, with the iteration count stored in the hash so it can be raised later. Comparison is constant-time.
- **Login returns the same error for "unknown email" and "wrong password"** so emails can't be probed.
- **Status history is append-only** (`status_updates`), so you can always answer "who changed this, and when".
- **The frontend never puts user text into `innerHTML`**, only `textContent` or an escape function, to prevent stored XSS.
- **Triage is isolated in one function** (`keyword_triage`). It is the planned insertion point for an LLM call, with the keyword rules kept as the fallback if the call fails.
- **Committee signup uses a shared code.** Fine for a single society; a production version would use invitations or admin approval.

## Known limitations (be upfront about these)

- No photo upload, email/WhatsApp notifications, or password reset yet
- No rate limiting on login
- Tables are created with `create_all`; a real deployment should use Alembic migrations
- Keyword triage is simple and will miss unusual wording; residents and the committee can override it

## Deploy (Render / Railway)

1. Create a PostgreSQL database; copy its URL into `DATABASE_URL` (`postgres://` URLs are handled automatically).
2. Set `SECRET_KEY` (long random string) and `COMMITTEE_CODE`.
3. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## Project layout

```
app/
  main.py        app setup, serves the frontend
  config.py      environment settings
  database.py    engine and session
  models.py      User, Complaint, StatusUpdate
  schemas.py     request/response validation (Pydantic)
  security.py    password hashing, JWT
  deps.py        auth dependencies (current user, committee-only)
  triage.py      category/urgency detection
  stats.py       dashboard calculations
  routers/       auth.py, complaints.py
static/          index.html, style.css, app.js
tests/           test_logic.py (unit), test_api.py (end to end)
scripts/seed.py  demo data
```
