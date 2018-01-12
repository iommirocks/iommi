from django.conf.urls import include, url
from django.contrib import admin
from examples import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^readme_example_1/$', views.readme_example_1, name='readme_example_1'),
    url(r'^readme_example_2/$', views.readme_example_2, name='readme_example_2'),
    url(r'^kitchen_sink/$', views.kitchen_sink, name='kitchen_sink'),

    url(r'^style.css$', views.style, name='style'),
]
