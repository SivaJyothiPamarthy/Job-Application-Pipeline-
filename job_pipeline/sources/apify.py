"""Apify-backed job source — for LinkedIn and other boards.

Apify (https://apify.com) runs marketplace "Actors" (e.g. LinkedIn Jobs scrapers)
on their infrastructure and exposes results via a REST API. This is the legal,
robust way to pull LinkedIn listings without DIY scraping or login automation.

Requires APIFY_API_TOKEN. The Actor and its input schema vary, so both are
configurable; field mapping is intentionally tolerant of naming differences
across Actors.

Config (env or profile.preferences):
  APIFY_API_TOKEN   (env, required)
  APIFY_ACTOR / preferences.apify_actor   default: bebity~linkedin-jobs-scraper
  preferences.apify_input                 dict merged into the Actor input
"""

from __future__ import annotations

import hashlib
import os
import re
from typing import Any, Optional

import requests

from ..models import Job
from ..profile import Profile
from .base import JobSource

# A widely used LinkedIn Jobs Actor. Actor IDs use '~' (not '/') in the API path.
DEFAULT_ACTOR = "bebity~linkedin-jobs-scraper"
API_BASE = "https://api.apify.com/v2"


class ApifySource(JobSource):
    name = "apify"

    def __init__(self, timeout: int = 300):
        self.token = os.environ.get("APIFY_API_TOKEN")
        self.timeout = timeout

    def fetch(self, profile: Profile, limit: int) -> list[Job]:
        if not self.token:
            raise RuntimeError(
                "APIFY_API_TOKEN is not set. Get a token at https://console.apify.com/account/integrations"
            )
        prefs = profile.preferences
        actor = prefs.get("apify_actor") or os.environ.get("APIFY_ACTOR") or DEFAULT_ACTOR

        title = " ".join(profile.search_terms()) or "software engineer"
        location = (prefs.get("locations") or ["Stockholm"])[0]

        # Default input matches common LinkedIn-jobs Actors; override per-Actor
        # via preferences.apify_input if your chosen Actor uses different keys.
        actor_input: dict[str, Any] = {
            "title": title,
            "location": location,
            "rows": limit,
        }
        actor_input.update(prefs.get("apify_input") or {})

        # Run the Actor and get its dataset items in one call.
        url = f"{API_BASE}/acts/{actor}/run-sync-get-dataset-items"
        resp = requests.post(
            url, params={"token": self.token}, json=actor_input, timeout=self.timeout
        )
        resp.raise_for_status()
        items = resp.json()
        if not isinstance(items, list):
            return []
        return [self._to_job(it, actor) for it in items[:limit]]

    @staticmethod
    def _to_job(it: dict[str, Any], actor: str) -> Job:
        title = _first(it, ["title", "jobTitle", "positionName", "position"]) or "Untitled role"
        company = _first(it, ["companyName", "company", "company_name", "employer"]) or "Unknown"
        location = _first(it, ["location", "place", "jobLocation", "formattedLocation"]) or "Sweden"
        url = _first(it, ["jobUrl", "link", "url", "jobPostingUrl"])
        apply_url = _first(it, ["applyUrl", "applyLink", "applicationUrl"]) or url

        description = _first(it, ["descriptionText", "description", "jobDescription", "text"])
        if not description:
            html = _first(it, ["descriptionHtml", "descriptionHTML"])
            description = _strip_html(html) if html else ""

        job_id = _first(it, ["id", "jobId", "trackingId"]) or _derive_id(url, title, company)

        return Job(
            id=str(job_id),
            title=str(title).strip(),
            company=str(company).strip(),
            location=str(location).strip(),
            description=(description or "").strip(),
            source=f"apify:{actor}",
            url=url,
            apply_url=apply_url,
            apply_email=_first(it, ["applyEmail", "contactEmail"]),
            salary=_first(it, ["salary", "salaryInfo", "compensation"]),
            employment_type=_first(it, ["employmentType", "contractType", "jobType"]),
            published=_first(it, ["postedTime", "postedAt", "publishedAt", "datePosted", "date"]),
            deadline=_first(it, ["applicationDeadline", "deadline"]),
        )


def _first(d: dict[str, Any], keys: list[str]) -> Optional[str]:
    for k in keys:
        v = d.get(k)
        if v not in (None, "", [], {}):
            return v
    return None


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


def _derive_id(url: Optional[str], title: str, company: str) -> str:
    basis = url or f"{title}|{company}"
    return "apify-" + hashlib.sha1(basis.encode("utf-8")).hexdigest()[:12]
