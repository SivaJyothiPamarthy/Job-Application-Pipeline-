"""Free web-search job source, powered by Claude's server-side web_search tool.

Two steps:
  1. A web_search-enabled call gathers real, recent postings (with URLs).
  2. A structured-extraction call turns those findings into Job records.

No extra API key beyond ANTHROPIC_API_KEY (requires web_search enabled on the
account). Coverage is broad but best-effort — always sanity-check the URLs, since
search results are less structured than a dedicated job API.
"""

from __future__ import annotations

import hashlib
from typing import Any, Optional

from .. import llm
from ..models import Job
from ..profile import Profile
from .base import JobSource

_SEARCH = """You are a job-search assistant. Use web search to find REAL, currently-open
job postings matching the candidate (profile above). Search reputable sources (LinkedIn,
TheHub, company career pages, Indeed). Only include postings you actually found via search,
each with its real URL — never invent listings. Prefer recent postings.

List what you find: for each, give title, company, location, the posting URL, a short
description/snippet, and salary or employment type if shown."""

_EXTRACT = """Convert the job findings below into structured records. Use only information
present in the findings. If a field is unknown, use an empty string. Do not invent jobs or
URLs."""

_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "jobs": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "title": {"type": "string"},
                    "company": {"type": "string"},
                    "location": {"type": "string"},
                    "url": {"type": "string"},
                    "description": {"type": "string"},
                    "salary": {"type": "string"},
                    "employment_type": {"type": "string"},
                },
                "required": [
                    "title",
                    "company",
                    "location",
                    "url",
                    "description",
                    "salary",
                    "employment_type",
                ],
            },
        }
    },
    "required": ["jobs"],
}


class WebSearchSource(JobSource):
    name = "websearch"

    def fetch(self, profile: Profile, limit: int) -> list[Job]:
        ctx = profile.to_context()
        titles = ", ".join(profile.preferences.get("target_titles", [])) or "software roles"
        location = (profile.preferences.get("locations") or ["Stockholm"])[0]

        findings = llm.complete_text_with_websearch(
            llm.system_blocks(ctx, _SEARCH),
            f"Find up to {limit} open jobs for: {titles} in {location}. "
            f"Working language English.",
            max_tokens=8000,
        )

        result = llm.complete_json(
            llm.system_blocks(ctx, _EXTRACT),
            f"Findings:\n{findings}\n\nReturn up to {limit} jobs.",
            _SCHEMA,
            max_tokens=8000,
        )

        jobs: list[Job] = []
        for j in result.get("jobs", [])[:limit]:
            url = j.get("url") or None
            jobs.append(
                Job(
                    id=_derive_id(url, j.get("title", ""), j.get("company", "")),
                    title=(j.get("title") or "Untitled role").strip(),
                    company=(j.get("company") or "Unknown").strip(),
                    location=(j.get("location") or location).strip(),
                    description=(j.get("description") or "").strip(),
                    source="websearch",
                    url=url,
                    apply_url=url,
                    salary=j.get("salary") or None,
                    employment_type=j.get("employment_type") or None,
                )
            )
        return jobs


def _derive_id(url: Optional[str], title: str, company: str) -> str:
    basis = url or f"{title}|{company}"
    return "web-" + hashlib.sha1(basis.encode("utf-8")).hexdigest()[:12]
