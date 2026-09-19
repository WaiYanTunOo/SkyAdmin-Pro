"""Appointments domain (Dashboard Calendar — local-only v1)."""

from __future__ import annotations

from .list_a import AppointmentsListMixin
from .mutate_a import AppointmentsMutateMixin


class AppointmentsMixin(AppointmentsListMixin, AppointmentsMutateMixin):
    pass


__all__ = ["AppointmentsMixin"]
