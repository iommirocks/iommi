from django.apps import AppConfig

from iommi.from_model import register_search_fields
from iommi.style_bootstrap_docs import bootstrap_docs


class IommiConfig(AppConfig):
    name = 'iommi'
    verbose_name = 'iommi'
    default = True

    def ready(self):
        from django.contrib.auth.models import (
            Permission,
            User,
        )

        register_search_fields(model=User, search_fields=['username'])
        register_search_fields(model=Permission, search_fields=['codename'])

        from iommi import Style, register_style
        from iommi.style_base import base
        from iommi.style_bootstrap import bootstrap
        from iommi.style_bootstrap5 import bootstrap5
        from iommi.style_bulma import bulma
        from iommi.style_django_admin import django_admin
        from iommi.style_foundation import foundation
        from iommi.style_semantic_ui import semantic_ui
        from iommi.style_test_base import test
        from iommi.style_uikit import uikit
        from iommi.style_water import water
        from iommi.style_us_web_design_system import us_web_design_system
        from iommi.style_vanilla_css import vanilla_css

        register_style('blank', Style(internal=True))
        register_style('base', base)
        register_style('test', test)
        register_style('bulma', bulma)
        register_style('bootstrap', bootstrap)
        register_style('bootstrap5', bootstrap5)
        register_style('semantic_ui', semantic_ui)
        register_style('water', water)
        register_style('foundation', foundation)
        register_style('django_admin', django_admin)
        register_style('uikit', uikit)
        register_style('us_web_design_system', us_web_design_system)
        register_style('bootstrap_docs', bootstrap_docs)
        register_style('vanilla_css', vanilla_css)

        from django.contrib.contenttypes.fields import (
            GenericForeignKey,
            GenericRelation,
        )

        from iommi import register_factory

        register_factory(GenericRelation, factory=None)
        register_factory(GenericForeignKey, factory=None)
