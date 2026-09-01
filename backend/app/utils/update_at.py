# TODO: Validate
"""When a record is next wanted."""

import hashlib
from datetime import datetime


# TODO: Validate
def staggered_monthly_update_at(key: str, data_timestamp: datetime) -> datetime:
    seed = hashlib.sha256(key.encode()).digest()
    due = data_timestamp.replace(day=int.from_bytes(seed) % 28 + 1)
    if due > data_timestamp:
        return due
    years, month = divmod(data_timestamp.month, 12)
    return due.replace(year=data_timestamp.year + years, month=month + 1)
