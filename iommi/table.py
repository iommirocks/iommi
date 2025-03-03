import csv
from datetime import (
    date,
    datetime,
    time,
)
from enum import (
    Enum,
    auto,
)
from functools import total_ordering
from io import StringIO
from itertools import groupby
from math import ceil
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Optional,
    Type,
    Union,
)
from urllib.parse import quote_plus

from django.db.models import (
    AutoField,
    BooleanField,
    ManyToManyField,
    Model,
    QuerySet,
)
from django.http import (
    FileResponse,
)
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.html import (
    conditional_escape,
)
from django.utils.translation import (
    gettext_lazy,
    gettext_lazy,
)

from iommi._web_compat import (
    HttpResponse,
    HttpResponseRedirect,
    Template,
    format_html,
    mark_safe,
    render_template,
    smart_str,
)
from iommi.action import (
    Action,
    Actions,
    group_actions,
)
from iommi.attrs import (
    Attrs,
    evaluate_attrs,
    render_attrs,
)
from iommi.base import (
    MISSING,
    NOT_BOUND_MESSAGE,
    build_as_view_wrapper,
    capitalize,
    get_display_name,
    items,
    keys,
    model_and_rows,
    values,
)
from iommi.declarative import declarative
from iommi.declarative.dispatch import dispatch
from iommi.declarative.namespace import (
    EMPTY,
    Namespace,
    flatten,
    getattr_path,
    setdefaults_path,
)
from iommi.declarative.with_meta import with_meta
from iommi.endpoint import (
    DISPATCH_PREFIX,
    path_join,
)
from iommi.evaluate import (
    evaluate,
    evaluate_member,
    evaluate_strict,
)
from iommi.form import (
    Field,
    Form,
)
from iommi.fragment import (
    Fragment,
    Header,
    Tag,
    TransientFragment,
    build_and_bind_h_tag,
    html,
)
from iommi.from_model import (
    AutoConfig,
    NoRegisteredSearchFieldException,
    create_members_from_model,
    get_search_fields,
    member_from_model,
)
from iommi.member import (
    bind_member,
    bind_members,
    refine_done_members,
)
from iommi.page import (
    Page,
    Part,
)
from iommi.part import render_root
from iommi.query import (
    Q_OPERATOR_BY_QUERY_OPERATOR,
    Query,
)
from iommi.refinable import (
    EvaluatedRefinable,
    Prio,
    Refinable,
    RefinableMembers,
    RefinableObject,
    SpecialEvaluatedRefinable,
    evaluated_refinable,
    refinable,
)
from iommi.shortcut import (
    Shortcut,
    with_defaults,
)
from iommi.sort_after import (
    LAST,
    sort_after,
)
from iommi.struct import (
    Struct,
    merged,
)
from iommi.traversable import (
    Traversable,
)

from ._db_compat import base_defaults_factory

LAST = LAST

_column_factory_by_field_type = {}


def register_column_factory(django_field_class, *, shortcut_name=MISSING, factory=MISSING, **kwargs):
    assert shortcut_name is not MISSING or factory is not MISSING
    if factory is MISSING:
        factory = Shortcut(call_target__attribute=shortcut_name, **kwargs)

    _column_factory_by_field_type[django_field_class] = factory


DESCENDING = 'descending'
ASCENDING = 'ascending'

DEFAULT_PAGE_SIZE = 16


def params_of_request(request):
    if request is None:
        return {}

    params = request.GET.copy()

    # There can be one dispatch parameter present, we need to filter out that
    for param in keys(params):
        if param.startswith(DISPATCH_PREFIX):
            del params[param]
            break

    return params


def prepare_headers(table):
    request = table.get_request()
    if request is None:
        return

    for name, column in items(table.columns):
        if column.sortable:
            params = params_of_request(request)
            param_path = path_join(table.iommi_path, 'order')
            order = request.GET.get(param_path) or table.default_sort_order
            start_sort_desc = column.sort_default_desc
            params[param_path] = name if not start_sort_desc else '-' + name
            column.is_sorting = False
            if order is not None:
                is_desc = order.startswith('-')
                order_field = order if not is_desc else order[1:]
                if order_field == name:
                    new_order = order_field if is_desc else ('-' + order_field)
                    params[param_path] = new_order
                    column.sort_direction = DESCENDING if is_desc else ASCENDING
                    column.is_sorting = True
            if table.iommi_namespace.parts.page:
                paginator_parameter_name = table.iommi_namespace.parts.page.iommi_path
                params.pop(paginator_parameter_name, None)
            column.header.url = "?" + params.urlencode()
        else:
            column.is_sorting = False


@total_ordering
class MinType:
    def __le__(self, other):
        return True

    def __eq__(self, other):
        return self is other


MIN = MinType()


def ordered_by_on_list(rows, sort_key, descending):
    """
    Utility function to sort objects django-style even for non-query set collections

    :param rows: list of objects to sort
    :param sort_key: field name, follows django conventions, so `foo__bar` means `foo.bar`, can be a callable.
    :param descending: reverse the sorting
    :return: a sorted sequence
    """

    def order_key(x):
        v = getattr_path(x, sort_key)
        if v is None:
            return MIN
        return v

    return sorted(rows, key=order_key, reverse=descending)


def yes_no_formatter(value, **_):
    """Handle True/False from Django model and 1/0 from raw sql"""
    if value is None:
        return ''
    if value == 1:  # boolean True is equal to 1
        return gettext_lazy('Yes')
    if value == 0:  # boolean False is equal to 0
        return gettext_lazy('No')
    assert False, f"Unable to convert {value} to Yes/No"


def list_formatter(value, **_):
    return ', '.join([conditional_escape(x) for x in value])


def datetime_formatter(value, **_):
    dt = timezone.localtime(value) if timezone.is_aware(value) else value
    return date_format(dt, format='DATETIME_FORMAT')


def date_formatter(value, **_):
    return date_format(value, format='DATE_FORMAT')


def time_formatter(value, **_):
    return date_format(value, format='TIME_FORMAT')


_cell_formatters = {
    bool: yes_no_formatter,
    tuple: list_formatter,
    list: list_formatter,
    set: list_formatter,
    QuerySet: lambda value, **_: list_formatter(list(value)),
    datetime: datetime_formatter,
    date: date_formatter,
    time: time_formatter,
}

_cell_formatters_types = tuple(_cell_formatters.keys())


def register_cell_formatter(type_or_class, formatter):
    """
    Register a default formatter for a type. A formatter is a function that takes four keyword arguments: table, column, row, value
    """
    global _cell_formatters, _cell_formatters_types
    _cell_formatters[type_or_class] = formatter
    _cell_formatters_types = tuple(_cell_formatters.keys())


def default_cell_formatter(table: 'Table', column: 'Column', row, value, **_):
    if isinstance(value, _cell_formatters_types):
        for type_, formatter in _cell_formatters.items():
            if isinstance(value, type_):
                value = formatter(table=table, column=column, row=row, value=value)
                break

    if value is None:
        return ''

    return conditional_escape(value)


def default_cell__value(column, row, **kwargs):
    if column.attr is None:
        return None
    else:
        return getattr_path(row, evaluate_strict(column.attr, row=row, column=column, **kwargs))


class DataRetrievalMethods(Enum):
    attribute_access = auto()
    prefetch = auto()
    select = auto()

    def __eq__(self, other):
        if self.__class__ == other.__class__:
            return self is other
        if isinstance(other, str):
            return self.name == other
        if other is None or other is MISSING:
            return False
        assert False, f'Invalid data retrieval method {other!r}'


def default_icon__cell__format(column, value, **_):
    if not value:
        return ''
    if not column.extra.get('icon', None):
        return column.display_name

    attrs = column.extra.icon_attrs
    attrs['class'][column.extra.get('icon_prefix', '') + column.extra.icon] = True

    return format_html('<i{}></i> {}', render_attrs(attrs), column.display_name)


def foreign_key__sort_key(column, **_):
    if column.model:
        try:
            sort_columns = get_search_fields(model=column.model)
            return f'{column.attr}__{sort_columns[0]}'
        except NoRegisteredSearchFieldException:
            pass

    return column.attr


def get_choices_from_column(table, traversable, **_):
    column_definition = table.iommi_namespace.columns[traversable.iommi_name()]
    return evaluate(
        column_definition.choices,
        **traversable.iommi_evaluate_parameters(),
    )


