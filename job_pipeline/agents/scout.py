"""Agent A: JOB SCOUT.

Collects jobs from a source (Platsbanken live, or sample data) matching the
profile, deduplicates, and returns up to the target count.
"""

from __future__ import annotations

from ..models import Job
from ..profile import Profile
from ..sources import get_source


def scout(profile: Profile, source_name: str, target: int) -> list[Job]:
    source = get_source(source_name)
    jobs = source.fetch(profile, target)

    seen: set[tuple[str, str]] = set()
    unique: list[Job] = []
    for job in jobs:
        key = (job.title.strip().lower(), job.company.strip().lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(job)

    return unique[:target]
