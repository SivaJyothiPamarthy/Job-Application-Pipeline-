"""Agent B: JOB FILTER.

Reads all the JDs, scores each against the profile (match + salary + location),
and shortlists the strongest. Done in a single structured-output call for cost.
"""

from __future__ import annotations

from .. import config, llm
from ..models import Job, ScoredJob
from ..profile import Profile

_INSTRUCTION = """You are a sharp, skeptical career advisor screening jobs for the candidate above.

For EACH job, judge fit honestly. The candidate is searching in Stockholm, works in
English, and already has the right to work in Sweden (permanent residency) — so visa
sponsorship is NOT needed and should never count against a job.

Score each job:
- match_score (0-100): fit between the candidate's resume/skills and the role. Be
  discerning — reserve 80+ for genuinely strong matches, penalize seniority mismatch,
  wrong discipline, or missing core skills.
- salary_fit: "good" if it meets/exceeds the candidate's minimum (or is clearly senior),
  "below" if it's an unpaid/internship/junior role beneath them, else "unclear".
- location_fit: "good" for Stockholm or remote-from-Sweden, "ok" for commutable/hybrid,
  "poor" otherwise.
- recommend: true only if it's worth the candidate's time to apply.
- reasons: 1-3 short bullet strings on why it fits.
- concerns: 0-3 short bullet strings on risks (e.g. "requires fluent Swedish",
  "below target seniority").

Treat a hard requirement of fluent Swedish as a significant concern (candidate works in
English) but not an automatic rejection."""

_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "rankings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string"},
                    "match_score": {"type": "integer"},
                    "salary_fit": {"type": "string", "enum": ["good", "unclear", "below"]},
                    "location_fit": {"type": "string", "enum": ["good", "ok", "poor"]},
                    "recommend": {"type": "boolean"},
                    "reasons": {"type": "array", "items": {"type": "string"}},
                    "concerns": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "id",
                    "match_score",
                    "salary_fit",
                    "location_fit",
                    "recommend",
                    "reasons",
                    "concerns",
                ],
            },
        }
    },
    "required": ["rankings"],
}


def _render_jobs(jobs: list[Job]) -> str:
    parts = []
    for j in jobs:
        parts.append(
            f"### Job id: {j.id}\n"
            f"Title: {j.title}\n"
            f"Company: {j.company}\n"
            f"Location: {j.location}\n"
            f"Salary: {j.salary or 'not stated'}\n"
            f"Employment: {j.employment_type or 'not stated'}\n"
            f"Description:\n{j.short()}\n"
        )
    return "\n".join(parts)


def _score_batch(system, batch: list[Job]) -> list[dict]:
    user = (
        f"Score these {len(batch)} jobs and return the rankings array. "
        f"Every job id must appear exactly once.\n\n" + _render_jobs(batch)
    )
    result = llm.complete_json(system, user, _SCHEMA, max_tokens=8000)
    return result.get("rankings", [])


def filter_jobs(profile: Profile, jobs: list[Job], top_n: int) -> list[ScoredJob]:
    if not jobs:
        return []

    system = llm.system_blocks(profile.to_context(), _INSTRUCTION)
    by_id = {j.id: j for j in jobs}
    batch_size = max(1, config.FILTER_BATCH)
    rankings: list[dict] = []

    # Score in batches so progress is visible and per-call latency stays low
    # (important for local models). Batches still get ranked together at the end.
    for start in range(0, len(jobs), batch_size):
        batch = jobs[start : start + batch_size]
        done = min(start + len(batch), len(jobs))
        print(f"    scoring {done}/{len(jobs)}…", flush=True)
        try:
            rankings.extend(_score_batch(system, batch))
        except Exception as e:  # one bad batch shouldn't sink the whole run
            print(f"    ⚠ batch {start//batch_size + 1} failed ({e}); skipping", flush=True)

    scored: list[ScoredJob] = []
    for r in rankings:
        job = by_id.get(r.get("id"))
        if not job:
            continue
        scored.append(
            ScoredJob(
                job=job,
                match_score=int(r.get("match_score", 0)),
                salary_fit=r.get("salary_fit", "unclear"),
                location_fit=r.get("location_fit", "ok"),
                recommend=bool(r.get("recommend", False)),
                reasons=r.get("reasons", []) or [],
                concerns=r.get("concerns", []) or [],
            )
        )

    # Recommended first, then by match score.
    scored.sort(key=lambda s: (s.recommend, s.match_score), reverse=True)
    return scored[:top_n]
