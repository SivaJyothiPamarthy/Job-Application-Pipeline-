"""Thin wrapper around the Anthropic SDK.

Centralizes model/effort config, prompt caching of the (stable) profile block,
and small helpers for text and JSON-schema-constrained completions — sync and async.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Optional

import anthropic

from . import config


@lru_cache(maxsize=1)
def _sync() -> anthropic.Anthropic:
    return anthropic.Anthropic()


@lru_cache(maxsize=1)
def _async() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic()


def system_blocks(profile_context: str, instruction: str) -> list[dict[str, Any]]:
    """Build a system prompt: cached profile prefix + per-agent instruction.

    The profile block is identical across every call in a run, so caching it
    saves the bulk of input cost across the 50-job filter and the 10x factory.
    """
    return [
        {"type": "text", "text": profile_context, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": instruction},
    ]


def _text(resp) -> str:
    return "".join(b.text for b in resp.content if b.type == "text").strip()


# --- sync -------------------------------------------------------------------

def complete_text(
    system: list[dict[str, Any]],
    user: str,
    *,
    effort: str = config.EFFORT_GEN,
    max_tokens: int = 8000,
) -> str:
    resp = _sync().messages.create(
        model=config.MODEL,
        max_tokens=max_tokens,
        system=system,
        thinking={"type": "adaptive"},
        output_config={"effort": effort},
        messages=[{"role": "user", "content": user}],
    )
    return _text(resp)


def complete_json(
    system: list[dict[str, Any]],
    user: str,
    schema: dict[str, Any],
    *,
    effort: str = config.EFFORT_HIGH,
    max_tokens: int = 8000,
) -> Any:
    resp = _sync().messages.create(
        model=config.MODEL,
        max_tokens=max_tokens,
        system=system,
        output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": user}],
    )
    return json.loads(_text(resp))


# --- async (used by the parallel Application Factory) -----------------------

async def acomplete_text(
    system: list[dict[str, Any]],
    user: str,
    *,
    effort: str = config.EFFORT_GEN,
    max_tokens: int = 8000,
) -> str:
    resp = await _async().messages.create(
        model=config.MODEL,
        max_tokens=max_tokens,
        system=system,
        thinking={"type": "adaptive"},
        output_config={"effort": effort},
        messages=[{"role": "user", "content": user}],
    )
    return _text(resp)


async def acomplete_json(
    system: list[dict[str, Any]],
    user: str,
    schema: dict[str, Any],
    *,
    effort: str = config.EFFORT_HIGH,
    max_tokens: int = 8000,
) -> Any:
    resp = await _async().messages.create(
        model=config.MODEL,
        max_tokens=max_tokens,
        system=system,
        output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": user}],
    )
    return json.loads(_text(resp))


def complete_text_with_websearch(
    system: list[dict[str, Any]],
    user: str,
    *,
    max_tokens: int = 8000,
) -> str:
    """Text completion that may use the server-side web_search tool.

    Falls back to a plain completion if web search isn't available on the account.
    """
    try:
        resp = _sync().messages.create(
            model=config.MODEL,
            max_tokens=max_tokens,
            system=system,
            thinking={"type": "adaptive"},
            output_config={"effort": config.EFFORT_HIGH},
            tools=[{"type": "web_search_20260209", "name": "web_search"}],
            messages=[{"role": "user", "content": user}],
        )
        return _text(resp)
    except anthropic.APIError:
        return complete_text(system, user, effort=config.EFFORT_HIGH, max_tokens=max_tokens)
