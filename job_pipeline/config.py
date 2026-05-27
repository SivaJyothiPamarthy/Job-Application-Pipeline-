"""Central configuration. Reads from environment, with sensible defaults."""

import os

# Which LLM backend to use. Explicit LLM_PROVIDER wins; otherwise auto-detect:
# OpenAI if OPENAI_API_KEY is set, else Anthropic if ANTHROPIC_API_KEY is set,
# else local Ollama (no key, no cost). Values: openai | anthropic | ollama.
PROVIDER = (
    os.environ.get("LLM_PROVIDER")
    or ("openai" if os.environ.get("OPENAI_API_KEY") else None)
    or ("anthropic" if os.environ.get("ANTHROPIC_API_KEY") else None)
    or "ollama"
).lower()

# Local Ollama OpenAI-compatible endpoint.
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")

# Default model per provider. Override with the matching *_MODEL env var.
if PROVIDER == "openai":
    MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")
elif PROVIDER == "ollama":
    MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1")
else:
    # Default to the most capable Claude model. Set ANTHROPIC_MODEL=claude-sonnet-4-6
    # to trade some quality for lower cost/latency on the parallel factory.
    MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-7")

# True for backends that speak the OpenAI chat-completions API (OpenAI + Ollama).
OPENAI_COMPATIBLE = PROVIDER in ("openai", "ollama")

# Effort for reasoning-sensitive calls (Anthropic only; ignored elsewhere).
EFFORT_HIGH = os.environ.get("ANTHROPIC_EFFORT", "high")
# Effort for bulk generation (resume/cover-letter drafting) — cheaper.
EFFORT_GEN = "medium"

# How many jobs Scout aims to collect, and how many Filter shortlists.
SCOUT_TARGET = int(os.environ.get("SCOUT_TARGET", "50"))
FILTER_TOP_N = int(os.environ.get("FILTER_TOP_N", "10"))

# Filter scores jobs in batches of this size (smaller = faster/steadier on local
# models). Default smaller for Ollama since local generation is slow.
FILTER_BATCH = int(os.environ.get("FILTER_BATCH", "6" if PROVIDER == "ollama" else "25"))

# Max concurrent jobs in the Application Factory (respects API rate limits).
FACTORY_CONCURRENCY = int(os.environ.get("FACTORY_CONCURRENCY", "4"))

# Where prepared application packages are written.
OUT_DIR = os.environ.get("PIPELINE_OUT_DIR", "out")

# Local application tracker (the CRM).
STORE_PATH = os.environ.get("PIPELINE_STORE", "data/applications.json")
