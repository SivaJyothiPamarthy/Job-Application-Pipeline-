"""Pluggable job sources. Add a new source by implementing JobSource."""

from .base import JobSource
from .platsbanken import PlatsbankenSource
from .sample import SampleSource


def get_source(name: str) -> JobSource:
    name = (name or "sample").lower()
    if name in ("platsbanken", "jobtech", "live"):
        return PlatsbankenSource()
    if name == "sample":
        return SampleSource()
    raise ValueError(f"Unknown source '{name}'. Options: platsbanken, sample")


__all__ = ["JobSource", "PlatsbankenSource", "SampleSource", "get_source"]
