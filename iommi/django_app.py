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

        from iommi import register_style
        from iommi.style_test import test
        from iommi.style_base import base
        from iommi.style_bootstrap import (
            bootstrap,
            bootstrap_horizontal,
        )
        from iommi.style_semantic_ui import semantic_ui
        register_style('base', base)
        register_style('test', test)
        register_style('bootstrap', bootstrap)
        register_style('bootstrap_horizontal', bootstrap_horizontal)
        register_style('semantic_ui', semantic_ui)
