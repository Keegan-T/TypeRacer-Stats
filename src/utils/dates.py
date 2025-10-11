from datetime import datetime, timezone

from dateutil import parser
from dateutil.relativedelta import relativedelta

from utils import strings


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


def parse_date(string):
    if string in ["now", "present", "today"]:
        date = now()
    elif string == "until":
        date = datetime.fromtimestamp(0, tz=timezone.utc)
    else:
        try:
            date = parser.parse(string).replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    return date


def set_command_date_range(args, user):
    start_date = None
    end_date = None
    dates = 0
    shorthands = ["yesterday", "day", "week", "month", "year"]
    _now = now()

    for arg in args[::-1]:
        date = strings.get_category(shorthands, arg)
        if date:
            if "day" in date:
                start_date = floor_day(_now)
                if date == "yesterday":
                    start_date -= relativedelta(days=1)
                end_date = start_date + relativedelta(days=1)
            elif date == "week":
                start_date = floor_week(_now)
                end_date = start_date + relativedelta(weeks=1)
            elif date == "month":
                start_date = floor_month(_now)
                end_date = start_date + relativedelta(months=1)
            elif date == "year":
                start_date = floor_year(_now)
                end_date = start_date + relativedelta(years=1)

            end_date -= relativedelta(microseconds=1)
            user["start_date"] = start_date.timestamp()
            user["end_date"] = end_date.timestamp()
            args = args[:-1]

            return args, user

        if (arg.isalpha() or arg.isnumeric()) and arg not in ["now", "present", "today", "until"]:
            date = None
        else:
            date = parse_date(arg)
        if date:
            if not start_date:
                start_date = date
            else:
                end_date = start_date
                start_date = date
            dates += 1
            if dates == 2:
                break

    if dates == 0:
        return args, user

    args = args[:-dates]

    if start_date:
        if end_date:
            if start_date.timestamp() > end_date.timestamp():
                start_date, end_date = end_date, start_date
            if floor_day(end_date) > floor_day(_now):
                end_date = None
            else:
                end_date = end_date.timestamp()
        if floor_day(start_date) > floor_day(_now):
            start_date = None
        else:
            start_date = start_date.timestamp()

    user["start_date"] = start_date
    user["end_date"] = end_date

    return args, user
