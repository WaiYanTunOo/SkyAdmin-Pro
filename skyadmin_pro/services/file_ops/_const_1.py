from __future__ import annotations

import re

_UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*]+')
