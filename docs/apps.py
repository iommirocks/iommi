from django.apps import AppConfig


class DocsConfig(AppConfig):
    name = 'docs'
    verbose_name = 'Discography'
    default = True

    def ready(self):
        from docs.models import Artist
        from iommi import register_search_fields

        register_search_fields(model=Artist, search_fields=['name'], allow_non_unique=True)
