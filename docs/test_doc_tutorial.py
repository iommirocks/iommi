# language=rst
"""
Tutorial
========

.. note::

    This tutorial is intended for a reader that is well versed in the Django basics of the ORM,
    urls routing, function based views, and templates.

    It is also expected that you have already installed iommi in your project. Read section 1 of :ref:`Getting started <getting-started>`.


In this tutorial you will build a discography app. By the end you will have:

- an index page with album artwork
- an artist page, and a page listing artists
- an album page, and a page listing albums
- a tracks page
- the iommi admin, enabled for all of these

Every step shows the code and the page it produces. Type the code in as you go;
each step builds on the one before it.


Set up
------

Put these models in your app's `models.py`:

.. literalinclude:: models.py
    :pyobject: Genre
    :end-before: def __str__

.. literalinclude:: models.py
    :pyobject: Artist
    :end-before: def __str__

.. literalinclude:: models.py
    :pyobject: Album
    :end-before: def __str__

.. literalinclude:: models.py
    :pyobject: Track
    :end-before: def __str__

Create the tables:

.. code-block:: shell

    python manage.py makemigrations
    python manage.py migrate

Now load the same example data used in this tutorial, so your pages look like the
screenshots. Download `big_discography.py`_ into your project and run it:

.. code-block:: shell

    python manage.py shell < big_discography.py

.. _big_discography.py: https://raw.githubusercontent.com/iommirocks/iommi/master/docs/custom/big_discography.py

You're ready to build the first page.
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
    Form,
    html,
    Page,
    Table,
)
from iommi.admin import Admin
from iommi.docs import (
    show_output,
    show_output_collapsed,
)
from iommi.path import register_path_decoding
from tests.helpers import (
    req,
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
    # Regenerates the example data script that the `Set up` section of this page
    # links to. Nothing is rendered into the docs from here.
    # @test
    with open(Path(__file__).parent / 'custom' / 'big_discography.py', 'w') as f:
        for line in create_discography_dump():
            f.write(line)
            f.write('\n')
    # @end


def test_declarative_tables():
    # language=rst
    """
    Tables
    ------

    Creating a table view of a model in iommi is simple:

    """
    urlpatterns = [
        path('', Table(auto__model=Album).as_view()),
    ]

    # @test
    show_output(urlpatterns[0])
    # @end

    # language=rst
    """
    You get sorting and pagination by default, and we're using the default bootstrap 5 style. iommi ships with :ref:`more styles <style>` that you can switch to, or you can :ref:`implement your own custom style <style>`.
    
    At this point you might think "Hold on! Where is the template?". There isn't one. We don't need a template. iommi works at a higher level of abstraction. Don't worry, you can drop down to templates if you need to. There are examples of this in the :ref:`table cookbook <cookbook-tables>`, and much more. One of the most important concepts is to include or exclude columns using includes: `auto__include=['name', 'artist']`, or using excludes: `auto__exclude=['artist', 'year']`. 
    """


def test_pages():
    # language=rst
    """
    Pages
    -----

    So far we’ve just created a single table, but often you want something a little more complex, especially for your index page. iommi has a concept of a :ref:`Page <pages>` that is used to build up a bigger page from smaller building blocks. Let’s build out our simple web app to have separate pages for albums, artists and tracks:
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

    First we register the path component we want to decode (in your `AppConfig` `ready`):
    """

    register_path_decoding(
        artist_name=Artist.name,
    )

    # language=rst
    """
    Then we define our page. Notice the lambdas we use to dynamically get the parameters to retrieve the correct data.
    """

    class ArtistPage(Page):
        title = html.h1(lambda artist, **_: artist.name)

        albums = Table(
            auto__model=Album,
            rows=lambda artist, **_: Album.objects.filter(artist=artist),
        )
        tracks = Table(
            auto__model=Track,
            rows=lambda artist, **_: Track.objects.filter(album__artist=artist),
        )

    urlpatterns = [
        path('artist/<artist_name>/', ArtistPage().as_view()),
    ]

    # @test
    show_output(urlpatterns[0].callback(req('get'), artist_name='Black Sabbath'))
    # @end

    # language=rst
    """
    Path decoders in iommi can be more convenient compared to Django path
    decoders, as instead of writing `<artist:artist>` everywhere, you can instead
    write `<artist_name>` or `<artist_pk>`. They are also easier to set up and 
    give you hook points for access control if needed. 
    """


def test_table_customization():
    # language=rst
    """
    Customize the table
    -------------------

    Change how a value is displayed
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Add `get_absolute_url` to your `Album` and `Artist` models, then let's make the
    album name link to the album page. `cell__url` turns a cell into a link:
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
    Notice that the *artist* column became a link too, without you asking for it:
    for a `ForeignKey` column iommi does this by default when the target model has
    `get_absolute_url`.

    `columns__name__cell__url` reads as `columns.name.cell.url`. iommi uses `__` to
    step down into nested configuration, because `.` isn't valid in a keyword
    argument. You'll see this everywhere from here on;
    :ref:`dunder-dict-equivalence` explains it properly.

    When you need to build the displayed string yourself rather than just link it,
    use `cell__format`:
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
    There is a ladder of hooks here, and you reach for the lowest one that does the
    job: `attr` picks which attribute is read, `value` computes the value, `format`
    turns the value into a string, and `template` replaces the cell's rendering
    outright, `td` tag included. Rows have a `template` too.

    Add filtering
    ~~~~~~~~~~~~~

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
    Add buttons, and edit/delete links for staff
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    An `Action` in iommi is a link or a button. Let's add a create button, plus edit
    and delete columns, and show all three only to staff. `Column.edit` and
    `Column.delete` are prebuilt shortcuts for the link columns:
    """

    albums = Table(
        auto__model=Album,
        actions__create_album=Action(
            attrs__href='/albums/create/',
            include=lambda request, **_: request.user.is_staff,
        ),
        columns__edit=Column.edit(
            after=0,
            include=lambda request, **_: request.user.is_staff,
        ),
        columns__delete=Column.delete(
            include=lambda request, **_: request.user.is_staff,
        ),
    )

    # @test
    show_output(albums, request=staff_req('get'))
    # @end

    # language=rst
    """
    For non-staff the "Create album" button isn't shown, neither are the edit and delete columns:
    """

    # @test
    show_output(albums)
    # @end

    # language=rst
    """
    
    Show album art in a column
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Now that we have a basic app, let's make the index page look better. A plain
    table of text doesn't look very cool, so we'll add the album covers.

    Add a column that has no model field behind it (`attr=None`) and give it a
    template that renders an image:

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
    
    That's a start, but we want something more showy, so let's get rid of the html
    table entirely.

    Turn the rows into cards
    ~~~~~~~~~~~~~~~~~~~~~~~~

    `row__template` replaces the rendering of a whole row, `tr` tag included. Render
    the table as a `div` instead of a `table`, turn off the header, and make each row
    a card:

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
            parts__menu__items_container__attrs__style = {'flex-direction': 'row'}
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
    
        <video controls style="max-width: 100%"><source src="iommi-admin-customization.mp4"></video>

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
    take a simple example of a `ModelForm`:

    """
    from django import forms

    class AlbumForm(forms.ModelForm):
        class Meta:
            model = Album
            fields = ['name', 'artist']

    # @test
    AlbumForm()
    # @end

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

    In iommi the same can be written as:
    """

    class AlbumForm(Form):
        class Meta:
            auto__model = Album
            auto__include = ['name', 'artist']

    # @test
    show_output(AlbumForm())
    # @end

    # language=rst
    """
    No template needed, and this is the view too with `Form.edit` or `Form.create`.
    
    In iommi you always get a form encoding specified on the form, so they all work
    with file uploads. Missing form encoding on the form tag is a very common 
    stumbling block for beginners. You also get a submit action by default which
    you can configure via `actions__submit`:
    """

    class AlbumForm(Form):
        class Meta:
            auto__model = Album
            auto__include = ['name', 'artist']
            actions__submit__display_name = 'Save'

    # language=rst
    """
    Everything you put in `class Meta` is passed to the constructor, and only valid
    constructor arguments are accepted there -- so a misspelled setting is an error,
    not silence. :doc:`equivalency` covers what that buys you.

    There are many more customization options available, you can find more
    in the :ref:`form cookbook <cookbook-forms>` and the docs for `Field`.


    Automatic views
    ~~~~~~~~~~~~~~~

    iommi goes a step further than Django forms, by supplying full views that can
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
    There are four built in forms/views like this: `create`, `edit`, `create_and_edit` and `delete`.
    The `delete` view is a read only form with some styling for the submit button
    and a submit handler that deletes the object. We find this to be really nice as
    a confirmation page because you can see what you are about to delete.
    """


# language=rst
"""    
Wrap up
-------

I'm glad you read this far! This has been a very shallow introduction, but
it has touched on all the major parts in some way, and there is a lot of
material to cover. We hope you want to give iommi a try. 
"""
