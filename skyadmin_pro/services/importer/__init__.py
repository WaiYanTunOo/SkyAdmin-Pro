"""CSV import for clients — validate, deduplicate, and batch insert."""

from __future__ import annotations

from ._const_0 import logger
from ._const_1 import _REQUIRED_COLUMNS
from ._const_2 import _OPTIONAL_COLUMNS
from .funcs import _import_clients_from_csv_p1, import_clients_from_csv
