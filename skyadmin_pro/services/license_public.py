"""Ed25519 public key embedded in the desktop client (verify-only).

The matching private key must live only in the Cloudflare Worker
(``LICENSE_ED25519_PRIVATE_KEY_B64``). Clients cannot forge signatures
signed with this key.
"""

from __future__ import annotations

LICENSE_SIGNATURE_ALGORITHM = "Ed25519-v1"
CONTROL_ENVELOPE_V2_PREFIX = "SKYCTRL2:"
PASSCODE_PREFIX = "SKYPASS1:"

# Generated keypair — rotate via Worker secret + app release together.
ED25519_PUBLIC_KEY_HEX = "b9bc4ee341f806f7cdfe698c048fc4b212e8b5ef6ebffcb63bc4d527d136b501"
ED25519_PUBLIC_KEY = bytes.fromhex(ED25519_PUBLIC_KEY_HEX)

LEGACY_FORMAT_SUNSET_MESSAGE = (
    "This activation code uses a retired format. Request a new license or passcode from Sky Creation Innovations."
)
