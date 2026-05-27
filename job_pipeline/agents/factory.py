"""Agent C: APPLICATION FACTORY.

For each shortlisted job, runs a four-step sub-pipeline:
    tailor resume -> cover letter -> critic -> revise
All jobs run concurrently (bounded by a semaphore) via the async client.
"""

from __future__ import annotations

import asyncio

from .. import config, llm
from ..models import ApplicationPackage, Job, ScoredJob
from ..profile import Profile

_TAILOR = """You tailor the candidate's resume (above) to one specific job.
Output a complete, ATS-friendly resume in Markdown, in English. Keep it truthful — only
use real experience from the profile; never invent employers, titles, or skills. Reorder
and reword to foreground what this job cares about, mirror key terminology from the JD,
and lead with a 2-3 line summary targeted at this role. Keep it to roughly one page of
content. Output ONLY the resume Markdown, no preamble."""

_COVER = """You write a focused cover letter (personligt brev) for this job, in English.
Address why the candidate is a strong fit using concrete evidence from their resume, show
genuine interest in this specific company/role, and keep it to 3-4 short paragraphs. Warm
but professional Stockholm-tech tone — no clichés, no fluff. Output ONLY the letter
Markdown, no preamble."""

_CRITIC = """You are a tough hiring-side reviewer. Critique the draft resume and cover
letter for THIS job. Be specific and actionable. Flag: weak/generic claims, missed JD
keywords, anything that reads as untruthful or exaggerated, tone problems, and length
issues. Score the package 0-100 on how likely it is to pass a first screen."""

_CRITIC_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "overall_score": {"type": "integer"},
        "resume_issues": {"type": "array", "items": {"type": "string"}},
        "letter_issues": {"type": "array", "items": {"type": "string"}},
        "must_fix": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["overall_score", "resume_issues", "letter_issues", "must_fix"],
}

_REVISE = """Revise the resume and cover letter to address the critique below. Keep
everything truthful to the candidate's real profile. Return the improved versions."""

_REVISE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "resume_md": {"type": "string"},
        "cover_letter_md": {"type": "string"},
    },
    "required": ["resume_md", "cover_letter_md"],
}

# Skip the revise step if the critic already rates the package this high.
_REVISE_THRESHOLD = 85


def _job_block(job: Job) -> str:
    return (
        f"Title: {job.title}\nCompany: {job.company}\nLocation: {job.location}\n"
        f"Job description:\n{job.short(3000)}"
    )


async def _build_one(profile: Profile, scored: ScoredJob, sem: asyncio.Semaphore) -> ApplicationPackage:
    job = scored.job
    ctx = profile.to_context()
    job_block = _job_block(job)

    async with sem:
        # 1. Tailor resume
        resume = await llm.acomplete_text(
            llm.system_blocks(ctx, _TAILOR),
            f"Tailor the resume for this job:\n\n{job_block}",
            effort=config.EFFORT_GEN,
        )

        # 2. Cover letter
        letter = await llm.acomplete_text(
            llm.system_blocks(ctx, _COVER),
            f"Write the cover letter for this job. Here is the tailored resume for "
            f"reference:\n\n{resume}\n\n---\nJob:\n{job_block}",
            effort=config.EFFORT_GEN,
        )

        # 3. Critic
        critique = await llm.acomplete_json(
            llm.system_blocks(ctx, _CRITIC),
            f"Job:\n{job_block}\n\n---\nDraft resume:\n{resume}\n\n---\n"
            f"Draft cover letter:\n{letter}",
            _CRITIC_SCHEMA,
            effort=config.EFFORT_HIGH,
        )

        revised = False
        if int(critique.get("overall_score", 0)) < _REVISE_THRESHOLD:
            # 4. Revise
            improved = await llm.acomplete_json(
                llm.system_blocks(ctx, _REVISE),
                f"Job:\n{job_block}\n\n---\nResume:\n{resume}\n\n---\nCover letter:\n{letter}"
                f"\n\n---\nCritique:\nmust_fix: {critique.get('must_fix')}\n"
                f"resume_issues: {critique.get('resume_issues')}\n"
                f"letter_issues: {critique.get('letter_issues')}",
                _REVISE_SCHEMA,
                effort=config.EFFORT_GEN,
                max_tokens=12000,
            )
            resume = improved.get("resume_md", resume)
            letter = improved.get("cover_letter_md", letter)
            revised = True

    return ApplicationPackage(
        job=job,
        resume_md=resume,
        cover_letter_md=letter,
        critique=critique,
        revised=revised,
    )


async def _run(profile: Profile, shortlist: list[ScoredJob]) -> list[ApplicationPackage]:
    sem = asyncio.Semaphore(config.FACTORY_CONCURRENCY)
    tasks = [_build_one(profile, s, sem) for s in shortlist]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    packages: list[ApplicationPackage] = []
    for scored, res in zip(shortlist, results):
        if isinstance(res, Exception):
            print(f"    ⚠ {scored.job.company}: package failed ({res}); skipping", flush=True)
            continue
        packages.append(res)
    return packages


def build_packages(profile: Profile, shortlist: list[ScoredJob]) -> list[ApplicationPackage]:
    """Synchronous entry point — runs the async factory to completion."""
    if not shortlist:
        return []
    return asyncio.run(_run(profile, shortlist))
