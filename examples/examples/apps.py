from django.apps import AppConfig


class ExampleConfig(AppConfig):
    name = 'examples'
    verbose_name = 'examples'
    default = True

    def ready(self):
        from examples.models import (
            Artist,
            Album,
        )
        from iommi import register_search_fields

        register_search_fields(model=Artist, search_fields=['name'], allow_non_unique=True)
        register_search_fields(model=Album, search_fields=['name'], allow_non_unique=True)
