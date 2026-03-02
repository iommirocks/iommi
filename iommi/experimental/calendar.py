import calendar as python_calendar
from collections import defaultdict
from datetime import date

from django.db.models import (
    Model,
    QuerySet,
)
from django.utils.safestring import mark_safe

from iommi._web_compat import (
    Template,
    render_template,
)
from iommi.action import (
    Action,
    Actions,
)
from iommi.attrs import (
    Attrs,
    render_attrs,
)
from iommi.base import (
    MISSING,
    NOT_BOUND_MESSAGE,
    build_as_view_wrapper,
    model_and_rows,
)
from iommi.declarative.dispatch import dispatch
from iommi.declarative.namespace import (
    EMPTY,
    Namespace,
)
from iommi.endpoint import path_join
from iommi.evaluate import (
    evaluate_member,
    evaluate_strict,
)
from iommi.fragment import (
    Fragment,
    Header,
    Tag,
    build_and_bind_h_tag,
)
from iommi.member import (
    bind_members,
    refine_done_members,
)
from iommi.page import Part
from iommi.refinable import (
    EvaluatedRefinable,
    Refinable,
    RefinableMembers,
    RefinableObject,
    SpecialEvaluatedRefinable,
)
from iommi.shortcut import with_defaults


class CalendarCellConfig(RefinableObject):
    tag: str = Refinable()
    attr: str = Refinable()
    display_name: str = Refinable()
    url = Refinable()
    attrs: Attrs = Refinable()

    @dispatch(
        attrs__class=EMPTY,
        attrs__style=EMPTY,
    )
    def __init__(self, **kwargs):
        super(CalendarCellConfig, self).__init__(**kwargs)


class CalendarAutoConfig(RefinableObject):
    model: type[Model] = SpecialEvaluatedRefinable()
    rows = Refinable()
    include = Refinable()
    exclude = Refinable()

    @dispatch
    def __init__(self, **kwargs):
        super(CalendarAutoConfig, self).__init__(**kwargs)


class CalendarEvent(Tag):
    """Represents a single event inside a day cell."""

    def __init__(self, event_object, display_name, url=None, tag='div', attrs=None):
        self.event_object = event_object
        self.display_name = display_name
        self.url = url
        self.tag = tag
        self.attrs = attrs if attrs is not None else {}

    def __html__(self):
        if self.url:
            content = f'<a href="{self.url}">{self.display_name}</a>'
        else:
            content = str(self.display_name)
        if self.tag:
            return mark_safe(f'<{self.tag}{render_attrs(self.attrs)}>{content}</{self.tag}>')
        return mark_safe(content)


class CalendarDayNumber(Tag):
    """Represents the day number display inside a day cell."""

    def __init__(self, number, tag='div', attrs=None):
        self.number = number
        self.tag = tag
        self.attrs = attrs if attrs is not None else {}

    def __html__(self):
        content = str(self.number)
        if self.tag:
            return mark_safe(f'<{self.tag}{render_attrs(self.attrs)}>{content}</{self.tag}>')
        return mark_safe(content)


class CalendarDay:
    """Represents a single day cell in the calendar grid."""

    def __init__(self, date, events, is_today, is_other_month):
        self.date = date
        self.events = events
        self.is_today = is_today
        self.is_other_month = is_other_month

    @property
    def day(self):
        return self.date.day


