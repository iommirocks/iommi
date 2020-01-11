from django.conf.urls import url
import examples.views as views

urlpatterns = [
    url(r'^$', views.index, name='index'),

    url(r'^form/$', views.form_index, name='form_index'),
    url(r'^form/example_1/$', views.form_example_1, name='example_1'),
    url(r'^form/example_2/$', views.form_example_2, name='example_2'),
    url(r'^form/example_3/$', views.form_example_3, name='example_3'),
    url(r'^form/example_4/$', views.form_example_4, name='example_4'),
    url(r'^form/example_5/$', views.form_example_5, name='example_5'),
    url(r'^form/kitchen/$', views.form_kitchen),
    url(r'^style.css$', views.form_style, name='style'),

    url(r'^table/$', views.table_index, name='table_index'),
    url(r'^table/readme_example_1/$', views.table_readme_example_1, name='readme_example_1'),
    url(r'^table/readme_example_2/$', views.table_readme_example_2, name='readme_example_2'),
    url(r'^table/kitchen_sink/$', views.table_kitchen_sink, name='kitchen_sink'),
]
