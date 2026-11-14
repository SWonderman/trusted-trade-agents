from datetime import date, datetime


def parse_timestamp(value: str | None) -> datetime | None:
    """
    A Valio Aimo API timestamp such as `2026-11-16T00:00:00+0200`, or None when missing
    or unreadable. Timestamps without an offset are not trusted, since they can't be
    compared with the current time.
    """
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def parse_date(value: str | None) -> date | None:
    """
    A Valio Aimo API date: `2026-11-16`, or the date part of a timestamp.
    """
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None
