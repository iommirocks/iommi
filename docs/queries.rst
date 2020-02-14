Queries
=======

iommi queries makes it easy to implement searching and filtering in your Django app.

Major features:

- Generate simple filtering GUIs
- Supply your views with an advanced query language
- Query language can be used stand alone without the GUI parts
- Highly customizable GUI based on iommi :doc:`forms`

Queries are normally used from inside iommi tables where they are an
integrated part, but can also be used stand alone. See below for an
example.

Read the full documentation and the :doc:`howto` for more.

.. contents::
    :local:


Query language
--------------

iommi comes with an advanced query language so users can filter tables
after what they want. Searching songs can look like this:

.. code::

    album=Paranoid AND lyrics:"have the power"

This will find the song War Pigs, as it's from the album Paranoid and
the lyrics contains the text "have the power".   The query language supports
`AND` and `OR`, parenthesis and the operations `<`, `<=`, `>`, `>=` for
numerical values, and `=` for all values which is an exact case insensitive
match. You can exclude with `!=`. As the example above shows `:` is used for
case insensitive "contains" queries, and the inverse of that is `!:`

iommi tries to support what the user might intuitively write for searching
boolean columns. It will interpret "n", "no", "0" (zero), "false", "f" and "off"
as `false`  and the corresponding values for `true`.

You can configure a `Variable` to be case sensitive by setting `query_operator_to_q_operator`
to `case_sensitive_query_operator_to_q_operator`.

iommi queries have a special form for filtering directly on pk, which can be
very handy: `album.pk=3`.

`query_operator_for_form` specifies what operation the simple form uses to
interpret its inputs. The default is `=`, meaning exact case insensitive match.

If you have table of `Song` and a foreign key to `Album`, if you search for
`album=Paranoid` iommi will by default create the Django query
`Q(album__name='Paranoid')`. If the name field isn't called `name` you can
register another name field with `register_name_field`, or if you want
something other special for just this view you can use the `name_field`
parameter to specify the name field to use. Note that you can use `pk` or
other non-string columns as the name field if you want.


Stand alone example
-------------------

Simple view that allows the user to search for a car by choosing the make from a drop down, and search
for specific model in the advanced mode:

.. code:: python

    class CarQuery(Query):
        make = Variable.choice(
            choices=['Toyota', 'Volvo', 'Ford'],
            form_fields__include=True)  # Display this field in the simple style GUI
        model = Variable.text()

    def cars(request):
        query = CarQuery()
        query.bind(request=request)
        cars_query_set = query.get_q()
        form = query.form
        return render(
            template_name='cars.html',
            context={
                'query_form': form,
                'cars': cars_query_set,
            },
        )


.. code:: html

    <!-- cars.html -->
    {% include "iommi/form.html" with form=query_form %}

    <ul>
        {% for car in cars %}
            <li>{{ car }}</li>
        {% endfor %}
    </ul>


.. image:: simple_gui.png

After switching to the advanced mode:

.. image:: advanced_gui.png

Programmatically call the search API:

.. code:: python

    query = CarQuery()
    cars_query_set = query.parse_query_string(
        'make=Toyota and (make=1991 or make=1992)'
    )
