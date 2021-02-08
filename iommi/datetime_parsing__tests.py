from datetime import (
    date,
    datetime,
    timedelta,
)

import freezegun
import pytest

from iommi._web_compat import ValidationError
from iommi.datetime_parsing import (
    parse_relative_date,
    parse_relative_datetime,
)

fake_now = datetime(2018, 2, 5, 7, 11, 13, 17)


@pytest.fixture(autouse=True)
def frozen_time():
    with freezegun.freeze_time(
        fake_now,
        ignore=[
            'tri.cassandra',
            '_pytest.terminal',
            '_pytest.runner',
            'selenium',
        ],
    ) as f:
        yield f


@pytest.mark.parametrize(
    'value, message',
    [
        ('foo days', '"foo days" is not a valid relative date. "foo " is not an integer.'),
        ('10000 days', '"10000 days" is not a valid relative date. 10000 is too big (max is 9999).'),
        ('2000 weeks', '"2000 weeks" is not a valid relative date. 2000 is too big (max is 1999).'),
        ('500 months', '"500 months" is not a valid relative date. 500 is too big (max is 499).'),
        ('167 quarters', '"167 quarters" is not a valid relative date. 167 is too big (max is 166).'),
        ('400 years', '"400 years" is not a valid relative date. 400 is too big (max is 399).'),
    ],
)
def test_parse_relative_date_error_conditions(value, message):
    with pytest.raises(ValidationError) as e:
        parse_relative_date(value)

    assert e.value.message == message


def test_parse_relative_date_error_condition_no_match():
    assert parse_relative_date('foo') is None
    assert parse_relative_datetime('foo') is None


def test_parse_relative_datetime():
    assert parse_relative_datetime('now') == datetime.now()


def test_parse_relative_date_relative():
    today = date.today()

    # past
    assert parse_relative_date('yesterday') == (today - timedelta(days=1))
    assert parse_relative_date('5 days ago') == (today - timedelta(days=5))
    assert parse_relative_date('5 day_ago') == (
        today - timedelta(days=5)
    )  # Weird, but the code was written for this case, so let's test it
    assert parse_relative_date('5 weekdays ago') == (today - timedelta(days=7))
    assert parse_relative_date('1 week ago') == (today - timedelta(days=7))
    assert parse_relative_date('1 month ago') == (today - timedelta(days=31))
    assert parse_relative_date('1 year ago') == (today - timedelta(days=365))
    assert parse_relative_date('1 quarter ago') == date(2017, 11, 5)

    # present
    assert parse_relative_date('today') == today

    # future
    assert parse_relative_date('tomorrow') == (today + timedelta(days=1))
    assert parse_relative_date('8 days') == (today + timedelta(days=8))
    assert parse_relative_date('8 weekdays') == (today + timedelta(days=10))
    assert parse_relative_date('1 week') == (today + timedelta(days=7))
    assert parse_relative_date('1 month') == (today + timedelta(days=28))
    assert parse_relative_date('1 year') == (today + timedelta(days=365))
    assert parse_relative_date('1 quarter') == date(2018, 5, 5)
    assert parse_relative_date('6 quarter') == date(2019, 8, 5)

    # start_date is ignored for "today"
    assert parse_relative_date('today', start_date=date(2020, 3, 5)) == today

    # using start_date
    assert parse_relative_date('1d', start_date=date(2020, 3, 5)) == date(2020, 3, 6)

    # negative
    assert parse_relative_date('-1 year') == (today - timedelta(days=365))

    # synonyms for weekday
    assert parse_relative_date('5 weekday ago') == (today - timedelta(days=7))
    assert parse_relative_date('5 wd ago') == (today - timedelta(days=7))
    assert parse_relative_date('5 bankday ago') == (today - timedelta(days=7))
    assert parse_relative_date('5 bankdays ago') == (today - timedelta(days=7))
    assert parse_relative_date('5 bd ago') == (today - timedelta(days=7))

    # synonyms for day
    assert parse_relative_date('8 d') == (today + timedelta(days=8))
    assert parse_relative_date('8 day') == (today + timedelta(days=8))

    # synonyms for week
    assert parse_relative_date('1 w') == (today + timedelta(days=7))
    assert parse_relative_date('1 wk') == (today + timedelta(days=7))
    assert parse_relative_date('1 weeks') == (today + timedelta(days=7))

    # synonyms for month
    assert parse_relative_date('1 m') == (today + timedelta(days=28))
    assert parse_relative_date('1 mo') == (today + timedelta(days=28))
    assert parse_relative_date('1 mon') == (today + timedelta(days=28))
    assert parse_relative_date('1 months') == (today + timedelta(days=28))

    # synonyms for quarter
    assert parse_relative_date('1 q') == date(2018, 5, 5)
    assert parse_relative_date('1 quarters') == date(2018, 5, 5)

    # synonyms for year
    assert parse_relative_date('1 y') == (today + timedelta(days=365))
    assert parse_relative_date('1 yr') == (today + timedelta(days=365))
    assert parse_relative_date('1 years') == (today + timedelta(days=365))


def test_parse_relative_date_weekdays():
    with freezegun.freeze_time('2018-02-02'):  # a friday
        assert parse_relative_date('1 weekday') == (date.today() + timedelta(days=3))

    with freezegun.freeze_time('2018-02-03'):  # a saturday
        assert parse_relative_date('1 weekday') == (date.today() + timedelta(days=2))

    with freezegun.freeze_time('2018-02-04'):  # a sunday
        assert parse_relative_date('1 weekday') == (date.today() + timedelta(days=1))

    with freezegun.freeze_time('2018-02-03'):  # a saturday
        assert parse_relative_date('1 weekday ago') == date(2018, 2, 2)

    with freezegun.freeze_time('2018-02-04'):  # a sunday
        assert parse_relative_date('1 weekday ago') == date(2018, 2, 2)


def test_parse_relative_date_month_overflow():
    assert parse_relative_date('1 month', start_date=date(2018, 1, 31)) == date(2018, 2, 28)


def test_parse_relative_date_leap_year_overflow():
    assert parse_relative_date('1 year', start_date=date(2020, 2, 29)) == date(2021, 2, 28)
