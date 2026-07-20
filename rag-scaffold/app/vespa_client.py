"""Thin wrapper over the Vespa query + feed HTTP API.

Exposes exactly what the pipeline needs: feed a batch of chunks, and run the two
first-stage searches (BM25 and vector), each already ACL-filtered.
"""
from typing import Dict, List

from vespa.application import Vespa

from config import VESPA_PORT, VESPA_URL
from app.acl import vespa_acl_filter


def client() -> Vespa:
    return Vespa(url=VESPA_URL, port=VESPA_PORT)


def feed(chunks: List[Dict]):
    """Feed chunk documents. Each chunk dict must match the schema fields."""
    app = client()
    docs = [{"id": c["doc_id"], "fields": c} for c in chunks]
    responses = app.feed_iterable(iter(docs), schema="document")
    ok = sum(1 for r in responses if r.is_successful())
    print(f"Fed {ok}/{len(docs)} chunks.")


def _hits_to_dicts(response) -> List[Dict]:
    out = []
    for h in response.hits:
        f = h["fields"]
        out.append({
            "doc_id": f.get("doc_id"),
            "title": f.get("title", ""),
            "content": f.get("content", ""),
            "url": f.get("url", ""),
            "source": f.get("source", ""),
            "relevance": h.get("relevance", 0.0),
        })
    return out


def bm25_search(query_text: str, user_groups: List[str], top_k: int) -> List[Dict]:
    """Keyword search — catches exact matches (build numbers, error codes, IDs)."""
    acl = vespa_acl_filter(user_groups)
    yql = (
        f'select * from document where userInput(@q) and {acl}'
    )
    body = {"yql": yql, "q": query_text, "ranking": "bm25", "hits": top_k}
    return _hits_to_dicts(client().query(body=body))


def vector_search(query_embedding: List[float], user_groups: List[str], top_k: int) -> List[Dict]:
    """Semantic search over BGE-M3 embeddings via HNSW nearestNeighbor."""
    acl = vespa_acl_filter(user_groups)
    yql = (
        f'select * from document where '
        f'({{targetHits:{top_k}}}nearestNeighbor(embedding, q_embedding)) and {acl}'
    )
    body = {
        "yql": yql,
        "input.query(q_embedding)": query_embedding,
        "ranking": "semantic",
        "hits": top_k,
    }
    return _hits_to_dicts(client().query(body=body))
