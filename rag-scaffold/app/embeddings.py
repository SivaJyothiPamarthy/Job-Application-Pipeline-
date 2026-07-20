"""BGE-M3 multilingual embedder.

BGE-M3 handles 100+ languages, so localized game docs embed into the same space
as English ones. Model is lazily loaded and cached process-wide.
"""
from functools import lru_cache
from typing import List

from config import EMBED_MODEL


@lru_cache(maxsize=1)
def _model():
    from FlagEmbedding import BGEM3FlagModel
    return BGEM3FlagModel(EMBED_MODEL, use_fp16=True)


def embed(texts: List[str]) -> List[List[float]]:
    """Return one dense vector per input text."""
    out = _model().encode(texts, batch_size=16, max_length=1024)
    return [v.tolist() for v in out["dense_vecs"]]


def embed_one(text: str) -> List[float]:
    return embed([text])[0]
