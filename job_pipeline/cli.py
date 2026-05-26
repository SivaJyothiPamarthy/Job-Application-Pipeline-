"""Command-line interface for the job search pipeline.

    python -m job_pipeline.cli run     --profile data/profile.yaml [--source sample|platsbanken]
    python -m job_pipeline.cli scout   --profile data/profile.yaml [--source ...]
    python -m job_pipeline.cli status
    python -m job_pipeline.cli approve <job_id> [--status submitted]
    python -m job_pipeline.cli coach   <job_id> --profile data/profile.yaml
"""

from __future__ import annotations

import argparse
import sys

from . import config, store
from .agents import coach as coach_agent
from .agents import scout as scout_agent
from .pipeline import run_pipeline
from .profile import Profile


def _cmd_run(args: argparse.Namespace) -> int:
    run_pipeline(args.profile, source=args.source, scout_target=args.target, top_n=args.top)
    return 0


def _cmd_scout(args: argparse.Namespace) -> int:
    profile = Profile.load(args.profile)
    jobs = scout_agent.scout(profile, args.source, args.target)
    print(f"Found {len(jobs)} jobs from '{args.source}':\n")
    for j in jobs:
        print(f"  [{j.id}] {j.title} @ {j.company} — {j.location}")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    records = store.all_records()
    if not records:
        print("No applications tracked yet. Run the pipeline first.")
        return 0
    print(f"{'STATUS':<10} {'COMPANY':<22} {'ROLE':<34} JOB ID")
    print("-" * 84)
    for r in records:
        print(
            f"{r.get('status',''):<10} {r.get('company','')[:21]:<22} "
            f"{r.get('title','')[:33]:<34} {r.get('id','')}"
        )
    return 0


def _cmd_approve(args: argparse.Namespace) -> int:
    ok = store.set_status(args.job_id, args.status)
    if not ok:
        print(f"Job '{args.job_id}' not found in the tracker.", file=sys.stderr)
        return 1
    print(f"Marked {args.job_id} as '{args.status}'.")
    return 0


def _cmd_coach(args: argparse.Namespace) -> int:
    profile = Profile.load(args.profile)
    rec = store.get(args.job_id)
    if not rec:
        print(f"Job '{args.job_id}' not found. Run the pipeline first.", file=sys.stderr)
        return 1

    company, title = rec.get("company", ""), rec.get("title", "")
    location, description = rec.get("location", "Stockholm"), rec.get("description", "")
    role_block = f"Company: {company}\nRole: {title}\nLocation: {location}"

    print(f"\n[E] Interview Coach — {title} @ {company}\n")
    print("Researching the company…\n")
    print(coach_agent.research(profile, company, title, location, description))

    print("\n" + "=" * 64)
    print("MOCK INTERVIEW — type your answer, or just press Enter to skip.")
    print("Ctrl-C to stop early.\n")
    questions = coach_agent.prep_questions(profile, company, title, location, description)

    transcript = ""
    try:
        for i, q in enumerate(questions, 1):
            print(f"\nQ{i} [{q.get('category','')}]: {q['question']}")
            try:
                answer = input("> ").strip()
            except EOFError:
                break
            if not answer:
                continue
            fb = coach_agent.feedback(profile, role_block, q["question"], answer, transcript)
            print(f"\n  Coach: {fb}")
            transcript += f"Q: {q['question']}\nA: {answer}\n\n"
    except KeyboardInterrupt:
        print("\n\nStopping mock interview.")

    print("\nGood luck — you're interview-ready.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="job_pipeline", description="Stockholm job search agent pipeline.")
    sub = p.add_subparsers(dest="command", required=True)

    def add_profile(sp):
        sp.add_argument("--profile", default="data/profile.yaml", help="Path to profile YAML.")

    run = sub.add_parser("run", help="Run the full pipeline (Scout->Filter->Factory->Submission).")
    add_profile(run)
    run.add_argument("--source", default="sample", help="sample | platsbanken | apify")
    run.add_argument("--target", type=int, default=config.SCOUT_TARGET, help="Jobs to scout.")
    run.add_argument("--top", type=int, default=config.FILTER_TOP_N, help="Shortlist size.")
    run.set_defaults(func=_cmd_run)

    sc = sub.add_parser("scout", help="Just fetch and list jobs.")
    add_profile(sc)
    sc.add_argument("--source", default="sample", help="sample | platsbanken | apify")
    sc.add_argument("--target", type=int, default=config.SCOUT_TARGET)
    sc.set_defaults(func=_cmd_scout)

    st = sub.add_parser("status", help="Show the application tracker.")
    st.set_defaults(func=_cmd_status)

    ap = sub.add_parser("approve", help="Update an application's status.")
    ap.add_argument("job_id")
    ap.add_argument("--status", default="submitted", choices=store.STATUSES)
    ap.set_defaults(func=_cmd_approve)

    co = sub.add_parser("coach", help="Run interview prep + mock interview for a job.")
    add_profile(co)
    co.add_argument("job_id")
    co.set_defaults(func=_cmd_coach)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
