from django.http import HttpResponse

from iommi.fragment import Fragment
from iommi import iommi_render
from tests.helpers import req


def test_render_decorator():
    @iommi_render
    def my_view(request, *args, **kwargs):
        assert args == ('foo',)
        assert kwargs == {'bar': 'baz'}
        return Fragment('The content')

    result = my_view(req('get'), 'foo', bar='baz')

    assert isinstance(result, HttpResponse)
    assert 'The content' in result.content.decode()
