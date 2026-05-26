"""Central configuration. Reads from environment, with sensible defaults."""

import os

# Default to the most capable model. Override with ANTHROPIC_MODEL=claude-sonnet-4-6
# if you want to trade some quality for lower cost/latency on the parallel factory.
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-7")

# Effort for reasoning-sensitive calls (filter scoring, critic).
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
