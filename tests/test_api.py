"""End-to-end API tests. Needs fastapi and httpx installed (see requirements.txt)."""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # the `with` runs the lifespan, which creates the tables
        yield c


def _register(client, email, committee=False, flat="A-101"):
    body = {"name": "Test User", "email": email, "flat_no": flat, "password": "password123"}
    if committee:
        body["committee_code"] = "test-code"
    r = client.post("/api/auth/register", json=body)
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}, r.json()["user"]


@pytest.fixture(scope="module")
def resident(client):
    return _register(client, "resident@example.com")


@pytest.fixture(scope="module")
def other_resident(client):
    return _register(client, "other@example.com", flat="B-202")


@pytest.fixture(scope="module")
def committee(client):
    return _register(client, "committee@example.com", committee=True, flat="Office")


# ---------- auth ----------
def test_register_roles(resident, committee):
    assert resident[1]["role"] == "resident"
    assert committee[1]["role"] == "committee"


def test_bad_committee_code_rejected(client):
    r = client.post(
        "/api/auth/register",
        json={"name": "Sneaky", "email": "s@example.com", "flat_no": "1", "password": "password123",
              "committee_code": "guess"},
    )
    assert r.status_code == 403


def test_duplicate_email_rejected(client, resident):
    r = client.post(
        "/api/auth/register",
        json={"name": "Dup", "email": "RESIDENT@example.com", "flat_no": "1", "password": "password123"},
    )
    assert r.status_code == 409  # emails are case-insensitive


def test_login(client, resident):
    ok = client.post("/api/auth/login", json={"email": "resident@example.com", "password": "password123"})
    assert ok.status_code == 200 and ok.json()["user"]["role"] == "resident"
    bad = client.post("/api/auth/login", json={"email": "resident@example.com", "password": "nope"})
    assert bad.status_code == 401


def test_requires_token(client):
    assert client.get("/api/complaints").status_code == 401
    assert client.get("/api/complaints", headers={"Authorization": "Bearer junk"}).status_code == 401


# ---------- complaints ----------
def test_create_autofills_category_and_urgency(client, resident):
    r = client.post(
        "/api/complaints",
        headers=resident[0],
        json={"title": "Pipe burst", "description": "A pipe burst in the kitchen and water is everywhere"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["category"] == "plumbing" and body["urgency"] == "high" and body["status"] == "open"


def test_manual_category_is_respected(client, resident):
    r = client.post(
        "/api/complaints",
        headers=resident[0],
        json={"title": "Something odd", "description": "Please look into this matter soon",
              "category": "security", "urgency": "low"},
    )
    assert r.json()["category"] == "security" and r.json()["urgency"] == "low"


def test_validation_errors(client, resident):
    r = client.post("/api/complaints", headers=resident[0], json={"title": "x", "description": "short"})
    assert r.status_code == 422


def test_residents_only_see_their_own(client, resident, other_resident, committee):
    created = client.post(
        "/api/complaints",
        headers=resident[0],
        json={"title": "Private matter", "description": "Only the author and committee may read this"},
    ).json()

    mine = client.get("/api/complaints", headers=resident[0]).json()
    assert created["id"] in [c["id"] for c in mine]

    theirs = client.get("/api/complaints", headers=other_resident[0]).json()
    assert created["id"] not in [c["id"] for c in theirs]
    assert client.get(f"/api/complaints/{created['id']}", headers=other_resident[0]).status_code == 404

    everyone = client.get("/api/complaints", headers=committee[0]).json()
    assert created["id"] in [c["id"] for c in everyone]


def test_filters(client, committee):
    only_plumbing = client.get("/api/complaints?category=plumbing", headers=committee[0]).json()
    assert only_plumbing and all(c["category"] == "plumbing" for c in only_plumbing)
    assert client.get("/api/complaints?status=bogus", headers=committee[0]).status_code == 422


# ---------- status updates ----------
def test_resident_cannot_change_status(client, resident):
    cid = client.get("/api/complaints", headers=resident[0]).json()[0]["id"]
    r = client.patch(f"/api/complaints/{cid}/status", headers=resident[0], json={"status": "resolved"})
    assert r.status_code == 403


def test_status_lifecycle_and_stats(client, resident, committee):
    cid = client.post(
        "/api/complaints",
        headers=resident[0],
        json={"title": "Lift stuck", "description": "The lift is stuck on the third floor again"},
    ).json()["id"]

    r = client.patch(f"/api/complaints/{cid}/status", headers=committee[0],
                     json={"status": "in_progress", "note": "Technician called"})
    assert r.status_code == 200 and r.json()["status"] == "in_progress"

    r = client.patch(f"/api/complaints/{cid}/status", headers=committee[0],
                     json={"status": "resolved", "note": "Fixed"})
    body = r.json()
    assert body["resolved_at"] is not None
    assert [u["status"] for u in body["updates"]] == ["open", "in_progress", "resolved"]

    stats = client.get("/api/stats", headers=committee[0]).json()
    assert stats["resolved"] >= 1 and stats["avg_resolution_hours"] is not None

    # reopening clears resolved_at
    r = client.patch(f"/api/complaints/{cid}/status", headers=committee[0],
                     json={"status": "open", "note": "Broke again"})
    assert r.json()["resolved_at"] is None


def test_noop_update_rejected(client, committee, resident):
    cid = client.get("/api/complaints", headers=resident[0]).json()[0]["id"]
    current = client.get(f"/api/complaints/{cid}", headers=committee[0]).json()["status"]
    r = client.patch(f"/api/complaints/{cid}/status", headers=committee[0], json={"status": current})
    assert r.status_code == 400


def test_stats_committee_only(client, resident):
    assert client.get("/api/stats", headers=resident[0]).status_code == 403


def test_frontend_served(client):
    assert "Society Complaint Tracker" in client.get("/").text
    assert client.get("/static/app.js").status_code == 200
