Queries
=======

iommi queries makes it easy to implement searching and filtering in your Django app.

Major features:

- Generate simple filtering GUIs
- Supply your views with an advanced query language
- Query language can be used stand alone without the GUI parts
- Highly customizable GUI based on iommi :doc:`forms`


Example
-------

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
        cars_query_set = query.to_q()
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
    cars_query_set = query.parse(
        'make=Toyota and (make=1991 or make=1992)'
    )
