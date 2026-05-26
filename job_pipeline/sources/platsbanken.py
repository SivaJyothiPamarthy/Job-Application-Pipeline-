"""Agent A's real data source: Platsbanken via the JobTech JobSearch API.

JobTech (Arbetsförmedlingen) exposes a free, public, no-auth search API over
Platsbanken — Sweden's national job board. This is the legal, robust alternative
to scraping LinkedIn/Indeed.

Docs: https://jobsearch.api.jobtechdev.se/  (Swagger at /  ; GET /search)
"""

from __future__ import annotations

from typing import Any, Optional

import requests

from ..models import Job
from ..profile import Profile
from .base import JobSource

BASE_URL = "https://jobsearch.api.jobtechdev.se"

# JobTech taxonomy concept IDs (stable identifiers).
STOCKHOLM_MUNICIPALITY = "AvNB_uwa_6n6"   # Stockholms kommun
STOCKHOLM_REGION = "CifL_Rzy_Mku"         # Stockholms län


class PlatsbankenSource(JobSource):
    name = "platsbanken"

    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    def fetch(self, profile: Profile, limit: int) -> list[Job]:
        q = " ".join(profile.search_terms()) or "developer"
        prefs = profile.preferences

        params: list[tuple[str, Any]] = [
            ("q", q),
            ("limit", min(limit, 100)),
            ("offset", 0),
            ("sort", "pubdate-desc"),
        ]

        # Default to Stockholm unless the profile asks for somewhere else.
        municipality = prefs.get("municipality_concept_id", STOCKHOLM_MUNICIPALITY)
        if municipality:
            params.append(("municipality", municipality))
        if prefs.get("remote"):
            params.append(("remote", "true"))

        headers = {
            "accept": "application/json",
            "User-Agent": "job-application-pipeline/0.1 (+https://github.com/)",
        }
        resp = requests.get(
            f"{BASE_URL}/search", params=params, headers=headers, timeout=self.timeout
        )
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
        return [self._to_job(h) for h in hits]

    @staticmethod
    def _to_job(h: dict[str, Any]) -> Job:
        addr = h.get("workplace_address") or {}
        location = ", ".join(
            x for x in (addr.get("municipality"), addr.get("region")) if x
        ) or (addr.get("country") or "Sweden")

        details = h.get("application_details") or {}
        salary = h.get("salary_description") or _salary_type(h.get("salary_type"))

        return Job(
            id=str(h.get("id")),
            title=(h.get("headline") or "Untitled role").strip(),
            company=((h.get("employer") or {}).get("name") or "Unknown").strip(),
            location=location,
            description=((h.get("description") or {}).get("text") or "").strip(),
            source="platsbanken",
            url=h.get("webpage_url"),
            apply_url=details.get("url"),
            apply_email=details.get("email"),
            salary=salary,
            employment_type=(h.get("employment_type") or {}).get("label")
            if isinstance(h.get("employment_type"), dict)
            else h.get("employment_type"),
            published=h.get("publication_date"),
            deadline=h.get("application_deadline"),
            remote=bool(h.get("remote_work")) if h.get("remote_work") is not None else None,
        )


def _salary_type(node: Optional[dict[str, Any]]) -> Optional[str]:
    if isinstance(node, dict):
        return node.get("label")
    return None
