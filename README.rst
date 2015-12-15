.. image:: https://travis-ci.org/TriOptima/tri.query.svg?branch=master
    :target: https://travis-ci.org/TriOptima/tri.query

.. image:: http://codecov.io/github/TriOptima/tri.query/coverage.svg?branch=master
    :target: http://codecov.io/github/TriOptima/tri.query?branch=master

tri.query
==========

tri.query makes it easy to implement searching and filtering in your Django app.

Major features:

- Generate simple filtering GUIs easily while at the same time:
- Supply your views with advanced query languages
- Query language can be used stand alone without the GUI parts
- Highly customizable GUI based on `tri.form <http://github.com/trioptima/tri.form#tri.form>`_


Example
-------


Simple view that allows the user to search for a car by choosing the make from a drop down, and search
for specific model in the advanced mode:

.. code:: python

    class CarQuery(Query):
        make = Variable.choice(
            choices=['Toyota', 'Volvo', 'Ford'],
            form_field__show=True)  # Display this field in the simple style GUI
        model = Variable.text()

    def cars(request):
        query = CarQuery()
        cars_query_set = query.request_to_q(request)
        form = query.form()
        return render(
            template_name='cars.html',
            context_instance=RequestContext(request, {'query_form': form, 'cars': cars_query_set}))


.. code:: html

    <!-- cars.html -->
    {% include "tri_query/form.html" with form=query_form %}

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
    cars_query_set = query.parse('make=Toyota and (make=1991 or make=1992)')


Running tests
-------------

You need tox installed then just `make test`.


License
-------

BSD


Documentation
-------------

http://triquery.readthedocs.org
