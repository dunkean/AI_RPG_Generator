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


class PersonColumns:
    """Contiguous structure-of-arrays; structured snapshots are only for diagnostics.

    Live and deceased people keep stable dense IDs. No Python instance is stored
    per person, and storage can stream the columns without repacking all records.
    """

    def __init__(self, capacity):
        self.columns = {name: np.zeros(capacity, DTYPE[name]) for name in DTYPE.names}
        self.capacity = capacity

    def __len__(self):
        return self.capacity

    @property
    def nbytes(self):
        return sum(column.nbytes for column in self.columns.values())

    def __getitem__(self, key):
        if isinstance(key, str):
            return self.columns[key]
        shape = np.shape(next(iter(self.columns.values()))[key])
        snapshot = np.empty(shape, DTYPE)
        for name, column in self.columns.items():
            snapshot[name] = column[key]
        return snapshot

    def reserve(self, capacity, used):
        for name, previous in self.columns.items():
            enlarged = np.zeros(capacity, previous.dtype)
            enlarged[:used] = previous[:used]
            self.columns[name] = enlarged
        self.capacity = capacity


def null_sentinel(field):
    """Unknown identifiers use -1; dates use a value outside allowed calendars."""
    return NO_YEAR if field == "death" else -1
