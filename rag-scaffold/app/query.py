"""End-to-end query: retrieve -> Claude -> cited answer.

Usage:
    python -m app.query "How do I roll back a shader cache build?" --groups eng,all
"""
import argparse
from typing import Dict, List

import anthropic

from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
from app.retrieval import retrieve

SYSTEM = (
    "You answer questions using ONLY the provided company documents. "
    "Cite the sources you use with bracketed numbers like [1], [2]. "
    "If the documents do not contain the answer, say so plainly — do not guess."
)


def _format_context(chunks: List[Dict]) -> str:
    blocks = []
    for i, c in enumerate(chunks, 1):
        blocks.append(f"[{i}] title: {c['title']} (source: {c['source']})\n{c['content']}")
    return "\n\n".join(blocks)


def answer(question: str, user_groups: List[str]) -> Dict:
    chunks = retrieve(question, user_groups)
    if not chunks:
        return {"answer": "No documents you have access to match this question.",
                "sources": []}

    context = _format_context(chunks)
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=1024,
        system=SYSTEM,
        messages=[{
            "role": "user",
            "content": f"Company documents:\n\n{context}\n\nQuestion: {question}",
        }],
    )
    text = "".join(b.text for b in msg.content if b.type == "text")
    sources = [{"n": i + 1, "title": c["title"], "url": c["url"],
                "score": round(c.get("rerank_score", 0.0), 3)}
               for i, c in enumerate(chunks)]
    return {"answer": text, "sources": sources}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--groups", default="all",
                    help="comma-separated groups the requesting user belongs to")
    args = ap.parse_args()

    groups = [g.strip() for g in args.groups.split(",") if g.strip()]
    result = answer(args.question, groups)

    print("\n=== ANSWER ===\n")
    print(result["answer"])
    print("\n=== SOURCES ===")
    for s in result["sources"]:
        print(f"  [{s['n']}] {s['title']}  ({s['url']})  rerank={s['score']}")


if __name__ == "__main__":
    main()
