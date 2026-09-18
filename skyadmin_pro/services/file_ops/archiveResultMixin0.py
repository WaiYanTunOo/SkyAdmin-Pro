from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ArchiveResultMixin0:
    month_folder: Path
    moved_ready: list[str] = field(default_factory=list)
    moved_staging: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def total_moved(self) -> int:
        return len(self.moved_ready) + len(self.moved_staging)
