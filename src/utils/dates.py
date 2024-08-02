from datetime import datetime, timezone

from dateutil.relativedelta import relativedelta


def floor_day(date):
    return date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)


def floor_week(date):
    return ((date - relativedelta(days=date.weekday()))
            .replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc))


def floor_month(date):
    return date.replace(day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)


def floor_year(date):
    return date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)


def now():
    return datetime.now(timezone.utc)


def count_unique_dates(start, end):
    start_date = datetime.fromtimestamp(start, tz=timezone.utc)
    end_date = datetime.fromtimestamp(end, tz=timezone.utc)

    unique_dates = set()

    while start_date <= end_date:
        unique_dates.add(start_date.strftime("%m-%d-%Y"))
        start_date += relativedelta(days=1)

    return len(unique_dates)
