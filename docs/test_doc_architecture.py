from docs.models import *
from iommi import *
from tests.helpers import req

request = req('get')

import pytest

pytestmark = pytest.mark.django_db


def test_architecture():
    # language=rst
    """
    Architecture
    ============

    """


def test_execution_phases():
    # language=rst
    """
    Execution phases
    ----------------

    `Part` objects have this life cycle:

    1. Definition
    2. Construction
    3. `Bind`_
    4. Traversal (e.g. render to html, respond to ajax, custom report creation)


    At definition time we can have just a bunch of dicts. This is really a stacking and merging of namespaces.

    At construction time we take the definition namespaces and materialize them into proper :code:`Table`, :code:`Column`, :code:`Form` etc objects.

    At bind time we:

    - register parents
    - evaluate callables into real values
    - invoke any user defined :code:`on_bind` handlers

    At traversal time we are good to go and can now invoke the final methods of all objects. We can now render html, respond to ajax, etc.


    """


def test_bind():
    # language=rst
    """
    .. _bind:

    Bind
    ----

    "Bind" is when we take an abstract declaration of what we want and convert it into the "bound" concrete expression of that. It consists of these parts:

    1. Copy of the part. (We set a member `_declared` to point to the original definition if you need to refer to it for debugging purposes.)
    2. Set the `parent` and set `_is_bound` to `True`
    3. Style application
    4. Call the parts `on_bind` method

    The parts are responsible for calling `bind(parent=self)` on all their children in `on_bind`.

    The root object of the graph is initialized with `bind(request=request)`. Only one object can be the root.
    """


def test_namespace_dispatching():
    # language=rst
    """
    .. _dispatching:

    Namespace dispatching
    ---------------------

    I've already hinted at this above in the example where we do
    ``columns__foo__include=False``. This is an example of the powerful
    namespace dispatch mechanism from iommi.declarative. It's inspired by the
    query syntax of Django where you use ``__`` to jump namespace. (If
    you're not familiar with Django, here's the gist of it: you can do
    ``Table.objects.filter(foreign_key__column='foo')``
    to filter.) We really like this style and have expanded on it. It
    enables functions to expose the *full* API of functions it calls while
    still keeping the code simple. Here's a contrived example:


    """
    from iommi.declarative.dispatch import dispatch
    from iommi.declarative.namespace import EMPTY

    @dispatch(
        b__x=1,  # these are default values. "b" here is implicitly
        # defining a namespace with a member "x" set to 1
        c__y=2,
    )
    def a(foo, b, c):
        print('foo:', foo)
        some_function(**b)
        another_function(**c)

    @dispatch(
        d=EMPTY,  # explicit namespace
    )
    def some_function(x, d):
        print('x:', x)
        another_function(**d)

    def another_function(y=None, z=None):
        if y:
            print('y:', y)
        if z:
            print('z:', z)

    # now to call a()!
    a('q')
    # output:
    # foo: q
    # x: 1
    # y: 2

    a('q', b__x=5)
    # foo: q
    # x: 5
    # y: 2

    a('q', b__d__z=5)
    # foo: q
    # x: 1
    # z: 5
    # y: 2

    # language=rst
    """
    This is really useful for the `Table` class as it means we can expose the full
    feature set of the underling `Query` and `Form` classes by just
    dispatching keyword arguments downstream. It also enables us to bundle
    commonly used features in what we call "shortcuts", which are pre-packaged sets of defaults.
    """


def test_evaluate():
    # language=rst
    """
    Evaluate
    --------

    To customize iommi you can pass functions/lambdas in many places. This makes it super easy and fast to customize things, but how does this all work? Let's start with a concrete example:

    """
    # @test
    Artist.objects.create(name='Dio')

    t = (
        # @end
        Table(
            auto__model=Artist,
            columns__name__cell__format=lambda value, **_: f'{value} !!!',
        )
        # @test
    )

    t = t.bind(request=req('get'))
    data = [[cell.render_cell_contents() for cell in cells] for cells in t.cells_for_rows()]
    assert data == [['Dio !!!']]
    # @end

    # language=rst
    """
    This will change the rendering of Dios name from `Dio` to `Dio !!!`. The obvious question here is: what other keyword arguments besides `value` do I get? In this case you get:

    """
    # @test
    kwargs = {}
    t = Table(
        auto__model=Artist,
        columns__name__cell__format=lambda **format_kwargs: kwargs.update(format_kwargs),
    )
    str(t.bind(request=req('get')))  # trigger render
    # @end

    # language=rst
    """
    .. code-block:: python
    """

    # @test

    expected = (
        (
            # @end
            # language=rst
            """

        request        WSGIRequest
        table          Table
        column         Column
        traversable    Column
        value          str
        row            Artist
        cells          Cells
        bound_cell     Cell

        """
            # @test
        )
        .strip()
        .split('\n')
    )
    expected = dict(
        x.strip().replace('  ', ' ').replace('  ', ' ').replace('  ', ' ').replace('  ', ' ').split(' ')
        for x in expected
    )

    assert {k: type(v).__name__ for k, v in kwargs.items()} == expected
    # @end

    # language=rst
    """
    The general idea here that you should get all useful objects up the tree and as they are named it becomes easy to understand what is happening when reading these functions. If you have an iommi object you can call the method `iommi_evaluate_parameters()` on it to retrieve this dict.

    `traversable` is exactly the same object as `column`. It's the general name of the closest object (or the leaf) for that callback. You can think of it as similar to `self`. This is useful for creating functions that you can use for `Field`, `Column`, and `Filter`; as the keyword argument `traversable` is the same, but they will get `field`, `column`, and `filter` as the specific keyword arguments. Prefer the specific name if possible since it makes the code more readable.


    .. note::

        It is a good idea to always give your callbacks `**_` even if you match all keyword arguments. We don't consider adding keyword arguments a breaking change so additional keyword arguments can be added at any time.

    """


def test_evaluate___under_the_hood():
    # language=rst
    """
    Evaluate - under the hood
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    There are three functions that handle the evaluation of callables into values when needed. All of these pass values straight through, which is why you can write e.g. `display_name='Artist'` instead of having to write lambdas for simple values.

    - `evaluate`: evaluates non-strict, which means it will allow functions that don't match the given signature to pass through
    - `evaluate_strict`: evaluates strictly, which means functions that don't match the given signature will be an error

    Each object in the tree declares what it adds to the evaluate parameters with a method `own_evaluate_parameters`. For example `Table` adds just one argument `table` which is itself. The method `iommi_evaluate_parameters` gives you all the evaluate parameters up the tree from where you are.

    There are two special cases: `traversable` which is the leaf node, and `request` which is the http request object.
    """
