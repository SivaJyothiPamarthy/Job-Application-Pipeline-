"""The retrieval pipeline: hybrid search -> RRF fusion -> rerank.

    BM25 top-20  +  Vector top-20
        -> RRF merge (top-30 unique)
        -> cross-encoder rerank (top-6)
"""
from typing import Dict, List

from config import (BM25_TOPK, RERANK_TOPK, RRF_K, RRF_POOL, VECTOR_TOPK)
from app import vespa_client
from app.embeddings import embed_one
from app.reranker import rerank


def _rrf_merge(rankings: List[List[Dict]], k: int, pool: int) -> List[Dict]:
    """Reciprocal Rank Fusion.

    Combines several ranked lists into one, robust to score-scale differences
    between BM25 and vector similarity. score = sum(1 / (k + rank)).
    """
    scores: Dict[str, float] = {}
    by_id: Dict[str, Dict] = {}
    for ranking in rankings:
        for rank, hit in enumerate(ranking):
            did = hit["doc_id"]
            scores[did] = scores.get(did, 0.0) + 1.0 / (k + rank)
            by_id.setdefault(did, hit)
    ordered = sorted(scores, key=scores.get, reverse=True)[:pool]
    return [by_id[did] for did in ordered]


def retrieve(query_text: str, user_groups: List[str]) -> List[Dict]:
    """Return the top reranked chunks the user is allowed to see."""
    # Stage 1: two first-stage retrievers, both ACL-filtered inside Vespa.
    bm25_hits = vespa_client.bm25_search(query_text, user_groups, BM25_TOPK)
    q_emb = embed_one(query_text)
    vector_hits = vespa_client.vector_search(q_emb, user_groups, VECTOR_TOPK)

    # Stage 2: fuse into one candidate pool.
    fused = _rrf_merge([bm25_hits, vector_hits], k=RRF_K, pool=RRF_POOL)

    # Stage 3: cross-encoder rerank to the final context set.
    return rerank(query_text, fused, top_k=RERANK_TOPK)
