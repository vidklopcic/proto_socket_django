import zoneinfo
from datetime import datetime

from django.utils import timezone


def to_timestamp(dt: timezone.datetime | datetime.date) -> int | None:
    if dt is None:
        return None
    if not hasattr(dt, 'timestamp'):
        dt = timezone.datetime(dt.year, dt.month, dt.day)
    return int(dt.timestamp() * 1000)


def from_timestamp(ts) -> timezone.datetime | None:
    if ts is None:
        return None
    return timezone.datetime.fromtimestamp(ts / 1000, tz=zoneinfo.ZoneInfo('UTC'))
