# Owned-Retrieval RAG Scaffold

A production-shaped starter for **self-hosted, permission-aware RAG** over internal
company documents. Built for a team that wants to **own the retrieval stack** rather
than buy a turnkey platform.

**Stack:** Vespa (vector + BM25 engine) · LlamaIndex (ingestion) · BGE-M3 (multilingual
embeddings) · BGE-reranker-v2 · Claude (generation).

```
Query
  → BM25 top-20  +  Vector top-20      (hybrid retrieval)
  → RRF merge → top-30 unique
  → Reranker → top 5-10                (biggest quality lever)
  → Claude (answer + citations)
```

Every chunk carries an `acl_groups` field and retrieval is **filtered by the requesting
user's groups at query time** — this is the #1 thing in-house RAG builds get wrong.

---

## 1. Prerequisites

- Docker + Docker Compose (to run Vespa locally)
- Python 3.10+
- ~4 GB RAM free for the embedding + reranker models (they download on first run)
- An Anthropic API key for the generation step

## 2. Setup

```bash
cd rag-scaffold
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env      # then edit .env and add your ANTHROPIC_API_KEY
```

## 3. Start Vespa and deploy the schema

```bash
docker compose up -d                 # starts Vespa on :8080 (config on :19071)
python -m app.deploy                 # deploys vespa/ application package
```

Wait until `python -m app.deploy` prints `Vespa is ready`.

## 4. Ingest documents

Drop files (`.md`, `.txt`, `.pdf`, `.html`) into `./data/` and run:

```bash
python -m app.ingest ./data --source confluence --acl eng,all
```

`--acl` sets which groups may retrieve these docs. In production you'd pull the real
ACL per document from the source system (Confluence space perms, Drive sharing, etc.)
instead of passing a flag — see `app/acl.py`.

## 5. Query

```bash
# The --groups flag simulates the requesting user's group membership.
python -m app.query "How do I roll back a shader cache build?" --groups eng,all
```

You'll get an answer with inline `[1][2]` citations and the source list.

## 6. Evaluate (do this early!)

The difference between an in-house RAG that ships and one that quietly fails is **eval
discipline**. Build a small golden set *before* you tune chunking or prompts.

```bash
cp eval/eval_set.example.jsonl eval/eval_set.jsonl   # then add your real Q/A pairs
python -m eval.run_eval
```

---

## Project layout

```
rag-scaffold/
├── docker-compose.yml        # Vespa container
├── requirements.txt
├── .env.example
├── config.py                 # all tunables in one place
├── vespa/
│   ├── services.xml          # Vespa app: one content cluster
│   └── schemas/document.sd   # doc schema: bm25 + embedding tensor + acl_groups
├── app/
│   ├── deploy.py             # deploy the app package to Vespa
│   ├── embeddings.py         # BGE-M3 multilingual embedder
│   ├── reranker.py           # BGE cross-encoder reranker
│   ├── acl.py                # per-document permission resolution
│   ├── ingest.py             # LlamaIndex load → chunk → embed → feed to Vespa
│   ├── retrieval.py          # BM25 + vector search, RRF merge, rerank
│   └── query.py              # end-to-end: retrieve → Claude → cited answer
└── eval/
    ├── eval_set.example.jsonl
    └── run_eval.py           # RAGAS-style hit-rate / MRR on your golden set
```

## Where to go next

- **Connectors:** replace the filesystem loader in `app/ingest.py` with LlamaIndex
  readers for Confluence, Jira, Slack, Drive, GitHub. Carry the source's real ACL
  into `acl_groups`.
- **Scale:** this runs single-node Vespa. For production, move to a multi-node Vespa
  content cluster and raise redundancy in `services.xml`.
- **Agentic retrieval:** add a re-retrieve loop only for hard multi-hop questions
  once your eval score on single-pass retrieval is solid.
- **Swap the generator:** `app/query.py` isolates the LLM call; swap Claude for any
  model without touching retrieval.
