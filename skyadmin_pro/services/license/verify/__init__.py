from skyadmin_pro.services.license.machine import live_machine_id as get_machine_id

from .chunk_1 import (
    _is_repair_activation,
    _license_paths,
    _saved_license_text,
    _self_heal_license,
    _shadow_path,
    find_license_file,
)
from .chunk_2 import _parse_expiry, _payload_of, _read_license_payload
from .chunk_3 import (
    _fetch_control_from_api,
    license_countdown_text,
    license_remaining_days,
    license_time_left_text,
    used_nonces,
)
from .chunk_4 import (
    _control_paths,
    _parse_control_lines,
    _replace_control_file,
    banned_machines,
    mark_used,
    revoked_passcodes,
)
from .chunk_5 import _apply_control_list
from .chunk_6 import _fetch_control_from_gist, fetch_revocations
from .chunk_7 import _verify_parsed_license, revoked_nonces
from .chunk_8 import verify_key_text
from .chunk_9 import license_status_text, read_update_info, verify_license
from .chunk_10 import (
    _version_tuple,
    available_update,
    check_for_updates,
    generate_license,
    is_newer_version,
    save_license_file,
    verify_passcode,
)
from .chunk_11 import _verify_integrity, generate_passcode, license_expiry_text
from .chunk_12 import check_activation_usable, report_activation_claim
from .chunk_13 import activation_request_message
