from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import (
    include,
    path,
)

import examples.views as views
from examples import (
    form_examples,
    menu_examples,
    page_examples,
    supernaut,
    table_examples,
)

urlpatterns = [
    path('', include(views)),
    path('page/', include(page_examples)),
    path('form/', include(form_examples)),
    path('table/', include(table_examples)),
    path('menu/', include(menu_examples)),
    path('supernaut/', include(supernaut)),

    path('admin/', admin.site.urls),  # This is mostly to make the django_admin style available

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
