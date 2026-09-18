from __future__ import annotations

import http.client
import urllib.error
import urllib.request

_NETWORK_ERRORS = (
    urllib.error.URLError,
    http.client.HTTPException,
    OSError,
    TimeoutError,
    ValueError,
)
