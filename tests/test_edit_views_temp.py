from django.http import HttpResponse


def foo_view(request):
    return HttpResponse('changed!')