@with_meta
class Column(Part):
    """
    Class that describes a column, i.e. the text of the header, how to get and display the data in the cell, etc.

    See :doc:`Table` for more complete examples.

    """

    attr: str = EvaluatedRefinable()
    sort_default_desc: bool = EvaluatedRefinable()
    sortable: bool = EvaluatedRefinable()
    group: Optional[str] = EvaluatedRefinable()
    auto_rowspan: bool = EvaluatedRefinable()
    row_group: Namespace = EvaluatedRefinable()
    cell: Namespace = Refinable()
    model: Type[Model] = SpecialEvaluatedRefinable()
    model_field = Refinable()
    model_field_name = Refinable()
    choices: Iterable = EvaluatedRefinable()
    bulk: Namespace = Refinable()
    filter: Namespace = Refinable()
    superheader = EvaluatedRefinable()
    header: Namespace = EvaluatedRefinable()
    data_retrieval_method = EvaluatedRefinable()
    render_column: bool = EvaluatedRefinable()

    class Meta:
        filter = EMPTY
        cell__attrs = EMPTY
        cell__contents__attrs = EMPTY
        cell__link = EMPTY

    @with_defaults(
        attr=MISSING,
        sort_default_desc=False,
        sortable=lambda column, **_: column.attr is not None,
        auto_rowspan=False,
        bulk__include=False,
        data_retrieval_method=DataRetrievalMethods.attribute_access,
        cell__template=None,
        cell__value=default_cell__value,
        cell__format=default_cell_formatter,
        cell__url=None,
        cell__url_title=None,
        header__attrs__class__sorted=lambda column, **_: column.is_sorting,
        header__attrs__class__descending=lambda column, **_: column.sort_direction == DESCENDING,
        header__attrs__class__ascending=lambda column, **_: column.sort_direction == ASCENDING,
        header__attrs__class__first_column=lambda header, **_: header.index_in_group == 0,
        header__attrs__class__subheader=True,
        header__template='iommi/table/header.html',
        header__url=None,
        render_column=True,
        row_group__include=False,
        row_group__template='iommi/table/row_group.html',
        row_group__tag='th',
        row_group__attrs__colspan='99',
    )
    def __init__(self, **kwargs):
        """
        Parameters with the prefix `filter__` will be passed along downstream to the `Filter` instance if applicable. This can be used to tweak the filtering of a column.

        :param after: Set the order of columns, see the `howto on ordering <https://docs.iommi.rocks/en/latest/cookbook_tables.html#how-do-i-reorder-columns>`_ for an example.
        :param attr: What attribute to use, defaults to same as name. Follows django conventions to access properties of properties, so `foo__bar` is equivalent to the python code `foo.bar`. This parameter is based on the filter name of the Column if you use the declarative style of creating tables.
        :param bulk: Namespace to configure bulk actions. See `howto on bulk editing <https://docs.iommi.rocks/en/latest/cookbook_tables.html#how-do-i-enable-bulk-editing>`_ for an example and more information.
        :param cell: Customize the cell, see See `howto on rendering <https://docs.iommi.rocks/en/latest/cookbook_tables.html#how-do-i-customize-the-rendering-of-a-cell>`_ and `howto on links <https://docs.iommi.rocks/en/latest/cookbook_tables.html#how-do-i-make-a-link-in-a-cell>`_
        :param display_name: the text of the header for this column. By default this is based on the `_name` so normally you won't need to specify it.
        :param url: URL of the header. This should only be used if sorting is off.
        :param include: set this to `False` to hide the column
        :param sortable: set this to `False` to disable sorting on this column
        :param sort_key: string denoting what value to use as sort key when this column is selected for sorting. (Or callable when rendering a table from list.)
        :param sort_default_desc: Set to `True` to make table sort link to sort descending first.
        :param group: string describing the group of the header. If this parameter is used the header of the table now has two rows. Consecutive identical groups on the first level of the header are joined in a nice way.
        :param auto_rowspan: enable automatic rowspan for this column. To join two cells with rowspan, just set this `auto_rowspan` to `True` and make those two cells output the same text and we'll handle the rest.
        :param cell__template: name of a template file, or `Template` instance. Gets arguments: `table`, `column`, `cells`, `row` and `value`. Your own arguments should be sent in the 'extra' parameter.
        :param cell__value: string or callable that receives kw arguments: `table`, `column` and `row`. This is used to extract which data to display from the object.
        :param cell__format: string or callable that receives kw arguments: `table`, `column`, `row` and `value`. This is used to convert the extracted data to html output (use `mark_safe`) or a string.
        :param cell__attrs: dict of attr name to callables that receive kw arguments: `table`, `column`, `row` and `value`.
        :param cell__url: callable that receives kw arguments: `table`, `column`, `row` and `value`.
        :param cell__url_title: callable that receives kw arguments: `table`, `column`, `row` and `value`.
        :param render_column: If set to `False` the column won't be rendered in the table, but still be available in `table.columns`. This can be useful if you want some other feature from a column like filtering.
        """

        model_field = kwargs.get('model_field')
        if model_field and model_field.remote_field:
            kwargs['model'] = model_field.remote_field.model
        super(Column, self).__init__(**kwargs)

    def on_refine_done(self):
        if 'choice' in getattr(self, 'iommi_shortcut_stack', []):
            assert (
                self.iommi_namespace.get('choices') is not None
            ), 'To use Column.choice, you must pass the choices list'

        model_field = self.model_field
        if model_field and model_field.remote_field:
            self.model = model_field.remote_field.model
        elif isinstance(self.model, SpecialEvaluatedRefinable):
            self.model = None

        self.header = HeaderColumnConfig(**self.header).refine_done(parent=self)
        self.is_sorting: bool = None
        self.sort_direction: str = None
        self.table = None
        super(Column, self).on_refine_done()

    def __html__(self, *, render=None):
        assert False, "This is implemented just to make linting happy that we've implemented all abstract methods. Don't call this!"  # pragma: no cover

    @staticmethod
    @evaluated_refinable
    def sort_key(table, column, **_):
        return column.attr

    @staticmethod
    @evaluated_refinable
    def display_name(traversable, **_):
        return get_display_name(traversable)

    def on_bind(self) -> None:
        self.table = self.iommi_parent().iommi_parent()

        if self.attr is MISSING:
            self.attr = self._name

        self.bulk = setdefaults_path(
            Struct(),
            self.bulk,
            attr=self.attr,
        )
        self.filter = setdefaults_path(
            Struct(),
            self.filter,
            attr=self.attr,
        )
        self.declared_column = self._declared
        self.cell = Namespace(flatten(self.cell))

        # Not strict evaluate on purpose
        self.model = evaluate(self.model, **self.iommi_evaluate_parameters())

        if self.auto_rowspan:
            assert 'rowspan' not in self.cell.attrs, (
                f'Explicitly set rowspan html attribute collides with ' f'auto_rowspan on column {self.iommi_path}'
            )

    def own_evaluate_parameters(self):
        return dict(column=self)

    @classmethod
    @dispatch(
        filter__call_target__attribute='from_model',
        bulk__call_target__attribute='from_model',
    )
    def from_model(cls, model=None, model_field_name=None, model_field=None, **kwargs):
        return member_from_model(
            cls=cls,
            model=model,
            factory_lookup=_column_factory_by_field_type,
            factory_lookup_register_function=register_column_factory,
            model_field_name=model_field_name,
            model_field=model_field,
            defaults_factory=base_defaults_factory,
            **kwargs,
        )

    @classmethod
    @with_defaults(
        display_name='',
        cell__value=lambda table, **_: True,
        cell__format=default_icon__cell__format,
        attr=None,
    )
    @dispatch(
        extra__icon_attrs__class=EMPTY,
        extra__icon_attrs__style=EMPTY,
    )
    def icon(cls, *args, **kwargs):
        # language=rst
        """
        Shortcut to create font awesome-style icons.

        :param extra__icon: the name of the icon

        .. code-block:: python

            table = Table(
                auto__model=Album,
                columns__icon=Column(extra__icon='music'),
            )

            # @test
            show_output(table)
            # @end
        """
        assert len(args) in (0, 1), "You can only pass 1 positional argument: icon, or you can pass no arguments."

        instance = cls(**kwargs)
        if args:
            instance = instance.refine(
                Prio.shortcut,
                extra__icon=args[0],
            )
        return instance

    @classmethod
    @with_defaults(
        cell__url=lambda row, **_: row.get_absolute_url() + 'edit/',
        display_name=gettext_lazy('Edit'),
    )
    def edit(cls, **kwargs):
        # language=rst
        """
        Shortcut for creating a clickable edit icon. The URL defaults to `your_object.get_absolute_url() + 'edit/'`. Specify the option cell__url to override.

        .. code-block:: python

            table = Table(
                auto__model=Album,
                columns__edit=Column.edit(after=0),
            )

            # @test
            show_output(table)
            # @end
        """
        return cls.icon(**kwargs)

    @classmethod
    @with_defaults(
        cell__url=lambda row, **_: row.get_absolute_url() + 'delete/',
        display_name=gettext_lazy('Delete'),
    )
    def delete(cls, **kwargs):
        # language=rst
        """
        Shortcut for creating a clickable delete icon. The URL defaults to `your_object.get_absolute_url() + 'delete/'`. Specify the option cell__url to override.

        .. code-block:: python

            table = Table(
                auto__model=Album,
                columns__delete=Column.delete(),
            )

            # @test
            show_output(table)
            # @end
        """

        return cls.icon(**kwargs)

    @classmethod
    @with_defaults(
        cell__url=lambda row, **_: row.get_absolute_url() + 'download/',
        cell__value=lambda row, **_: getattr(row, 'pk', False),
        display_name=gettext_lazy('Download'),
    )
    def download(cls, **kwargs):
        # language=rst
        """
        Shortcut for creating a clickable download icon. The URL defaults to `your_object.get_absolute_url() + 'download/'`. Specify the option cell__url to override.


        .. code-block:: python

            table = Table(
                auto__model=Album,
                columns__download=Column.download(),
            )

            # @test
            show_output(table)
            # @end
        """
        return cls.icon(**kwargs)

    @classmethod
    @with_defaults(
        cell__url=lambda row, **_: row.get_absolute_url() + 'run/',
        display_name=gettext_lazy('Run'),
    )
    def run(cls, **kwargs):
        # language=rst
        """
        Shortcut for creating a clickable run icon. The URL defaults to `your_object.get_absolute_url() + 'run/'`. Specify the option cell__url to override.


        .. code-block:: python

            table = Table(
                auto__model=Album,
                columns__run=Column.run(),
            )

            # @test
            show_output(table)
            # @end
        """
        return cls.icon(**kwargs)

    @classmethod
    @with_defaults(
        header__template='iommi/table/select_column_header.html',
        sortable=False,
        filter__is_valid_filter=lambda **_: (True, ''),
        filter__field__include=False,
        attr=None,
        cell__value=lambda table, cells, row, **_: (
            row.pk
            if isinstance(table.rows, QuerySet)
            # row_index is the visible row number
            # See selection() for the code that does the lookup
            else cells.row_index
        ),
        cell__format=lambda column, row, value, **kwargs: format_html(
            # language=HTML
            '<input type="checkbox" class="checkbox" name="{checkbox_name}_{row_id}" {checked_str} />',
            checkbox_name=column.extra.checkbox_name,
            row_id=value,
            checked_str=(
                'checked'
                if evaluate_strict(column.extra.checked, column=column, row=row, value=value, **kwargs)
                else ''
            ),
        ),
        extra__checkbox_name='pk',
        extra__checked=lambda **_: False,
        extra__icon='fa fa-check-square-o',
    )
    def select(cls, **kwargs):
        # language=rst
        """
        Shortcut for a column of checkboxes to select rows. This is useful for implementing bulk operations.

        By default tables have a column named `select` that is hidden that is used for this purpose, so you only
        need to turn it on to get it. See the example below.

        To implement a custom post handler that operates on the selected rows, do

         .. code-block:: python

            def my_handler(table):
                rows = table.selection()
                # rows will either be a queryset, or a list of elements
                # matching the type of rows of the table
                ...

            table = Table(
                auto__model=Album,
                columns__select__include=True,
                bulk__actions__submit=Action.submit(post_handler=my_handler)
            )

            # @test
            show_output(table)
            my_handler(table.bind(request=req('get')))
            # @end

        :param extra__checkbox_name: the name of the checkbox. Default is `"pk"`, resulting in checkboxes like `"pk_1234"`.
        :param extra__checked: callable to specify if the checkbox should be checked initially. Defaults to `False`.
        """
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        filter__call_target__attribute='boolean',
        filter__field__call_target__attribute='boolean_tristate',
        bulk__call_target__attribute='boolean',
        cell__format=lambda value, **_: mark_safe(f'<span title="{gettext_lazy("Yes")}">&#10004;</span>') if value else '',
    )
    def boolean(cls, **kwargs):
        # language=rst
        """
        Shortcut to render booleans as a check mark if true or blank if false.


        .. code-block:: python

            table = Table(
                columns__name=Column(),
                columns__boolean=Column.boolean(),
                rows=[
                    Struct(name='true!', boolean=True),
                    Struct(name='false!', boolean=False),
                ]
            )

            # @test
            show_output(table)
            # @end

        """
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        filter__call_target__attribute='boolean_tristate',
    )
    def boolean_tristate(cls, **kwargs):
        # language=rst
        """
        This shortcut sets up `boolean_tristate` for the filter.
        """

        return cls.boolean(**kwargs)

    @classmethod
    @with_defaults(
        bulk__call_target__attribute='choice',
        bulk__choices=get_choices_from_column,
        filter__call_target__attribute='choice',
        filter__choices=get_choices_from_column,
    )
    def choice(cls, **kwargs):
        # language=rst
        """
        This shortcut sets up `choices` for the filter and bulk form.
        """
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        bulk__call_target__attribute='choice_queryset',
        filter__call_target__attribute='choice_queryset',
    )
    def choice_queryset(cls, **kwargs):
        # language=rst
        """
        This shortcut sets up `choices` for the filter and bulk form for the choice queryset case.
        """
        setdefaults_path(
            kwargs,
            dict(
                bulk__model=kwargs.get('model'),
                filter__model=kwargs.get('model'),
            ),
        )
        return cls.choice(**kwargs)

    @classmethod
    @with_defaults(
        bulk__call_target__attribute='multi_choice_queryset',
        filter__call_target__attribute='multi_choice_queryset',
    )
    def multi_choice_queryset(cls, **kwargs):
        # language=rst
        """
        This shortcut sets up `choices` for the filter and bulk form for the multi choice queryset case.
        """
        setdefaults_path(
            kwargs,
            dict(
                bulk__model=kwargs.get('model'),
                filter__model=kwargs.get('model'),
            ),
        )
        return cls.choice_queryset(**kwargs)

    @classmethod
    @with_defaults(
        bulk__call_target__attribute='multi_choice',
        filter__call_target__attribute='multi_choice',
    )
    def multi_choice(cls, **kwargs):
        # language=rst
        """
        This shortcut sets up `choices` for the filter and bulk form for the multi choice case.
        """
        setdefaults_path(
            kwargs,
            dict(
                bulk__model=kwargs.get('model'),
                filter__model=kwargs.get('model'),
            ),
        )
        return cls.choice(**kwargs)

    @classmethod
    def checkboxes(cls, **kwargs):
        return cls.multi_choice(**kwargs)

    @classmethod
    @with_defaults(
        bulk__call_target__attribute='text',
        filter__call_target__attribute='text',
    )
    def text(cls, **kwargs):
        # language=rst
        """
        This is an explicit synonym for `Column()`.
        """
        return cls(**kwargs)

    @classmethod
    @with_defaults
    def textarea(cls, **kwargs):
        return cls.text(**kwargs)

    @classmethod
    @with_defaults
    def link(cls, **kwargs):
        # language=rst
        """
        Shortcut for creating a cell that is a link. The URL is the result of calling `get_absolute_url()` on the object.
        """

        def link_cell_url(column, row, **_):
            r = getattr_path(row, column.attr)
            return r.get_absolute_url() if r else ''

        setdefaults_path(
            kwargs,
            dict(
                cell__url=link_cell_url,
            ),
        )
        return cls(**kwargs)

    @classmethod
    @with_defaults
    def number(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        filter__call_target__attribute='float',
        bulk__call_target__attribute='float',
    )
    def float(cls, **kwargs):
        return cls.number(**kwargs)

    @classmethod
    @with_defaults(
        filter__call_target__attribute='integer',
        bulk__call_target__attribute='integer',
    )
    def integer(cls, **kwargs):
        return cls.number(**kwargs)

    @classmethod
    @with_defaults(
        filter__query_operator_for_field=':',
    )
    def substring(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        filter__call_target__attribute='date',
        filter__query_operator_to_q_operator=lambda op: {'=': 'exact', ':': 'contains'}.get(op)
        or Q_OPERATOR_BY_QUERY_OPERATOR[op],
        bulk__call_target__attribute='date',
    )
    def date(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        filter__call_target__attribute='datetime',
        filter__query_operator_to_q_operator=lambda op: {'=': 'exact', ':': 'contains'}.get(op)
        or Q_OPERATOR_BY_QUERY_OPERATOR[op],
        bulk__call_target__attribute='datetime',
    )
    def datetime(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        filter__call_target__attribute='time',
        filter__query_operator_to_q_operator=lambda op: {'=': 'exact', ':': 'contains'}.get(op)
        or Q_OPERATOR_BY_QUERY_OPERATOR[op],
        bulk__call_target__attribute='time',
    )
    def time(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        filter__call_target__attribute='email',
        bulk__call_target__attribute='email',
    )
    def email(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        bulk__call_target__attribute='decimal',
        filter__call_target__attribute='decimal',
    )
    def decimal(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        bulk__call_target__attribute='file',
        filter__call_target__attribute='file',
        cell__format=lambda value, **_: str(value),
    )
    def file(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        bulk__call_target__attribute='duration',
        filter__call_target__attribute='duration',
    )
    def duration(cls, **kwargs):
        return cls.text(**kwargs)

    @classmethod
    @with_defaults(
        bulk__call_target__attribute='many_to_many',
        filter__call_target__attribute='many_to_many',
        cell__format=lambda value, **_: ', '.join(['%s' % x for x in value.all()]),
        data_retrieval_method=DataRetrievalMethods.prefetch,
        sortable=False,
        extra__django_related_field=True,
    )
    def many_to_many(cls, model_field, **kwargs):
        setdefaults_path(
            kwargs,
            choices=model_field.remote_field.model.objects.all(),
            model_field=model_field,
        )
        return cls.multi_choice_queryset(**kwargs)

    @classmethod
    @with_defaults(
        bulk__call_target__attribute='many_to_many_reverse',
        filter__call_target__attribute='many_to_many_reverse',
        display_name=lambda column, **_: capitalize(column.model_field.remote_field.model._meta.verbose_name_plural),
    )
    def many_to_many_reverse(cls, model_field, **kwargs):
        return cls.many_to_many(model_field=model_field, **kwargs)

    @classmethod
    @with_defaults(
        bulk__call_target__attribute='foreign_key',
        filter__call_target__attribute='foreign_key',
        data_retrieval_method=DataRetrievalMethods.select,
        sort_key=foreign_key__sort_key,
    )
    def foreign_key(cls, model_field, **kwargs):
        remote_model = model_field.remote_field.model
        if hasattr(remote_model, 'get_absolute_url'):
            setdefaults_path(
                kwargs,
                cell__url=lambda value, **_: value.get_absolute_url() if value is not None else None,
            )
        setdefaults_path(
            kwargs,
            choices=remote_model.objects.all(),
        )
        return cls.choice_queryset(model_field=model_field, **kwargs)

    @classmethod
    @with_defaults(
        bulk__call_target__attribute='foreign_key_reverse',
        filter__call_target__attribute='foreign_key_reverse',
        cell__format=lambda value, **_: ', '.join(['%s' % x for x in value.all()]),
        data_retrieval_method=DataRetrievalMethods.prefetch,
        sortable=False,
        extra__django_related_field=True,
        display_name=lambda column, **_: capitalize(column.model_field.remote_field.model._meta.verbose_name_plural),
    )
    def foreign_key_reverse(cls, *, model_field, **kwargs):
        setdefaults_path(
            kwargs,
            choices=model_field.remote_field.model.objects.all(),
        )
        return cls.multi_choice_queryset(model_field=model_field, **kwargs)


