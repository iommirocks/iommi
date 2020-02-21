from django.apps import AppConfig

from iommi.from_model import register_name_field


class IommiConfig(AppConfig):
    name = 'iommi'
    verbose_name = 'iommi'

    def ready(self):
        from django.contrib.auth.models import (
            User,
            Permission,
        )
        register_name_field(model=User, name_field='username')
        register_name_field(model=Permission, name_field='codename')
