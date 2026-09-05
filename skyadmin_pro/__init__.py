"""SkyAdmin Pro — offline desktop workflow for corporate services administrators."""

# Canonical version lives in pyproject.toml (read at runtime as config.APP_VERSION).
# This alias is kept for tooling that expects __version__; it must not drift.
from .config import APP_VERSION as __version__  # noqa: N811

__app_name__ = "SkyAdmin Pro"
