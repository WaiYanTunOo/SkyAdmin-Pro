from __future__ import annotations

from datetime import date

from ._const_3 import _CYCLE_ORDER
from ._types import CycleStatus, Stage


def _days_in_month(year: int, month: int) -> int:
    import calendar

    return calendar.monthrange(year, month)[1]


def _current_stage(stages: tuple[Stage, ...], day: int) -> Stage | None:
    for stage in stages:
        if stage.start_day <= day <= stage.end_day:
            return stage
    return None


def monthly_cycle_status(today: date | None = None) -> tuple[CycleStatus, ...]:
    today = today or date.today()
    day = today.day
    days_this_month = _days_in_month(today.year, today.month)
    # Next month's length (for cycles whose next stage falls across the month
    # boundary) and the gap to the 1st of the next month.
    if today.month == 12:
        days_next_month = _days_in_month(today.year + 1, 1)
    else:
        days_next_month = _days_in_month(today.year, today.month + 1)
    gap_to_next_month = days_this_month - day + 1  # e.g. day 30 of 31 → 2
    month_label = today.strftime("%B %Y")
    results = []
    for cycle, key, stages in _CYCLE_ORDER:
        stage = _current_stage(stages, day)
        days_to_next = 0
        if stage is not None:
            remaining = stage.end_day - day
            if remaining >= 0:
                days_to_next = remaining
            # else: stage end clamped past month end (payroll "30-31" in a
            # 30-day month) spills into the 1st — nothing left this month.
        else:
            upcoming = [s for s in stages if s.start_day > day]
            if upcoming:
                days_to_next = upcoming[0].start_day - day
            else:
                # All stages passed — count the wrap to next month's first.
                days_to_next = gap_to_next_month + min(stages[0].start_day - 1, days_next_month)
        results.append(
            CycleStatus(
                key=key,
                cycle=cycle,
                stage=stage,
                days_to_next=days_to_next,
                month_label=month_label,
            )
        )
    return tuple(results)
