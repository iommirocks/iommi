import datetime

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
from iommi.struct import Struct

from examples import (
    example_adding_decorator,
    example_links,
)
from examples.models import (
    Album,
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
    Header,
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
    message = mark_safe(
        "\n".join(format_html("{}: {}", name, bound_field.value) for name, bound_field in form.fields.items())
    )

    return HttpResponse(
        Template(
            """
            <html>
                <head>
                    {% for asset in form.iommi_collected_assets.values %}
                         {{ asset }}
                    {% endfor %}
                <body>
                    {{ form }}
                    {{ message }}
                </body>
            </html>
        """
        ).render(context=RequestContext(request, dict(form=form, message=message))),
    )


@example(gettext("Use more ideomatic like an iommi part"))
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


@example(gettext("Endpoints using ajax need no extra url entry"))
def form_example_3(request):
    class TrackForm(Form):
        artist = Field.choice_queryset(choices=Track.objects.all())

    return TrackForm()


@example(gettext("Create forms from database models"))
def form_example_4(request):
    return Form.create(auto__model=Artist)


@example(gettext("Create edit forms from database models"))
def form_example_5(request):
    class MyForm(Form):
        name = Field()

    return MyForm.edit(instance=Artist.objects.all().first())


@example(gettext("Custom actions can be added to forms"))
def form_example_6(request):
    do_nothing = lambda **_: None
    return Form.edit(
        auto__instance=Artist.objects.all().first(),
        actions=dict(
            foo=Action.submit(display_name='Foo', post_handler=do_nothing),
            bar=Action.submit(display_name='Bar', post_handler=do_nothing),
            a=Action.submit(display_name='Foo', group='x', post_handler=do_nothing),
            b=Action.submit(display_name='Bar', group='x', post_handler=do_nothing),
            back=Action(display_name='Back to index', attrs__href='/', post_handler=do_nothing),
        ),
    )


@example(gettext("Multiple forms can be composed in a page"))
class KitchenForm(Form):
    kitchen_foo = Field()

    fisk = Field.multi_choice(choices=[1, 2, 3, 4], parse=choice_parse, initial=[1, 2], editable=False)

    textarea = Field.textarea(initial='initial value')

    radio = Field.radio(choices=['foo!!_"', 'bar', 'baz'])

    checkbox = Field.boolean()

    date = Field.date()

    choice = Field.choice(choices=['a1', 'a2', 'a3', 'b1', 'b2', 'b3', 'X'])

    choice_with_groups = Field.choice(
        choices=['a1', 'a2', 'a3', 'b1', 'b2', 'b3', 'X'],
        choice_to_optgroup=lambda choice, **_: choice[0] if choice[0].islower() else None,
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


@example(gettext("Custom validation for all fields in a form"))
def form_example_8(request):
    class FruitForm(Form):
        class Meta:
            @staticmethod
            def post_validation(form, **_):
                # Notice that post_validation is run, even if there are invalid fields,
                # so you either have to check that fields that you are interested in
                # are not None, or alternatively if you only want to run your validation if all fields
                # passed their individual checks you can just call form.is_valid (see below).
                # BUT when form.is_valid is called outside of a Form's post_validation
                # handler its result includes errors caused by the post_validation (as you
                # would expect).
                if form.is_valid() and form.fields.name.value == "tomato" and form.fields.color.value == "Blue":
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


@example(gettext("Error messages"))
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
    )


@example(gettext("Form children do not need to be all fields"))
def form_example_children_that_are_not_fields(request):
    def on_submit(form, **_):
        if not form.is_valid():
            return
        return html.pre(f"You posted: {form.apply(Struct())}").bind(request=request)

    def post_validation(form, **_):
        if form.is_valid():
            if form.fields.f1.value + form.fields.f2.value != form.fields.f3.value:
                form.add_error("Calculate again!")

    return Form(
        iommi_style="bulma",
        title="Children that are not fields",
        fields__name=Field(),
        fields__color=Field.choice(choices=['Red', 'Green', 'Blue']),
        fields__in_box=html.div(
            children__f1=Field.integer(attrs__class__column=True),
            children__plus=html.span("+", attrs__class={'column': True, 'is-narrow': True}),
            children__f2=Field.integer(
                attrs__class__column=True,
            ),
            children__equals=html.span("=", attrs__class={'column': True, 'is-narrow': True}),
            children__f3=Field.integer(attrs__class_column=True),
            iommi_style="horizontal",
            attrs__class={'box': True, 'columns': True, 'is-vcentered': True},
        ),
        post_validation=post_validation,
        actions__submit__post_handler=on_submit,
    )


@example(gettext("Form children do not need to be all fields -- declarative"))
def form_example_children_that_are_not_fields_declarative(request):
    def on_submit(form, **_):
        if not form.is_valid():
            return
        return html.pre(f"You posted: {form.apply(Struct())}").bind(request=request)

    def post_valid(form, **_):
        if form.is_valid():
            if form.fields.f1.value + form.fields.f2.value != form.fields.f3.value:
                form.add_error("Calculate again!")

    class MyForm(Form):
        name = Field()
        color = Field.choice(choices=['Red', 'Green', 'Blue'])
        in_a_box = html.div(
            children__f1=Field.integer(attrs__class__column=True),
            children__plus=html.span("+", attrs__class={'column': True, 'is-narrow': True}),
            children__f2=Field.integer(
                attrs__class__column=True,
            ),
            children__equals=html.span("=", attrs__class={'column': True, 'is-narrow': True}),
            children__f3=Field.integer(attrs__class_column=True),
            iommi_style="horizontal",
            attrs__class={'box': True, 'columns': True, 'is-vcentered': True},
        )

        class Meta:
            iommi_style = "bulma"
            title = "Children that are not fields"
            post_validation = post_valid
            actions__submit__post_handler = on_submit

    return MyForm()


@example(gettext("Nested forms -- to abstract out behaviour and create complex 'fields'."))
def form_example_nested_forms(request):
    """Here we have two fields first_day, last_day and want to abstract
    out the validation behaviour. Maybe because we have several
    different forms that that edit different models that all have
    a first_day and a last_day field."""

    class DateRangeField(Form):
        first_day = Field.date()
        last_day = Field.date()

        class Meta:
            @staticmethod
            def post_validation(form, **_):
                print("post validation", form.is_valid())
                if form.is_valid():
                    if form.fields.first_day.value > form.fields.last_day.value:
                        form.add_error("First day must be <= last day")

    class MyForm(Form):
        event = Field()
        # attr='' => instance.first_day, instance.last_day instead of instance.when.first_day, instance.when.last_day
        when = DateRangeField(attr='')

        class Meta:
            @staticmethod
            def actions__submit__post_handler(form, **_):
                if not form.is_valid():
                    return
                return html.pre(f"You posted {form.apply(Struct())}").bind(request=request)

    today = datetime.date.today()
    return Page(
        parts__title1=Header("Without instance"),
        parts__form1=MyForm(),
        parts__title2=Header("With instance"),
        parts__form2=MyForm(instance=Struct(first_day=today, last_day=today, event="Party")),
    )


@example(gettext("File upload"))
def form_example_file_upload(request):
    class FileForm(Form):
        upload = Field.file()

        class Meta:
            @staticmethod
            def actions__submit__post_handler(form, **_):
                if form.is_valid():
                    print(f"Uploaded {len(form.fields.upload.value)} bytes")

    return FileForm()


@example(gettext("Field groups"))
def form_example_field_groups(request):
    class FieldGroupForm(Form):
        a = Field()
        b = Field(group='1')
        c = Field(group='1')
        d = Field()
        e = Field(group='2')
        f = Field(group='2')

    return FieldGroupForm()


@example(gettext("Dependent choices"))
def form_example_dependent_fields(request):
    def album_choices(form, **_):
        if form.fields.artist.value:
            return Album.objects.filter(artist=form.fields.artist.value)
        else:
            return Album.objects.all()

    return Form(
        auto__model=Track,
        fields__artist=Field.choice_queryset(
            attr=None,
            choices=Artist.objects.all(),
            after=0,
        ),
        fields__album__choices=album_choices,
    )


class IndexPage(ExamplesPage):
    header = html.h1('Form examples')
    description = html.p('Some examples of iommi Forms')

    examples = example_links(examples)

    all_fields = Action(
        display_name='Example with all types of fields',
        attrs__href='all_fields',
    )


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
    path('example_10/', form_example_children_that_are_not_fields),
    path('example_11/', form_example_children_that_are_not_fields_declarative),
    path('example_12/', form_example_nested_forms),
    path('example_13/', form_example_file_upload),
    path('example_14/', form_example_field_groups),
    path('example_15/', form_example_dependent_fields),
    path('all_fields/', all_field_sorts),
]
