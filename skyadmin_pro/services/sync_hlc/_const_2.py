from __future__ import annotations

import re

_HLC_RE = re.compile(r"^(\d{1,15})-(\d{1,9})-([A-Z0-9]{1,32})$")
