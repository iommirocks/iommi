from iommi import (
    Asset,
    html,
    Page,
)
from tests.helpers import (
    prettify,
    req,
)


def test_assets_float_to_root():
    class MyPage(Page):
        foo = html.div('foo', assets__my_asset=Asset.css(attrs__href='http://foo.bar/baz'))

    expected = prettify(
        '''
        <!DOCTYPE html>
        <html>
            <head>
                <title/>
                <link href='http://foo.bar/baz' rel="stylesheet"/>
            </head>
            <body>
                <div> foo </div>
            </body>
        </html>
    '''
    )
    actual = prettify(MyPage().bind(request=req('get')).render_to_response().content)
    assert actual == expected


def test_assets_render_once():
    an_asset = Asset.css(attrs__href='http://foo.bar/baz')

    class MyPage(Page):
        foo = html.div('foo', assets__my_asset=an_asset)
        bar = html.div('bar', assets__my_asset=an_asset)

    expected = prettify(
        '''
        <!DOCTYPE html>
        <html>
            <head>
                <title/>
                <link href='http://foo.bar/baz' rel="stylesheet"/>
            </head>
            <body>
                <div> foo </div>
                <div> bar </div>
            </body>
        </html>
    '''
    )
    actual = prettify(MyPage().bind(request=req('get')).render_to_response().content)
    assert actual == expected


def test_assets_render_any_fragment():
    class MyPage(Page):
        foo = html.div('foo', assets__my_asset=html.span(attrs__href='http://foo.bar/baz'))

    expected = prettify(
        '''
        <!DOCTYPE html>
        <html>
            <head>
                <title/>
                <span href='http://foo.bar/baz'/>
            </head>
            <body>
                <div> foo </div>
            </body>
        </html>
    '''
    )
    actual = prettify(MyPage().bind(request=req('get')).render_to_response().content)
    assert actual == expected


def test_asset_shortcuts():
    class MyPage(Page):
        class Meta:
            assets__css_asset = Asset.css(attrs__href='http://foo.bar/baz.css')
            assets__js_asset = Asset.js(attrs__href='http://foo.bar/baz.j')

    expected = prettify(
        '''
        <!DOCTYPE html>
        <html>
            <head>
                <title/>
                <link href="http://foo.bar/baz.css" rel="stylesheet"/>
                <script href="http://foo.bar/baz.j"/>
            </head>
             <body />
        </html>
    '''
    )
    actual = prettify(MyPage().bind(request=req('get')).render_to_response().content)
    assert actual == expected
