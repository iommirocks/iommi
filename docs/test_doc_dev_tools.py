from tests.helpers import req

request = req('get')


def test_dev_tools():
    # language=rst
    """
    Dev tools
    =========

    iommi ships with several integrated tools to increase your development speed. They
    are shown on iommi pages when `settings.DEBUG` is `True`. Some are always
    active and some are optional and needs to be added to your project.


    """
    

def test_code_():
    # language=rst
    """
    Code (jump to your code)
    ------------------------

    Click this button to jump to the code of the current view in your IDE. By
    default it is configured to jump into PyCharm, but you can configure it
    for your use case by defining `settings.IOMMI_DEBUG_URL_BUILDER`. This is a
    callable that takes `filename` and `lineno` arguments and returns a string.

    On your staging server you can use this to point to your source code too,
    which can be very handy.

    For VSCode: `IOMMI_DEBUG_URL_BUILDER = lambda filename, lineno: 'vscode://file/%s:' % (filename,)+ ('' if lineno is None else "%d" % (lineno,))`


    """
    

def test_tree():
    # language=rst
    """
    Tree
    ----

    This tool shows you the full tree of the current page with the names, full
    iommi paths, types (with links to documentation), and the included state
    of all the nodes in the tree.


    """
    

def test_pick():
    # language=rst
    """
    Pick
    ----

    If you want to configure some part of a page, pick is your friend. Start the
    pick tool and then click on the item and you'll get the iommi path to that
    part with the type shown (with a link to the documentation). You will also
    get the paths and types of all the parent components up the tree.


    """
    

def test_edit():
    # language=rst
    """
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

    This tool is full arbitrary remote execution so it will be *very* bad if you run this in production! It will only work when `DEBUG` is true.


    """
    

def test_profile():
    # language=rst
    """
    Profile
    -------

    Press this tool to get a cProfile output for the current page. By default it
    will do sorting on the cumulative time, but you can do `?_iommi_prof=tottime`
    to get the total time.

    - If you have gprof2dot installed you can also do `?_iommi_prof=graph` to get a graph output.
    - If you have snakeviz installed you can also do `?iommi_prof=snake` to get snakeviz output.

    .. note::

        This feature isn't enabled by default because it requires you to add
        `'iommi.profiling.Middleware'` to `settings.MIDDLEWARE`. Note that you
        need to put this below `django.contrib.auth.middleware.AuthenticationMiddleware`
        if you want to use this in production. Only staff users are allowed to
        profile in production, but all users can profile in debug mode.


    """
    

def test_sql_trace():
    # language=rst
    """
    SQL trace
    ---------

    This tool gives you a list of all SQL statements issued by the page, with
    timing for each, and a timeline at the top for each statement. There is also
    a grouped time graph so if you have many similar database hits you will see
    those easily.

    .. note::

        This feature isn't enabled by default because it requires you to add
        `'iommi.sql_trace.Middleware'` to `settings.MIDDLEWARE`. Note that you
        need to put this below `django.contrib.auth.middleware.AuthenticationMiddleware`
        if you want to use this in production. Only staff users are allowed to
        trace sql in production, but all users can trace sql in debug mode.

    In DEBUG the SQL trace middleware will automatically warn you if you have views
    appear to have `N+1 type errors <https://stackoverflow.com/questions/97197/what-is-the-n1-selects-problem-in-orm-object-relational-mapping>`_. By default iommi will will print stack traces and example SQL statements
    for the worst offenders for your view to the console:

    .. code-block::

        ------ 5 times: -------
        From source:
          File "/Users/boxed/Projects/iommi/examples/examples/table_examples.py", line 146, in root => return Page(
        With Stack:
          File "iommi/table.py", line 308, in default_cell__value => return getattr_path(row, evaluate_strict(column.attr, row=row, column=column, **kwargs))
          File "iommi/evaluate.py", line 60, in evaluate => return func_or_value(**kwargs)
          File "iommi/evaluate.py", line 76, in evaluate_strict => return evaluate(func_or_value, __signature=None, __strict=True, __match_empty=__match_empty, **kwargs)
          File "iommi/table.py", line 933, in __init__ => self.tag = evaluate_strict(self.tag, **self._evaluate_parameters)
          File "iommi/table.py", line 887, in __iter__ => yield Cell(cells=self, column=column)
        SELECT "examples_tfoo"."id", "examples_tfoo"."name", "examples_tfoo"."a" FROM "examples_tfoo" WHERE "examples_tfoo"."id" = 1
        SELECT "examples_tfoo"."id", "examples_tfoo"."name", "examples_tfoo"."a" FROM "examples_tfoo" WHERE "examples_tfoo"."id" = 2
        SELECT "examples_tfoo"."id", "examples_tfoo"."name", "examples_tfoo"."a" FROM "examples_tfoo" WHERE "examples_tfoo"."id" = 3
        SELECT "examples_tfoo"."id", "examples_tfoo"."name", "examples_tfoo"."a" FROM "examples_tfoo" WHERE "examples_tfoo"."id" = 4
        ... and 1 more unique statements


    If you want more detailed information in your console to debug a problem you can set
    `settings.SQL_DEBUG` to `'all'` (which prints all SQL statements), `'stacks'` (all SQL statements with tracebacks). You can also set it to `None` to turn it off.


    You can use this middleware on non-iommi views too. Just add `?_iommi_sql_trace` to your url.
    """
