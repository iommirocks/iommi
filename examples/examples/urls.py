from django.conf.urls import patterns, include, url
from django.contrib import admin

urlpatterns = patterns('',
    url(r'^$', 'examples.views.index', name='index'),
    url(r'^example_1/$', 'examples.views.example_1', name='example_1'),
    url(r'^example_2/$', 'examples.views.example_2', name='example_2'),
    url(r'^example_3/$', 'examples.views.example_3', name='example_3'),
    url(r'^style.css$', 'examples.views.style', name='style'),

    url(r'^admin/', include(admin.site.urls)),
)
