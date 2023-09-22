import zoneinfo
from datetime import datetime
from typing import Optional, Union

from django.utils import timezone


def to_timestamp(dt: Union[timezone.datetime, datetime.date]) -> Optional[int]:
    if dt is None:
        return None
    if not hasattr(dt, 'timestamp'):
        dt = timezone.datetime(dt.year, dt.month, dt.day)
    return int(dt.timestamp() * 1000)


def from_timestamp(ts) -> Optional[timezone.datetime]:
    if ts is None:
        return None
    return timezone.datetime.fromtimestamp(ts / 1000, tz=zoneinfo.ZoneInfo('UTC'))
