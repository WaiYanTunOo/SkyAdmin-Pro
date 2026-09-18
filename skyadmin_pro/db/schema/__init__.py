"""SQLite schema DDL."""

from __future__ import annotations

from ._schema_sql_0 import SCHEMA_SQL_PART_0
from ._schema_sql_1 import SCHEMA_SQL_PART_1
from ._schema_sql_2 import SCHEMA_SQL_PART_2
from ._schema_sql_3 import SCHEMA_SQL_PART_3
from ._schema_sql_4 import SCHEMA_SQL_PART_4
from ._schema_sql_5 import SCHEMA_SQL_PART_5

SCHEMA_SQL = (
    SCHEMA_SQL_PART_0
    + SCHEMA_SQL_PART_1
    + SCHEMA_SQL_PART_2
    + SCHEMA_SQL_PART_3
    + SCHEMA_SQL_PART_4
    + SCHEMA_SQL_PART_5
)
