from iommi.live_edit import live_edit_view
from tests.helpers import req

def view(request):
    return HttpResponse('hello!')


def test_live_edit():
    live_edit_view(req('get'), view)
