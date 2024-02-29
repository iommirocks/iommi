
from iommi._web_compat import HttpResponse


def foo_view(request):
    return HttpResponse('changed!')
