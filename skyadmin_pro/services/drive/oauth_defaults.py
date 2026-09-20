"""Vendor Google OAuth Desktop client (public client ID only).

Paste the Client ID from Google Cloud Console → Credentials → Desktop client
into BUNDLED_GOOGLE_OAUTH_CLIENT_ID (or set GOOGLE_OAUTH_CLIENT_ID at runtime).
Never commit a client secret — desktop flow uses PKCE.
"""

from __future__ import annotations

# Public OAuth client ID for SkyAdmin Pro (Desktop). PKCE — no secret in the binary.
BUNDLED_GOOGLE_OAUTH_CLIENT_ID = "536398687838-6287se76cktmjh8lf9cejs5otv8pq7fb.apps.googleusercontent.com"
