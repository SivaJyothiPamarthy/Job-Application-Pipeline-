"""Your profile: resume + preferences. Loaded from a YAML file."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import yaml


@dataclass
class Profile:
    name: str
    location: str
    resume_markdown: str
    preferences: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str) -> "Profile":
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        missing = [k for k in ("name", "location", "resume_markdown") if not data.get(k)]
        if missing:
            raise ValueError(f"Profile {path} is missing required fields: {missing}")
        return cls(
            name=data["name"],
            location=data["location"],
            resume_markdown=data["resume_markdown"],
            preferences=data.get("preferences", {}) or {},
        )

    def search_terms(self) -> list[str]:
        """Query terms Scout uses to hit the job source."""
        prefs = self.preferences
        terms: list[str] = []
        terms += prefs.get("target_titles", []) or []
        terms += prefs.get("keywords", []) or []
        return [t for t in terms if t]

    def to_context(self) -> str:
        """Render the profile as a single block for the model's system prompt."""
        prefs = self.preferences
        lines = [
            f"# Candidate profile: {self.name}",
            f"Base location: {self.location}",
            "",
            "## Preferences",
        ]

        def add(label: str, key: str):
            val = prefs.get(key)
            if val in (None, "", [], {}):
                return
            if isinstance(val, list):
                val = ", ".join(str(v) for v in val)
            lines.append(f"- {label}: {val}")

        add("Target titles", "target_titles")
        add("Keywords", "keywords")
        add("Preferred locations", "locations")
        add("Minimum salary (SEK/month)", "min_salary_sek")
        add("Employment type", "employment_type")
        add("Remote preference", "remote")
        add("Working languages", "languages")
        add("Work authorization", "work_authorization")
        add("Avoid", "exclude")
        if prefs.get("notes"):
            lines.append(f"- Notes: {prefs['notes']}")

        lines += ["", "## Resume", self.resume_markdown.strip()]
        return "\n".join(lines)
