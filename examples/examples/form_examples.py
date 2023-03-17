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


class FruitForm(Form):
    class Meta:
        title = 'An iommi form'
        @staticmethod
        def actions__submit__post_handler(request, form, **_):
            if form.is_valid():
                return html.pre(f"You posted: {form.apply(Struct())}")

    name = Field()
    amount = Field.integer()
    color = Field.choice(
        choices=['Red', 'Green', 'Blue'],
    )


form_example_2 = example(gettext("Create forms from database models"))(Form.create(auto__model=Artist).as_view())


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
def form_example_7(request):


    class KitchenPage(Page):
        kitchen_form = Form.create(auto__model=Album, actions__submit__post_handler=kitchen_form_post_handler)
        sink_form = Form.edit(.... actions__submit__post_handler=sink_form_post_handler)

    return KitchenPage()



@example(gettext("Form children do not need to be fields"))
def form_example_children_that_are_not_fields(request):


    return Form(
        auto__model=Album,
        fields__album_art=html.img(....)
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
    path('example_1/', FruitForm().as_view()),

    path('example_2/', form_example_2),
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

def index_page(urlpatterns):
    return IndexPage

urlpatterns += [
    path('', index_page(urlpatterns))
]
