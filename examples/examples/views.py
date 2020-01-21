from os.path import (
    abspath,
    dirname,
    join,
)

from django.http import HttpResponse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from tri_struct import Struct
from iommi import (
    Action,
    Column,
    Table,
    Page,
)
from iommi.form import (
    Field,
    Form,
    choice_parse,
)

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
    return HttpResponse(
        """<html><body>
        <a href="form/">form examples</a><br/>
        <a href="table/">table examples</a><br/>
        </body></html>""")


def form_index(request):
    return HttpResponse(
        """<html><body>
        <a href="example_1/">Example 1</a><br/>
        <a href="example_2/">Example 2 create</a><br/>
        <a href="example_3/">Example 3 edit</a><br/>
        <a href="example_4/">Example 4 custom buttons</a><br/>
        <a href="example_5/">Example 5 automatic AJAX endpoint</a><br/>
        <a href="kitchen/">Kitchen sink</a><br/>
        </body></html>""")


def form_style(request):
    return HttpResponse(open(join(dirname(dirname(dirname(abspath(__file__)))), 'form.css')).read())


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

    return HttpResponse(format_html(
        """
            <html>
                <body>
                    {}
                    {}
                </body>
            </html>
        """,
        form.render_part(),
        message))


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
        base_template='iommi/form/base_select2.html',
        fields__b__input_template='iommi/form/choice_select2.html',
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


def table_index(request):
    return HttpResponse(
        """<html><body>
        <a href="readme_example_1/">Example 1 from the README</a><br/>
        <a href="readme_example_2/">Example 2 from the README</a><br/>
        <a href="kitchen_sink/">Kitchen sink</a><br/>
        </body></html>""")


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

        class Meta:
            template = 'base.html'

    # now to get an HTML table:
    return FooTable(data=foos)


def fill_dummy_data():
    if not Bar.objects.all():
        # Fill in some dummy data if none exists
        for i in range(200):
            f = TFoo.objects.create(a=i, name='Foo: %s' % i)
            TBar.objects.create(b=f, c='foo%s' % (i % 3))


def table_readme_example_2(request):
    fill_dummy_data()

    class BarTable(Table):
        select = Column.select()  # Shortcut for creating checkboxes to select rows
        b__a = Column.number(  # Show "a" from "b". This works for plain old objects too.
            query__show=True,  # put this field into the query language
            query__gui__show=True)  # put this field into the simple filtering GUI
        c = Column(
            bulk__show=True,  # Enable bulk editing for this field
            query__show=True,
            query__gui__show=True)

    return BarTable(data=Bar.objects.all(), template='base.html', paginate_by=20)


def table_kitchen_sink(request):
    fill_dummy_data()

    class BarTable(Table):
        select = Column.select()  # Shortcut for creating checkboxes to select rows
        b__a = Column.number()  # Show "a" from "b". This works for plain old objects too.
        b = Column.choice_queryset(
            show=False,
            choices=TFoo.objects.all(),
            model=TFoo,
            bulk__show=True,
            query__show=True,
            query__gui__show=True,
        )
        c = Column(bulk__show=True)  # The form is created automatically

        d = Column(display_name='Display name',
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
                   cell__url_title='cell url title')
        e = Column(group='Foo', cell__value='explicit value', sortable=False)
        f = Column(show=False, sortable=False)
        g = Column(attr='c', sortable=False)
        django_templates_for_cells = Column(sortable=False, cell__value=None, cell__template='kitchen_sink_cell_template.html')

        class Meta:
            name = 'bar'
            model = Bar
            template = 'base.html'
            page_size = 20

    return BarTable(data=Bar.objects.all())


# TODO: Page, Fragment examples
# TODO: admin