@with_meta
class Cells(Traversable, Tag):
    """
    Internal class used in row rendering.

    You can access the current row via `.row` and the current row index via `.row_index`.
    """

    template: Union[str, Template] = EvaluatedRefinable()
    attrs: Attrs = SpecialEvaluatedRefinable()
    tag: str = EvaluatedRefinable()
    extra: Dict[str, Any] = Refinable()
    # not EvaluatedRefinable because this is an evaluated container so is special
    extra_evaluated: Dict[str, Any] = Refinable()
    cell_class: Type['Cell'] = Refinable()

    def __init__(self, row, row_index, cell_class=None, **kwargs):
        # This doesn't use a nice Meta definition because it would be a circular
        if cell_class is None:
            cell_class = Cell
        super(Cells, self).__init__(_name='row', cell_class=cell_class, **kwargs)
        assert not isinstance(row, Cells)
        self.row: Any = row
        self.row_index = row_index

    def own_evaluate_parameters(self):
        return dict(cells=self, row=self.row)

    def get_table(self):
        return self.iommi_evaluate_parameters()['table']

    def __html__(self):
        if self.template:
            return render_template(self.iommi_parent().get_request(), self.template, self.iommi_evaluate_parameters())

        return self.render()

    def render(self):
        return TransientFragment(
            tag=self.tag,
            attrs=self.attrs,
            children=dict(text=mark_safe('\n'.join(bound_cell.__html__() for bound_cell in self))),
            parent=self,
        ).__html__()

    def __str__(self):
        return self.__html__()

    def __iter__(self):
        for column in values(self.get_table().columns):
            if not column.render_column:
                continue
            yield self.cell_class(cells=self, column=column).refine_done(parent=self)

    def __len__(self):
        return self.column_count()

    def column_count(self):
        return len([x for x in values(self.get_table().columns) if x.render_column])

    def __getitem__(self, name):
        column = self.iommi_parent().columns[name]
        return self.cell_class(cells=self, column=column).refine_done(parent=self)


