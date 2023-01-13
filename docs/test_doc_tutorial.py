# language=rst
"""
Tutorial
~~~~~~~~

.. note::

    This tutorial is intended for a reader that is well versed in the Django basics of the ORM,
    urls routing, function based views, and templates.

    It is also expected that you have already installed iommi in your project. Read section 1 of :doc:`Getting started <getting_started>`.


This tutorial will build a discography app. Let's start with the models:


.. literalinclude:: models.py
    :pyobject: Artist
    :end-before: def __str__

.. literalinclude:: models.py
    :pyobject: Album
    :end-before: def __str__

.. literalinclude:: models.py
    :pyobject: Track
    :end-before: def __str__

We will build up to these pages:

- index page with album artwork
- an artist page
- an artists page
- an album page
- an albums page
- a tracks page

Plus we're going to enable the iommi admin for these models.
"""
from pathlib import Path

import pytest
from django.template import Template
from django.urls import (
    include,
    path,
)
from django.utils.html import format_html

from docs.models import (
    Album,
    Artist,
    Track,
)
from iommi import (
    Action,
    Column,
    Field,
    Form,
    html,
    Page,
    Table,
)
from iommi.admin import Admin
from iommi.path import register_path_decoding
from tests.helpers import (
    req,
    show_output,
    show_output_collapsed,
    staff_req,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def auto_use(big_discography):
    pass


def create_discography_dump():
    for artist in Artist.objects.all():
        yield f"x = Artist.objects.create(name={artist.name!r})"
        for album in artist.albums.all():
            yield f"y = Album.objects.create(artist=x, name={album.name!r})"
            for track in album.tracks.all():
                yield f"Track.objects.create(album=y, name={track.name!r}, index={track.index})"

def test_setup_data():
    # @test
    with open(Path(__file__).parent / 'custom' / 'big_discography.py', 'w') as f:
        for l in create_discography_dump():
            f.write(l)
            f.write('\n')
    # @end

    # language=rst
    """
    Example data
    ------------
    
    The example data is quite long, if you want it to get the same examples as in this tutorial, run `this code`_.

    .. _this code: ../big_discography.py
    """


def test_declarative_tables():
    # language=rst
    """
    Tables
    ------

    We’ll start with using iommi declarative tables to create a list of albums:
    """

    class AlbumsTable(Table):
        name = Column()
        artist = Column()
        year = Column()

    def index(request):
        return AlbumsTable(
            title='Albums',
            rows=Album.objects.all(),
        )

    # @test
    show_output(index(req('get')))
    # @end

    # language=rst
    """
    The iommi middleware will handle if you return an iommi type and render it properly.
    
    At this point you might think "Hold on! Where is the template?". There isn't one. We don't need a template. iommi works at a higher level of abstraction. Don't worry, you can drop down to templates if you need to though. This will be covered later.
    
    
    You get sorting and pagination by default, and we're using the default bootstrap 4 style. iommi ships with more styles that you can switch to, or you can implement your own custom style.
    """


def test_class_meta():
    # language=rst
    """
    class Meta
    ==========
    
    The `class Meta` concept in iommi is slightly different from how it's used in Django. In iommi any argument to the constructor of a class can be put into `Meta`. In fact, ONLY valid arguments to the constructor can be set in `Meta`. In our example above we set `title` and `rows`. We can also instead set them via `Meta`:
    """

    class AlbumsTable(Table):
        name = Column()
        artist = Column()
        year = Column()

        class Meta:
            title = 'Albums'
            rows = Album.objects.all()

    def index(request):
        return AlbumsTable()

    # @test
    index(req('get'))
    # @end

    # language=rst
    """
    This will do the same thing! But with a slight twist: parameters set in `Meta` are just defaults, meaning you can still override them later in the constructor call (or in subclasses).
    
    Using as_view
    =============
    
    The view we have so far doesn't use the `request` argument. We can simplify it by doing this instead:    
    """

    urlpatterns = [
        path('', AlbumsTable().as_view()),
    ]

    # @test
    show_output_collapsed(urlpatterns[0])
    # @end

    # language=rst
    """
    This looks superficially similar to class based views, but they are very different! Notice the parenthesis after the class name for example. And Django CBVs can't be combined with iommi classes because they are radically different concepts. 
    
    That an instance of `AlbumsTable` is created here means we can pass arguments here:
    """

    urlpatterns = [
        path('', AlbumsTable(title='Other title', page_size=2).as_view()),
    ]

    # @test
    show_output_collapsed(urlpatterns[0])
    # @end

    # language=rst
    """
    
    auto__model
    ===========
    
    The next step in the simplification is to realize that this table is trivially derived from the model definition. iommi has features to do this for you so we can simplify even further! We delete the entire `AlbumsTable` class and replace the url definition with this single line:
    """

    urlpatterns = [
        path('', Table(auto__model=Album).as_view()),
    ]

    # @test
    show_output_collapsed(urlpatterns[0])
    # @end

    # language=rst
    """
    You don't even need to specify the title of the table, as we use the plural verbose name of the model. These are all defaults, not hard coded values, so you can pass parameters to the `Table` constructor here to override anything you want.
    """


def test_pages():
    # language=rst
    """
    Pages
    -----

    So far we’ve just created a table, but often you want something a little more complex, especially for your index page. iommi has a concept of a `Page` that is used to build up a bigger page from smaller building blocks. Let’s build out our simple web app to have separate pages for albums, artists and tracks:
    """

    urlpatterns = [
        path('albums/', Table(auto__model=Album).as_view()),
        path('artists/', Table(auto__model=Artist).as_view()),
        path('tracks/', Table(auto__model=Track).as_view()),
    ]

    # @test
    show_output_collapsed(urlpatterns[0])
    show_output_collapsed(urlpatterns[1])
    show_output_collapsed(urlpatterns[2])
    # @end


    # language=rst
    """
    and an index page with three tables, a header and some text:
    """

    class IndexPage(Page):
        title = html.h1('Supernaut')
        welcome_text = 'This is a discography of the best acts in music!'

        artists = Table(auto__model=Artist, page_size=5)
        albums = Table(auto__model=Album, page_size=5)
        tracks = Table(auto__model=Track, page_size=5)

    urlpatterns = [
        path('', IndexPage().as_view()),
    ]

    # @test
    show_output(urlpatterns[0])
    # @end

    # language=rst
    """
    `html` is a little fragment builder to make it easier and faster to build small html parts. `html.div('foo')` is just a more convenient way to write `Fragment(tag='div', children__text='foo')`. Fragments are used internally throughout iommi, because they allow you to define a small bit of html that can be customized later. Let’s look at an example:
    
    .. code-block:: pycon
        
        >>> class MyPage(Page):
        ...    title = html.h1('Supernaut')
        
        >>> MyPage().bind().__html__()
        '<h1>Supernaut</h1>'
        
        >>> MyPage(parts__title__attrs__class__foo=True).bind().__html__()
        '<h1 class="foo">Supernaut</h1>'
    
    This is used throughout iommi to provide good defaults that can be customized easily when needed.
    
    A `Page` can contain any `Part` (like `Fragment`, `Table`, `Form`, `Menu`, etc), plain strings or Django `Template` objects even. Escaping is handled like you’d expect from Django where strings are escaped, and you can use `format_html`/`mark_safe` to send your raw html straight through.
    """


def test_path_decoding():
    # language=rst
    """
    Path decoding
    -------------

    We’ll also introduce a page for an individual artist. We will use iommi's :doc:`path` here.

    First we register the path component we want to decode:
    """

    register_path_decoding(
        artist_name=Artist.name,
    )

    # language=rst
    """
    Then we define our page. Notice the lambdas we use to dynamically get the parameters to retrieve the correct data.
    """

    class ArtistPage(Page):
        title = html.h1(lambda params, **_: params.artist.name)

        albums = Table(
            auto__model=Album,
            rows=lambda params, **_: Album.objects.filter(artist=params.artist),
        )
        tracks = Table(
            auto__model=Track,
            rows=lambda params, **_: Track.objects.filter(album__artist=params.artist),
        )

    urlpatterns = [
        path('artist/<artist_name>/', ArtistPage().as_view()),
    ]

    # @test
    show_output(urlpatterns[0].callback(req('get'), artist_name='Black Sabbath'))
    # @end

    # language=rst
    """
    Path decoders in iommi are more convenient compared to Django path decoders, as instead of writing `<artist:artist>` everywhere, you can instead write `<artist_name>`. They are also much easier to set up. 
    """


def test_table_customization():
    # language=rst
    """
    Deeper customization
    --------------------

    cell__format
    ============
    
    In iommi you can customize the rendering on many different levels, depending
    on what the situation requires. The last layer of customization is
    `format` which is used to convert the value of a cell to a string that
    is inserted into the html (or CSV or whatever output format you are targeting):
    """

    albums = Table(
        auto__model=Album,
        columns__artist__cell__format=lambda value, **_:
            format_html('<a href="/artist/{}/">{}</a>', value, value)
    )

    # @test
    show_output(albums)
    # @end


    # language=rst
    """    
    `columns__artist__cell__format` should be read as something similar to
    `columns.artist.cell.format`. This way of jumping namespace with `__` instead
    of `.` (because `.` is syntactically invalid!) is something Django started 
    doing for query sets and we really like it so we've taken this concept further
    and it is now everywhere in iommi.
    
    The other levels of customization are `value` which is how the value is 
    extracted from the row, `attr` which is the attribute that is read (if
    you don't customize `value`), and lastly `template` which you use to override
    the entire rendering of the cell (including the `td` tag!). 
    
    You can also override `template` on the row to customize the row rendering.
    Again this includes the `tr` tag.
    
    
    cell__url
    =========
    
    A very common case of tables is to show a link in the cell. You can do that
    with `cell_format` and `cell__template` like above, but it's such a common
    case that we supply a special convenience method `cell__url` for this. Let's
    make the artist column link to the artist page in our table. First we add
    a `get_absolute_url` on the model, then replace the 
    `columns__artist__cell__format` we had above with:
    
    """
    albums = Table(
        auto__model=Album,
            columns__artist__cell__url=lambda value, **_: value.get_absolute_url(),
    )

    # @test
    show_output(albums)
    # @end


    # language=rst
    """
    
    Much better!
    
    But actually, this is such a common case that we do this by default for you
    for `ForeignKey` columns if the target model has `get_absolute_url`. So we
    can just remove the `columns__artist__cell__url` specification entirely. But 
    we do want the *name* column to link to the album page so the total definition
    becomes:
    
    """
    
    albums = Table(
        auto__model=Album,
        columns__name__cell__url=lambda row, **_: row.get_absolute_url(),
    )

    # @test
    show_output(albums)
    # @end

    # language=rst
    """ 
    Filters
    =======
    
    Tables also have built in filtering. To enable a filter make sure `include` is `True` for the `filter` of a column.    
    """
    
    albums = Table(
        auto__model=Album,
        columns__name__filter__include=True,
        columns__year__filter__include=True,
        columns__year__filter__field__include=False,
        columns__artist__filter__include=True,
    )

    # @test
    show_output(albums)
    # @end
    
    # language=rst
    """    
    `columns__year__filter__field__include=False` means we turn off the `Field` in
    the form that is created, but we can still search for the year in the
    advanced search language. 
    
    To handle selecting from a choice field that is backed by a `QuerySet` that
    can contain thousands or millions of rows, iommi by default uses a select2
    filter control with an automatic ajax endpoint. The automatic endpoint is handled by iommi on the
    same url as the view. An advantage to this approach is that we only need
    to be sure our view has the correct permission checks and then we also know
    the select box (or ajax endpoint) has the same checks. This makes it easy to
    reason about the security of the product. 
    
    The advanced filter means users can write queries like `year>1960 and title:war`
    to find albums published after 1960 and that contain the word "war".
    """


def test__foo():
    # language=rst
    """
    Actions
    =======
    
    An `Action` in iommi is a link or a button. We use them for submit buttons of
    forms and for links that you can add to a part. A common use case is to add
    links to a table. In our example app we want to add a create button for staff:
    """

    albums = Table(
        auto__model=Album,
        actions__create_album=Action(
            attrs__href='/albums/create/', 
            include=lambda request, **_: request.user.is_staff,
        )
    )

    # @test
    show_output(albums.as_view()(staff_req('get')))
    # @end

    # language=rst
    """
    For non-staff the button isn't shown:
    """

    # @test
    show_output(albums)
    # @end

    # language=rst
    """
    
    cell__template
    ==============
    
    Now that we have a basic app, we'd like to customize the look of the index page
    a bit. A plain html table with text doesn't look very cool, so we will spice it
    up with album covers. We'll start by removing the artists section. 
    
    A custom cell template for albums might be a good start to make it look nicer. 
    
    """
    albums = Table(
        auto__model=Album,
        columns__album_art=Column(
            attr=None,
            cell__template=Template('''
                <td>
                    <img 
                        height="30"
                        src="../../album_art/{{ row.artist }}/{{ row.name }}.jpg">
                </td>
            '''),
        ),
    )

    # @test
    show_output(albums)
    # @end


    # language=rst
    """
    
    That's a start, but we want something a bit more showy, let's get rid of html
    tables entirely:
    
    row__template
    =============
    
    To override the rendering of an entire row we use `cell__template`. We also
    change the table from rendering a `table` tag to a `div`, and turn off the 
    table header:
    
    """
    albums = Table(
        auto__model=Album,
        tag='div',
        header__template=None,
        row__template=Template("""
            <div class="card" style="width: 15rem; display: inline-block;" {{ cells.attrs }}>
                <img class="card-img-top" src="../../album_art/{{ row.artist }}/{{ row.name|urlencode }}.jpg">
                <div class="card-body text-center">
                    <h5>{{ cells.name }}</h5>
                    <p class="card-text">
                        {{ cells.artist }}
                    </p>
                </div>
            </div>
        """),
    )

    # @test
    show_output(albums)
    # @end


    # language=rst
    """
    
    You can specify the name of a template file here instead of writing the
    template inline like this. This way is nicer for small things and quick prototypes though.
    
    
    Admin
    -----
    
    With these high level abstractions we've seen so far (pages, tables, queries, 
    forms, fragments) we can easily build more powerful components. Which is what
    we've done with the administration interface built into iommi. Installing it
    is as simple as:
    
    """
    class MyAdmin(Admin):
        class Meta:
            pass
            # @test
            parts__menu__items_container__attrs__style={'flex-direction': 'row'}
            parts__menu__sub_menu__change_password__attrs__style__margin = '0 1rem'
            # @end

    
    urlpatterns = [
        path('iommi-admin/', include(MyAdmin.urls())),
    ]

    # @test
    show_output(urlpatterns[0].url_patterns[0].callback(staff_req('get')))
    # @end

    # language=rst
    """
    Customization is easy with `IOMMI_DEBUG` on (default on if `DEBUG` is on), 
    here's how to use the pick tool:
    
    .. raw:: html
    
        <video controls><source src="iommi-admin-customization.mp4"></video>

    You can override an entire field rendering with `template`, the template 
    of the label with `label__template`, the name of a field with `display_name`,
    add a CSS class to the label tag with `label__attrs__class__foo=True`, and 
    much more. Customization is at all levels, and in all these cases you can
    supply a callable for even more flexibility.
        
    """

def test_forms():
    # language=rst
    """
    Forms
    -----

    iommi also comes with a library for forms. This can look very much like the
    forms library built into Django, but is different in some crucial ways. Let's
    look at the most basic example from the Django documentation:

    """
    from django import forms

    class NameForm(forms.Form):
        your_name = forms.CharField(label='Your name')

    # language=rst
    """ 
    .. code-block:: html

        {% extends "base.html" %}
        {% block content %}
    
        <form action="/your-name/" method="post">
            {% csrf_token %}
            {{ form }}
            <input type="submit" value="Submit">
        </form>

        {% endblock %}

    In iommi the same is written as:

    """
    class NameForm(Form):
        your_name = Field.text()


    # @test
    show_output(NameForm())
    # @end


    # language=rst
    """
    No template needed, and this the view too.
    
    In iommi you always get a form encoding specified on the form, so they all work
    with file uploads. Missing form encoding on the form tag is a very common 
    stumbling block for beginners. You also get a submit action by default which
    you can configure via `actions__submit`:
    """

    class NameForm(Form):
        your_name = Field.text()

        class Meta:
            actions__submit__display_name = 'Save'

    # language=rst
    """    
    In iommi we use `class Meta` a lot, similar to Django, but in iommi it's not
    just a bucket of values, it has a precise definition: values in `Meta` are 
    passed into the constructor. So the example above is roughly the same as:
    """

    NameForm(actions__submit__display_name='Save')

    # language=rst
    """
    Worth pointing out is that values of `Meta` are defaults, so you can still
    override at the constructor call.

    An advantage to this strict definition is that we don't have silent failures
    in iommi. If you make a spelling mistake in a value in `Meta`, you will get
    an error message.


    Automatic forms
    ===============

    iommi can also derive forms from Django model definitions: 
    `Form(auto__model=Artist)`. You can specify which fields to include or exclude
    via `auto__include` or `auto__exclude`, and the fields can still be customized
    fully. An example of this could be to insert a CSS class `foo` on the label
    tag of a field `name`: 
    """

    form = Form(
        auto__model=Artist,
        fields__name__label__attrs__class__foo=True,
    )

    # @test
    show_output(form)
    # @end


    # language=rst
    """
    There are many many more customizations options available, you can find more
    in the cookbook and the docs for `Field`.


    Automatic views
    ===============

    iommi goes a step further than this though, by supplying full views that can
    be used from either a declarative form or an auto generated form. An example
    is to have a create view for an `Artist`:

    """
    urlpatterns = [
        path('create/', Form.create(auto__model=Artist).as_view()),
    ]

    # @test
    show_output(urlpatterns[0])
    # @end


    # language=rst
    """ 
    There are three built in forms/views like this: `create`, `edit`, and `delete`.
    The `delete` view is a read only form with some styling for the submit button
    and a submit handler that delete the object. We find this to be really nice as
    a confirmation page because you can see what you are about to delete.

    """

# language=rst
"""    
Wrap up
-------

I'm glad you read this far! This has been a very shallow introduction, but
I've touched on all the major parts in some way, and there is a lot of
material to cover. I hope you want to give iommi a try. 
"""
