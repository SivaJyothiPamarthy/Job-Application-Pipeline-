"""Application tracker — a simple JSON-backed CRM.

Tracks each job through its lifecycle so the search is managed, not fire-and-forget.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

from . import config
from .models import Job

# Lifecycle states.
STATUSES = ["prepared", "approved", "submitted", "responded", "interview", "offer", "rejected", "withdrawn"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load() -> dict[str, Any]:
    path = config.STORE_PATH
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict[str, Any]) -> None:
    path = config.STORE_PATH
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def upsert(job: Job, status: str = "prepared", extra: Optional[dict[str, Any]] = None) -> None:
    data = _load()
    rec = data.get(job.id, {})
    rec.setdefault("history", [])
    rec.update(
        {
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "apply_url": job.apply_url or job.url,
            "apply_email": job.apply_email,
            "deadline": job.deadline,
            "status": status,
        }
    )
    if extra:
        rec.update(extra)
    if not rec["history"] or rec["history"][-1].get("status") != status:
        rec["history"].append({"status": status, "at": _now()})
    data[job.id] = rec
    _save(data)


def set_status(job_id: str, status: str) -> bool:
    if status not in STATUSES:
        raise ValueError(f"Unknown status '{status}'. Valid: {', '.join(STATUSES)}")
    data = _load()
    if job_id not in data:
        return False
    data[job_id]["status"] = status
    data[job_id].setdefault("history", []).append({"status": status, "at": _now()})
    _save(data)
    return True


def get(job_id: str) -> Optional[dict[str, Any]]:
    return _load().get(job_id)


def all_records() -> list[dict[str, Any]]:
    return sorted(_load().values(), key=lambda r: r.get("company", "").lower())