class Calendar(Part, Tag):
    # language=rst
    """
    A calendar component that renders a month-grid calendar.

    Example:

    .. code-block:: python

        calendar = Calendar(
            auto__model=Album,
            event__attr='event_date',
        )
    """

    rows = SpecialEvaluatedRefinable()
    model: type[Model] = SpecialEvaluatedRefinable()
    year: int = EvaluatedRefinable()
    month: int = EvaluatedRefinable()
    attrs: Attrs = SpecialEvaluatedRefinable()
    template: str | Template = EvaluatedRefinable()
    title: str = SpecialEvaluatedRefinable()
    h_tag: Fragment | str = SpecialEvaluatedRefinable()
    tag: str = EvaluatedRefinable()
    day: CalendarCellConfig = Refinable()
    day_number: CalendarCellConfig = Refinable()
    event: CalendarCellConfig = Refinable()
    weekday: CalendarCellConfig = Refinable()
    today: CalendarCellConfig = Refinable()
    other_month: CalendarCellConfig = Refinable()
    weekend: CalendarCellConfig = Refinable()
    navigation: Namespace = Refinable()
    actions: dict[str, Action] = RefinableMembers()
    auto: CalendarAutoConfig = Refinable()

    class Meta:
        actions = EMPTY
        auto = EMPTY
        attrs__class = EMPTY
        attrs__style = EMPTY
        day = EMPTY
        day_number = EMPTY
        event = EMPTY
        weekday = EMPTY
        today = EMPTY
        other_month = EMPTY
        weekend = EMPTY
        navigation = EMPTY

    @with_defaults(
        template='iommi/calendar/calendar.html',
        tag='table',
        h_tag__call_target=Header,
        title=MISSING,
        year=None,
        month=None,
        day_number__tag='div',
        event__display_name=lambda event, **_: str(event),
        event__tag='div',
        weekday__tag='th',
        navigation__tag='td',
        navigation__attrs__colspan='7',
    )
    def __init__(self, *, event__attr, **kwargs):
        super(Calendar, self).__init__(event__attr=event__attr, **kwargs)

    @property
    def _date_field(self):
        return self.event.get('attr')

    def on_refine_done(self):
        model = self.model
        rows = self.rows

        if self.auto:
            auto = CalendarAutoConfig(**self.auto).refine_done(parent=self)
            if auto.model:
                model = auto.model
            if auto.rows is not None:
                rows = auto.rows

        # Validate cell config namespaces (will raise on unknown keys like today__foo)
        for name in ('day', 'day_number', 'event', 'weekday', 'today', 'other_month', 'weekend'):
            ns = getattr(self, name)
            if ns:
                CalendarCellConfig(**ns)

        if self.title is MISSING:
            self.title = None

        self.model, self.rows = model_and_rows(model, rows)

        refine_done_members(
            self,
            name='actions',
            members_from_namespace=self.actions,
            cls=Action,
            members_cls=Actions,
        )

        super(Calendar, self).on_refine_done()

    def on_bind(self) -> None:
        bind_members(self, name='actions')
        bind_members(self, name='endpoints')

        request = self.get_request()

        # GET params override everything, then evaluate configured default, then today
        today = date.today()

        year_param = request.GET.get(path_join(self.iommi_path, 'year')) if request else None
        month_param = request.GET.get(path_join(self.iommi_path, 'month')) if request else None

        if year_param is not None:
            self.year = int(year_param)
        else:
            evaluate_member(self, 'year', **self.iommi_evaluate_parameters())
            if self.year is None:
                self.year = today.year

        if month_param is not None:
            self.month = int(month_param)
        else:
            evaluate_member(self, 'month', **self.iommi_evaluate_parameters())
            if self.month is None:
                self.month = today.month

        self.title = evaluate_strict(self.title, **self.iommi_evaluate_parameters()) if self.title is not None else None
        build_and_bind_h_tag(self)

        # Keep unfiltered rows for prev/next-with-data queries
        self._all_rows = self.rows

        # Compute the actual displayed date range (includes adjacent-month days in the grid)
        cal = python_calendar.Calendar(firstweekday=0)
        weeks = cal.monthdatescalendar(self.year, self.month)
        self._grid_start = weeks[0][0]
        self._grid_end = weeks[-1][-1]

        # Filter rows to the displayed date range
        if self.rows is not None and self._date_field:
            if isinstance(self.rows, QuerySet):
                self.rows = self.rows.filter(**{
                    f'{self._date_field}__gte': self._grid_start,
                    f'{self._date_field}__lte': self._grid_end,
                })
            # For list data, filtering happens in _group_events_by_date

        self._events_by_date = self._group_events_by_date()

    def _group_events_by_date(self):
        events_by_date = defaultdict(list)
        if self.rows is None:
            return events_by_date

        for row in self.rows:
            if self._date_field:
                event_date = getattr(row, self._date_field)
            else:
                continue

            if event_date is None:
                continue

            # Handle datetime fields by extracting the date
            if hasattr(event_date, 'date'):
                event_date = event_date.date()

            # For list data, filter to the displayed date range
            if not isinstance(self.rows, QuerySet):
                if event_date < self._grid_start or event_date > self._grid_end:
                    continue

            display_name = evaluate_strict(self.event.get('display_name'), event=row, **self.iommi_evaluate_parameters())

            url = None
            event_url = self.event.get('url')
            if event_url:
                url = evaluate_strict(event_url, event=row, **self.iommi_evaluate_parameters())
            elif hasattr(row, 'get_absolute_url'):
                url = row.get_absolute_url()

            events_by_date[event_date].append(
                CalendarEvent(
                    event_object=row,
                    display_name=display_name,
                    url=url,
                    tag=self.event.get('tag', 'div'),
                    attrs=self._build_attrs('event'),
                )
            )

        return events_by_date

    def days_for_month(self):
        """Generate CalendarDay instances for each day in the calendar grid."""
        today = date.today()
        cal = python_calendar.Calendar(firstweekday=0)  # Monday first

        for d in cal.itermonthdates(self.year, self.month):
            yield CalendarDay(
                date=d,
                events=self._events_by_date.get(d, []),
                is_today=(d == today),
                is_other_month=(d.month != self.month),
            )

    def weeks_for_month(self):
        """Generate weeks (lists of 7 CalendarDay instances) for the calendar grid."""
        cal = python_calendar.Calendar(firstweekday=0)
        today = date.today()

        for week in cal.monthdatescalendar(self.year, self.month):
            yield [
                CalendarDay(
                    date=d,
                    events=self._events_by_date.get(d, []),
                    is_today=(d == today),
                    is_other_month=(d.month != self.month),
                )
                for d in week
            ]

    def get_weekday_names(self):
        return ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

    def get_month_name(self):
        return python_calendar.month_name[self.month]

    def get_prev_month(self):
        if self.month == 1:
            return self.year - 1, 12
        return self.year, self.month - 1

    def get_next_month(self):
        if self.month == 12:
            return self.year + 1, 1
        return self.year, self.month + 1

    def _make_url(self, year, month):
        year_key = path_join(self.iommi_path, 'year')
        month_key = path_join(self.iommi_path, 'month')
        return f'?{year_key}={year}&{month_key}={month}'

    def get_prev_url(self):
        return self._make_url(*self.get_prev_month())

    def get_next_url(self):
        return self._make_url(*self.get_next_month())

    def get_today_url(self):
        today = date.today()
        if today.year == self.year and today.month == self.month:
            return None
        return self._make_url(today.year, today.month)

    def _get_date_value(self, row):
        if not self._date_field:
            return None
        v = getattr(row, self._date_field, None)
        if v is None:
            return None
        if hasattr(v, 'date'):
            v = v.date()
        return v

    def get_prev_month_with_data(self):
        """Return (year, month) of the closest earlier month that has data, or None."""
        current = date(self.year, self.month, 1)
        return self._ym_from_query(f'-{self._date_field}', **{f'{self._date_field}__lt': current})

    def get_next_month_with_data(self):
        """Return (year, month) of the closest later month that has data, or None."""
        if self.month == 12:
            next_month_start = date(self.year + 1, 1, 1)
        else:
            next_month_start = date(self.year, self.month + 1, 1)
        return self._ym_from_query(self._date_field, **{f'{self._date_field}__gte': next_month_start})

    def _ym_from_query(self, order, **filter_kwargs):
        """Helper: query _all_rows for a single date, return (year, month) or None."""
        if self._all_rows is None or not self._date_field:
            return None

        if isinstance(self._all_rows, QuerySet):
            qs = self._all_rows.exclude(**{f'{self._date_field}__isnull': True})
            if filter_kwargs:
                qs = qs.filter(**filter_kwargs)
            row = qs.order_by(order).values_list(self._date_field, flat=True).first()
            if row is None:
                return None
            d = row.date() if hasattr(row, 'date') else row
            return d.year, d.month
        else:
            best = None
            for row in self._all_rows:
                d = self._get_date_value(row)
                if d is None:
                    continue
                # Apply the same filter logic for lists
                if filter_kwargs:
                    threshold_key = next(iter(filter_kwargs))
                    threshold_val = filter_kwargs[threshold_key]
                    if '__lt' in threshold_key:
                        if d >= threshold_val:
                            continue
                    elif '__gte' in threshold_key:
                        if d < threshold_val:
                            continue
                if best is None:
                    best = d
                elif order.startswith('-'):
                    if d > best:
                        best = d
                else:
                    if d < best:
                        best = d
            if best is None:
                return None
            return best.year, best.month

    def get_first_month_with_data(self):
        """Return (year, month) of the earliest month that has data, or None."""
        result = self._ym_from_query(self._date_field)
        if result and result == (self.year, self.month):
            return None
        return result

    def get_last_month_with_data(self):
        """Return (year, month) of the latest month that has data, or None."""
        result = self._ym_from_query(f'-{self._date_field}')
        if result and result == (self.year, self.month):
            return None
        return result

    def get_prev_with_data_url(self):
        result = self.get_prev_month_with_data()
        if result is None:
            return None
        return self._make_url(*result)

    def get_next_with_data_url(self):
        result = self.get_next_month_with_data()
        if result is None:
            return None
        return self._make_url(*result)

    def get_first_with_data_url(self):
        result = self.get_first_month_with_data()
        if result is None:
            return None
        return self._make_url(*result)

    def get_last_with_data_url(self):
        result = self.get_last_month_with_data()
        if result is None:
            return None
        return self._make_url(*result)

    def own_evaluate_parameters(self):
        return dict(calendar=self)

    def _get_ns_classes(self, namespace):
        ns = getattr(self, namespace) if isinstance(namespace, str) else namespace
        return dict(ns.get('attrs', {}).get('class', {}))

    def _build_attrs(self, namespace, extra_class=None):
        ns = getattr(self, namespace) if isinstance(namespace, str) else namespace
        attrs_ns = ns.get('attrs', {})
        if extra_class:
            class_dict = dict(attrs_ns.get('class', {}))
            class_dict.update(extra_class)
            return Attrs(
                _parent=self,
                **{k: v for k, v in attrs_ns.items() if k != 'class'},
                **{'class': class_dict},
            )
        return Attrs(_parent=self, **{k: v for k, v in attrs_ns.items()})

    @property
    def render_body(self):
        lines = []

        # Navigation row
        first_url = self.get_first_with_data_url()
        prev_data_url = self.get_prev_with_data_url()
        next_data_url = self.get_next_with_data_url()
        last_url = self.get_last_with_data_url()

        nav_row_attrs_ns = self.navigation.get('row_attrs', {})
        nav_row_attrs = Attrs(_parent=self, **{k: v for k, v in nav_row_attrs_ns.items()})
        nav_tag = self.navigation.get('tag', 'td')
        nav_attrs = self._build_attrs('navigation')
        lines.append(f'<tr{render_attrs(nav_row_attrs)}><{nav_tag}{render_attrs(nav_attrs)}><div>')
        if first_url:
            lines.append(f'<a href="{first_url}">&laquo; First</a> ')
        if prev_data_url:
            lines.append(f'<a href="{prev_data_url}">&lsaquo; Prev with data</a> ')
        today_url = self.get_today_url()

        lines.append(f'<a href="{self.get_prev_url()}">&lsaquo; Prev</a>')
        if today_url:
            lines.append(f' <a href="{today_url}">Today</a>')
        lines.append(f' <strong>{self.get_month_name()} {self.year}</strong> ')
        lines.append(f'<a href="{self.get_next_url()}">Next &rsaquo;</a>')
        if next_data_url:
            lines.append(f' <a href="{next_data_url}">Next with data &rsaquo;</a>')
        if last_url:
            lines.append(f' <a href="{last_url}">Last &raquo;</a>')
        lines.append(f'</div></{nav_tag}></tr>')

        # Weekday header row
        weekday_tag = self.weekday.get('tag', 'th')
        weekend_classes = self._get_ns_classes('weekend')
        # Monday=0 .. Sunday=6; weekend is 5 (Sat) and 6 (Sun)
        lines.append('<tr>')
        for i, name in enumerate(self.get_weekday_names()):
            extra_class = {}
            if i >= 5:
                extra_class.update(weekend_classes)
            weekday_attrs = self._build_attrs('weekday', extra_class=extra_class or None)
            lines.append(f'<{weekday_tag}{render_attrs(weekday_attrs)}>{name}</{weekday_tag}>')
        lines.append('</tr>')

        # Week rows
        today_classes = self._get_ns_classes('today')
        other_month_classes = self._get_ns_classes('other_month')
        for week in self.weeks_for_month():
            lines.append('<tr>')
            for day in week:
                extra_class = {}
                if day.is_today:
                    extra_class.update(today_classes)
                if day.is_other_month:
                    extra_class.update(other_month_classes)
                if day.date.weekday() >= 5:
                    extra_class.update(weekend_classes)

                day_attrs = self._build_attrs('day', extra_class=extra_class or None)

                day_number = CalendarDayNumber(
                    number=day.day,
                    tag=self.day_number.get('tag', 'div'),
                    attrs=self._build_attrs('day_number'),
                )

                lines.append(f'<td{render_attrs(day_attrs)}>')
                lines.append(day_number.__html__())
                for event in day.events:
                    lines.append(event.__html__())
                lines.append('</td>')
            lines.append('</tr>')

        return mark_safe('\n'.join(lines))

    @dispatch(
        render=render_template,
    )
    def __html__(self, *, template=None, render=None):
        assert self._is_bound, NOT_BOUND_MESSAGE

        request = self.get_request()
        context = self.iommi_evaluate_parameters().copy()

        return render(request=request, template=template or self.template, context=context)

    def as_view(self):
        return build_as_view_wrapper(self)
