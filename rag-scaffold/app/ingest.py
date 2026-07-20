"""Ingestion: load documents with LlamaIndex, chunk, embed, feed to Vespa.

Usage:
    python -m app.ingest ./data --source confluence --acl eng,all

Swap SimpleDirectoryReader for LlamaIndex's Confluence/Jira/Slack/Drive/GitHub
readers to ingest from real source systems. When you do, carry each document's
real permissions into acl_groups via app.acl.groups_for_document.
"""
import argparse
import hashlib
from typing import Dict, List

from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter

from config import CHUNK_OVERLAP, CHUNK_SIZE
from app import vespa_client
from app.acl import groups_for_document
from app.embeddings import embed


def _chunk_id(doc_id: str, i: int) -> str:
    return hashlib.sha1(f"{doc_id}:{i}".encode()).hexdigest()


def build_chunks(path: str, source: str, default_groups: List[str]) -> List[Dict]:
    docs = SimpleDirectoryReader(path, recursive=True).load_data()
    splitter = SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

    chunks: List[Dict] = []
    for doc in docs:
        meta = doc.metadata or {}
        doc_name = meta.get("file_name", meta.get("file_path", "unknown"))
        acl = groups_for_document(source, meta, default_groups)
        nodes = splitter.get_nodes_from_documents([doc])
        texts = [n.get_content() for n in nodes]
        vectors = embed(texts) if texts else []
        for i, (node, vec) in enumerate(zip(nodes, vectors)):
            chunks.append({
                "doc_id": _chunk_id(doc_name, i),
                "title": doc_name,
                "content": node.get_content(),
                "url": meta.get("file_path", doc_name),
                "source": source,
                "lang": meta.get("lang", "en"),
                "acl_groups": acl,
                "embedding": vec,
            })
    return chunks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="directory of documents to ingest")
    ap.add_argument("--source", default="filesystem", help="source system label")
    ap.add_argument("--acl", default="all",
                    help="comma-separated groups allowed to see these docs")
    args = ap.parse_args()

    groups = [g.strip() for g in args.acl.split(",") if g.strip()]
    chunks = build_chunks(args.path, args.source, groups)
    print(f"Built {len(chunks)} chunks from {args.path} (acl={groups}).")
    vespa_client.feed(chunks)


if __name__ == "__main__":
    main()
