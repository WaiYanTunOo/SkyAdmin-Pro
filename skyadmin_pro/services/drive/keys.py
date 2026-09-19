"""Setting keys for customer Google Drive OAuth (Plane B)."""

SETTING_DRIVE_FILES_ENABLED = "drive_files_enabled"
SETTING_DRIVE_REFRESH_TOKEN = "drive_refresh_token_enc"
SETTING_DRIVE_CLIENT_ID = "drive_oauth_client_id"
SETTING_DRIVE_CLIENT_SECRET = "drive_oauth_client_secret_enc"
SETTING_LICENSE_DRIVE_FILES = "license_drive_files"  # "1" when SKU allows Drive
SETTING_LICENSE_WEB = "license_web"
SETTING_LICENSE_SYNC = "license_sync"
SETTING_LICENSE_MAX_DEVICES = "license_max_devices"  # int; 0 = unlimited; empty = unknown
SETTING_LICENSE_ORG_ID = "license_org_id"  # firm org_id from sync register
