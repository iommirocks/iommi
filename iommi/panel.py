from typing import Type

from django.utils.functional import Promise
from django.utils.translation import gettext_lazy

from iommi.fragment import Fragment
from iommi.part import Part
from iommi.evaluate import evaluate_member
from iommi.refinable import EvaluatedRefinable, Refinable
from iommi.declarative.namespace import Namespace
from iommi._web_compat import Template
from iommi.shortcut import with_defaults


class PanelCol(Fragment):
    """
    generates div.col - for wrapping all children of Panel.row
    """

    @with_defaults(
        tag='div',
        attrs__class__col=True,
        **{
            'attrs__data-iommi-type': lambda traversable, **_: type(traversable).__name__
        },
    )
    def __init__(self, **kwargs):
        super(PanelCol, self).__init__(**kwargs)


class Panel(Fragment):
    """
    wrappers for defining Form.layout
    """
    _parent_form = Refinable()  # Form|None
    _parent_table = Refinable()  # Table|None
    _parent_table_cells = Refinable()  # Cells|None
    parent_panel = None
    fieldset_legend: str = EvaluatedRefinable()
    col_class: Type[PanelCol] = Refinable()
    col = Refinable()
    nested_path: str = EvaluatedRefinable()  # path of a field in nested forms

    class Meta:
        col_class = PanelCol
        _parent_form = None
        _parent_table = None
        _parent_table_cells = None

    @with_defaults(
        tag=None,
    )
    def __init__(self, children: dict=None, **kwargs):
        super(Panel, self).__init__(children=children, **kwargs)

    def as_dict(self):
        return self.iommi_namespace.children

    def _get_cached_ancestor(self, property_name, instance_of):
        cache_property_name = f'_parent{property_name}'
        if (cached_value := getattr(self, cache_property_name)) is not None:
            return cached_value

        node = self
        while node.iommi_parent() is not None:
            node = node.iommi_parent()
            if isinstance(node, Panel) and (value := getattr(node, property_name)) is not None:
                setattr(self, cache_property_name, value)
                break
            elif isinstance(node, instance_of):
                setattr(self, cache_property_name, node)
                break

        return getattr(self, cache_property_name)

    @property
    def _form(self):
        # I can't do this in on_bind
        # I need to have this as @property, so I can use form in include, because include is called before on_bind
        from iommi.form import Form
        return self._get_cached_ancestor('_form', Form)

    @property
    def _table(self):
        # I can't do this in on_bind
        # I need to have this as @property, so I can use table in include, because include is called before on_bind
        from iommi.table import Table
        return self._get_cached_ancestor('_table', Table)

    @property
    def _table_cells(self):
        # I can't do this in on_bind
        # I need to have this as @property, so I can use cells in include, because include is called before on_bind
        from iommi.table import Cells
        return self._get_cached_ancestor('_table_cells', Cells)

    def on_bind(self) -> None:
        super(Panel, self).on_bind()

        node = self
        while node.iommi_parent() is not None:
            node = node.iommi_parent()
            if isinstance(node, Panel) and self.parent_panel is None:
                self.parent_panel = node
                break

        if self._form is not None:
            if 'field' in getattr(self, 'iommi_shortcut_stack', []):
                related_field = self._form.get_field(self.nested_path if self.nested_path is not None else self.iommi_name())
                self.children['field'] = related_field
                self._bound_members.children._bound_members['field'] = related_field
            elif 'nested_form' in getattr(self, 'iommi_shortcut_stack', []):
                nested_form = self._form.get_nested_form(self.iommi_name())  # ? also self.nested_path or not ?
                self.children['nested_form'] = nested_form
                self._bound_members.children._bound_members['nested_form'] = nested_form

        if self._table is not None and 'cell' in getattr(self, 'iommi_shortcut_stack', []):
            cells = self._table_cells
            assert cells is not None

            related_cell = cells[self.nested_path if self.nested_path is not None else self.iommi_name()]
            self.children['cell'] = related_cell
            self._bound_members.children._bound_members['cell'] = related_cell

        evaluate_member(self, 'fieldset_legend', **self.iommi_evaluate_parameters())

    def own_evaluate_parameters(self):
        # pass panel, form and table to all callables + to template rendering
        return dict(
            panel=self,
            form=self._form,
            table=self._table,
            **super(Panel, self).own_evaluate_parameters()
        )

    def __html__(self, *args, **kwargs):
        r = super(Panel, self).__html__(*args, **kwargs)
        if self.col_class is None or not self.is_col:
            return r
        col_kwargs = self.col
        if col_kwargs is None:
            col_kwargs = {}
        return self.col_class(text=r, **col_kwargs).bind(parent=self).__html__()

    def get_fields(self):
        """recursively gets all fields from the panel"""
        from iommi.form import Field

        fields = {}
        for child in self.children.values():
            if isinstance(child, Field):
                fields[child.iommi_name()] = child
            elif isinstance(child, Panel):
                fields.update(child.get_fields())

        return fields

    def get_cell_panels(self):
        """recursively gets all cells from the panel"""
        cells = {}
        for child in self.children.values():
            if isinstance(child, Panel) and 'cell' in getattr(child, 'iommi_shortcut_stack', []):
                cells[child.iommi_name()] = child
            elif isinstance(child, Panel):
                cells.update(child.get_cell_panels())

        return cells

    @classmethod
    @with_defaults(
        tag=None,
    )
    def part(cls, child=None, **kwargs):
        """
        for non-field parts/fragments
        you don't need to call this by hand, non-field children of rows/fieldsets get wrapped automatically
        """
        children = kwargs.pop('children', {})
        if child is not None:
            key = 'child'
            x = 1
            while key in children:
                key = f'child{x}'
                x += 1
            children[key] = child
        return cls(children=children, **kwargs)

    @classmethod
    @with_defaults(
        tag=None,
    )
    def field(cls, **kwargs):
        """
        generates form field
        """
        return cls(**kwargs)

    @property
    def is_col(self):
        if self.parent_panel is None:
            return False
        return 'row' in getattr(self.parent_panel, 'iommi_shortcut_stack', [])

    @classmethod
    def _get_children_as_panels(cls, children: dict):
        children_as_panels = {}
        for name, child in children.items():
            if isinstance(child, (cls, dict, Namespace)):
                assert '__' not in name
                children_as_panels[name] = child
            elif isinstance(child, Part):
                assert '__' not in name
                children_as_panels[name] = cls.part(child)
            elif isinstance(child, Template) or (isinstance(child, str) and name.endswith('__template')):
                if name.endswith('__template'):
                    name = name[:-10]
                assert '__' not in name
                children_as_panels[name] = cls.part(Fragment(template=child))
            elif isinstance(child, (str, Promise)):  # Promise for gettext_lazy etc.
                assert '__' not in name
                children_as_panels[name] = cls.part(child)
            else:
                raise ValueError(f'Invalid child type: {type(child)} for {name}')
        return children_as_panels

    @classmethod
    @with_defaults(
        tag='div',
        attrs__class__row=True,
    )
    def row(cls, children: dict=None, **kwargs):
        """generates div.row"""
        return cls(children=cls._get_children_as_panels(children), **kwargs)

    @classmethod
    @with_defaults(
        tag='fieldset',
        template='iommi/form/panel_fieldset.html',
    )
    def fieldset(cls, children: dict=None, legend=None, **kwargs):
        """generates <fieldset><legend>{legend}</legend>{subfields/subpanels}</fieldset>"""
        kwargs.setdefault('fieldset_legend', legend)
        return cls(children=cls._get_children_as_panels(children), **kwargs)

    @classmethod
    @with_defaults(
        tag='div',
        attrs__class__card=True,
        template='iommi/form/panel_card.html',
    )
    def card(cls, children: dict=None, header=None, footer=None, **kwargs):
        """eg. for bootstrap div.card"""
        _children = {}

        if header is not None:
            if not isinstance(header, cls) or 'card_header' not in getattr(header, 'iommi_shortcut_stack', []):
                header = cls.card_header(header)
            _children['panel_card_header'] = header

        if footer is not None:
            if not isinstance(footer, cls) or 'card_footer' not in getattr(footer, 'iommi_shortcut_stack', []):
                footer = cls.card_footer(footer)
            _children['panel_card_footer'] = footer

        _children.update(children)

        return cls(children=cls._get_children_as_panels(_children), **kwargs)

    @classmethod
    @with_defaults(
        tag='div',
        **{'attrs__class__card-header': True}
    )
    def card_header(cls, child=None, **kwargs):
        children = kwargs.pop('children', {})
        if child is not None:
            children['header'] = child
        return cls(children=children, **kwargs)

    @classmethod
    @with_defaults(
        tag='div',
        **{'attrs__class__card-footer': True}
    )
    def card_footer(cls, child=None, **kwargs):
        children = kwargs.pop('children', {})
        if child is not None:
            children['footer'] = child
        return cls(children=children, **kwargs)

    @classmethod
    @with_defaults(
        tag='div',
        attrs__role='alert',
        **{'attrs__class__alert': True}
    )
    def alert(cls, child=None, level='info', **kwargs):
        children = kwargs.pop('children', {})
        if child is not None:
            children['footer'] = child
        kwargs[f'attrs__class__alert-{level}'] = True
        return cls(children=children, **kwargs)

    @classmethod
    @with_defaults(
        tag=None,
    )
    def nested_form(cls, **kwargs):
        """
        generates nested form
        """
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        tag='div',
    )
    def div(cls, children: dict=None, **kwargs):
        return cls(children=cls._get_children_as_panels(children), **kwargs)

    @classmethod
    @with_defaults(
        tag=None,
    )
    def cell(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        tag='span',
        attrs__title=gettext_lazy('Drag and drop to reorder'),
        **{
            'attrs__class__reordering-handle-cell': True,
            'attrs__data-iommi-reordering-handle': True,
        }
    )
    def reorder_handle(cls, **kwargs):
        return cls.cell(**kwargs)
