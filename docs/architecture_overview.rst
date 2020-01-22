Architecture overview
=====================

iommi follows a design philosophy that adds a few rules on top of the Zen of python.

* Things that are similar should look similar, things that are different should look different
* Things that are connected should be close, things that are separate should be apart.
* Layers should be layered.
* Everything needs a name, so we can reference it for customization.
* Traversing a namespace is done with :code:`__` when :code:`.` can't be used in normal python syntax.
* Every place you can place a value, you should be able to place a lambda.
* Late evaluation is preferred. Sometimes we can avoid work, and sometimes it enables better customization.
* You should be able to use a declarative or a programmatic style as fits the need.
* Strong and reasonable defaults, but full ability to customize those defaults.


Design goal
-----------

We want it to be possible always to create higher abstractions where you can use those
abstractions but tweaked *without having to change the abstraction to enable this*. If
you have code that create a complex page with tables, forms, and help text fragments in
several places, then you should be able to reuse that but with a single line of code
change to change a single small detail of that page.

In standard APIs you often have to
copy paste the entire page and make a small change. This hides the difference between
the two pages because you spend 99% of the code to say the same thing. Or alternatively
you have to pollute the definition of the first page with some super specific option
that makes that code worse. We want to avoid both these scenarios.

In short we want to be able to have code that reads like:

    It's like that one, but different like this.


Declarative/programmatic hybrid API
-----------------------------------

The ``@declarative`` and ``@with_meta``
decorators from tri.declarative enables us to very easily write an API
that can look both like a normal simple python API:

.. code:: python

    my_table = Table(
        columns=dict(
            foo=Column(),
            bar=Column(),
        ),
        sortable=False)

This code is hopefully pretty self explanatory. But the cool thing is
that we can do the exact same thing with a declarative style:

.. code:: python

    class MyTable(Table):
        foo = Column()
        bar = Column()

        class Meta:
            sortable = False

    my_table = MyTable()

This style can be much more readable. There's a subtle different though
between the first and second styles: the second is really a way to
declare defaults, not hard coding values. This means we can create
instances of the class and set the values in the call to the
constructor:

.. code:: python

    my_table = MyTable(
        columns__foo__show=False,  # <- hides the column foo
        sortable=True,            # <- turns on sorting again
    )

...without having to create a new class inheriting from ``MyTable``. So
the API keeps all the power of the simple style and also getting the
nice syntax of a declarative API.

Namespace dispatching
---------------------

I've already hinted at this above in the example where we do
``columns__foo__show=False``. This is an example of the powerful
namespace dispatch mechanism from tri.declarative. It's inspired by the
query syntax of Django where you use ``__`` to jump namespace. (If
you're not familiar with Django, here's the gist of it: you can do
``Table.objects.filter(foreign_key__column='foo')``
to filter.) We really like this style and have expanded on it. It
enables functions to expose the *full* API of functions it calls while
still keeping the code simple. Here's a contrived example:

.. code:: python

    from tri_declarative import dispatch, EMPTY


    @dispatch(
        b__x=1,  # these are default values. "b" here is implicitly
                 # defining a namespace with a member "x" set to 1
        c__y=2,
    )
    def a(foo, b, c):
        print('foo:', foo)
        some_function(**b)
        another_function(**c)


    @dispatch (
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

This is really useful for the Table class as it means we can expose the full
feature set of the underling Query and Form classes by just
dispatching keyword arguments downstream. It also enables us to bundle
commonly used features in what we call "shortcuts", which are pre
packaged sets of defaults.


Execution phases
----------------

Page parts have this life cycles:

1. Definition
2. Construction
3. Bind
4. Traversal (e.g. render to html, respond to ajax, custom report creation)


At definition time we can have just a bunch of dicts. This is really a stacking and merging of namespaces.

At construction time we take the definition namespaces and materialize them into proper :code:`Table`, :code:`Column`, :code:`Form` etc objects.

At bind time we:

- set request object if applicable
- register parents
- evaluate callables into real values
- invoke any user defined :code:`on_bind` handlers

At traversal time we are good to go and can now invoke the final methods of all objects. We can now render html, respond to ajax, etc.
