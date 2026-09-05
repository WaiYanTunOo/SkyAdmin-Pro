"""License module constants."""

from __future__ import annotations

LICENSE_FILENAME = "license.key"
HARDWARE_ID_FILENAME = "hardware.id"
DAILY_SYNC_FILENAME = "last_online_check.txt"
# Everyday online required - customer must be online at least once per 24h
MAX_OFFLINE_SECONDS = 24 * 3600
# Rate limit: max 5 failed activations per 60s
_MAX_ATTEMPTS = 5
_ATTEMPT_WINDOW = 60
