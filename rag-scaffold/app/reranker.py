"""BGE cross-encoder reranker.

Reranking is the single biggest quality lever in the pipeline (+15-30% on RAGAS).
The cross-encoder scores (query, chunk) pairs jointly, which is far more accurate
than the bi-encoder similarity used for first-stage retrieval.
"""
from functools import lru_cache
from typing import List, Tuple

from config import RERANK_MODEL


@lru_cache(maxsize=1)
def _model():
    from FlagEmbedding import FlagReranker
    return FlagReranker(RERANK_MODEL, use_fp16=True)


def rerank(query: str, candidates: List[dict], top_k: int) -> List[dict]:
    """Sort candidates by cross-encoder relevance, return the top_k.

    Each candidate is a dict with at least a 'content' key. A 'rerank_score' is
    attached to every returned item.
    """
    if not candidates:
        return []
    pairs: List[Tuple[str, str]] = [[query, c["content"]] for c in candidates]
    scores = _model().compute_score(pairs, normalize=True)
    if not isinstance(scores, list):
        scores = [scores]
    for c, s in zip(candidates, scores):
        c["rerank_score"] = float(s)
    return sorted(candidates, key=lambda c: c["rerank_score"], reverse=True)[:top_k]
