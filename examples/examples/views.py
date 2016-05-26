from os.path import dirname, abspath, join

from django.http import HttpResponse, HttpResponseRedirect
from django.utils.safestring import mark_safe
from django.utils.html import format_html

from examples.models import Foo
from tri.form import Form, Field
from tri.form.views import create_or_edit_object, create_object, edit_object


def index(request):
    return HttpResponse(
        """<html><body>
        <a href="example_1/">Example 1</a><br/>
        <a href="example_2/">Example 2 create</a><br/>
        <a href="example_3/">Example 3 edit</a><br/>
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
        form.render(request),
        message))


def example_2(request):
    return create_object(request, model=Foo)


def example_3(request):
    return edit_object(request, instance=Foo.objects.all().first())
