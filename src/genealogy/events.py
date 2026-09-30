"""Batch event buffers: numeric columns stay native until an explicit SQL export."""

import numpy as np


class EventBuffer:
    def __init__(self, reason_index=-1):
        self.reason_index = reason_index
        self.chunks = []
        self.count = 0

    def append(self, row):
        self.chunks.append((None, row))
        self.count += 1

    def extend(self, rows):
        for row in rows:
            self.append(row)

    def batch(self, columns, reason=None):
        array = np.asarray(columns, dtype=np.int32)
        self.chunks.append((array, reason))
        self.count += len(array)

    def __len__(self):
        return self.count

    def __iter__(self):
        for array, reason in self.chunks:
            if array is None:
                yield reason
            else:
                for row in array.tolist():
                    if reason is not None:
                        row.insert(
                            self.reason_index if self.reason_index >= 0 else len(row), reason
                        )
                    yield tuple(row)

    def numeric(self, reasons=None):
        """Encode categorical reasons once per batch; no object per event."""
        chunks = []
        for array, reason in self.chunks:
            if array is None:
                row = list(reason)
                if reasons is not None:
                    reason = row.pop(self.reason_index)
                    row.append(reasons[reason])
                chunks.append(np.asarray([row], dtype=np.int32))
            elif reasons is None:
                chunks.append(array)
            else:
                chunks.append(np.column_stack((array, np.full(len(array), reasons[reason]))))
        return np.concatenate(chunks) if chunks else None
