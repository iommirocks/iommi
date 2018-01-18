from .models import Bar, Foo
from os.path import dirname, abspath, join
from django.http import HttpResponse
from tri.table import Table, render_table_to_response
from tri.table import Column


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
            model = Bar

    return render_table_to_response(request, table=BarTable(data=Bar.objects.all()), template='base.html', paginate_by=20)
