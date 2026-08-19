"""
Complete Auto Repair - Shared sync helpers

Small utilities shared by sync.py (employees + repair orders) and
sync_jobs.py (jobs, labor lines, parts), so the two scripts can't drift
out of sync with each other on timestamp format or date-range logic.
"""

from datetime import date, datetime, timezone


def now():
    """Return the current UTC timestamp as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def previous_year_range():
    """
    Return (start_datetime, end_datetime) as ISO-8601 UTC strings
    covering the previous 12 months through today, in the format
    Tekmetric's API expects.
    """
    today = date.today()

    try:
        start_date = today.replace(year=today.year - 1)
    except ValueError:
        # today is Feb 29 and last year wasn't a leap year.
        start_date = today.replace(year=today.year - 1, day=28)

    start_datetime = f"{start_date.isoformat()}T00:00:00Z"
    end_datetime = f"{today.isoformat()}T23:59:59Z"

    return start_datetime, end_datetime