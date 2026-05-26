"""Offline sample source so the pipeline runs end-to-end without network/API keys.

Reads data/sample_jobs.json. Use --source platsbanken for the live JobTech API.
"""

from __future__ import annotations

import json
import os

from ..models import Job
from ..profile import Profile
from .base import JobSource

_DEFAULT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "sample_jobs.json"
)


class SampleSource(JobSource):
    name = "sample"

    def __init__(self, path: str = _DEFAULT_PATH):
        self.path = path

    def fetch(self, profile: Profile, limit: int) -> list[Job]:
        with open(self.path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        jobs = [Job(**j) for j in raw]
        return jobs[:limit]
