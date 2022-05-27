from django.urls import (
    include,
    path,
)

from iommi.admin import Admin


class MyAdmin(Admin):
    class Meta:
        iommi_style = 'bootstrap_docs'


urlpatterns = [
    path('admin/', include(MyAdmin.urls()))
]
