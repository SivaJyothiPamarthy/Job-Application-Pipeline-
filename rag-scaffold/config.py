"""Central config. All tunables live here so you can sweep them during eval."""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Vespa ---
VESPA_URL = os.getenv("VESPA_URL", "http://localhost")
VESPA_PORT = int(os.getenv("VESPA_PORT", "8080"))
VESPA_CONFIG_PORT = int(os.getenv("VESPA_CONFIG_PORT", "19071"))
APP_NAME = "docsearch"

# --- Models ---
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-m3")
RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
EMBED_DIM = 1024  # BGE-M3 output dimension; must match vespa/schemas/document.sd

# --- Generation ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

# --- Chunking (tune against your eval set) ---
CHUNK_SIZE = 512        # tokens per chunk
CHUNK_OVERLAP = 64

# --- Retrieval pipeline knobs ---
BM25_TOPK = 20          # candidates from keyword search
VECTOR_TOPK = 20        # candidates from vector search
RRF_K = 60              # reciprocal-rank-fusion constant
RRF_POOL = 30           # unique candidates kept after fusion
RERANK_TOPK = 6         # final chunks handed to the LLM
