"""LLM wrapper supporting three backends: OpenAI, Anthropic, or local Ollama.

The backend is chosen in config.PROVIDER (explicit LLM_PROVIDER, else auto:
OpenAI if OPENAI_API_KEY, else Anthropic if ANTHROPIC_API_KEY, else local Ollama).
OpenAI and Ollama share the OpenAI chat-completions API path; Ollama just points
the client at localhost. The five agents only call the public helpers below, so
switching providers needs no agent changes.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

from . import config


# --- system prompt assembly -------------------------------------------------

def system_blocks(profile_context: str, instruction: str) -> list[dict[str, Any]]:
    """Build a system prompt: stable profile prefix + per-agent instruction.

    On Anthropic the profile block carries a cache_control breakpoint so it's
    prompt-cached across the run. On OpenAI/Ollama the blocks are flattened to a
    string (OpenAI caches long prefixes automatically; Ollama is local).
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


# --- OpenAI-compatible clients (OpenAI + Ollama) ----------------------------

@lru_cache(maxsize=1)
def _compat_sync():
    from openai import OpenAI

    if config.PROVIDER == "ollama":
        return OpenAI(base_url=config.OLLAMA_BASE_URL, api_key="ollama")
    return OpenAI()


@lru_cache(maxsize=1)
def _compat_async():
    from openai import AsyncOpenAI

    if config.PROVIDER == "ollama":
        return AsyncOpenAI(base_url=config.OLLAMA_BASE_URL, api_key="ollama")
    return AsyncOpenAI()


def _compat_messages(system: list[dict[str, Any]], user: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": _flatten(system)},
        {"role": "user", "content": user},
    ]


def _response_format(schema: dict[str, Any]) -> dict[str, Any]:
    js: dict[str, Any] = {"name": "result", "schema": schema}
    if config.PROVIDER == "openai":  # OpenAI supports strict; Ollama may not
        js["strict"] = True
    return {"type": "json_schema", "json_schema": js}


def _loads_lenient(text: str) -> Any:
    """Parse JSON that may be wrapped in code fences or surrounded by prose."""
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        i, j = text.find("{"), text.rfind("}")
        if i != -1 and j != -1 and j > i:
            return json.loads(text[i : j + 1])
        raise


# --- public: text completion ------------------------------------------------

def complete_text(
    system: list[dict[str, Any]],
    user: str,
    *,
    effort: str = config.EFFORT_GEN,
    max_tokens: int = 8000,
) -> str:
    if config.OPENAI_COMPATIBLE:
        resp = _compat_sync().chat.completions.create(
            model=config.MODEL,
            max_tokens=max_tokens,
            messages=_compat_messages(system, user),
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
    if config.OPENAI_COMPATIBLE:
        resp = await _compat_async().chat.completions.create(
            model=config.MODEL,
            max_tokens=max_tokens,
            messages=_compat_messages(system, user),
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

def _json_instruction(user: str, schema: dict[str, Any]) -> str:
    return (
        f"{user}\n\nRespond with ONLY a single valid JSON object matching this schema "
        f"(no prose, no markdown, no code fences):\n{json.dumps(schema)}"
    )


def complete_json(
    system: list[dict[str, Any]],
    user: str,
    schema: dict[str, Any],
    *,
    effort: str = config.EFFORT_HIGH,
    max_tokens: int = 8000,
) -> Any:
    if config.OPENAI_COMPATIBLE:
        client = _compat_sync()
        if config.PROVIDER == "ollama":
            # Grammar-constrained decoding is slow locally — instruct JSON instead.
            resp = client.chat.completions.create(
                model=config.MODEL,
                max_tokens=max_tokens,
                messages=_compat_messages(system, _json_instruction(user, schema)),
            )
            return _loads_lenient(resp.choices[0].message.content)
        resp = client.chat.completions.create(
            model=config.MODEL,
            max_tokens=max_tokens,
            messages=_compat_messages(system, user),
            response_format=_response_format(schema),
        )
        return _loads_lenient(resp.choices[0].message.content)

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
    if config.OPENAI_COMPATIBLE:
        client = _compat_async()
        if config.PROVIDER == "ollama":
            resp = await client.chat.completions.create(
                model=config.MODEL,
                max_tokens=max_tokens,
                messages=_compat_messages(system, _json_instruction(user, schema)),
            )
            return _loads_lenient(resp.choices[0].message.content)
        resp = await client.chat.completions.create(
            model=config.MODEL,
            max_tokens=max_tokens,
            messages=_compat_messages(system, user),
            response_format=_response_format(schema),
        )
        return _loads_lenient(resp.choices[0].message.content)

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
    completion if unavailable. OpenAI/Ollama: no web search — falls back to a
    plain completion (the coach then relies on the model's own knowledge).
    """
    if config.OPENAI_COMPATIBLE:
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
