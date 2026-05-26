"""Agent D: SUBMISSION AGENT.

Does NOT blind-submit. Swedish applications mostly run through ATS platforms
(Teamtailor, Workday, Greenhouse) or need login/BankID, which can't and shouldn't be
automated. Instead this agent:
  - writes each ready-to-submit package to disk (resume + cover letter),
  - generates a "how to apply" brief from the JD,
  - records the application in the tracker as 'prepared',
  - and stops at a human approval gate.

You review, then run `approve <job_id>` to mark it submitted.
"""

from __future__ import annotations

import os
import re

from .. import config, llm, store
from ..models import ApplicationPackage
from ..profile import Profile

_BRIEF = """Write a concise "how to apply" brief for the candidate for this job. Cover:
- exactly where/how to apply (use the apply URL or email given; note if it's an ATS),
- which documents to attach,
- the deadline (and urgency),
- 2-3 tailored tips for this specific application,
- any red flags to confirm before applying (e.g. Swedish-language requirement).
Keep it short and practical. Output Markdown."""


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:50] or "job"


def prepare(profile: Profile, packages: list[ApplicationPackage]) -> list[str]:
    """Write packages to disk, record them, and return the output directory paths."""
    os.makedirs(config.OUT_DIR, exist_ok=True)
    dirs: list[str] = []

    for pkg in packages:
        job = pkg.job
        folder = os.path.join(config.OUT_DIR, f"{_slug(job.company)}__{job.id}")
        os.makedirs(folder, exist_ok=True)

        with open(os.path.join(folder, "resume.md"), "w", encoding="utf-8") as f:
            f.write(pkg.resume_md)
        with open(os.path.join(folder, "cover_letter.md"), "w", encoding="utf-8") as f:
            f.write(pkg.cover_letter_md)

        brief = llm.complete_text(
            llm.system_blocks(profile.to_context(), _BRIEF),
            f"Job: {job.title} at {job.company}\nLocation: {job.location}\n"
            f"Apply URL: {job.apply_url or job.url or 'not provided'}\n"
            f"Apply email: {job.apply_email or 'none'}\n"
            f"Deadline: {job.deadline or 'not stated'}\n\n"
            f"Job description:\n{job.short(2500)}",
            effort=config.EFFORT_GEN,
        )
        pkg.submission_brief = brief
        with open(os.path.join(folder, "HOW_TO_APPLY.md"), "w", encoding="utf-8") as f:
            f.write(brief)

        store.upsert(job, status="prepared", extra={"package_dir": folder})
        dirs.append(folder)

    return dirs
