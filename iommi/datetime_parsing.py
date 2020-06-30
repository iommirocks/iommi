from datetime import (
    date,
    datetime,
    timedelta,
)

from iommi._web_compat import ValidationError


def parse_relative_datetime(s, start_date=None):
    result = parse_relative_date(s, start_date=start_date)
    if result is None:
        return None
    return datetime.combine(result, datetime.now().time())


def parse_relative_date(s, start_date=None):
    period = s.strip()
    weekday_symbols = ['wd', 'weekday', 'weekdays', 'bd', 'bankday', 'bankdays']
    day_symbols = ['d', 'day', 'days']
    week_symbols = ['w', 'wk', 'week', 'weeks']
    month_symbols = ['m', 'mo', 'mon', 'month', 'months']
    quarter_symbols = ['q', 'quarter', 'quarters']
    year_symbols = ['y', 'yr', 'year', 'years']
    period_symbols = weekday_symbols + day_symbols + week_symbols + month_symbols + quarter_symbols + year_symbols
    neg = False
    period = period.lower()
    if period in ('today', 'now'):
        period = '0d'
        start_date = None
    elif period == 'yesterday':
        period = '-1d'
        start_date = None
    elif period == 'tomorrow':
        period = '1d'
        start_date = None
    if period.endswith('ago'):
        period = period[:-len('ago')].strip()
        neg = True
        if period.endswith('_'):
            period = period[:-1]

    sym = None
    for symbol in period_symbols:
        if period.endswith(symbol):
            period = period[:-len(symbol)]
            sym = symbol
            break
    d = None
    if sym:
        try:
            count = int(period)
        except ValueError:
            raise ValidationError(f'"{s}" is not a valid relative date. "{period}" is not an integer.')
        if neg:
            count = -count
        if start_date:
            today = start_date
        else:
            today = date.today()
        day = today.day
        month = today.month
        year = today.year
        if sym in day_symbols:
            if count >= 10000:
                raise ValidationError(f'"{s}" is not a valid relative date. {count} is too big (max is 9999).')
            d = today + timedelta(days=count)
        elif sym in week_symbols:
            if count >= 2000:
                raise ValidationError(f'"{s}" is not a valid relative date. {count} is too big (max is 1999).')
            d = today + timedelta(weeks=count)
        elif sym in month_symbols or sym in quarter_symbols:
            if sym in quarter_symbols:
                if count >= 167:
                    raise ValidationError(f'"{s}" is not a valid relative date. {count} is too big (max is 166).')
                count *= 3
            if count >= 500:
                raise ValidationError(f'"{s}" is not a valid relative date. {count} is too big (max is 499).')
            month += count
            if month < 1 or month > 12:
                (y, m) = divmod(month - 1, 12)
                year += y
                month = m + 1
            valid = False
            while not valid:
                try:
                    d = date(year, month, day)
                    valid = True
                except ValueError:
                    day -= 1

        elif sym in year_symbols:
            if count >= 400:
                raise ValidationError(f'"{s}" is not a valid relative date. {count} is too big (max is 399).')
            year += count
            valid = False
            while not valid:
                try:
                    d = date(year, month, day)
                    valid = True
                except ValueError:
                    day -= 1
        elif sym in weekday_symbols:
            weeks, days = divmod(count, 5)
            d = today
            weekday = d.weekday()
            if weekday in [5, 6]:
                d -= timedelta(days=weekday - 4)
                weekday = 4
            if weeks:
                d += timedelta(days=weeks * 7)
            if days:
                d += timedelta(days=days)
            new_weekday = d.weekday()
            if new_weekday in [5, 6] or new_weekday < weekday:
                d += timedelta(days=2)

    return d
