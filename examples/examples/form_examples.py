from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.template import (
    RequestContext,
    Template,
)
from django.urls import path
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext
from tri_struct import Struct

from examples import (
    example_adding_decorator,
    example_links,
)
from examples.models import (
    Artist,
    Track,
)
from examples.views import (
    all_field_sorts,
    ExamplesPage,
)
from iommi import (
    Action,
    Field,
    Form,
    html,
    Page,
)
from iommi.form import choice_parse

examples = []

example = example_adding_decorator(examples)


@example(gettext("Use much like a django form"))
def form_example_1(request):
    class FruitForm(Form):
        name = Field()
        amount = Field.integer()
        color = Field.choice(
            choices=['Red', 'Green', 'Blue'],
        )

    form = FruitForm().bind(request=request)
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
            {% extends "iommi/base.html" %} 
            {% block content %}
                {{ form }} 
                {{ message }} 
            {% endblock %}
        """).render(
            context=RequestContext(
                request,
                dict(title='Example 1', form=form, message=message)
            )
        ),
    )


@example(gettext(("Use more ideomatic like an iommi part")))
def form_example_2(request):
    class FruitForm(Form):
        class Meta:
            @staticmethod
            def actions__submit__post_handler(form, **_):
                if form.is_valid():
                    return html.pre(f"You posted: {form.apply(Struct())}").bind(request=request)

        name = Field()
        amount = Field.integer()
        color = Field.choice(
            choices=['Red', 'Green', 'Blue'],
        )

    return FruitForm()


@example(gettext(("Endpoints using ajax need no extra url entry")))
def form_example_3(request):
    class TrackForm(Form):
        artist = Field.choice_queryset(choices=Track.objects.all())

    return TrackForm(
        actions__submit__include=False,
    )


@example(gettext(("Create create forms from database models")))
def form_example_4(request):
    return Form.create(auto__model=Artist)


@example(gettext(("Create edit forms from database models")))
def form_example_5(request):
    return Form.edit(auto__instance=Artist.objects.all().first())


@example(gettext(("Custom actions can be added to forms")))
def form_example_6(request):
    return Form.edit(
        auto__instance=Artist.objects.all().first(),
        actions=dict(
            foo=Action.submit(attrs__value='Foo'),
            bar=Action.submit(attrs__value='Bar'),
            a=Action.submit(attrs__value='Foo', group='x'),
            b=Action.submit(attrs__value='Bar', group='x'),
            back=Action(display_name='Back to index', attrs__href='/'),
        )
    )


@example(gettext(("Multiple forms can be composed in a page")))
class KitchenForm(Form):
    kitchen_foo = Field()

    fisk = Field.multi_choice(
        choices=[1, 2, 3, 4],
        parse=choice_parse,
        initial=[1, 2],
        editable=False
    )

    textarea = Field.textarea(initial='initial value')

    radio = Field.radio(choices=['foo!!_"', 'bar', 'baz'])

    checkbox = Field.boolean()

    date = Field.date()

    choice = Field.choice(choices=['a1', 'a2', 'a3', 'b1', 'b2', 'b3', 'X'])

    choice_with_groups = Field.choice(
        choices=['a1', 'a2', 'a3', 'b1', 'b2', 'b3', 'X'],
        choice_to_optgroup=lambda choice, **_:
        choice[0] if choice[0].islower() else None
    )


class SinkForm(Form):
    foo = Field()


def form_example_7(request):
    def kitchen_form_post_handler(form, **_):
        if not form.is_valid():
            return

        values = form.apply(Struct())
        return HttpResponse(format_html("Kitchen values was {}", values))

    def sink_form_post_handler(form, **_):
        if not form.is_valid():
            return

        values = form.apply(Struct())
        return HttpResponse(format_html("Sink values from form {} was {}", form._name, values))

    class KitchenPage(Page):
        kitchen_form = KitchenForm(actions__submit__post_handler=kitchen_form_post_handler)
        sink_form = SinkForm(actions__submit__post_handler=sink_form_post_handler)
        sink_form2 = SinkForm(fields__foo__display_name='foo2', actions__submit__post_handler=sink_form_post_handler)

    return KitchenPage()


@example(gettext(("Custom validation for all fields in a form")))
def form_example_8(request):
    class FruitForm(Form):
        class Meta:
            @staticmethod
            def post_validation(form, **_):
                # Notice that post_validation is run, even if there are invalid fields
                # hence the 'or' below
                if (form.fields.name.value or '').lower() == "tomato" and form.fields.color.value == "Blue":
                    # Or alternatively call form.add_error
                    raise ValidationError("Tomatoes are not blue")

            @staticmethod
            def actions__submit__post_handler(form, **_):
                if form.is_valid():
                    return html.pre(f"You posted: {form.apply(Struct())}").bind(request=request)

        name = Field()
        amount = Field.integer()
        color = Field.choice(
            choices=['Red', 'Green', 'Blue'],
        )

    return FruitForm()


@example(gettext(("Error messages")))
def form_example_error_messages(request):
    def form_error_messages(form, **_):
        form.add_error(gettext('Global error message 1'))
        form.add_error(gettext('Global error message 2'))

    def field_error_messages(field, **_):
        field.add_error(gettext('Field error message 1'))
        field.add_error(gettext('Field error message 2'))

    return Form(
        title=gettext('Error messages'),
        auto__model=Artist,
        post_validation=form_error_messages,
        fields__name__post_validation=field_error_messages,
        actions__submit__include=False,
    )


class IndexPage(ExamplesPage):
    header = html.h1('Form examples')
    description = html.p('Some examples of iommi Forms')
    all_fields = html.p(
        Action(
            display_name='Example with all types of fields',
            attrs__href='all_fields',
        ),
        html.br(),
        after='example_9',
    )

    class Meta:
        parts = example_links(examples)


urlpatterns = [
    path('', IndexPage().as_view()),
    path('example_1/', form_example_1),
    path('example_2/', form_example_2),
    path('example_3/', form_example_3),
    path('example_4/', form_example_4),
    path('example_5/', form_example_5),
    path('example_6/', form_example_6),
    path('example_7/', form_example_7),
    path('example_8/', form_example_8),
    path('example_9/', form_example_error_messages),
    path('all_fields/', all_field_sorts),
]
