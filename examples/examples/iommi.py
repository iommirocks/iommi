from django.template import Template

import iommi
from iommi.shortcut import with_defaults


class Page(iommi.Page):
    pass


class Action(iommi.Action):
    pass


class Field(iommi.Field):
    @classmethod
    @with_defaults()
    def artist(cls, **kwargs):
        return cls.foreign_key(**kwargs)


class Form(iommi.Form):
    class Meta:
        member_class = Field
        page_class = Page
        action_class = Action


class Filter(iommi.Filter):
    @classmethod
    @with_defaults()
    def artist(cls, **kwargs):
        return cls.foreign_key(**kwargs)


class Query(iommi.Query):
    class Meta:
        member_class = Filter
        form_class = Form


class Column(iommi.Column):
    @classmethod
    @with_defaults()
    def artist(cls, **kwargs):
        return cls.foreign_key(**kwargs)


class Table(iommi.Table):
    class Meta:
        member_class = Column
        form_class = Form
        query_class = Query
        page_class = Page
        action_class = Action


class EditColumn(iommi.EditColumn):
    @classmethod
    @with_defaults()
    def artist(cls, **kwargs):
        return cls.foreign_key(**kwargs)


class EditTable(iommi.EditTable):
    class Meta:
        member_class = EditColumn
        form_class = Form
        query_class = Query
        page_class = Page
        action_class = Action


class Menu(iommi.Menu):
    pass


class MenuItem(iommi.MenuItem):
    pass
