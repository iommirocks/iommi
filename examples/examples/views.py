from os.path import dirname, abspath, join

from django.http import HttpResponse
from django.utils.safestring import mark_safe
from django.utils.html import format_html

from examples.models import Foo
from tri_form import Form, Field, Link
from tri_form.views import create_object, edit_object


def index(request):
    return HttpResponse(
        """<html><body>
        <a href="example_1/">Example 1</a><br/>
        <a href="example_2/">Example 2 create</a><br/>
        <a href="example_3/">Example 3 edit</a><br/>
        <a href="example_4/">Example 4 custom buttons</a><br/>
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
