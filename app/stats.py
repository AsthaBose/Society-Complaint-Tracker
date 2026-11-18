"""Dashboard numbers. Pure function over complaint objects, so it can be tested without a database."""
from collections import Counter
from typing import Iterable


def compute_stats(complaints: Iterable) -> dict:
    complaints = list(complaints)
    by_status = Counter(c.status for c in complaints)

    resolution_hours = [
        (c.resolved_at - c.created_at).total_seconds() / 3600
        for c in complaints
        if c.status == "resolved" and c.resolved_at is not None
    ]
    avg = round(sum(resolution_hours) / len(resolution_hours), 1) if resolution_hours else None

    return {
        "total": len(complaints),
        "open": by_status.get("open", 0),
        "in_progress": by_status.get("in_progress", 0),
        "resolved": by_status.get("resolved", 0),
        "high_urgency_open": sum(
            1 for c in complaints if c.urgency == "high" and c.status != "resolved"
        ),
        "avg_resolution_hours": avg,
        "by_category": dict(Counter(c.category for c in complaints)),
    }
