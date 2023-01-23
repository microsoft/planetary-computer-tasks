from datetime import datetime

from dateutil.tz import tzutc


def tzutc_now() -> datetime:
    """Consistent timezone-aware UTC timestamp for record models that are
    serialized for API responses."""
    return datetime.now(tzutc())
