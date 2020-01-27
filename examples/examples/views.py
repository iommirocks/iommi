from os.path import (
    abspath,
    dirname,
    join,
)

from django.http import HttpResponse
from django.template import (
    RequestContext,
    Template,
)
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from iommi import (
    Action,
    Column,
    Page,
    Table,
    html,
)
from iommi.admin import admin
from iommi.form import (
    Field,
    Form,
    choice_parse,
)
from tri_struct import Struct

from .models import (
    Bar,
    Foo,
    TBar,
    TFoo,
)


def ensure_objects():
    for i in range(100 - Foo.objects.count()):
        Foo.objects.create(name=f'X{i}', a=i, b=True)


def index(request):
    class AdminPage(Page):
        admin_header = html.h2('Admin example')

        admin_a = html.a('Admin', attrs__href="iommi-admin/")

    class IndexPage(Page):
        header = html.h1('iommi examples')

        form_header = html.h2('Form examples')

        # We can create html fragments...
        f_a_1 = html.a('Example 1: echo submitted data', attrs__href="form_example_1/")
        f_b_1 = html.br()
        f_a_2 = html.a('Example 2: create a Foo', attrs__href="form_example_2/")
        f_b_2 = html.br()
        f_a_3 = html.a('Example 3: edit a Foo', attrs__href="form_example_3/")
        f_b_3 = html.br()
        f_a_4 = html.a('Example 4: custom buttons', attrs__href="form_example_4/")
        f_b_4 = html.br()
        f_a_5 = html.a('Example 5: automatic AJAX endpoint', attrs__href="form_example_5/")
        f_b_5 = html.br()
        f_a_k = html.a('Kitchen sink', attrs__href="form_kitchen/")

        table_header = html.h2('Table examples')

        # ...or just throw a big chunk of html in here
        table_links = mark_safe("""
        <a href="table_readme_example_1/">Example 1 from the README</a><br>
        <a href="table_readme_example_2/">Example 2 from the README</a><br>
        <a href="table_kitchen_sink/">Kitchen sink</a><br>
        """)

        # You can also nest pages
        admin = AdminPage()


    return IndexPage()


def form_example_1(request):
    class MyForm(Form):
        foo = Field()
        bar = Field()

    form = MyForm()
    form.bind(request=request)

    message = mark_safe("\n".join(
        format_html(
            "{}: {}",
            name,
            bound_field.value
        )
        for name, bound_field in form.fields.items())
    )

    return HttpResponse(
        Template("""
            {% extends "base.html" %} 
            {% block content %}
                {{ form }} 
                {{ message }} 
            {% endblock %}
        """).render(
            context=RequestContext(
                request,
                dict(form=form, message=message)
            )
        ),
    )


def form_example_2(request):
    ensure_objects()
    return Form.as_create_page(model=Foo)


def form_example_3(request):
    ensure_objects()
    return Form.as_edit_page(instance=Foo.objects.all().first())


def form_example_4(request):
    ensure_objects()
    return Form.as_edit_page(
        instance=Foo.objects.all().first(),
        actions=dict(
            foo=Action.submit(attrs__value='Foo'),
            bar=Action.submit(attrs__value='Bar'),
            back=Action(display_name='Back to index', attrs__href='/'),
        )
    )


def form_example_5(request):
    ensure_objects()
    return Form.as_create_page(
        model=Bar,
        fields__b__input__template='iommi/form/choice_select2.html',
        actions=dict(
            foo=Action.submit(attrs__value='Foo'),
            bar=Action.submit(attrs__value='Bar'),
            back=Action(display_name='Back to index', attrs__href='/'),
        )
    )


class KitchenForm(Form):
    class Meta:
        name = 'kitchen'

    foo = Field()

    fisk = Field.multi_choice(
        choices=[1, 2, 3, 4],
        parse=choice_parse,
        initial_list=[1, 2],
        editable=False
    )


class SinkForm(Form):
    class Meta:
        name = 'sink'

    foo = Field()


