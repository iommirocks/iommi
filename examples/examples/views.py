from django import forms
from examples.models import Bar, Foo
from os.path import dirname, abspath, join
from django.http import HttpResponse
from tri.tables import Table, render_table_to_response
from tri.tables import Column


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
    foos = [Foo(i) for i in xrange(4)]

    # I can declare a table:
    class FooTable(Table):
        a = Column.number()  # This is a shortcut that results in the css class "rj" (for right justified) being added to the header and cell
        b = Column()
        c = Column(cell_format=lambda value: value[-1])  # Display the last value of the tuple
        sum_c = Column(cell_value=lambda row: sum(row.c), sortable=False)  # Calculate a value not present in Foo

    # now to get an HTML table:
    return render_table_to_response(request, FooTable(foos), template_name='base.html')

def fill_dummy_data():
    if not Bar.objects.all():
        # Fill in some dummy data if none exists
        for i in xrange(200):
            f = Foo.objects.create(a=i)
            Bar.objects.create(b=f, c='foo%s' % (i % 3))

def readme_example_2(request):
    fill_dummy_data()

    class BarTable(Table):
        select = Column.select()  # Shortcut for creating checkboxes to select rows
        b__a = Column.number()  # Show "a" from "b". This works for plain old objects too.
        c = Column(bulk=True)  # The form is created automatically

    return render_table_to_response(request, BarTable(Bar.objects.all()), template_name='base.html', paginate_by=20)


def kitchen_sink(request):
    fill_dummy_data()

    class BarTable(Table):
        select = Column.select()  # Shortcut for creating checkboxes to select rows
        b__a = Column.number()  # Show "a" from "b". This works for plain old objects too.
        b = Column(show=False, filter_field=forms.ChoiceField(choices=[('', '')] + [(x.pk, x) for x in Foo.objects.all()[:10]]))
        c = Column(bulk=True)  # The form is created automatically
        # TODO: examples for filter_field, filter_type
        d = Column(display_name='Display name',
                   css_class='css_class',
                   url='url',
                   title='title',
                   sortable=False,
                   group='Foo',
                   filter=False,
                   auto_rowspan=True,
                   cell_value=lambda row: row.b.a // 3,
                   cell_format=lambda value: '- %s -' % value,
                   cell_attrs={
                       'class': lambda row: 'cj',
                       'title': 'cell title'},
                   cell_url='url',
                   cell_url_title='cell url title')
        e = Column(group='Foo', cell_value='explicit value', filter=False, sortable=False)
        f = Column(show=False, filter=False, sortable=False)
        g = Column(attr='c', filter=False)
        django_templates_for_cells = Column(filter=False, sortable=False, cell_template='kitchen_sink_cell_template.html')

    return render_table_to_response(request, BarTable(Bar.objects.all()), template_name='base.html', paginate_by=20)
