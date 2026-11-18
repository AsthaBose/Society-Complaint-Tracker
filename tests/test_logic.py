"""Unit tests for logic that needs no web framework or database."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt as pyjwt

from app import config, security
from app.stats import compute_stats
from app.triage import keyword_triage


# ---------- passwords ----------
def test_password_roundtrip():
    h = security.hash_password("correct horse battery")
    assert security.verify_password("correct horse battery", h)
    assert not security.verify_password("wrong password", h)


def test_password_hashes_are_salted():
    assert security.hash_password("same-password") != security.hash_password("same-password")


def test_verify_rejects_garbage_hash():
    assert not security.verify_password("x", "not-a-valid-hash")
    assert not security.verify_password("x", "md5$1$aa$bb")


# ---------- tokens ----------
def test_token_roundtrip():
    token = security.create_access_token(42)
    assert security.decode_access_token(token)["sub"] == "42"


def test_token_rejects_tampering_and_wrong_key():
    assert security.decode_access_token("garbage") is None
    forged = pyjwt.encode({"sub": "1"}, "some-other-key-that-is-also-32-bytes-long!", algorithm="HS256")
    assert security.decode_access_token(forged) is None


def test_expired_token_rejected():
    expired = pyjwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        config.SECRET_KEY,
        algorithm="HS256",
    )
    assert security.decode_access_token(expired) is None


# ---------- triage ----------
def test_triage_categories():
    assert keyword_triage("Water leaking", "Pipe is leaking in the bathroom")[0] == "plumbing"
    assert keyword_triage("Lift not working", "The elevator stops between floors")[0] == "lift"
    assert keyword_triage("Loud music", "Party noise every night")[0] == "noise"
    assert keyword_triage("Hello", "Something unrelated to anything")[0] == "other"


def test_triage_urgency():
    assert keyword_triage("Short circuit", "Sparks from the switch board")[1] == "high"
    assert keyword_triage("Dustbin", "The dustbin near gate B is dirty")[1] == "medium"


def test_triage_prefix_match_handles_word_forms():
    assert keyword_triage("Leakage", "There is leakage near the tap")[0] == "plumbing"


# ---------- stats ----------
def _c(status, urgency="medium", category="other", hours=None):
    created = datetime(2026, 1, 1)
    return SimpleNamespace(
        status=status,
        urgency=urgency,
        category=category,
        created_at=created,
        resolved_at=created + timedelta(hours=hours) if hours is not None else None,
    )


def test_stats_counts_and_average():
    s = compute_stats(
        [
            _c("open", "high"),
            _c("in_progress", "high"),
            _c("resolved", "high", hours=10),
            _c("resolved", hours=20),
        ]
    )
    assert (s["total"], s["open"], s["in_progress"], s["resolved"]) == (4, 1, 1, 2)
    assert s["high_urgency_open"] == 2  # the resolved high one does not count
    assert s["avg_resolution_hours"] == 15.0


def test_stats_empty():
    s = compute_stats([])
    assert s["total"] == 0 and s["avg_resolution_hours"] is None and s["by_category"] == {}
