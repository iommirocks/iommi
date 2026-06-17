from docs.models import *
from iommi import *
from iommi.docs import show_output
from iommi.experimental.calendar import Calendar
from tests.helpers import req

request = req('get')

import pytest
pytestmark = pytest.mark.django_db


def test_calendar():
    # language=rst
    """
    .. _cookbook-calendar:

    Calendar
    --------

    .. note::

        The `Calendar` component is experimental. The API may change in future versions.

    """


def test_how_do_i_make_a_calendar_from_a_model(really_big_discography):
    # language=rst
    """
    .. _calendar-from-model:

    How do I make a calendar from a model?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    .. uses Calendar.model
    .. uses Calendar.rows
    .. uses Calendar.year
    .. uses Calendar.month
    .. uses Calendar.event

    Point `auto__model` at a model and tell the calendar which date field to place
    events on with `event__attr`. By default the calendar shows the current month;
    pass `year` and `month` to show a specific one. Each row of the queryset becomes an
    `event`. You can also pass `rows` (or `auto__rows`) directly instead of a model:
    """

    calendar = Calendar(
        auto__model=Album,
        event__attr='published_date',
        event__display_name=lambda event, **_: event.name,
        year=1983,
        month=11,
    )

    # @test
    show_output(calendar)
    # @end


def test_how_do_i_style_the_calendar_cells(really_big_discography):
    # language=rst
    """
    .. _calendar-cell-styling:

    How do I style the calendar's cells?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    .. uses Calendar.day
    .. uses Calendar.day_number
    .. uses Calendar.weekday
    .. uses Calendar.today
    .. uses Calendar.other_month
    .. uses Calendar.weekend

    Each kind of cell has its own config namespace where you can set `attrs`, a `tag`
    and so on: `day` for a day cell, `day_number` for the date number inside it,
    `weekday` for the weekday header row, and `today`, `weekend` and `other_month` for
    those special days:
    """

    calendar = Calendar(
        auto__model=Album,
        event__attr='published_date',
        year=1983,
        month=11,
        today__attrs__class={'bg-warning': True},
        weekend__attrs__class={'bg-light': True},
        other_month__attrs__style__opacity='0.5',
        weekday__attrs__class={'fw-bold': True},
    )

    # @test
    show_output(calendar)
    # @end


def test_how_do_i_customize_calendar_navigation_and_actions(really_big_discography):
    # language=rst
    """
    .. _calendar-navigation:

    How do I customize the calendar navigation and actions?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    .. uses Calendar.navigation
    .. uses Calendar.actions

    The previous/next month navigation row is configured through `navigation`, and you
    can add your own buttons or links via `actions`, just like on a table or form:
    """

    calendar = Calendar(
        auto__model=Album,
        event__attr='published_date',
        year=1983,
        month=11,
        navigation__attrs__class={'bg-light': True},
        actions__today=Action(display_name='Today', attrs__href='?'),
    )

    # @test
    show_output(calendar)
    # @end
