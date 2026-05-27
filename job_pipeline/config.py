"""Central configuration. Reads from environment, with sensible defaults."""

import os

# Which LLM backend to use. Defaults to OpenAI if OPENAI_API_KEY is set (and no
# explicit choice), else Anthropic. Override with LLM_PROVIDER=openai|anthropic.
PROVIDER = os.environ.get(
    "LLM_PROVIDER",
    "openai" if os.environ.get("OPENAI_API_KEY") else "anthropic",
).lower()

# Default model per provider. Override with ANTHROPIC_MODEL / OPENAI_MODEL.
if PROVIDER == "openai":
    MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")
else:
    # Default to the most capable Claude model. Set ANTHROPIC_MODEL=claude-sonnet-4-6
    # to trade some quality for lower cost/latency on the parallel factory.
    MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-7")

# Effort for reasoning-sensitive calls (Anthropic only; ignored on OpenAI chat models).
EFFORT_HIGH = os.environ.get("ANTHROPIC_EFFORT", "high")
# Effort for bulk generation (resume/cover-letter drafting) — cheaper.
EFFORT_GEN = "medium"

# How many jobs Scout aims to collect, and how many Filter shortlists.
SCOUT_TARGET = int(os.environ.get("SCOUT_TARGET", "50"))
FILTER_TOP_N = int(os.environ.get("FILTER_TOP_N", "10"))

# Max concurrent jobs in the Application Factory (respects API rate limits).
FACTORY_CONCURRENCY = int(os.environ.get("FACTORY_CONCURRENCY", "4"))

# Where prepared application packages are written.
OUT_DIR = os.environ.get("PIPELINE_OUT_DIR", "out")

# Local application tracker (the CRM).
STORE_PATH = os.environ.get("PIPELINE_STORE", "data/applications.json")
