"""Decide category and urgency for a complaint when the resident does not pick them.

This is a plain keyword matcher on purpose. It is the single place where an LLM call
can later be plugged in, and it stays as the fallback for when that call fails or times out.
"""
import re

CATEGORY_KEYWORDS = {
    "plumbing": ["leak", "pipe", "tap", "water", "drain", "sewage", "overflow", "seepage", "flush"],
    "electrical": ["electric", "power", "light", "wiring", "short circuit", "fuse", "switch", "spark", "generator"],
    "lift": ["lift", "elevator"],
    "security": ["security", "guard", "theft", "stolen", "gate", "cctv", "intruder", "stranger"],
    "cleaning": [
        "garbage", "trash", "dustbin", "clean", "sweep", "smell", "dirty",
        "pest", "mosquito", "cockroach", "stagnant", "fogging", "breeding",
    ],
    "parking": ["parking", "parked", "vehicle", "scooter", "motorcycle"],
    "noise": ["noise", "loud", "music", "party", "drilling", "construction"],
}

HIGH_URGENCY = [
    "fire", "spark", "short circuit", "gas leak", "flood", "burst", "trapped", "stuck",
    "emergency", "urgent", "sewage", "theft", "stolen", "intruder", "no water", "no power",
]


def _matches(word: str, text: str) -> bool:
    # \b at the start only, so "leak" also matches "leaking" and "leakage".
    return re.search(rf"\b{re.escape(word)}", text) is not None


def keyword_triage(title: str, description: str) -> tuple[str, str]:
    """Return (category, urgency). Category with the most keyword hits wins; ties go to the first listed."""
    text = f"{title} {description}".lower()

    best_category, best_hits = "other", 0
    for category, words in CATEGORY_KEYWORDS.items():
        hits = sum(1 for w in words if _matches(w, text))
        if hits > best_hits:
            best_category, best_hits = category, hits

    urgency = "high" if any(_matches(w, text) for w in HIGH_URGENCY) else "medium"
    return best_category, urgency
