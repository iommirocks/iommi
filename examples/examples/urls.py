from django.conf import settings
from django.conf.urls.static import static
from django.urls import (
    include,
    path,
)

import examples.views as views
from examples.models import (
    Foo,
    TFoo,
)
from iommi import (
    Form,
    Table,
)


class MyAdmin(Admin):
    class Meta:
        iommi_style = 'bulma'


urlpatterns = [
    path('', views.index, name='index'),

    path('form_example_1/', views.form_example_1, name='example_1'),
    path('form_example_2/', views.form_example_2, name='example_2'),
    path('form_example_2b/', Form.create(auto__model=Foo).as_view(), name='example_2b'),
    path('form_example_3/', views.form_example_3, name='example_3'),
    path('form_example_4/', views.form_example_4, name='example_4'),
    path('form_example_5/', views.form_example_5, name='example_5'),
    path('form_kitchen/', views.form_kitchen),

    path('table_readme_example_1/', views.table_readme_example_1, name='readme_example_1'),
    path('table_readme_example_2/', views.table_readme_example_2, name='readme_example_2'),
    path('table_auto_example_1/', views.table_auto_example_1, name='readme_example_1'),
    path('table_auto_example_2/', views.table_auto_example_2, name='readme_example_2'),
    path('table_kitchen_sink/', views.table_kitchen_sink, name='kitchen_sink'),
    path('table_as_view/', Table(
        auto__model=TFoo,
        columns__a__bulk__include=True,
        bulk__actions__delete__include=True,
        extra_evaluated__report_name='example_download',
        columns__a__extra_evaluated__report_name='A'
    ).as_view()),

    path('page_busy/', views.page_busy, name='page_busy'),
    path('all_field_sorts/', views.all_field_sorts, name='all_field_sorts'),
    path('all_column_sorts/', views.all_column_sorts, name='all_column_sorts'),

    path('iommi-admin/', include(views.ExampleAdmin.urls())),

    path('menu_test/', views.menu_test, name='menu_test'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
