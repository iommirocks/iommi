from django.urls import (
    include,
    path,
)

from iommi._web_compat import HttpResponse
from iommi.admin import Admin


class MyAdmin(Admin):
    class Meta:
        iommi_style = 'bootstrap_docs'


def dummy_view(request):
    return HttpResponse('this is a dummy view')


urlpatterns = [path('dummy/', dummy_view, name='dummy_view'), path('admin/', include(MyAdmin.urls()))]
