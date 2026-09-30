"""Shared compact person fields and sentinels for memory and archive storage."""

import numpy as np

NO_YEAR = np.iinfo(np.int32).min
STORED_FIELDS = (
    ("sex", "u1", False),
    ("birth", "i4", False),
    ("death", "i4", True),
    ("father", "i4", True),
    ("mother", "i4", True),
    ("birth_place", "i4", False),
    ("place", "i4", False),
    ("death_place", "i4", True),
    ("family", "i4", False),
    ("status", "u1", False),
    ("activity", "i2", False),
    ("race", "i2", False),
)
RUNTIME_FIELDS = (
    ("partner", "i4"),
    ("union", "i4"),
    ("last_birth", "i4"),
    ("eligible_year", "i4"),
    ("place_slot", "i4"),
)
DTYPE = np.dtype([(name, dtype) for name, dtype, _ in STORED_FIELDS] + list(RUNTIME_FIELDS))


def null_sentinel(field):
    """Unknown identifiers use -1; dates use a value outside allowed calendars."""
    return NO_YEAR if field == "death" else -1
