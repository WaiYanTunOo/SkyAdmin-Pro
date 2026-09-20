"""Setting keys for customer Google Drive OAuth (Plane B).

Shared license/drive-setting keys are single-sourced in
``skyadmin_pro.config.licensing`` and re-exported here for import stability.
Only Drive-OAuth/org-id unique keys are defined in this module.
"""

from skyadmin_pro.config import (
    SETTING_DRIVE_FILES_ENABLED as SETTING_DRIVE_FILES_ENABLED,
)
from skyadmin_pro.config import (
    SETTING_LICENSE_DRIVE_FILES as SETTING_LICENSE_DRIVE_FILES,
)
from skyadmin_pro.config import (
    SETTING_LICENSE_MAX_DEVICES as SETTING_LICENSE_MAX_DEVICES,
)
from skyadmin_pro.config import (
    SETTING_LICENSE_ORG_ID as SETTING_LICENSE_ORG_ID,
)
from skyadmin_pro.config import (
    SETTING_LICENSE_SYNC as SETTING_LICENSE_SYNC,
)
from skyadmin_pro.config import (
    SETTING_LICENSE_WEB as SETTING_LICENSE_WEB,
)

SETTING_DRIVE_REFRESH_TOKEN = "drive_refresh_token_enc"
SETTING_DRIVE_CLIENT_ID = "drive_oauth_client_id"
SETTING_DRIVE_CLIENT_SECRET = "drive_oauth_client_secret_enc"
