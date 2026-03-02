from datetime import date

from django.test import RequestFactory

from iommi.experimental.calendar import (
    Calendar,
    CalendarDay,
    CalendarEvent,
)
from iommi.struct import Struct
from tests.helpers import req


class Event:
    def __init__(self, name, event_date, pk=None):
        self.name = name
        self.event_date = event_date
        self.pk = pk

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f'/events/{self.pk}/'


def make_events():
    return [
        Event('Meeting', date(2026, 3, 5), pk=1),
        Event('Lunch', date(2026, 3, 5), pk=2),
        Event('Workshop', date(2026, 3, 15), pk=3),
        Event('Conference', date(2026, 4, 1), pk=4),  # next month
    ]


def test_basic_rendering():
    events = make_events()
    cal = Calendar(
        rows=events,
        event__attr='event_date',
        year=2026,
        month=3,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    html = bound.__html__()

    assert 'March 2026' in html
    assert 'Meeting' in html
    assert 'Lunch' in html
    assert 'Workshop' in html
    # Conference is April 1, which is visible in the March grid
    assert 'Conference' in html


def test_weekday_headers():
    cal = Calendar(
        rows=[],
        event__attr='event_date',
        year=2026,
        month=3,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    html = bound.__html__()

    for day_name in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']:
        assert day_name in html


def test_navigation_links():
    cal = Calendar(
        rows=[],
        event__attr='event_date',
        year=2026,
        month=3,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    html = bound.__html__()

    assert 'Prev' in html
    assert 'Next' in html


def test_prev_next_url():
    cal = Calendar(
        rows=[],
        event__attr='event_date',
        year=2026,
        month=3,
    ).refine_done()

    bound = cal.bind(request=req('get'))

    prev_url = bound.get_prev_url()
    assert 'year=2026' in prev_url
    assert 'month=2' in prev_url

    next_url = bound.get_next_url()
    assert 'year=2026' in next_url
    assert 'month=4' in next_url


def test_prev_url_year_boundary():
    cal = Calendar(
        rows=[],
        event__attr='event_date',
        year=2026,
        month=1,
    ).refine_done()

    bound = cal.bind(request=req('get'))

    prev_url = bound.get_prev_url()
    assert 'year=2025' in prev_url
    assert 'month=12' in prev_url


def test_next_url_year_boundary():
    cal = Calendar(
        rows=[],
        event__attr='event_date',
        year=2026,
        month=12,
    ).refine_done()

    bound = cal.bind(request=req('get'))

    next_url = bound.get_next_url()
    assert 'year=2027' in next_url
    assert 'month=1' in next_url


def test_event_with_url():
    events = [Event('Meeting', date(2026, 3, 5), pk=1)]
    cal = Calendar(
        rows=events,
        event__attr='event_date',
        year=2026,
        month=3,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    html = bound.__html__()

    assert '/events/1/' in html
    assert '<a href="/events/1/">Meeting</a>' in html


def test_event_display_name_field():
    class NamedEvent:
        def __init__(self, title, event_date):
            self.title = title
            self.event_date = event_date

        def __str__(self):
            return 'should not appear'

    events = [NamedEvent('Custom Title', date(2026, 3, 5))]
    cal = Calendar(
        rows=events,
        event__attr='event_date',
        event__display_name=lambda event, **_: event.title,
        year=2026,
        month=3,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    html = bound.__html__()

    assert 'Custom Title' in html
    assert 'should not appear' not in html


def test_weeks_for_month():
    cal = Calendar(
        rows=[],
        event__attr='event_date',
        year=2026,
        month=3,
    ).refine_done()

    bound = cal.bind(request=req('get'))

    weeks = list(bound.weeks_for_month())
    assert len(weeks) >= 4
    assert len(weeks) <= 6

    for week in weeks:
        assert len(week) == 7

    # March 2026 starts on Sunday, so first day should be Monday Feb 23
    first_day = weeks[0][0]
    assert first_day.is_other_month is True
    assert first_day.date.month == 2


def test_days_for_month():
    cal = Calendar(
        rows=[],
        event__attr='event_date',
        year=2026,
        month=3,
    ).refine_done()

    bound = cal.bind(request=req('get'))

    days = list(bound.days_for_month())
    # Should be a multiple of 7
    assert len(days) % 7 == 0
    # Should contain all days of March
    march_days = [d for d in days if not d.is_other_month]
    assert len(march_days) == 31


def test_today_marking():
    today = date.today()
    cal = Calendar(
        rows=[],
        event__attr='event_date',
        year=today.year,
        month=today.month,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    html = bound.__html__()
    assert 'iommi-calendar-today' in html


def test_other_month_marking():
    cal = Calendar(
        rows=[],
        event__attr='event_date',
        year=2026,
        month=3,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    html = bound.__html__()
    assert 'iommi-calendar-other-month' in html


def test_year_month_from_get_params():
    # When calendar is root, iommi_path is '' and path_join gives 'year'/'month'
    request = RequestFactory().get('/', {'year': '2025', 'month': '6'})
    request.user = Struct(is_staff=False, is_authenticated=False, is_superuser=False)

    cal = Calendar(
        _name='calendar',
        rows=[],
        event__attr='event_date',
    ).refine_done()

    bound = cal.bind(request=request)
    assert bound.year == 2025
    assert bound.month == 6
    html = bound.__html__()
    assert 'June 2025' in html


def test_calendar_event_html():
    event = CalendarEvent(event_object=None, display_name='Test Event')
    assert event.__html__() == '<div>Test Event</div>'


def test_calendar_event_html_with_url():
    event = CalendarEvent(event_object=None, display_name='Test Event', url='/test/')
    assert event.__html__() == '<div><a href="/test/">Test Event</a></div>'


def test_calendar_event_html_no_tag():
    event = CalendarEvent(event_object=None, display_name='Test Event', tag=None)
    assert event.__html__() == 'Test Event'


def test_calendar_day():
    day = CalendarDay(
        date=date(2026, 3, 5),
        events=[],
        is_today=False,
        is_other_month=False,
    )
    assert day.day == 5
    assert day.date == date(2026, 3, 5)
    assert day.is_today is False
    assert day.is_other_month is False


def test_as_view():
    cal = Calendar(
        rows=[],
        event__attr='event_date',
        year=2026,
        month=3,
    )
    view = cal.as_view()
    assert callable(view)


def test_own_evaluate_parameters():
    cal = Calendar(
        rows=[],
        event__attr='event_date',
        year=2026,
        month=3,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    params = bound.iommi_evaluate_parameters()
    assert 'calendar' in params
    assert params['calendar'] is bound


def test_empty_rows():
    cal = Calendar(
        rows=[],
        event__attr='event_date',
        year=2026,
        month=3,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    html = bound.__html__()

    assert 'March 2026' in html
    assert 'iommi-calendar-event' not in html


def test_none_date_events_skipped():
    class NullDateEvent:
        def __init__(self, name, event_date):
            self.name = name
            self.event_date = event_date

        def __str__(self):
            return self.name

    events = [
        NullDateEvent('Valid', date(2026, 3, 5)),
        NullDateEvent('No Date', None),
    ]
    cal = Calendar(
        rows=events,
        event__attr='event_date',
        year=2026,
        month=3,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    html = bound.__html__()

    assert 'Valid' in html
    assert 'No Date' not in html


def test_calendar_title():
    cal = Calendar(
        rows=[],
        event__attr='event_date',
        year=2026,
        month=3,
        title='My Calendar',
    ).refine_done()

    bound = cal.bind(request=req('get'))
    html = bound.__html__()
    assert 'My Calendar' in html


def test_none_rows():
    cal = Calendar(
        rows=None,
        event__attr='event_date',
        year=2026,
        month=3,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    html = bound.__html__()
    assert 'March 2026' in html


def test_custom_event_url():
    events = [Event('Meeting', date(2026, 3, 5), pk=1)]
    cal = Calendar(
        rows=events,
        event__attr='event_date',
        year=2026,
        month=3,
        event__url=lambda event, **_: f'/custom/{event.pk}/',
    ).refine_done()

    bound = cal.bind(request=req('get'))
    html = bound.__html__()

    assert '/custom/1/' in html


def test_tag_is_table():
    cal = Calendar(
        rows=[],
        event__attr='event_date',
        year=2026,
        month=3,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    html = bound.__html__()

    assert '<table' in html
    assert '</table>' in html


def test_multiple_events_same_day():
    events = [
        Event('Morning Meeting', date(2026, 3, 5), pk=1),
        Event('Afternoon Meeting', date(2026, 3, 5), pk=2),
        Event('Evening Event', date(2026, 3, 5), pk=3),
    ]
    cal = Calendar(
        rows=events,
        event__attr='event_date',
        year=2026,
        month=3,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    html = bound.__html__()

    assert 'Morning Meeting' in html
    assert 'Afternoon Meeting' in html
    assert 'Evening Event' in html


def test_month_names():
    for month_num, month_name in [
        (1, 'January'), (2, 'February'), (3, 'March'),
        (4, 'April'), (5, 'May'), (6, 'June'),
        (7, 'July'), (8, 'August'), (9, 'September'),
        (10, 'October'), (11, 'November'), (12, 'December'),
    ]:
        cal = Calendar(
            rows=[],
            event__attr='event_date',
            year=2026,
            month=month_num,
        ).refine_done()

        bound = cal.bind(request=req('get'))
        assert bound.get_month_name() == month_name


def _sparse_events():
    return [
        Event('January thing', date(2026, 1, 10), pk=1),
        Event('March thing', date(2026, 3, 5), pk=2),
        Event('March other', date(2026, 3, 20), pk=3),
        Event('June thing', date(2026, 6, 15), pk=4),
        Event('December thing', date(2026, 12, 25), pk=5),
    ]


def test_next_with_data():
    events = _sparse_events()
    cal = Calendar(
        rows=events,
        event__attr='event_date',
        year=2026,
        month=1,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    result = bound.get_next_month_with_data()
    assert result == (2026, 3)


def test_prev_with_data():
    events = _sparse_events()
    cal = Calendar(
        rows=events,
        event__attr='event_date',
        year=2026,
        month=6,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    result = bound.get_prev_month_with_data()
    assert result == (2026, 3)


def test_next_with_data_none_at_end():
    events = _sparse_events()
    cal = Calendar(
        rows=events,
        event__attr='event_date',
        year=2026,
        month=12,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    assert bound.get_next_month_with_data() is None


def test_prev_with_data_none_at_start():
    events = _sparse_events()
    cal = Calendar(
        rows=events,
        event__attr='event_date',
        year=2026,
        month=1,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    assert bound.get_prev_month_with_data() is None


def test_next_with_data_skips_current_month():
    events = _sparse_events()
    cal = Calendar(
        rows=events,
        event__attr='event_date',
        year=2026,
        month=3,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    result = bound.get_next_month_with_data()
    # Should skip to June, not stay in March
    assert result == (2026, 6)


def test_prev_with_data_skips_current_month():
    events = _sparse_events()
    cal = Calendar(
        rows=events,
        event__attr='event_date',
        year=2026,
        month=3,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    result = bound.get_prev_month_with_data()
    assert result == (2026, 1)


def test_with_data_urls_rendered():
    events = _sparse_events()
    cal = Calendar(
        rows=events,
        event__attr='event_date',
        year=2026,
        month=3,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    html = bound.__html__()

    assert 'Prev with data' in html
    assert 'Next with data' in html
    assert 'First' in html
    assert 'Last' in html


def test_with_data_urls_hidden_when_none():
    events = [Event('Only event', date(2026, 3, 5), pk=1)]
    cal = Calendar(
        rows=events,
        event__attr='event_date',
        year=2026,
        month=3,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    html = bound.__html__()

    assert 'Prev with data' not in html
    assert 'Next with data' not in html
    assert 'First' not in html
    assert 'Last' not in html


def test_with_data_empty_rows():
    cal = Calendar(
        rows=[],
        event__attr='event_date',
        year=2026,
        month=3,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    assert bound.get_prev_month_with_data() is None
    assert bound.get_next_month_with_data() is None


def test_with_data_none_rows():
    cal = Calendar(
        rows=None,
        event__attr='event_date',
        year=2026,
        month=3,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    assert bound.get_prev_month_with_data() is None
    assert bound.get_next_month_with_data() is None


def test_with_data_cross_year():
    events = [
        Event('Early', date(2025, 11, 1), pk=1),
        Event('Late', date(2026, 2, 1), pk=2),
    ]
    cal = Calendar(
        rows=events,
        event__attr='event_date',
        year=2026,
        month=2,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    result = bound.get_prev_month_with_data()
    assert result == (2025, 11)


def test_next_with_data_cross_year():
    events = [
        Event('This year', date(2025, 11, 1), pk=1),
        Event('Next year', date(2026, 3, 1), pk=2),
    ]
    cal = Calendar(
        rows=events,
        event__attr='event_date',
        year=2025,
        month=11,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    result = bound.get_next_month_with_data()
    assert result == (2026, 3)


def test_first_with_data():
    events = _sparse_events()
    cal = Calendar(
        rows=events,
        event__attr='event_date',
        year=2026,
        month=6,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    assert bound.get_first_month_with_data() == (2026, 1)


def test_last_with_data():
    events = _sparse_events()
    cal = Calendar(
        rows=events,
        event__attr='event_date',
        year=2026,
        month=1,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    assert bound.get_last_month_with_data() == (2026, 12)


def test_first_with_data_none_when_on_first():
    events = _sparse_events()
    cal = Calendar(
        rows=events,
        event__attr='event_date',
        year=2026,
        month=1,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    assert bound.get_first_month_with_data() is None


def test_last_with_data_none_when_on_last():
    events = _sparse_events()
    cal = Calendar(
        rows=events,
        event__attr='event_date',
        year=2026,
        month=12,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    assert bound.get_last_month_with_data() is None


def test_first_last_with_empty_rows():
    cal = Calendar(
        rows=[],
        event__attr='event_date',
        year=2026,
        month=3,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    assert bound.get_first_month_with_data() is None
    assert bound.get_last_month_with_data() is None


def test_event_attrs_respected():
    events = [Event('Meeting', date(2026, 3, 5), pk=1)]
    cal = Calendar(
        rows=events,
        event__attr='event_date',
        year=2026,
        month=3,
        event__attrs__class={'my-custom-event': True},
        event__attrs__data_type='event',
    ).refine_done()

    bound = cal.bind(request=req('get'))
    html = bound.__html__()

    assert 'my-custom-event' in html
    assert 'iommi-calendar-event' in html
    assert 'data_type="event"' in html


def test_event_default_attrs():
    events = [Event('Meeting', date(2026, 3, 5), pk=1)]
    cal = Calendar(
        rows=events,
        event__attr='event_date',
        year=2026,
        month=3,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    html = bound.__html__()

    assert 'class="iommi-calendar-event"' in html


def test_day_attrs_respected():
    cal = Calendar(
        rows=[],
        event__attr='event_date',
        year=2026,
        month=3,
        day__attrs__class={'my-custom-day': True},
    ).refine_done()

    bound = cal.bind(request=req('get'))
    html = bound.__html__()

    assert 'my-custom-day' in html
    assert 'iommi-calendar-day' in html


def test_day_number_default_attrs():
    cal = Calendar(
        rows=[],
        event__attr='event_date',
        year=2026,
        month=3,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    html = bound.__html__()

    assert 'class="iommi-calendar-day-number"' in html


def test_day_number_attrs_respected():
    cal = Calendar(
        rows=[],
        event__attr='event_date',
        year=2026,
        month=3,
        day_number__attrs__class={'my-day-number': True},
    ).refine_done()

    bound = cal.bind(request=req('get'))
    html = bound.__html__()

    assert 'my-day-number' in html
    assert 'iommi-calendar-day-number' in html


def test_day_number_tag_customizable():
    cal = Calendar(
        rows=[],
        event__attr='event_date',
        year=2026,
        month=3,
        day_number__tag='span',
    ).refine_done()

    bound = cal.bind(request=req('get'))
    html = bound.__html__()

    assert '<span class="iommi-calendar-day-number">' in html


def test_today_link_shown_when_not_current_month():
    cal = Calendar(
        rows=[],
        event__attr='event_date',
        year=2020,
        month=1,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    html = bound.__html__()

    assert 'Today' in html
    today = date.today()
    assert f'year={today.year}' in html
    assert f'month={today.month}' in html


def test_today_link_hidden_when_on_current_month():
    today = date.today()
    cal = Calendar(
        rows=[],
        event__attr='event_date',
        year=today.year,
        month=today.month,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    html = bound.__html__()

    assert 'Today' not in html


def test_get_today_url():
    cal = Calendar(
        rows=[],
        event__attr='event_date',
        year=2020,
        month=6,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    today = date.today()
    url = bound.get_today_url()

    assert url is not None
    assert f'year={today.year}' in url
    assert f'month={today.month}' in url


def test_get_today_url_none_when_current():
    today = date.today()
    cal = Calendar(
        rows=[],
        event__attr='event_date',
        year=today.year,
        month=today.month,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    assert bound.get_today_url() is None


def test_weekend_class_on_day_cells():
    # March 2026: 7th is Saturday, 8th is Sunday
    cal = Calendar(
        rows=[],
        event__attr='event_date',
        year=2026,
        month=3,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    html = bound.__html__()

    assert 'iommi-calendar-weekend' in html


def test_weekend_class_on_weekday_headers():
    cal = Calendar(
        rows=[],
        event__attr='event_date',
        year=2026,
        month=3,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    html = bound.__html__()

    # Sat and Sun headers should have the weekend class
    assert 'iommi-calendar-weekend' in html
    # Mon-Fri headers should not — check that at least one weekday header lacks it
    lines = html.split('\n')
    weekday_lines = [l for l in lines if '>Mon<' in l or '>Fri<' in l]
    for line in weekday_lines:
        assert 'iommi-calendar-weekend' not in line


def test_weekend_class_not_applied_when_not_configured():
    cal = Calendar(
        rows=[],
        event__attr='event_date',
        year=2026,
        month=3,
        weekend__attrs__class={'iommi-calendar-weekend': False},
    ).refine_done()

    bound = cal.bind(request=req('get'))
    html = bound.__html__()

    assert 'weekend' not in html


def test_navigation_row_attrs():
    cal = Calendar(
        rows=[],
        event__attr='event_date',
        year=2026,
        month=3,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    html = bound.__html__()

    assert 'iommi-calendar-nav-row' in html


def test_adjacent_month_events_shown_in_grid():
    # March 2026 grid spans Feb 23 - Apr 5
    events = [
        Event('Feb event in grid', date(2026, 2, 25), pk=1),
        Event('Apr event in grid', date(2026, 4, 3), pk=2),
        Event('Apr event outside grid', date(2026, 4, 10), pk=3),
        Event('Feb event outside grid', date(2026, 2, 20), pk=4),
    ]
    cal = Calendar(
        rows=events,
        event__attr='event_date',
        year=2026,
        month=3,
    ).refine_done()

    bound = cal.bind(request=req('get'))
    html = bound.__html__()

    assert 'Feb event in grid' in html
    assert 'Apr event in grid' in html
    assert 'Apr event outside grid' not in html
    assert 'Feb event outside grid' not in html


def _assert_invalid_config_is_error(**kwargs):
    import pytest
    with pytest.raises(TypeError):
        Calendar(
            rows=[],
            event__attr='event_date',
            **kwargs,
        ).refine_done()


def test_invalid_today_config_is_error():
    _assert_invalid_config_is_error(today__foo=True)


def test_invalid_other_month_config_is_error():
    _assert_invalid_config_is_error(other_month__foo=True)


def test_invalid_weekend_config_is_error():
    _assert_invalid_config_is_error(weekend__foo=True)


def test_invalid_day_config_is_error():
    _assert_invalid_config_is_error(day__foo=True)


def test_invalid_event_config_is_error():
    _assert_invalid_config_is_error(event__foo=True)


def test_invalid_weekday_config_is_error():
    _assert_invalid_config_is_error(weekday__foo=True)


def test_invalid_day_number_config_is_error():
    _assert_invalid_config_is_error(day_number__foo=True)