class RowGroup(Fragment):
    def __init__(self, *, value, **kwargs):
        super(RowGroup, self).__init__(**kwargs)
        self.value = value

    def get_context(self):
        return {**super(RowGroup, self).get_context(), 'value': self.value}

    def own_evaluate_parameters(self):
        return dict(row_group=self)


class CellConfig(RefinableObject, Tag):
    url: str = Refinable()
    url_title: str = Refinable()
    attrs: Attrs = Refinable()
    tag: str = Refinable()
    template: Union[str, Template] = Refinable()
    value = Refinable()
    contents = Refinable()
    format: Callable = Refinable()
    link: Namespace = Refinable()


class Cell(CellConfig):
    @dispatch
    def __init__(self, cells: Cells, column):
        kwargs = setdefaults_path(
            Namespace(),
            column.cell,
            column.table.cell,
        )
        super(Cell, self).__init__(**kwargs)
        self._name = 'cell'
        self._parent = cells
        self._is_bound = True
        self.iommi_style = None
        self._unapplied_config = {}

        self.column = column
        self.cells = cells
        self.table = cells.get_table()
        self.row = cells.row

    def on_refine_done(self):
        self._evaluate_parameters = merged(
            self.column.iommi_evaluate_parameters(),
            cells=self.cells,
            column=self.column,
            row=self.row,
            bound_cell=self,
        )

        self.value = evaluate_strict(self.value, **self._evaluate_parameters)
        self._evaluate_parameters['value'] = self.value
        self.url = evaluate_strict(self.url, **self._evaluate_parameters)
        self.attrs = evaluate_attrs(self, **self._evaluate_parameters)
        self.url_title = evaluate_strict(self.url_title, **self._evaluate_parameters)
        self.tag = evaluate_strict(self.tag, **self._evaluate_parameters)

    @property
    def iommi_dunder_path(self):
        return path_join(self.column.iommi_dunder_path, 'cell', separator='__')

    def iommi_evaluate_parameters(self):
        return self._evaluate_parameters

    def __html__(self):
        cell__template = self.column.cell.template
        if cell__template:
            context = self._evaluate_parameters
            return render_template(self.table.get_request(), cell__template, context)

        if self.tag:
            return format_html('<{}{}>{}</{}>', self.tag, self.attrs, self.render_cell_contents(), self.tag)
        else:
            return format_html('{}', self.render_cell_contents())

    def render_cell_contents(self):
        cell_contents = self.render_formatted()

        url = self.url
        if url:
            url_title = self.url_title
            # TODO: `url`, `url_title` and `link` is overly complex
            cell_contents = TransientFragment(
                parent=self,
                tag='a',
                attrs__title=url_title,
                attrs__href=url,
                children__content=cell_contents,
                **self.link,
            ).__html__()
        return cell_contents

    def render_formatted(self):
        return evaluate_strict(self.column.cell.format, **self._evaluate_parameters)

    def __str__(self):
        return self.__html__()

    def __repr__(self):
        return f"<{type(self).__name__} column={self.column.declared_column!r} row={self.cells.row!r}>"

    def get_context(self):
        return self.cells.get_context()

    def get_request(self):
        return self.cells.get_request()


class TemplateConfig(RefinableObject):
    template: str = Refinable()


@with_meta
class HeaderConfig(Traversable, Tag):
    tag: str = EvaluatedRefinable()
    attrs: Attrs = SpecialEvaluatedRefinable()
    template: Union[str, Template] = EvaluatedRefinable()
    extra: Dict[str, Any] = Refinable()
    extra_evaluated: Dict[str, Any] = Refinable()
    include: bool = SpecialEvaluatedRefinable()

    class Meta:
        include = True
        template = MISSING

    def __html__(self):
        if self.template is None:
            return ''
        if self.template is not MISSING:
            return render_template(self.iommi_parent().get_request(), self.template, self.iommi_evaluate_parameters())

        return self.render()

    def render(self):
        children = {}
        header_levels = self.iommi_parent().header_levels
        assert len(header_levels) in (1, 2)

        def header_list_to_transient_fragment(header_list):
            return TransientFragment(
                tag='tr',
                attrs={},
                children={f'header_{i}': v for i, v in enumerate(header_list)},
                parent=self,
            )

        if len(header_levels) > 1:
            children['superheader'] = header_list_to_transient_fragment(header_levels[0])

        children['subheader'] = header_list_to_transient_fragment(header_levels[-1])

        return TransientFragment(
            tag=self.tag,
            attrs=self.attrs,
            children=children,
            parent=self,
        ).__html__()

    def __str__(self):
        return self.__html__()


class HeaderColumnConfig(Traversable):
    attrs: Attrs = SpecialEvaluatedRefinable()
    template: Union[str, Template] = EvaluatedRefinable()
    url = EvaluatedRefinable()


class RowConfig(RefinableObject, Tag):
    attrs: Attrs = SpecialEvaluatedRefinable()
    tag = Refinable()
    template: Union[str, Template] = Refinable()
    extra: Dict[str, Any] = Refinable()
    extra_evaluated: Dict[str, Any] = Refinable()

    def as_dict(self):
        return {k: getattr(self, k) for k in keys(self.get_declared('refinable'))}


class ColumnHeader:
    """
    Internal class implementing a column header. For configuration options
    read the docs for :doc:`HeaderConfig`.
    """

    class Meta:
        attrs = EMPTY

    @dispatch
    def __init__(
        self,
        *,
        display_name,
        attrs,
        template,
        table,
        url=None,
        column=None,
        number_of_columns_in_group=None,
        index_in_group=None,
    ):
        self.table = table
        self.display_name = mark_safe(display_name)
        self.template = template
        self.url = url
        self.column = column
        self.number_of_columns_in_group = number_of_columns_in_group
        self.index_in_group = index_in_group
        self.attrs = attrs
        self._name = 'header'
        self.attrs = evaluate_attrs(self, table=table, column=column, header=self)

    def __html__(self):
        return self.rendered

    @property
    def rendered(self):
        return render_template(self.table.get_request(), self.template, dict(header=self))

    def __repr__(self):
        return f'<Header: {"superheader" if self.column is None else self.column._name}>'

    @property
    def iommi_dunder_path(self):
        if self.column is None:
            return None
        return path_join(self.column.iommi_dunder_path, self._name, separator='__')


