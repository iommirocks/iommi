
Parts & Pages
-------------

    


How do I override part of a part/page?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is all just *standard* tri.declarative magic, but as you are likely new to it
this might take a while to get used to. Let's say you created yourself a master template
for your site.


.. code-block:: python

    class BasePage(Page):
        title = html.h1('My awesome webpage')
        subtitle = html.h2('It rocks')

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('db037d54-f1cb-48c2-963d-065d899b5faf', this)">▼ Hide result</div>
        <iframe id="db037d54-f1cb-48c2-963d-065d899b5faf" src="doc_includes/cookbook_parts_pages/test_how_do_i_override_part_of_a_part_page.html" style="background: white; display: ; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    

Which you can use like this:


.. code-block:: python

    def index(request):
        class IndexPage(BasePage):
            body = 'body'
        return IndexPage(parts__subtitle__children__child='Still rocking...')

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('4c9f1952-fd48-4b0f-99ae-9bc99a60c596', this)">▼ Hide result</div>
        <iframe id="4c9f1952-fd48-4b0f-99ae-9bc99a60c596" src="doc_includes/cookbook_parts_pages/test_how_do_i_override_part_of_a_part_page1.html" style="background: white; display: ; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    

Here you can see that `Part` s (`Page` s are themselves `Part` s) form a tree and the direct children are gathered in the `parts` namespace. Here we overwrote a leaf of
an existing namespace, but you can also add new elements or replace bigger
parts (and most of the time it doesn't matter if you use the `class Meta` or the
keyword arguments to init syntax):


.. code-block:: python

    def index(request):
        class IndexPage(BasePage):
            title = html.img(attrs=dict(src='https://docs.iommi.rocks/en/latest/_static/logo_with_outline.svg', alt='iommi logo', width='70px'))
        return IndexPage(parts__subtitle=None)

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('66931f05-1a7b-4a8d-83be-609195bb36d0', this)">▼ Hide result</div>
        <iframe id="66931f05-1a7b-4a8d-83be-609195bb36d0" src="doc_includes/cookbook_parts_pages/test_how_do_i_override_part_of_a_part_page2.html" style="background: white; display: ; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    

In the above we replaced the title and removed the subtitle element completely. The
latter of which shows one of the gotchas as only `str`, `Part` and the django
template types are gathered into the parts structure when a `Part` class definition
is processed. As `None` is not an instance of those types, you can remove things
by setting their value to `None`.

    


.. _Page.title:

How do I set the title of my page?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As in the text shown in the browser status bar?

.. code-block:: python

    Page(title='The title in the browser')


Note that this is different from

.. code-block:: python

    class MyPage(Page):
        title = Header('A header element in the dom')

    MyPage()


Which is equivalent to:
    
.. code-block:: python

    Page(parts__title=Header('A header element in the dom'))



.. _Page.context:

How do I specify the context used when a Template is rendered?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: python

    def index(request):
        context = {'today': date.today()}

        class MyPage(Page):
            body = Template("""A django template was rendered on {{today}}.""")

        return MyPage(context=context)

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('9e1bd4f5-a55d-4678-b5d8-afa73dcbc666', this)">▼ Hide result</div>
        <iframe id="9e1bd4f5-a55d-4678-b5d8-afa73dcbc666" src="doc_includes/cookbook_parts_pages/test_how_do_i_specify_the_context_used_when_a_template_is_rendered.html" style="background: white; display: ; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    

You can use the full power of `tri.declarative` to construct the context. This
not only makes the above shorter, but also makes it easy to write abstractions that
can be extended later:


.. code-block:: python

    Page(
        parts__body=Template("""A django template was rendered on {{today}}."""),
        context__today=date.today(),
    )

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('6f692202-c78b-4fcf-a6ac-eadbfcb68524', this)">▼ Hide result</div>
        <iframe id="6f692202-c78b-4fcf-a6ac-eadbfcb68524" src="doc_includes/cookbook_parts_pages/test_how_do_i_specify_the_context_used_when_a_template_is_rendered1.html" style="background: white; display: ; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    