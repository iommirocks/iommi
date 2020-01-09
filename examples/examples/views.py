from os.path import dirname, abspath, join
from tri.struct import Struct

from django.http import HttpResponse
from django.utils.safestring import mark_safe
from django.utils.html import format_html

from .models import Foo, Bar
from tri_form import Form, Field, Link, choice_parse
from tri_form.views import create_object, edit_object

for i in range(100 - Foo.objects.count()):
    Foo.objects.create(name=f'X{i}', a=i, b=True)


def index(request):
    return HttpResponse(
        """<html><body>
        <a href="example_1/">Example 1</a><br/>
        <a href="example_2/">Example 2 create</a><br/>
        <a href="example_3/">Example 3 edit</a><br/>
        <a href="example_4/">Example 4 custom buttons</a><br/>
        <a href="example_5/">Example 5 automatic AJAX endpoint</a><br/>
        <a href="kitchen/">Kitchen sink</a><br/>
        </body></html>""")


def style(request):
    return HttpResponse(open(join(dirname(dirname(dirname(abspath(__file__)))), 'form.css')).read())


def example_1(request):
    class MyForm(Form):
        foo = Field()
        bar = Field()

    form = MyForm(request=request)

    message = mark_safe("\n".join(
        format_html(
            "{}: {}",
            name,
            bound_field.value
        )
        for name, bound_field in form.fields_by_name.items()))

    return HttpResponse(format_html(
        """
            <html>
                <body>
                    {}
                    {}
                </body>
            </html>
        """,
        form.render(),
        message))


def example_2(request):
    return create_object(request, model=Foo)


def example_3(request):
    return edit_object(request, instance=Foo.objects.all().first())


def example_4(request):
    return edit_object(
        request,
        instance=Foo.objects.all().first(),
        form__links=[
            Link.submit(attrs__value='Foo'),
            Link.submit(attrs__value='Bar'),
            Link(title='Back to index', attrs__href='/'),
        ]
    )


def example_5(request):
    return create_object(
        request,
        model=Bar,
        form__base_template='tri_form/base_select2.html',
        form__field__b__input_template='tri_form/choice_select2.html',
        form__links=[
            Link.submit(attrs__value='Foo'),
            Link.submit(attrs__value='Bar'),
            Link(title='Back to index', attrs__href='/'),
        ]
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


def kitchen(request):
    kitchen_form = KitchenForm(request)
    sink_form = SinkForm(request)
    sink_form2 = SinkForm(request, name='sinkform2')

    if request.method == 'POST':
        if kitchen_form.is_target() and kitchen_form.is_valid():
            values = kitchen_form.apply(Struct())
            return HttpResponse(format_html("Kitchen values was {}", values))

        if sink_form.is_target() and sink_form.is_valid():
            values = sink_form.apply(Struct())
            return HttpResponse(format_html("Sink values was {}", values))

    return HttpResponse(format_html(
        """\
            <html>
                <body>
                    <h2>Kitchen</h2>
                    {}
                    <h2>Sink</h2>
                    {}
                    <h2>Sink</h2>
                    {}
                </body>
            </html>
        """,
        kitchen_form.render(),
        sink_form.render(),
        sink_form2.render()))


from .models import Bar, Foo
from os.path import dirname, abspath, join
from django.http import HttpResponse
from tri_table import Table, render_table_to_response
from tri_table import Column


def index(request):
    return HttpResponse(
        """<html><body>
        <a href="readme_example_1/">Example 1 from the README</a><br/>
        <a href="readme_example_2/">Example 2 from the README</a><br/>
        <a href="kitchen_sink/">Kitchen sink</a><br/>
        </body></html>""")


def style(request):
    return HttpResponse(open(join(dirname(dirname(dirname(abspath(__file__)))), 'table.css')).read())


def readme_example_1(request):
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
        c = Column(cell__format=lambda table, column, row, value, **_: value[-1])  # Display the last value of the tuple
        sum_c = Column(cell__value=lambda table, column, row, **_: sum(row.c), sortable=False)  # Calculate a value not present in Foo

    # now to get an HTML table:
    return render_table_to_response(request, table=FooTable(data=foos), template='base.html')


def fill_dummy_data():
    if not Bar.objects.all():
        # Fill in some dummy data if none exists
        for i in range(200):
            f = Foo.objects.create(a=i, name='Foo: %s' % i)
            Bar.objects.create(b=f, c='foo%s' % (i % 3))


def readme_example_2(request):
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

    return render_table_to_response(request, table=BarTable(data=Bar.objects.all()), template='base.html', paginate_by=20)


def kitchen_sink(request):
    fill_dummy_data()

    class BarTable(Table):
        select = Column.select()  # Shortcut for creating checkboxes to select rows
        b__a = Column.number()  # Show "a" from "b". This works for plain old objects too.
        b = Column.choice_queryset(
            show=False,
            choices=Foo.objects.all(),
            model=Foo,
            bulk__show=True,
            query__show=True,
            query__gui__show=True,
        )
        c = Column(bulk__show=True)  # The form is created automatically

        d = Column(display_name='Display name',
                   css_class={'css_class'},
                   url='url',
                   title='title',
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

    return render_table_to_response(request, table=BarTable(data=Bar.objects.all()), template='base.html', paginate_by=20)
