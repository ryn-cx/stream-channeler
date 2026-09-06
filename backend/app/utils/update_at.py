# TODO: Validate
"""When a record is next wanted."""

import hashlib
from datetime import datetime


# TODO: Validate
def _staggered_update_at(key: str, data_timestamp: datetime, months: int) -> datetime:
    seed = hashlib.sha256(key.encode()).digest()
    due = data_timestamp.replace(day=int.from_bytes(seed) % 28 + 1)
    offset = months - 1 if due > data_timestamp else months
    years, month = divmod(due.month - 1 + offset, 12)
    return due.replace(year=due.year + years, month=month + 1)


# TODO: Validate
def staggered_monthly_update_at(key: str, data_timestamp: datetime) -> datetime:
    return _staggered_update_at(key, data_timestamp, 1)


# TODO: Validate
def title_update_at(
    key: str,
    data_timestamp: datetime,
    last_air_date: datetime | None,
) -> datetime:
    if last_air_date is None:
        return _staggered_update_at(key, data_timestamp, 1)
    years_since_last_episode = (data_timestamp - last_air_date).days // 365
    months = min(max(years_since_last_episode + 1, 1), 12)
    return _staggered_update_at(key, data_timestamp, months)