def bulk__post_handler(table, form, **_):
    if not form.is_valid():
        return

    queryset = table.bulk_queryset()

    simple_updates = []
    m2m_updates = []
    for field in values(form.fields):
        if field.value is None:
            continue
        if field.value in ['', []]:
            continue
        if field.attr is None:
            continue

        if isinstance(field.model_field, ManyToManyField):
            assert '__' not in field.attr, "Nested m2m relations is currently not supported for bulk editing"
            m2m_updates.append(field)
        else:
            simple_updates.append(field)

    updates = {field.attr: field.value for field in simple_updates}
    m2m_updates = {field.attr: field.value for field in m2m_updates}

    pks = list(queryset.values_list('pk', flat=True))

    queryset.model.objects.filter(pk__in=pks).update(**updates)

    if m2m_updates:
        for obj in queryset:
            for attr, value in items(m2m_updates):
                getattr(obj, attr).set(value)
            obj.save()

    response = table.invoke_callback(
        table.post_bulk_edit,
        pks=pks,
        queryset=queryset,
        updates=updates,
        m2m_updates=m2m_updates,
    )

    if response is not None:
        return response

    return HttpResponseRedirect(form.get_request().META.get('HTTP_REFERER', '/'))


def bulk_delete__post_handler(table, form, **_):
    if not form.is_valid():
        return

    queryset = table.bulk_queryset()

    from iommi.page import (
        Page,
    )

    class ConfirmPage(Page):
        title = html.h1(
            gettext_lazy('Are you sure you want to delete these {count} items?').format(count=queryset.count())
        )
        confirm = Table(
            auto__rows=queryset,
            columns__select=dict(
                include=True,
                extra__checked=True,
                bulk__include=True,
                bulk__attrs__style__display='none',
            ),
            bulk=dict(
                fields__confirmed=Field.hidden(initial='confirmed'),
                actions__submit__include=False,
                actions__delete=dict(
                    attrs__name=table.bulk.actions.delete.attrs.name,
                    call_target__attribute='delete',
                    display_name=gettext_lazy('Yes, delete all!'),
                    include=True,
                ),
            ),
        )

    request = form.get_request()
    # We need to remove the target for the old delete button that we pressed to get here,
    # otherwise ConfirmPage will give an error saying it can't find that button
    request.POST = request.POST.copy()
    del request.POST[form.actions.delete.own_target_marker()]

    p = ConfirmPage().bind(request=request)

    if request.POST.get(p.parts.confirm.bulk.fields.confirmed.iommi_path) == 'confirmed':
        queryset.delete()
        return HttpResponseRedirect(form.get_request().META.get('HTTP_REFERER', '/'))

    return HttpResponse(render_root(part=p))


def paginator__count(rows, **_):
    if isinstance(rows, QuerySet):
        return rows.count()
    try:
        return len(rows)
    except TypeError:
        return None


@with_meta
class Paginator(Traversable, Tag):
    tag: str = Refinable()
    attrs: Attrs = SpecialEvaluatedRefinable()
    template: Union[str, Template] = EvaluatedRefinable()
    container = Refinable()
    page: int = SpecialEvaluatedRefinable()
    active_item = Refinable()
    item = Refinable()
    link = Refinable()
    active_link = Refinable()
    adjacent_pages: int = Refinable()
    min_page_size: int = Refinable()
    number_of_pages: int = SpecialEvaluatedRefinable()
    count: int = SpecialEvaluatedRefinable()
    slice = Refinable()
    show_always = Refinable()

    class Meta:
        attrs__class = EMPTY
        attrs__style = EMPTY
        container__attrs__class = EMPTY
        container__attrs__style = EMPTY
        active_item__attrs__class = EMPTY
        active_item__attrs__style = EMPTY
        item__attrs__class = EMPTY
        item__attrs__style = EMPTY
        link__attrs__class = EMPTY
        link__attrs__style = EMPTY
        active_link__attrs__class = EMPTY
        active_link__attrs__style = EMPTY

    @with_defaults(
        adjacent_pages=6,
        min_page_size=1,
        page=1,
        count=paginator__count,
        number_of_pages=lambda paginator, rows, **_: ceil(
            max(1, (paginator.count - (paginator.min_page_size - 1))) / paginator.page_size
        ),
        slice=lambda top, bottom, rows, **_: rows[bottom:top],
    )
    def __init__(self, **kwargs):
        super(Paginator, self).__init__(**kwargs)

    def on_refine_done(self):
        self.context = None
        self.page_size = None
        self.rows = None

        self.active_link = Namespace(self.link, self.active_link)
        self.active_item = Namespace(self.item, self.active_item)

        super(Paginator, self).on_refine_done()

    def on_bind(self) -> None:
        request = self.get_request()
        table = self.iommi_evaluate_parameters()['table']
        page_size = None
        if request:
            page_size_str = request.GET.get(self.iommi_path + '_size')
            if page_size_str is not None:
                try:
                    page_size = int(page_size_str)
                except ValueError:
                    pass
        self.page_size = page_size if page_size is not None else table.page_size

        rows = table.sorted_and_filtered_rows
        evaluate_parameters = merged(
            self.iommi_evaluate_parameters(),
            page_size=self.page_size,
            rows=rows,
        )

        # TODO: will arguments to these that don't hit tag/attrs be silently ignored?
        self.attrs = evaluate_attrs(self, **evaluate_parameters)
        self.container.attrs = evaluate_attrs(self.container, **evaluate_parameters)
        self.active_item.attrs = evaluate_attrs(self.active_item, **evaluate_parameters)
        self.item.attrs = evaluate_attrs(self.item, **evaluate_parameters)
        self.link.attrs = evaluate_attrs(self.link, **evaluate_parameters)
        self.active_link.attrs = evaluate_attrs(self.active_link, **evaluate_parameters)

        self.container.tag = evaluate_strict(self.container.tag, **evaluate_parameters)
        self.active_item.tag = evaluate_strict(self.active_item.tag, **evaluate_parameters)
        self.item.tag = evaluate_strict(self.item.tag, **evaluate_parameters)
        self.link.tag = evaluate_strict(self.link.tag, **evaluate_parameters)
        self.active_link.tag = evaluate_strict(self.active_link, **evaluate_parameters)

        if self.page_size is None:
            self.number_of_pages = 1
            self.count = None
        else:
            self.count = evaluate_strict(self.count, **evaluate_parameters) if rows is not None else 0
            if self.count is None:
                self.number_of_pages = 1
            else:
                self.number_of_pages = evaluate_strict(self.number_of_pages, **evaluate_parameters)

        page = request.GET.get(self.iommi_path) if request else None
        page = evaluate_strict(self.page, **evaluate_parameters) if page is None else int(page)
        self.page = page

        if self.page > self.number_of_pages:
            self.page = self.number_of_pages
        elif self.page < 1:
            self.page = 1

        self.context = self.iommi_evaluate_parameters().copy()

        if self.number_of_pages != 1:
            bottom = (self.page - 1) * self.page_size
            top = bottom + self.page_size
            if top + self.min_page_size - 1 >= self.count:
                top = self.count
            paginated_rows = self.slice(**evaluate_parameters, bottom=bottom, top=top)
            self.rows = paginated_rows
        else:
            self.rows = evaluate_parameters['rows']

        foo = self.page
        if foo <= self.adjacent_pages:
            foo = self.adjacent_pages + 1
        elif foo > self.number_of_pages - self.adjacent_pages:
            foo = self.number_of_pages - self.adjacent_pages
        page_numbers = [
            n
            for n in range(self.page - self.adjacent_pages, foo + self.adjacent_pages + 1)
            if 0 < n <= self.number_of_pages
        ]

        get = params_of_request(request)

        if self.iommi_path in get:
            del get[self.iommi_path]

        self.context.update(
            dict(
                extra=get and (get.urlencode() + "&") or "",
                page_numbers=page_numbers,
                show_first=1 not in page_numbers,
                show_last=self.number_of_pages not in page_numbers,
            )
        )

        has_next = self.page < self.number_of_pages
        has_previous = self.page > 1
        self.context.update(
            {
                'page_size': table.page_size,
                'has_next': has_next,
                'has_previous': has_previous,
                'next': self.page + 1 if has_next else None,
                'previous': self.page - 1 if has_previous else None,
                'page': self.page,
                'pages': self.number_of_pages,
                'hits': self.count,
                'paginator': self,
            }
        )

    def own_evaluate_parameters(self):
        return dict(paginator=self)

    def is_paginated(self):
        assert self._is_bound, NOT_BOUND_MESSAGE
        return self.number_of_pages > 1

    def __html__(self):
        assert self._is_bound, NOT_BOUND_MESSAGE
        if not self.show_always:
            if self.page_size is None:
                return ''

            if self.number_of_pages <= 1:
                return ''

        return render_template(
            request=self.get_request(),
            template=self.template,
            context=self.context,
        )

    def __str__(self):
        return self.__html__()


class TableAutoConfig(AutoConfig):
    """
    :param rows: A `QuerySet` object. If this field is specified, the `model` attribute will be automatically derived. This cannot be a callable, in that case set `model` and use `rows=lambda...` instead of `auto__rows`.
    """

    rows = Refinable()

def endpoint__tbody(table, **_):
    return {
        'html': table.container.__html__(
            render=lambda fragment, context: fragment.render_text_or_children(context=context)
        )
    }


