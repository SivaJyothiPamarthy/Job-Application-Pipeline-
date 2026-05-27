"""LLM wrapper supporting two backends: OpenAI or Anthropic.

The backend is chosen in config.PROVIDER (auto: OpenAI if OPENAI_API_KEY is set,
else Anthropic; override with LLM_PROVIDER). The five agents only ever call the
public helpers below, so switching providers needs no agent changes.

Helpers: text + JSON-schema-constrained completions, sync and async, plus a
best-effort web-search-backed text completion (Anthropic only; OpenAI falls back
to a plain completion).
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from . import config


# --- system prompt assembly -------------------------------------------------

def system_blocks(profile_context: str, instruction: str) -> list[dict[str, Any]]:
    """Build a system prompt: stable profile prefix + per-agent instruction.

    On Anthropic the profile block carries a cache_control breakpoint so it's
    prompt-cached across the run. On OpenAI the blocks are flattened to a string
    (OpenAI caches long prompt prefixes automatically).
    """
    return [
        {"type": "text", "text": profile_context, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": instruction},
    ]


def _flatten(system: list[dict[str, Any]]) -> str:
    return "\n\n".join(b.get("text", "") for b in system).strip()


# --- Anthropic clients ------------------------------------------------------

@lru_cache(maxsize=1)
def _anthropic_sync():
    import anthropic

    return anthropic.Anthropic()


@lru_cache(maxsize=1)
def _anthropic_async():
    import anthropic

    return anthropic.AsyncAnthropic()


def _anthropic_text(resp) -> str:
    return "".join(b.text for b in resp.content if b.type == "text").strip()


# --- OpenAI clients ---------------------------------------------------------

@lru_cache(maxsize=1)
def _openai_sync():
    from openai import OpenAI

    return OpenAI()


@lru_cache(maxsize=1)
def _openai_async():
    from openai import AsyncOpenAI

    return AsyncOpenAI()


def _openai_messages(system: list[dict[str, Any]], user: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": _flatten(system)},
        {"role": "user", "content": user},
    ]


def _openai_response_format(schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {"name": "result", "schema": schema, "strict": True},
    }


# --- public: text completion ------------------------------------------------

def complete_text(
    system: list[dict[str, Any]],
    user: str,
    *,
    effort: str = config.EFFORT_GEN,
    max_tokens: int = 8000,
) -> str:
    if config.PROVIDER == "openai":
        resp = _openai_sync().chat.completions.create(
            model=config.MODEL,
            max_tokens=max_tokens,
            messages=_openai_messages(system, user),
        )
        return (resp.choices[0].message.content or "").strip()

    resp = _anthropic_sync().messages.create(
        model=config.MODEL,
        max_tokens=max_tokens,
        system=system,
        thinking={"type": "adaptive"},
        output_config={"effort": effort},
        messages=[{"role": "user", "content": user}],
    )
    return _anthropic_text(resp)


async def acomplete_text(
    system: list[dict[str, Any]],
    user: str,
    *,
    effort: str = config.EFFORT_GEN,
    max_tokens: int = 8000,
) -> str:
    if config.PROVIDER == "openai":
        resp = await _openai_async().chat.completions.create(
            model=config.MODEL,
            max_tokens=max_tokens,
            messages=_openai_messages(system, user),
        )
        return (resp.choices[0].message.content or "").strip()

    resp = await _anthropic_async().messages.create(
        model=config.MODEL,
        max_tokens=max_tokens,
        system=system,
        thinking={"type": "adaptive"},
        output_config={"effort": effort},
        messages=[{"role": "user", "content": user}],
    )
    return _anthropic_text(resp)


# --- public: JSON-schema-constrained completion -----------------------------

def complete_json(
    system: list[dict[str, Any]],
    user: str,
    schema: dict[str, Any],
    *,
    effort: str = config.EFFORT_HIGH,
    max_tokens: int = 8000,
) -> Any:
    if config.PROVIDER == "openai":
        resp = _openai_sync().chat.completions.create(
            model=config.MODEL,
            max_tokens=max_tokens,
            messages=_openai_messages(system, user),
            response_format=_openai_response_format(schema),
        )
        return json.loads(resp.choices[0].message.content)

    resp = _anthropic_sync().messages.create(
        model=config.MODEL,
        max_tokens=max_tokens,
        system=system,
        output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": user}],
    )
    return json.loads(_anthropic_text(resp))


async def acomplete_json(
    system: list[dict[str, Any]],
    user: str,
    schema: dict[str, Any],
    *,
    effort: str = config.EFFORT_HIGH,
    max_tokens: int = 8000,
) -> Any:
    if config.PROVIDER == "openai":
        resp = await _openai_async().chat.completions.create(
            model=config.MODEL,
            max_tokens=max_tokens,
            messages=_openai_messages(system, user),
            response_format=_openai_response_format(schema),
        )
        return json.loads(resp.choices[0].message.content)

    resp = await _anthropic_async().messages.create(
        model=config.MODEL,
        max_tokens=max_tokens,
        system=system,
        output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": user}],
    )
    return json.loads(_anthropic_text(resp))


# --- public: web-search-backed text -----------------------------------------

def complete_text_with_websearch(
    system: list[dict[str, Any]],
    user: str,
    *,
    max_tokens: int = 8000,
) -> str:
    """Text completion that may use live web search.

    Anthropic: uses the server-side web_search tool, falling back to a plain
    completion if unavailable. OpenAI: no web search here — falls back to a plain
    completion (the coach then relies on model knowledge).
    """
    if config.PROVIDER == "openai":
        return complete_text(system, user, effort=config.EFFORT_HIGH, max_tokens=max_tokens)

    import anthropic

    try:
        resp = _anthropic_sync().messages.create(
            model=config.MODEL,
            max_tokens=max_tokens,
            system=system,
            thinking={"type": "adaptive"},
            output_config={"effort": config.EFFORT_HIGH},
            tools=[{"type": "web_search_20260209", "name": "web_search"}],
            messages=[{"role": "user", "content": user}],
        )
        return _anthropic_text(resp)
    except anthropic.APIError:
        return complete_text(system, user, effort=config.EFFORT_HIGH, max_tokens=max_tokens)
