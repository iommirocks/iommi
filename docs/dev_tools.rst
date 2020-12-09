Dev tools
=========

iommi ships with several integrated tools to make it faster to develop. They
are shown by on iommi pages when `settings.DEBUG` is `True`. Some are always
active and some are optional and needs to be added to your project.

.. toctree::


Code (jump to your code)
------------------------

Click this button to jump to the code of the current view in your IDE. By
default it is configured to jump into PyCharm, but you can configure it
for your use case by defining `settings.IOMMI_DEBUG_URL_BUILDER`. This is a
callable that takes `filename` and `lineno` arguments and returns a string.

On your staging server you can use this to point to your source code too,
which can be very handy.


Tree
----

This tool shows you the full tree of the current page with the names, full
iommi paths, types (with links to documentation), and the included state
of all the nodes in the tree.


Pick
----

If you want to configure some part of a page, pick is your friend. Start the
pick tool and then click on the item and you'll get the iommi path to that
part with the type shown (with a link to the documentation). You will also
get the paths and types of all the parent components up the tree.


Edit
----

Edit the code of your view directly in your browser. It re-renders
as-you-type and when the syntax is correct and execution succeeded it will
save the code back to disk. This works not just for iommi views, but for any
function based view.

.. note::

    This feature isn't enabled by default because it requires you to add
    `'iommi.live_edit.Middleware'` to `settings.MIDDLEWARE`. Note that you need
    to add this at the very top of the middleware list!



Profile
-------

Press this tool to get a cProfile output for the current page. By default it
will do sorting on the cumulative time, but you can do `?_iommi_prof=tottime`
to get the total time. If you have gprof2dot installed you can also do
`?_iommi_prof=graph` to get a graph output.

.. note::

    This feature isn't enabled by default because it requires you to add
    `'iommi.profiling.Middleware'` to `settings.MIDDLEWARE`.


SQL trace
---------

This tool gives you a list of all SQL statements issued by the page, with
timing for each, and a timeline at the top for each statement. There is also
a grouped time graph so if you have many similar database hits you will see
those easily.

.. note::

    This feature isn't enabled by default because it requires you to add
    `'iommi.sql_trace.Middleware'` to `settings.MIDDLEWARE`.
