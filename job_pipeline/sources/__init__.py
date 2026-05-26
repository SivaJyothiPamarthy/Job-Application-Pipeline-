"""Pluggable job sources. Add a new source by implementing JobSource."""

from .apify import ApifySource
from .base import JobSource
from .platsbanken import PlatsbankenSource
from .sample import SampleSource
from .websearch import WebSearchSource


def get_source(name: str) -> JobSource:
    name = (name or "sample").lower()
    if name in ("platsbanken", "jobtech", "live"):
        return PlatsbankenSource()
    if name in ("apify", "linkedin"):
        return ApifySource()
    if name in ("websearch", "web", "search"):
        return WebSearchSource()
    if name == "sample":
        return SampleSource()
    raise ValueError(f"Unknown source '{name}'. Options: platsbanken, apify, websearch, sample")


__all__ = [
    "JobSource",
    "PlatsbankenSource",
    "ApifySource",
    "WebSearchSource",
    "SampleSource",
    "get_source",
]
