"""Agent E: INTERVIEW COACH.

Per-company prep for when you get a callback:
  - researches the company (web search when available),
  - preps likely interview questions tuned to the role and Swedish norms,
  - runs an interactive mock interview, giving feedback after each answer.
"""

from __future__ import annotations

from .. import config, llm
from ..profile import Profile

_RESEARCH = """Research this company and role to prepare the candidate (profile above)
for an interview. Produce a tight briefing in Markdown:
- What the company does, products, scale, and recent news (last ~12 months).
- The team/role context and what they likely value.
- Stockholm/Swedish interview norms relevant here (often competency-based, culture/
  värdegrund fit, sometimes a technical/case round, informal fika-style chats).
- 3 smart questions the candidate should ask them.
Be concrete; cite what you find via search."""

_QUESTIONS = """Generate likely interview questions for this candidate and role. Mix
behavioral, role-specific/technical, and motivation questions. Tailor to the candidate's
background and the company."""

_QUESTIONS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "category": {"type": "string"},
                    "question": {"type": "string"},
                },
                "required": ["category", "question"],
            },
        }
    },
    "required": ["questions"],
}

_FEEDBACK = """You are an experienced interview coach running a mock interview for the
role below. The candidate just answered the question. Give brief, candid feedback:
what worked, what to improve, and a sharper way to frame it (nudge toward STAR where it
fits). 4-6 sentences. Encouraging but honest."""


def _role_block(company: str, title: str, location: str, description: str) -> str:
    block = f"Company: {company}\nRole: {title}\nLocation: {location}"
    if description:
        block += f"\nJob description:\n{description[:2500]}"
    return block


def research(profile: Profile, company: str, title: str, location: str, description: str) -> str:
    return llm.complete_text_with_websearch(
        llm.system_blocks(profile.to_context(), _RESEARCH),
        _role_block(company, title, location, description),
    )


def prep_questions(profile: Profile, company: str, title: str, location: str, description: str):
    result = llm.complete_json(
        llm.system_blocks(profile.to_context(), _QUESTIONS),
        _role_block(company, title, location, description) + "\n\nGenerate 6 questions.",
        _QUESTIONS_SCHEMA,
    )
    return result.get("questions", [])


def feedback(profile: Profile, role_block: str, question: str, answer: str, transcript: str) -> str:
    return llm.complete_text(
        llm.system_blocks(profile.to_context(), _FEEDBACK),
        f"Role:\n{role_block}\n\nQuestion: {question}\n\nCandidate's answer: {answer}\n\n"
        f"Earlier in this mock interview:\n{transcript or '(start of interview)'}",
        effort=config.EFFORT_HIGH,
    )
