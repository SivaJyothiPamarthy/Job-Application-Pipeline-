"""Retrieval eval on a golden set. Run this BEFORE tuning chunking/prompts.

Measures two retrieval-quality metrics that don't need an LLM judge:
  - Hit@k : did any relevant doc appear in the final reranked chunks?
  - MRR   : 1 / rank of the first relevant doc (0 if none).

Golden set format (eval/eval_set.jsonl), one JSON object per line:
  {"question": "...", "groups": ["eng","all"], "relevant_doc_ids": ["file.md"]}

`relevant_doc_ids` are matched against each chunk's title (the source file name).
"""
import json
import os
from statistics import mean

from app.retrieval import retrieve

HERE = os.path.dirname(__file__)
EVAL_FILE = os.path.join(HERE, "eval_set.jsonl")


def _is_relevant(chunk: dict, relevant_ids: list) -> bool:
    hay = f"{chunk.get('title','')} {chunk.get('doc_id','')} {chunk.get('url','')}"
    return any(rid in hay for rid in relevant_ids)


def main():
    if not os.path.exists(EVAL_FILE):
        raise SystemExit(
            f"{EVAL_FILE} not found. Copy eval_set.example.jsonl to eval_set.jsonl "
            "and fill in real question/answer pairs."
        )

    cases = [json.loads(line) for line in open(EVAL_FILE) if line.strip()]
    hits, rr = [], []

    for case in cases:
        chunks = retrieve(case["question"], case.get("groups", ["all"]))
        relevant = case["relevant_doc_ids"]
        rank = next((i for i, c in enumerate(chunks, 1)
                     if _is_relevant(c, relevant)), None)
        hits.append(1 if rank else 0)
        rr.append(1.0 / rank if rank else 0.0)
        status = f"hit@rank {rank}" if rank else "MISS"
        print(f"  [{status:>12}] {case['question']}")

    n = len(cases)
    print("\n=== RETRIEVAL EVAL ===")
    print(f"  cases : {n}")
    print(f"  Hit@k : {mean(hits):.2%}")
    print(f"  MRR   : {mean(rr):.3f}")


if __name__ == "__main__":
    main()
