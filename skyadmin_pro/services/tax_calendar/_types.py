from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Stage:
    start_day: int
    end_day: int
    name: str
    action: str


@dataclass(frozen=True)
class CycleStatus:
    key: str
    cycle: str
    stage: Stage | None
    days_to_next: int
    month_label: str
