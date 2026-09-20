"""
Application constants, default settings, and UI copy.

Re-exports every public name from the sub-modules so that
``from skyadmin_pro.config import X`` continues to work unchanged.
The name sets are pinned in ``config/_exports_{a,b,c,d}`` and app identity
lives in ``config/_app``.
"""

from skyadmin_pro.config._app import (
    APP_NAME,
    APP_TAGLINE,
    APP_VERSION,
    DEFAULT_APPEARANCE_MODE,
    DEFAULT_COLOR_THEME,
)
from skyadmin_pro.config._exports_a import *
from skyadmin_pro.config._exports_b import *
from skyadmin_pro.config._exports_c import *
from skyadmin_pro.config._exports_d import *
from skyadmin_pro.config._exports_e import *