def endpoint__csv(table, **_):
    from datetime import timezone

    columns = [c for c in values(table.columns) if c.extra_evaluated.get('report_name')]
    csv_safe_column_indexes = {i for i, c in enumerate(values(table.columns)) if 'csv_whitelist' in c.extra}
    assert columns, 'To get CSV output you must specify at least one column with extra_evaluated__report_name'
    assert (
        'report_name' in table.extra_evaluated
    ), 'To get CSV output you must specify extra_evaluated__report_name on the table'
    filename = table.extra_evaluated.report_name + '.csv'

    header = [c.extra_evaluated.report_name for c in columns]

    def smart_text2(s):
        if s is None:
            return ''
        elif isinstance(s, float):
            result = ('%f' % s).strip('0')
            if result[-1] == '.':
                result += '0'
            return result
        else:
            assert not isinstance(s, bytes)
            return str(s).strip()

    def safe_csv_value(value):
        # CSV formula injection protection: http://georgemauer.net/2017/10/07/csv-injection.html
        if value and value[0] in ('+', '-', '@', '='):
            return '\t' + value
        else:
            return value

    def cell_value(cells, bound_column):
        value = Cell(cells, bound_column).refine_done(parent=cells).value
        return bound_column.extra_evaluated.get('report_value', value)

    def rows():
        for cells in table.cells_for_rows(paginate=False):
            if isinstance(cells, Cells):
                yield [cell_value(cells, bound_column) for bound_column in columns]

    def write_csv_row(writer, row):
        row_strings = [smart_text2(value) for value in row]
        safe_row = [v if i in csv_safe_column_indexes else safe_csv_value(v) for i, v in enumerate(row_strings)]
        writer.writerow(safe_row)

    csv_writer_kwargs = table.extra_evaluated.get('csv_writer_kwargs', {})

    f = StringIO()
    writer = csv.writer(f, **csv_writer_kwargs)
    writer.writerow(header)
    for row in rows():
        write_csv_row(writer, row)

    response = FileResponse(f.getvalue(), 'text/csv')

    # RFC 2183, RFC 2184
    response['Content-Disposition'] = smart_str(
        "attachment; filename*=UTF-8''{value}".format(value=quote_plus(filename))
    )
    response['Last-Modified'] = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
    return response


class _Lazy_tbody:
    def __init__(self, table):
        self.table = table

    def __html__(self):
        return mark_safe('\n'.join([cells.__html__() for cells in self.table.cells_for_rows()]))


