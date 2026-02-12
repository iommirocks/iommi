import pytest
from django.urls import (
    path,
)

from docs.models import (
    Album,
)
from iommi import (
    Column,
    Table,
)
from iommi.docs import (
    show_output,
    show_output_collapsed,
)
from tests.helpers import req

pytestmark = pytest.mark.django_db

# Table(auto...)
# Table(columns__foo=Column.from_model...)
# Table(columns__foo=Column(....))


# .as_view
# FBV using middleware


# reverse of

def test_foo():
    # language=rst
    """




    We’ll start with using iommi declarative tables to create a list of albums:
    """

    class AlbumTable(Table):
        name = Column()
        artist = Column()
        year = Column()

    def index(request):
        return AlbumTable(
            title='Albums',
            rows=Album.objects.all(),
        )

    # @test
    show_output(index(req('get')))
    # @end

    # language=rst
    """
    The iommi middleware will detect when you return an iommi type and render it properly.
    
    At this point you might think "Hold on! Where is the template?". There isn't one. We don't need a template. iommi works at a higher level of abstraction. Don't worry, you can drop down to templates if you need to though. This will be covered later.
    
    
    You get sorting and pagination by default, and we're using the default bootstrap 5 style. iommi ships with `more styles <style>`_ that you can switch to, or you can `implement your own custom style <style>`_.
    """


def test_class_meta():
    # language=rst
    """
    class Meta
    ==========

    The `class Meta` concept in iommi is slightly different from how it's used in Django. In iommi any argument to the constructor of a class can be put into `Meta`. In fact, ONLY valid arguments to the constructor can be set in `Meta`. In our example above we set `title` and `rows`. We can also instead set them via `Meta`:
    """

    class AlbumTable(Table):
        name = Column()
        artist = Column()
        year = Column()

        class Meta:
            title = 'Albums'
            rows = Album.objects.all()

    def index(request):
        return AlbumTable()

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
        path('', AlbumTable().as_view()),
    ]

    # @test
    show_output_collapsed(urlpatterns[0])
    # @end

    # language=rst
    """
    This looks superficially similar to class based views, but they are very different! Notice the parenthesis after the class name for example. And Django CBVs can't be combined with iommi classes because they are radically different concepts. 
    
    That an instance of `AlbumTable` is created here means we can pass arguments here:
    """

    urlpatterns = [
        path('', AlbumTable(title='Other title', page_size=2).as_view()),
    ]

    # @test
    show_output_collapsed(urlpatterns[0])
    # @end

    # language=rst
    """
    
    auto__model
    ===========
    
    The next step in the simplification is to realize that this table is trivially derived from the model definition. iommi has features to do this for you so we can simplify even further! We delete the entire `AlbumTable` class and replace the url definition with this single line:
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
