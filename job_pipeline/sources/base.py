"""Job source interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Job
from ..profile import Profile


class JobSource(ABC):
    name = "base"

    @abstractmethod
    def fetch(self, profile: Profile, limit: int) -> list[Job]:
        """Return up to `limit` jobs relevant to the profile."""
        raise NotImplementedError
