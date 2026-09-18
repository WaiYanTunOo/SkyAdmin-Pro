from __future__ import annotations

from typing import Any

try:  # Fail-closed at connect time if the driver is missing (see driver()).
    from sqlcipher3.dbapi2 import Connection as CipherConnection
    from sqlcipher3.dbapi2 import DatabaseError as CipherDatabaseError
    from sqlcipher3.dbapi2 import Error as CipherError
    from sqlcipher3.dbapi2 import IntegrityError as CipherIntegrityError
    from sqlcipher3.dbapi2 import OperationalError as CipherOperationalError
    from sqlcipher3.dbapi2 import ProgrammingError as CipherProgrammingError
    from sqlcipher3.dbapi2 import Row as CipherRow

    HAS_CIPHER = True
except ImportError:  # pragma: no cover — production always has the driver.
    CipherConnection = Any  # type: ignore[assignment,misc]
    CipherDatabaseError = Exception  # type: ignore[assignment,misc]
    CipherError = Exception  # type: ignore[assignment,misc]
    CipherIntegrityError = Exception  # type: ignore[assignment,misc]
    CipherOperationalError = Exception  # type: ignore[assignment,misc]
    CipherProgrammingError = Exception  # type: ignore[assignment,misc]
    CipherRow = Any  # type: ignore[assignment,misc]
    HAS_CIPHER = False
