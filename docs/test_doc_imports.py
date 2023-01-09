# language=rst
"""
Imports used in the iommi documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""


# noinspection PyUnresolvedReferences
def test_imports():
    # language=rst
    """
    iommi imports
    =============
    """

    from iommi import (
        Action,
        Asset,
        Column,
        EditTable,
        EditColumn,
        Field,
        Fragment,
        Form,
        Fragment,
        Header,
        Menu,
        MenuItem,
        middleware,
        Page,
        Part,
        Query,
        Table,
        Filter,
        LAST,
        MISSING,
        register_factory,
        register_field_factory,
        register_filter_factory,
        register_column_factory,
        register_cell_formatter,
        register_style,
        register_search_fields,
        Style,
        html,
        iommi_render,
    )
    from iommi.path import (
        decode_path,
        decode_path_components,
        register_path_decoding,
    )

    # language=rst
    """
    Django imports
    ==============
    """
    from django.template import Template
    from django.contrib.auth.models import User
    from django.shortcuts import get_object_or_404
    from django.urls import path

    # language=rst
    """
    Documentation models
    ====================
    """
    from docs.models import (
        Artist,
        Album,
        Track,
        Musician,
        Car,
    )
