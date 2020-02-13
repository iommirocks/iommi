Philosophy
==========

iommi follows a design philosophy that has evolved over several
years. It might feel a bit strange in the beginning but we believe
it's well worth it.

We want it to always be possible to create higher abstractions where
you can reuse those abstractions with small tweaks *without having to
change the abstraction to enable this*. If you have code that creates
a complex page with tables, forms, and help text fragments in several places,
then you should be able to reuse that but with a single line of code
change to change a single small detail of that page.

In standard APIs you often have to copy paste the entire page and make
a small change. This hides the difference between the two pages because you
spend 99% of the code to say the same thing. Or alternatively you have to
pollute the definition of the first page with some super specific option
that makes that code worse. We want to avoid both these scenarios.

In short we want to be able to have code that reads like:

    It's like that one, but different like this.

The philosophy has these main parts:

* `Everything has a name`_
* `Traversing a namespace is done with __ when . can't be used in normal python syntax`_
* `Callables for advanced usage, values for the simple cases`_
* `Late binding`_
* `Declarative/programmatic hybrid API`_
* `Prepackaged commonly used patterns (that can still be customized!)`_
* `Single point customization with no boilerplate`_
* `Escape hatches included`_


Everything has a name
---------------------

We like to think of GUIs as a tree of items like tables, buttons, links
and pages. We want it to be easy to reference an item in this tree so we
can change some property of it, ask it about its configuration, or its state,
and more. This is why iommi requires names for everything. This might seem
overly verbose in the beginning but this is what enables many of the powerful
features of iommi and the robust error handling and error messages.

This philosophy is what enables `Single point customization with no boilerplate`_ via :ref:`dispatching`.

Traversing a namespace is done with __ when . can't be used in normal python syntax
-----------------------------------------------------------------------------------

If you have a class `Car` that has a member `engine` of type `Engine`. Now
let's say you want to create a `Car` with an electric engine. In standard
OOP the `Car` constructor might take an `engine` parameter so you'll end up
with something like:

.. code:: python

    car = Car(engine=ElectricEngine())

which is fine if you want to replace the entire engine, but if you just wanted
to configure a small thing but keep all the defaults this can become noisy:

.. code:: python

    car = Car(
        engine=InternalCombustionEngine(
            turbo=True,
            cylinders=6,
            gearbox=SequentialGearbox(
                clutch_type='double',
            ),
            color='blue',
            doors=4,
            make='toyota'
            # ...and on and on!...
    )

Now it's impossible to see the intent of the programmer: which of all those
options was the single thing they wanted to change and which are copy paste
of the defaults? Turns out in this case it was just the `clutch_type`! We
would like to write:

.. code:: python

    car = Car(engine.gearbox.clutch_type='double')

but pythons syntax doesn't allow this. So instead we use `__`:

.. code:: python

    car = Car(engine__gearbox__clutch_type='double')

this is an elegant solution to this problem, one we've stolen from Djangos ORM.


Callables for advanced usage, values for the simple cases
---------------------------------------------------------

We want the simple cases to be obvious and simple and the complex cases to
be possible. To enable this we aim to make it so that every place you can
place a value, you can use a lambda. So for example the simple case could be:

.. code:: python

    form = Form(
        auto__model=Musician,
        fields__instrument__initial='guitar',
    )

but for the more dynamic case we can write:


.. code:: python

    form = Form(
        auto__model=Musician,
        fields__instrument__initial=
            lambda form, **_: 'guitar' if form.get_request().is_staff else 'tambourine',
    )

The rule here is that the callable has to match at least one argument of those
we supply. In this case you have `form`, and `field` accessible. If you don't
know which arguments you can use, you can write whatever and you will get an
error message telling you what arguments are available.

The reason we don't allow you to match a function that takes just `**` is
because we've found that this becomes very error prone and confusing.

Late binding
------------

Late binding allows us to sometimes avoid doing work, but more importantly
it enables us to build more flexible customizations. A concrete example can
be to show a column in a table for only staff users even though the table is
defined in the module scope, long before there even is a request object.

Late binding is accomplished by two mechanisms:

- not creating object structures until the :ref:`bind` phase
- and `Callables for advanced usage, values for the simple cases`_


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
        columns__foo__include=False,  # <- hides the column foo
        sortable=True,                # <- turns on sorting again
    )

...without having to create a new class inheriting from ``MyTable``. So
the API keeps all the power of the simple style and also getting the
nice syntax of a declarative API.

Prepackaged commonly used patterns (that can still be customized!)
------------------------------------------------------------------

A pattern you'll see often in iommi is that we have class methods instead of
classes. We call these "shortcuts". We don't need to have classes in order to
share functionality and in fact we think this hinders composability and hides
lack of customizability.

A shortcut is a bunch of config (and sometimes a tiny bit of code) that also
has a name. We use these instead of writing `Field` subclasses. The names of
these shortcuts is also used by the style system to determine what rules to
apply.

An important difference between a traditional class and a shortcut is that the
config in a shortcut are defaults, not hard behavior. That means we can start
with a shortcut that does mostly what we want and then pass one or more
arguments to further refine. Again without writing a class.

Single point customization with no boilerplate
----------------------------------------------

GUIs consists of layers of abstraction like a form containing fields,
fields containing input tags, and a button. But to customize the input tag of
a form field row you must subclass several classes even for very trivial
things. Often trivial things also requires copy pasting a template and making
a minor change. This leads to lots of code that basically does nothing and it
*hides* the unique and relevant code in the noise of the other cruft around
it that is just copy paste or boilerplate.

In iommi we strive to avoid this by enabling one-off customizations with
*no overhead*. To set a CSS style on a specific input field inside a form
that was automatically generated we can write:

.. code:: python

    Form(
        auto__model=Foo,
        fields__a_field__input__attrs__style__font='helvetica')

See also `Everything has a name`_

Escape hatches included
-----------------------

It's frustrating when a library can't do what you want. But if the library
can't be *extended* to do what you want it's even worse. We aim to include escape
hatches for when you reach the limits of iommi. You should be able to add your
own logic and data without having to subclass or patch the code.

Very often it's useful to add some little bit of data on the side that you need
later to customize something. We think it's important to support this use case
with minimal amounts of code. To do this we have a field called `extra` on most
of the classes in iommi. This is your place to put whatever you want in order
to extend iommi for a general feature or just some simple one-off customization
for a single view. We also have `extra_evaluated` that is similar but values
here are evaluated (see
`Callables for advanced usage, values for the simple cases`_)   All Part
derived classes have `extra` and `extra_evaluated` namespaces, for example:
Page, Column, Table, Field, Form, and Action.
