"""Plain data structures passed between the agents."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class Job:
    id: str
    title: str
    company: str
    location: str
    description: str
    source: str = "unknown"
    url: Optional[str] = None
    apply_url: Optional[str] = None
    apply_email: Optional[str] = None
    salary: Optional[str] = None
    employment_type: Optional[str] = None
    published: Optional[str] = None
    deadline: Optional[str] = None
    remote: Optional[bool] = None

    def short(self, n: int = 1500) -> str:
        desc = (self.description or "").strip().replace("\n\n", "\n")
        if len(desc) > n:
            desc = desc[:n] + " …[truncated]"
        return desc

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScoredJob:
    job: Job
    match_score: int          # 0-100, fit against the profile
    salary_fit: str           # "good" | "unclear" | "below"
    location_fit: str         # "good" | "ok" | "poor"
    recommend: bool
    reasons: list[str] = field(default_factory=list)
    concerns: list[str] = field(default_factory=list)


@dataclass
class ApplicationPackage:
    job: Job
    resume_md: str
    cover_letter_md: str
    critique: dict[str, Any]
    revised: bool
    submission_brief: str = ""
