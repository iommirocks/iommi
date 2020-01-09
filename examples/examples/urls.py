from django.conf.urls import url
import examples.views as views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^example_1/$', views.example_1, name='example_1'),
    url(r'^example_2/$', views.example_2, name='example_2'),
    url(r'^example_3/$', views.example_3, name='example_3'),
    url(r'^example_4/$', views.example_4, name='example_4'),
    url(r'^example_5/$', views.example_5, name='example_5'),
    url(r'^kitchen/$', views.kitchen),
    url(r'^style.css$', views.style, name='style'),

    url(r'^readme_example_1/$', views.readme_example_1, name='readme_example_1'),
    url(r'^readme_example_2/$', views.readme_example_2, name='readme_example_2'),
    url(r'^kitchen_sink/$', views.kitchen_sink, name='kitchen_sink'),
]
