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


def get_start_end(date, period):
    if period == "week":
        start = floor_week(date)
        end = start + relativedelta(weeks=1)
    elif period == "month":
        start = floor_month(date)
        end = start + relativedelta(months=1)
    elif period == "year":
        start = floor_year(date)
        end = start + relativedelta(years=1)
    else:
        start = floor_day(date)
        end = start + relativedelta(days=1)

    return start, end


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


def time_travel_dates(user, start_date, end_date):
    if user["start_date"] and start_date:
        user_start_date = datetime.fromtimestamp(user["start_date"], tz=timezone.utc)
        if user_start_date > start_date:
            start_date = user_start_date
    if user["end_date"] and end_date:
        user_end_date = datetime.fromtimestamp(user["end_date"], tz=timezone.utc)
        if user_end_date < end_date:
            end_date = user_end_date

    return start_date, end_date
