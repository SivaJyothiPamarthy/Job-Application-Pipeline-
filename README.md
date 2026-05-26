# Job Application Pipeline — Stockholm edition

Five agents, end to end, from job discovery to mock interview:

```
YOUR PROFILE (resume + preferences)
        │
   [A] JOB SCOUT          Platsbanken (JobTech API) → ~50 jobs
        │
   [B] JOB FILTER         reads every JD → shortlist top 10
        │                 (match + salary + location, English/PR-aware)
   [C] APPLICATION        runs in parallel, one per job:
       FACTORY            tailor resume → cover letter → critic → revise
        │
   [D] SUBMISSION         assembles package + "how to apply" brief,
        │                 tracks status — STOPS at an approval gate
   ─ ─ ─ ─ ─ ─ ─ ─ ─ ─    (you review & submit; nothing auto-sends)
        │
   [E] INTERVIEW COACH    per company: research → question prep → mock interview
        │
   READY TO INTERVIEW
```

## Why this differs from "scrape LinkedIn and auto-apply"

This is tuned for a real Stockholm search (English-language roles, work authorization
already in hand), and deliberately avoids the brittle/risky parts of the original sketch:

- **Scout uses Platsbanken's [JobTech JobSearch API](https://jobsearch.api.jobtechdev.se/)** —
  Sweden's official, free, public job-search API — instead of scraping LinkedIn/Indeed
  (which is against their terms and gets blocked). A bundled sample dataset lets the whole
  pipeline run offline with no API access.
- **LinkedIn coverage via [Apify](https://apify.com)** (`--source apify`): a managed
  scraping platform with a real API and marketplace Actors (e.g. a LinkedIn Jobs scraper),
  so you get LinkedIn listings without DIY scraping or login automation. Needs
  `APIFY_API_TOKEN`; the Actor and its input are configurable (see below).
- **Free web-search source** (`--source websearch`): uses Claude's server-side web search
  to find real, recent postings (LinkedIn-indexed, TheHub, company pages) and extract them
  into structured records. No extra key; best-effort coverage — verify the URLs.
- **Filter is English- and PR-aware:** it never penalizes a job for lacking visa
  sponsorship, and flags (rather than auto-passes) roles that require fluent Swedish.
- **Submission does not auto-submit.** Most Swedish applications go through ATS platforms
  (Teamtailor, Workday, Greenhouse) or need login/BankID. The agent prepares everything and
  stops at an approval gate — you click submit.
- **A first-class application tracker** records every job through its lifecycle.

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...        # see .env.example
cp data/profile.example.yaml data/profile.yaml   # then edit with your real resume
```

## Usage

```bash
# Full pipeline on bundled sample jobs (no network needed beyond the API):
python -m job_pipeline.cli run --profile data/profile.yaml --source sample

# Against live Stockholm jobs from Platsbanken:
python -m job_pipeline.cli run --profile data/profile.yaml --source platsbanken

# Against LinkedIn (and other boards) via Apify — needs APIFY_API_TOKEN:
python -m job_pipeline.cli run --profile data/profile.yaml --source apify

# Just see what Scout finds:
python -m job_pipeline.cli scout --profile data/profile.yaml --source platsbanken

# After you submit an application yourself:
python -m job_pipeline.cli approve <job_id> --status submitted

# Track everything:
python -m job_pipeline.cli status

# When you get a callback — research + mock interview for one job:
python -m job_pipeline.cli coach <job_id> --profile data/profile.yaml
```

Prepared packages are written to `out/<company>__<job_id>/`:
`resume.md`, `cover_letter.md`, and `HOW_TO_APPLY.md`.

## Configuration

Environment variables (all optional):

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_MODEL` | `claude-opus-4-7` | Model. Set to `claude-sonnet-4-6` to lower cost. |
| `SCOUT_TARGET` | `50` | Jobs to collect. |
| `FILTER_TOP_N` | `10` | Shortlist size. |
| `FACTORY_CONCURRENCY` | `4` | Parallel application builds. |
| `PIPELINE_OUT_DIR` | `out` | Where packages are written. |
| `APIFY_API_TOKEN` | — | Required for `--source apify`. |
| `APIFY_ACTOR` | `bebity~linkedin-jobs-scraper` | Which Apify Actor to run. |

Apify Actors differ in their input/output schemas. The source maps common field names
automatically, but if you pick a different Actor you can override its input via
`preferences.apify_input` in your profile YAML (a dict merged into the Actor input) and
set `preferences.apify_actor` (or `APIFY_ACTOR`).

## How it's built

- **Claude API (Opus 4.7)** for all reasoning, via the Anthropic SDK. Adaptive thinking +
  the `effort` parameter; structured outputs for filter scoring and the critic.
- The **profile is prompt-cached** as a stable system prefix, so the 50-job filter and the
  10× factory reuse it cheaply.
- The **Application Factory runs concurrently** on the async client (bounded by a semaphore).
- **Truthfulness guardrail:** the factory only reorders/rewords real experience from your
  profile — it never invents employers, titles, or skills.

## Layout

```
job_pipeline/
  agents/    scout, filter, factory, submission, coach   (A–E)
  sources/   base, platsbanken (JobTech API), sample
  llm.py     Anthropic wrapper (caching, structured output, sync+async)
  store.py   application tracker (JSON CRM)
  pipeline.py / cli.py
data/        profile.example.yaml, sample_jobs.json
```
