from django.conf.urls import patterns, include, url
from django.contrib import admin

urlpatterns = patterns('',
    url(r'^$', 'examples.views.index', name='index'),
    url(r'^readme_example_1/$', 'examples.views.readme_example_1', name='readme_example_1'),
    url(r'^readme_example_2/$', 'examples.views.readme_example_2', name='readme_example_2'),
    url(r'^kitchen_sink/$', 'examples.views.kitchen_sink', name='kitchen_sink'),

    url(r'^style.css$', 'examples.views.style', name='style'),

    url(r'^admin/', include(admin.site.urls)),
)