def form_kitchen(request):
    ensure_objects()

    def kitchen_form_post_handler(form, **_):
        values = form.apply(Struct())
        return HttpResponse(format_html("Kitchen values was {}", values))

    def sink_form_post_handler(form, **_):
        values = form.apply(Struct())
        return HttpResponse(format_html("Sink values was {}", values))

    class KitchenPage(Page):
        kitchen_form = KitchenForm(post_handler=kitchen_form_post_handler)
        sink_form = SinkForm(post_handler=sink_form_post_handler)
        sink_form2 = SinkForm(name='sinkform2')

    return KitchenPage()


def table_style(request):
    return HttpResponse(open(join(dirname(dirname(dirname(abspath(__file__)))), 'table.css')).read())


def table_readme_example_1(request):
    # Say I have a class...
    class Foo(object):
        def __init__(self, i):
            self.a = i
            self.b = 'foo %s' % (i % 3)
            self.c = (i, 1, 2, 3, 4)

    # and a list of them
    foos = [Foo(i) for i in range(4)]

    # I can declare a table:
    class FooTable(Table):
        a = Column.number()  # This is a shortcut that results in the css class "rj" (for right justified) being added to the header and cell
        b = Column()
        c = Column(cell__format=lambda value, **_: value[-1])  # Display the last value of the tuple
        sum_c = Column(cell__value=lambda row, **_: sum(row.c), sortable=False)  # Calculate a value not present in Foo

    # now to get an HTML table:
    return FooTable(rows=foos)


def fill_dummy_data():
    if not TBar.objects.all():
        # Fill in some dummy data if none exists
        for i in range(200):
            f = TFoo.objects.create(a=i, name='Foo: %s' % i)
            TBar.objects.create(b=f, c='foo%s' % (i % 3))


def table_readme_example_2(request):
    fill_dummy_data()

    class BarTable(Table):
        select = Column.select()  # Shortcut for creating checkboxes to select rows
        # TODO: this doesn't work anymore :(
        b__a = Column.number(  # Show "a" from "b". This works for plain old objects too.
            query__show=True,  # put this field into the query language
            query__gui__show=True,  # put this field into the simple filtering GUI
        )
        c = Column(
            bulk__show=True,  # Enable bulk editing for this field
            query__show=True,
            query__gui__show=True,
        )

    return BarTable(rows=TBar.objects.all(), page_size=20)


def table_kitchen_sink(request):
    fill_dummy_data()

    class BarTable(Table):
        select = Column.select()  # Shortcut for creating checkboxes to select rows
        b__a = Column.number()  # Show "a" from "b". This works for plain old objects too.

        b = Column.from_model(
            render_column=False,
            model=TBar,
            field_name='b',
            bulk__show=True,
            query__show=True,
            query__gui__show=True,
        )
        c = Column(bulk__show=True)  # The form is created automatically

        d = Column(
            display_name='Display name',
            attr__class__css_class=True,
            url='url',
            sortable=False,
            group='Foo',
            auto_rowspan=True,
            cell__value=lambda row, **_: row.b.a // 3,
            cell__format=lambda value, **_: '- %s -' % value,
            cell__attrs__class__cj=True,
            cell__attrs__title='cell title',
            cell__url='url',
            cell__url_title='cell url title',
        )
        e = Column(group='Foo', cell__value='explicit value', sortable=False)
        f = Column(show=False, sortable=False)
        g = Column(attr='c', sortable=False)
        django_templates_for_cells = Column(sortable=False, cell__value=None, cell__template='kitchen_sink_cell_template.html')

        class Meta:
            name = 'bar'
            page_size = 20

    return BarTable(rows=TBar.objects.all())


def iommi_admin(request, **kwargs):
    del request
    return admin(
        all_models__app__sessions__session__show=False,
        list_model__app__auth__user__table__columns=dict(
            # groups__query=dict(show=True, gui__show=True),
            # email__call_target__attribute='freetext_search',
            # username__call_target__attribute='freetext_search',
            username__query__freetext=True,
            username__query__show=True,
            # first__call_target__attribute='freetext',
            # last__call_target__attribute='freetext',
            password__show=False,
        ),
        **kwargs,
    )
