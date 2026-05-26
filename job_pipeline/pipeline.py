"""Orchestrator: wires the five agents into the end-to-end pipeline.

    Scout (A) -> Filter (B) -> Application Factory (C) -> Submission (D)
                                                          [approval gate]
    Interview Coach (E) runs separately, per company, when you get a callback.
"""

from __future__ import annotations

from . import config
from .agents import factory, filter as filter_agent, scout, submission
from .models import ApplicationPackage, ScoredJob
from .profile import Profile


def run_pipeline(
    profile_path: str,
    source: str = "sample",
    scout_target: int = config.SCOUT_TARGET,
    top_n: int = config.FILTER_TOP_N,
) -> dict:
    profile = Profile.load(profile_path)

    print(f"\n[A] Job Scout — searching '{source}' for up to {scout_target} jobs…")
    jobs = scout.scout(profile, source, scout_target)
    print(f"    Found {len(jobs)} jobs.")
    if not jobs:
        return {"jobs": 0, "shortlist": [], "packages": []}

    print(f"\n[B] Job Filter — reading {len(jobs)} JDs, shortlisting top {top_n}…")
    shortlist: list[ScoredJob] = filter_agent.filter_jobs(profile, jobs, top_n)
    for s in shortlist:
        flag = "✓" if s.recommend else "·"
        print(f"    {flag} {s.match_score:3d}  {s.job.title} @ {s.job.company}")
        for c in s.concerns:
            print(f"          ⚠ {c}")

    if not shortlist:
        return {"jobs": len(jobs), "shortlist": [], "packages": []}

    print(f"\n[C] Application Factory — tailoring {len(shortlist)} packages in parallel…")
    packages: list[ApplicationPackage] = factory.build_packages(profile, shortlist)
    for p in packages:
        score = p.critique.get("overall_score", "?")
        tag = "revised" if p.revised else "first-pass"
        print(f"    • {p.job.company}: package ready (critic {score}/100, {tag})")

    print(f"\n[D] Submission Agent — preparing packages + briefs (no auto-submit)…")
    dirs = submission.prepare(profile, packages)
    for d in dirs:
        print(f"    → {d}/")

    print("\n" + "=" * 64)
    print("APPROVAL GATE — nothing has been submitted.")
    print("Review each package, then submit yourself and run:")
    print("    python -m job_pipeline.cli approve <job_id>")
    print("Track everything with:")
    print("    python -m job_pipeline.cli status")
    print("=" * 64)

    return {"jobs": len(jobs), "shortlist": shortlist, "packages": packages, "dirs": dirs}