@declarative(Column, '_columns_dict', add_init_kwargs=False)
@with_meta
class Table(Part, Tag):
    # language=rst
    """
    Describe a table. Example:

    .. code-block:: python

        class AlbumTable(Table):
            name = Column()
            artist = Column()

            class Meta:
                sortable = False

        # @test
        artist = Artist.objects.create(name='Black Sabbath')
        Album.objects.create(name='Heaven & Hell', artist=artist, year=1980),
        Album.objects.create(name='Mob Rules', artist=artist, year=1981),

        show_output(AlbumTable(rows=Album.objects.all()))
        # @end
    """

    query = Refinable()
    bulk_filter: Namespace = EvaluatedRefinable()
    bulk_exclude: Namespace = EvaluatedRefinable()
    sortable: bool = EvaluatedRefinable()
    query_from_indexes: bool = Refinable()
    default_sort_order = Refinable()
    attrs: Attrs = SpecialEvaluatedRefinable()
    template: Union[str, Template] = EvaluatedRefinable()
    tag: str = EvaluatedRefinable()
    h_tag: Union[Fragment, str] = SpecialEvaluatedRefinable()
    title: str = SpecialEvaluatedRefinable()
    row: RowConfig = EvaluatedRefinable()
    cell: CellConfig = EvaluatedRefinable()
    header = Refinable()
    model: Type[Model] = SpecialEvaluatedRefinable()
    rows = SpecialEvaluatedRefinable()
    actions: Dict[str, Action] = RefinableMembers()
    parts: Namespace = RefinableMembers()
    bulk: Optional[Form] = EvaluatedRefinable()
    bulk_container: Fragment = Refinable()
    superheader: Namespace = Refinable()
    paginator: Paginator = Refinable()
    page_size: int = EvaluatedRefinable()
    actions_template: Union[str, Template] = EvaluatedRefinable()
    actions_below: bool = EvaluatedRefinable()
    tbody: Fragment = EvaluatedRefinable()
    container: Fragment = EvaluatedRefinable()
    table_tag_wrapper: Fragment = EvaluatedRefinable()
    outer: Fragment = EvaluatedRefinable()

    member_class = Refinable()
    form_class: Type[Form] = Refinable()
    query_class: Type[Query] = Refinable()
    action_class: Type[Action] = Refinable()
    page_class: Type[Page] = Refinable()
    cells_class: Type[Cells] = Refinable()
    row_group_class: Type[RowGroup] = Refinable()

    empty_message: str = EvaluatedRefinable()
    invalid_form_message: str = EvaluatedRefinable()
    auto: TableAutoConfig = Refinable()

    # Columns need to be at the end to not steal the short names
    columns: Dict[str, Column] = RefinableMembers()

    class Meta:
        member_class = Column
        form_class = Form
        query_class = Query
        action_class = Action
        page_class = Page
        cells_class = Cells
        row_group_class = RowGroup

        columns = EMPTY
        parts = EMPTY
        row__attrs__class = EMPTY
        row__attrs__style = EMPTY
        row__extra = EMPTY
        row__extra_evaluated = EMPTY
        actions = EMPTY
        query = EMPTY
        bulk__fields = EMPTY
        endpoints = EMPTY
        auto = EMPTY
        attrs__class = EMPTY
        attrs__style = EMPTY
        table_tag_wrapper = EMPTY

    @staticmethod
    @refinable
    def preprocess_rows(rows, **_):
        # TODO: Should we rename this into preprocess_visible_rows ?
        return rows

    @staticmethod
    @refinable
    def preprocess_row(table, row, **_):
        # TODO: Should we rename this into preprocess_visible_row ?
        del table
        return row

    @staticmethod
    @refinable
    def post_bulk_edit(table, queryset, updates, **_):
        pass

    @with_defaults(
        bulk_filter={},
        bulk_exclude={},
        sortable=True,
        default_sort_order=None,
        template='iommi/table/table.html',
        tbody__call_target=Fragment,
        tbody__tag='tbody',
        container__tag='div',
        container__attrs__class={'iommi-table-container': True},
        container__children__text__template='iommi/table/table_container.html',
        container__call_target=Fragment,
        table_tag_wrapper__call_target=Fragment,
        outer__call_target=Fragment,
        row__tag='tr',
        row__attrs={'data-pk': lambda row, **_: getattr(row, 'pk', None)},
        row__template=None,
        cell__tag='td',
        header=EMPTY,
        h_tag__call_target=Header,
        actions_template='iommi/form/actions.html',
        actions_below=False,
        bulk__title=gettext_lazy('Bulk change'),
        bulk_container__call_target=Fragment,
        page_size=DEFAULT_PAGE_SIZE,
        superheader__attrs__class__superheader=True,
        superheader__template='iommi/table/header.html',
        tag='table',
        parts__page__call_target=Paginator,
        # The filter action on a table will often not be the primary
        # action button on the page. So let's use the secondary
        # style
        query__form__actions__submit__call_target=Action.button,
        title=MISSING,
        endpoints__tbody__func=endpoint__tbody,
        endpoints__csv__func=endpoint__csv,
        query__advanced__assets__query_form_toggle_script__template = "iommi/query/form_toggle_script.html",
        query__form__attrs = {
            'data-iommi-id-of-table': lambda table, **_: table.iommi_path,
        },
        assets__table_js_select_all__template = "iommi/table/js_select_all.html",
        container__attrs ={
            'data-endpoint': lambda table, **_: DISPATCH_PREFIX + table.endpoints.tbody.iommi_path,
            'data-iommi-id': lambda table, **_: table.iommi_path,
        },
    )
    def __init__(
        self,
        **kwargs,
    ):
        """
        :param rows: a list or QuerySet of objects
        :param columns: (use this only when not using the declarative style) a list of Column objects
        :param attrs: dict of strings to string/callable of HTML attributes to apply to the table
        :param row__attrs: dict of strings to string/callable of HTML attributes to apply to the row. Callables are passed the row as argument.
        :param row__template: name of template (or `Template` object) to use for rendering the row
        :param bulk_filter: filters to apply to the `QuerySet` before performing the bulk operation
        :param bulk_exclude: exclude filters to apply to the `QuerySet` before performing the bulk operation
        :param sortable: set this to `False` to turn off sorting for all columns
        """
        super(Table, self).__init__(**kwargs)

    def on_refine_done(self):
        extra_column_defaults = {}
        extra_column_defaults['select'] = dict(
            call_target__attribute='select',
            attr=None,
            after=-1,
            include=False,
        )

        model = self.model
        rows = self.rows
        if self.auto:
            auto = TableAutoConfig(**self.auto).refine_done(parent=self)
            auto_model, auto_rows, columns_from_auto = self._from_model(
                model=auto.model,
                rows=auto.rows,
                include=auto.include,
                exclude=auto.exclude,
                default_included=auto.default_included,
            )

            assert 'select' not in columns_from_auto

            assert model is None, (
                "You can't use the auto feature and explicitly pass model. "
                "Either pass auto__model, or we will set the model for you from auto__rows"
            )
            model = auto_model

            if rows is None:
                rows = auto_rows

            if self.title is MISSING:
                self.title = capitalize(model._meta.verbose_name_plural)
        else:
            columns_from_auto = None

        if self.title is MISSING:
            self.title = None

        self.model, self.rows = model_and_rows(model, rows)

        self.initial_rows = self.rows
        self.header = HeaderConfig(_name='header', **self.header).refine_done(parent=self)
        self.row = RowConfig(**self.row).refine_done(parent=self)
        self._preprocessed_rows = None

        # In bind initial_rows will be used to set these 3 (in that order)
        self.sorted_rows = None
        self.sorted_and_filtered_rows = None
        self.visible_rows = None

        refine_done_members(
            self,
            name='actions',
            members_from_namespace=self.actions,
            cls=self.get_meta().action_class,
            members_cls=Actions,
        )
        refine_done_members(
            self,
            name='columns',
            members_from_namespace=self.columns,
            members_from_declared=self.get_declared('_columns_dict'),
            members_from_auto=columns_from_auto,
            cls=self.get_meta().member_class,
            extra_member_defaults=extra_column_defaults,
        )

        if not self.sortable:
            for column in values(self.iommi_namespace.columns):
                # Special case for entire table not sortable
                column.sortable = False

        refine_done_members(self, name='parts', members_from_namespace=self.parts, cls=Fragment)

        query_args = self.query
        bulk_args = self.bulk

        self.query: Query = None
        self.bulk: Form = None
        self.header_levels = None

        def add_hidden_all_pks_field(declared_bulk_fields):
            declared_bulk_fields._all_pks_ = form_class.get_meta().member_class.hidden(
                _name='_all_pks_',
                attr=None,
                initial='0',
                required=False,
                input__attrs__class__all_pks=True,
            )

        form_class = self.get_meta().form_class
        if self.model:
            # Query
            filters = Struct()

            field_class = self.get_meta().query_class.get_meta().member_class

            for name, column in items(self.iommi_namespace.columns):
                if getattr(column, 'include', None) is False:
                    continue
                if getattr(column.filter, 'include', None) is False:
                    continue
                filter = setdefaults_path(
                    Namespace(),
                    column.filter,
                    call_target__cls=field_class,
                    model=column.model,
                    model_field_name=column.model_field_name,
                    _name=name,
                    attr=name if column.attr is MISSING else column.attr,
                    field__call_target__cls=self.get_meta().query_class.get_meta().form_class.get_meta().member_class,
                    field__display_name=column.display_name,
                )
                # Special case for automatic query config
                should_have_filter = bool(
                    self.query_from_indexes
                    and column.model_field
                    and (getattr(column.model_field, 'db_index', False) or isinstance(column.model_field, AutoField))
                )
                setdefaults_path(
                    filter,
                    include=should_have_filter,
                )

                filters[name] = filter()

            self.query = self.get_meta().query_class(
                **setdefaults_path(
                    Namespace(),
                    query_args,
                    filters=filters,
                    _name='query',
                    model=self.model,
                )
            )

            declared_filters = self.query.iommi_namespace.filters
            self.query = self.query.refine(Prio.table_defaults, filters=declared_filters)

            # Bulk
            field_class = self.get_meta().form_class.get_meta().member_class

            declared_bulk_fields = Struct()
            for name, column in items(self.iommi_namespace.columns):
                if getattr(column, 'include', None) is False:
                    continue
                if getattr(column.bulk, 'include', None) is False:
                    continue
                field = setdefaults_path(
                    Namespace(),
                    column.bulk,
                    dict(
                        call_target__cls=field_class,
                        model=self.model,
                        model_field_name=column.model_field_name,
                        _name=name,
                        attr=name if column.attr is MISSING else column.attr,
                        required=False,
                        parse_empty_string_as_none=True,
                        display_name=column.display_name,
                        initial=None,
                    ),
                )
                if isinstance(column.model_field, BooleanField):
                    field.call_target.attribute = 'boolean_tristate'

                declared_bulk_fields[name] = field

            add_hidden_all_pks_field(declared_bulk_fields)

            # x.bulk.include can be a callable here. We treat that as truthy on purpose.
            if (
                any(x.bulk.include for x in values(self.iommi_namespace.columns))
                or 'actions' in self.iommi_namespace.bulk
            ):
                self.bulk = form_class(
                    **setdefaults_path(
                        Namespace(),
                        bulk_args,
                        _name='bulk',
                        model=self.model,
                        actions__submit=dict(
                            post_handler=bulk__post_handler,
                            display_name=gettext_lazy('Bulk change'),
                            include=lambda table, **_: any(c.bulk.include for c in values(table.columns)),
                        ),
                        actions__delete=dict(
                            call_target__attribute='delete',
                            post_handler=bulk_delete__post_handler,
                            display_name=gettext_lazy('Bulk delete'),
                            include=False,
                        ),
                    )
                ).refine(
                    Prio.table_defaults,
                    fields=declared_bulk_fields,
                )

        if not self.model and not self.bulk and 'actions' in self.iommi_namespace.bulk:
            # TODO: Support custom 'bulk' actions even when there is no model
            if any(x.bulk.include for x in values(self.iommi_namespace.columns)):
                assert False, "The builtin bulk actions only work on querysets."
            declared_bulk_fields = Struct()
            add_hidden_all_pks_field(declared_bulk_fields)
            self.bulk = form_class(
                _name='bulk',
                # We don't want form's default submit button unless somebody
                # explicitly added it again.
                actions__submit=bulk_args['actions'].get('submit', None),
                **bulk_args,
            ).refine(
                Prio.table_defaults,
                fields=declared_bulk_fields,
            )

        if self.bulk is not None:
            self.bulk = self.bulk.refine_done(parent=self)

        if self.query is not None:
            self.query = self.query.refine_done(parent=self)

        self.bulk_container = self.bulk_container(_name='bulk_container').refine_done(parent=self)
        self.container = self.container(_name='container').refine_done(parent=self)
        self.table_tag_wrapper = self.table_tag_wrapper(_name='table_tag_wrapper').refine_done(parent=self)

        self.outer = (
            self.outer(_name='outer').refine(
                children=dict(
                    h_tag__template=Template('{{ table.h_tag|default_if_none:"" }}'),
                    query__template=Template('{{ table.query|default_if_none:"" }}'),
                    actions=dict(
                        after=LAST if self.actions_below else 'h_tag',
                        template=Template('{{ table.render_actions|default_if_none:"" }}'),
                    ),
                    container__template=Template('{{ table.container|default_if_none:"" }}'),
                ),
            )
        ).refine_done(parent=self)

        self.tbody = self.tbody(_name='tbody').refine_done(parent=self)

        super(Table, self).on_refine_done()

    @classmethod
    @with_defaults(
        tag='div',
        tbody__tag='div',
        cell__tag=None,
        row__tag='div',
        header__template=None,
    )
    def div(cls, **kwargs):
        return cls(**kwargs)

    @property
    def paginator(self):
        return self.parts.page

    def on_bind(self) -> None:
        bind_members(self, name='actions')
        bind_members(self, name='columns')
        bind_members(self, name='endpoints')
        bind_members(self, name='parts')

        self.title = evaluate_strict(self.title, **self.iommi_evaluate_parameters())
        build_and_bind_h_tag(self)

        bind_member(self, name='tbody')
        self.tbody.children.text = _Lazy_tbody(self)
        self.tbody.children = sort_after(self.tbody.children)

        bind_member(self, name='container')
        bind_member(self, name='table_tag_wrapper')
        bind_member(self, name='outer')
        bind_member(self, name='header')
        if self.header is None:
            self.header = ''

        # needs to be done first because _bind_headers depends on it
        evaluate_member(self, 'sortable', **self.iommi_evaluate_parameters())

        evaluate_member(self, 'model', __strict=False, **self.iommi_evaluate_parameters())
        evaluate_member(self, 'initial_rows', **self.iommi_evaluate_parameters())

        if isinstance(self.initial_rows, QuerySet):
            # Copy the QuerySet so we don't get the original QuerySets result cache
            self.initial_rows = self.initial_rows.all()
            self.rows = self.initial_rows

        self._prepare_sorting()

        self._bind_query()
        self._bind_bulk_form()
        self._bind_headers()

        # If the column is not included, the down stream query filters and bulk fields should also be gone
        for name, column in items(self.iommi_namespace.columns):
            if name not in keys(self.columns):
                if self.query and name in self.query.filters:
                    del self.query.filters[name]
                if self.query and self.query.form and name in self.query.form.fields:
                    del self.query.form.fields[name]
                    del self.query.form.parts[name]
                if self.bulk and name in self.bulk.fields:
                    del self.bulk.fields[name]

        if isinstance(self.sorted_and_filtered_rows, QuerySet):
            prefetch = [
                x.attr
                for x in values(self.columns)
                if x.data_retrieval_method == DataRetrievalMethods.prefetch and x.attr
            ]
            select = [
                x.attr
                for x in values(self.columns)
                if x.data_retrieval_method == DataRetrievalMethods.select and x.attr
            ]
            if prefetch:
                self.sorted_and_filtered_rows = self.sorted_and_filtered_rows.prefetch_related(*prefetch)
                self.rows = self.sorted_and_filtered_rows
            if select:
                self.sorted_and_filtered_rows = self.sorted_and_filtered_rows.select_related(*select)
                self.rows = self.sorted_and_filtered_rows

        bind_member(self, name='bulk_container')

    def get_visible_rows(self):
        if self.visible_rows is None:
            self.visible_rows = self.parts.page.rows
        return self.visible_rows

    def _bind_query(self):
        """
        Bind the query form and apply it.
        """
        self.sorted_and_filtered_rows = self.sorted_rows
        self.rows = self.sorted_and_filtered_rows

        if self.query is None:
            return

        bind_member(self, name='query')

        if self.query is not None:
            self.sorted_and_filtered_rows = self.invoke_callback(
                self.query.filter, query=self.query, rows=self.sorted_rows
            )
            self.rows = self.sorted_and_filtered_rows
        else:
            self.sorted_and_filtered_rows = self.sorted_rows
            self.rows = self.sorted_and_filtered_rows

        if self.query and self.query.form and (self.query.form.get_errors() or self.query.query_error):
            if isinstance(self.initial_rows, QuerySet):
                empty_result = self.initial_rows.none()
            else:
                empty_result = []
            self.rows = self.sorted_and_filtered_rows = self.sorted_rows = empty_result

    def _bind_bulk_form(self):
        if self.bulk is None:
            return

        bind_member(self, name='bulk')
        if self.should_render_form_tag():
            self._bound_members.bulk = self.bulk
        else:
            self.bulk = None

    # property for jinja2 compatibility
    @property
    def render_actions(self):
        assert self._is_bound, NOT_BOUND_MESSAGE
        non_grouped_actions, grouped_actions = group_actions(self.actions)
        return render_template(
            self.get_request(),
            self.actions_template,
            dict(
                actions=self.iommi_bound_members().actions,
                non_grouped_actions=non_grouped_actions,
                grouped_actions=grouped_actions,
                table=self,
            ),
        )

    def _prepare_auto_rowspan(self):
        auto_rowspan_columns = [column for column in values(self.columns) if column.auto_rowspan]
        if auto_rowspan_columns:
            no_value_set = object()
            for column in auto_rowspan_columns:
                if column.cell.attrs.get('rowspan', no_value_set) is not no_value_set:
                    continue

                rowspan_by_row = {}  # cells for rows in this dict are displayed, if they're not in here, they get style="display: none"
                prev_value = no_value_set
                prev_row = no_value_set
                for cells in self.cells_for_rows():
                    value = Cell(cells, column).refine_done(parent=self).value
                    if prev_value != value:
                        rowspan_by_row[id(cells.row)] = 1
                        prev_value = value
                        prev_row = cells.row
                    else:
                        rowspan_by_row[id(prev_row)] += 1

                def rowspan(row, **_):
                    return rowspan_by_row[id(row)] if id(row) in rowspan_by_row else None

                def auto_rowspan_style(row, **_):
                    return 'none' if id(row) not in rowspan_by_row else ''

                column.cell.attrs['rowspan'] = rowspan
                if 'style' not in column.cell.attrs:
                    column.cell.attrs['style'] = {}
                column.cell.attrs['style']['display'] = auto_rowspan_style

    def _prepare_sorting(self):
        """Sort all the rows.

        self.sorted_rows = sorted(self.initial_rows)
        """
        # TODO: Sorting less values is faster then sorting more values, so we should
        # filter first and then sort.
        self.sorted_rows = self.initial_rows
        self.rows = self.sorted_rows
        request = self.get_request()
        if request is None:
            return

        # `or self.default_sort_order` is on purpose here, because an empty string should go to default_sort_order too
        order = request.GET.get(path_join(self.iommi_path, 'order')) or self.default_sort_order
        if order is not None:
            descending = order.startswith('-')
            order_field = order[1:] if descending else order
            sort_column = self.columns.get(order_field, None)
            if sort_column is None:
                return
            if sort_column.sortable:
                sort_key = sort_column.sort_key
                self.sorted_rows = self.invoke_callback(
                    self.sorter,
                    rows=self.initial_rows,
                    sort_key=sort_key,
                    descending=descending,
                )
                self.rows = self.sorted_rows

    @staticmethod
    @refinable
    def sorter(
        rows: Union[QuerySet, list],
        sort_key: str,
        descending: bool,
        table,
        **_,
    ):
        if isinstance(rows, list):
            return ordered_by_on_list(rows, sort_key, descending)
        else:
            sort_keys = [sort_key] if not isinstance(sort_key, list) else sort_key
            sort_keys = [('-' + x if descending else x) for x in sort_keys]
            if table.model._meta.ordering:
                sort_keys.extend(table.model._meta.ordering)
            if sort_keys[-1] != 'pk':
                sort_keys.append('pk')  # Add pk to always guarantee stable order for pagination.
            return rows.order_by(*sort_keys)

    def _bind_headers(self):
        prepare_headers(self)

        superheaders = []
        subheaders = []

        # The id(header) and stuff is to make None not be equal to None in the grouping
        for _, group_iterator in groupby(
            (x for x in values(self.columns) if x.render_column), key=lambda header: header.group or id(header)
        ):
            columns_in_group = list(group_iterator)
            group_name = columns_in_group[0].group

            number_of_columns_in_group = len(columns_in_group)

            superheaders.append(
                ColumnHeader(
                    display_name=group_name or '',
                    table=self,
                    attrs=self.superheader.attrs,
                    attrs__colspan=number_of_columns_in_group,
                    template=self.superheader.template,
                )
            )

            for i, column in enumerate(columns_in_group):
                subheaders.append(
                    ColumnHeader(
                        display_name=column.display_name,
                        table=self,
                        attrs=column.header.attrs,
                        template=column.header.template,
                        url=column.header.url,
                        column=column,
                        number_of_columns_in_group=number_of_columns_in_group,
                        index_in_group=i,
                    )
                )

        if all(c.display_name == '' for c in superheaders):
            superheaders = None

        if superheaders is None:
            self.header_levels = [subheaders]
        else:
            self.header_levels = [superheaders, subheaders]

    def own_evaluate_parameters(self):
        return dict(table=self)

    def cells_for_rows(self, paginate=True):
        """Yield a Cells instance for each visible row on the screen."""
        assert self._is_bound, NOT_BOUND_MESSAGE
        if paginate:
            rows = self.get_visible_rows()
        else:
            rows = self.sorted_and_filtered_rows
        if not self._preprocessed_rows:
            self._preprocessed_rows = list(self.invoke_callback(self.preprocess_rows, rows=rows))

        row_groups = [c for c in values(self.columns) if c.row_group.include]
        row_group_values = {c._name: None for c in row_groups}

        for i, row in enumerate(self._preprocessed_rows):
            row = self.invoke_callback(self.preprocess_row, row=row)
            assert row is not None, 'preprocess_row must return the row'

            for column in row_groups:
                v = getattr_path(row, column.attr)
                old_value = row_group_values[column._name]
                if old_value != v:
                    # noinspection PyCallingNonCallable
                    yield self.row_group_class(**column.row_group, value=v).bind(parent=self).__html__()
                row_group_values[column._name] = v

            # noinspection PyCallingNonCallable
            yield self.cells_class(row=row, row_index=i, **self.row.as_dict()).bind(parent=self)

    @classmethod
    @dispatch()
    def columns_from_model(cls, **kwargs):
        return create_members_from_model(
            member_class=cls.get_meta().member_class,
            **kwargs,
        )

    @classmethod
    @dispatch()
    def _from_model(cls, *, rows=None, model=None, include=None, exclude=None, default_included=True):
        assert rows is None or isinstance(rows, QuerySet), (
            'auto__rows needs to be a QuerySet for column generation to work. '
            'If it needs to be a lambda, provide a model with auto__model for column generation, '
            f'and pass the lambda as rows. I got a {type(rows)}'
        )

        model, rows = model_and_rows(model, rows)
        assert model is not None or rows is not None, "auto__model or auto__rows must be specified"
        columns = cls.columns_from_model(
            model=model, include=include, exclude=exclude, default_included=default_included
        )
        return model, rows, columns

    def _selection_identifiers(self, prefix):
        """Return a list of identifiers of the selected rows. Or 'all' if all
        sorted_and_filtered_rows are selected."""
        # TODO: this needs to be namespaced
        if self.get_request().POST.get('_all_pks_') == '1':
            return 'all'
        else:
            return [key[len(prefix) :] for key in self.get_request().POST if key.startswith(prefix)]

    def selection(self, prefix='pk_'):
        """Return the selected rows.

        For use in post_handlers. It's a queryset if rows is a queryset and a list otherwise.
        Unlike bulk_queryset neither bulk_filter nor bulk_exclude are applied.
        """
        identifiers = self._selection_identifiers(prefix=prefix)
        if identifiers == 'all':
            return self.sorted_and_filtered_rows
        else:
            if isinstance(self.sorted_and_filtered_rows, QuerySet):
                return self.sorted_and_filtered_rows.filter(pk__in=identifiers)
            else:
                identifiers = frozenset([int(i) for i in identifiers])
                return [row for ndx, row in enumerate(self.get_visible_rows()) if ndx in identifiers]

    def bulk_queryset(self, prefix='pk_'):
        """Return the queryset that contains only the selected rows with
        bulk_filter and bulk_exclude applied.

        For use in post_handlers. Only valid when rows was a queryset.
        """
        assert isinstance(self.initial_rows, QuerySet), "bulk_queryset can only be used on querysets"

        return self.selection(prefix=prefix).filter(**self.bulk_filter).exclude(**self.bulk_exclude)

    def should_render_form_tag(self):
        return bool(self.bulk and self.bulk.actions)

    @dispatch(
        render=render_template,
    )
    def __html__(self, *, template=None, render=None):
        assert self._is_bound, NOT_BOUND_MESSAGE

        request = self.get_request()

        self._prepare_auto_rowspan()

        assert self.get_visible_rows() is not None

        context = self.iommi_evaluate_parameters().copy()

        return render(request=request, template=template or self.template, context=context)

    def as_view(self):
        return build_as_view_wrapper(self)
