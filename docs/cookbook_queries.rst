
Queries
-------

.. _Filter.query_operator_to_q_operator:

    


How do I override what operator is used for a query?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The member `query_operator_to_q_operator` for `Filter` is used to convert from e.g. `:`
to `icontains`. You can specify another callable here:


.. code-block:: python

    Table(
        auto__model=Track,
        columns__album__filter__query_operator_to_q_operator=lambda op: 'exact',
    )


The above will force the album name to always be looked up with case
sensitive match even if the user types `album<Paranoid` in the
advanced query language. Use this feature with caution!

See also `How do I control what Q is produced?`_

.. _Filter.value_to_q:

    


How do I control what Q is produced?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For more advanced customization you can use `value_to_q`. It is a
callable that takes `filter, op, value_string_or_f` and returns a
`Q` object. The default handles `__`, different operators, negation
and special handling of when the user searches for `null`.
