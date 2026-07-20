"""Permission handling — the part in-house RAG builds most often get wrong.

Two responsibilities:
  1. Ingestion: stamp each chunk with the groups allowed to see it (`acl_groups`).
  2. Query:     turn the requesting user's groups into a Vespa filter so restricted
                chunks are never even retrieved (not just hidden after the fact).

In production, replace `groups_for_document` with a real lookup against the source
system's permissions (Confluence space perms, Drive sharing, GitHub team access...).
"""
from typing import List


def groups_for_document(source: str, metadata: dict, default_groups: List[str]) -> List[str]:
    """Resolve the ACL for one source document.

    Scaffold behavior: fall back to the groups passed on the CLI. Wire real
    permission resolution here per source, e.g.:

        if source == "confluence":
            return confluence_space_groups(metadata["space_key"])
        if source == "drive":
            return drive_shared_with_groups(metadata["file_id"])
    """
    return default_groups or ["all"]


def vespa_acl_filter(user_groups: List[str]) -> str:
    """YQL fragment that keeps only chunks the user is allowed to see.

    `acl_groups` is an array<string>; "user is in any allowed group" is expressed
    as an OR of contains clauses. Returns a condition to AND into a WHERE clause.
    """
    if not user_groups:
        # No groups => can only see fully public docs.
        user_groups = ["all"]
    clauses = " or ".join(f'acl_groups contains "{g}"' for g in user_groups)
    return f"({clauses})"
