import functools
import json
from typing import (
    Dict,
    List,
    Optional,
)

from django.db.models import QuerySet
from django.http.response import (
    HttpResponse,
    HttpResponseRedirect,
)
from django.template.context_processors import csrf
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from iommi.base import render_template_name, PartType, render_or_respond_part, path_join, NO_ENDPOINT_PREFIX, DISPATCH_PATH_SEPARATOR, PagePart
from iommi.table import table_context
from tri_declarative import (
    dispatch,
    EMPTY,
    declarative,
    sort_after,
    should_show,
    setdefaults_path,
    Namespace,
    class_shortcut,
    Refinable,
)
from iommi.render import render_attrs

from iommi._web_compat import (
    Template,
    render_template,
    ValidationError,
)
from iommi.views import create_or_edit_object_redirect
from tri_struct import Struct


@declarative(
    parameter='parts_dict',
    is_member=lambda obj: isinstance(obj, (PagePart, str, Template)),
    sort_key=lambda x: 0,
)
class Page(PagePart):
    @dispatch(
        part=EMPTY,
    )
    def __init__(
        self,
        *,
        parts: List[PartType] = None,
        parts_dict: Dict[str, PartType] = None,
        part: dict,
        endpoint_dispatch_prefix=NO_ENDPOINT_PREFIX,
    ):
        self.endpoint_dispatch_prefix = endpoint_dispatch_prefix

        def generate_parts():
            if parts is not None:
                for part_ in parts:
                    yield part_
            for name, part_ in {**parts_dict, **part}.items():
                if isinstance(part_, dict):
                    if 'call_target' not in part_:
                        assert False, f"I got a 'part' that didn't result in a PagePart. It's called {name} and looks like {part_}."

                    yield Namespace(part_)(name=name)
                elif isinstance(part_, PagePart):
                    part_.name = name
                    if self.endpoint_dispatch_prefix:
                        part_.endpoint_dispatch_prefix = path_join(self.endpoint_dispatch_prefix, name)
                    yield part_
                else:
                    kwargs = dict(endpoint_dispatch_prefix=path_join(self.endpoint_dispatch_prefix, name)) if self.endpoint_dispatch_prefix else {}
                    yield Fragment(part_, name=name, **kwargs)

        self.declared_parts = {x.name: x for x in sort_after(list(generate_parts()))}

        def bind_part(p):
            if hasattr(p, 'bind'):
                return p.bind()
            return p

        parts = {name: bind_part(p) for name, p in self.declared_parts.items()}

        self.parts = Struct({name: p for name, p in parts.items() if should_show(p)})

    @property
    def children(self):
        return self.parts

    @dispatch(
        context=EMPTY,
        render=lambda rendered: format_html('{}' * len(rendered), *rendered.values())
    )
    def render_or_respond(self, *, request, context=None, render=None):
        rendered = {}
        for part in self.parts.values():
            assert part.name not in context
            rendered[part.name] = render_or_respond_part(part=part, request=request, context=context)

        return render(rendered)


def fragment__render(fragment, request, context):
    if fragment.tag:
        return format_html(
            '<{}{}>{}</{}>',
            fragment.tag,
            render_attrs(fragment.attrs),
            fragment.render_text_or_children(request=request, context=context),
            fragment.tag,
        )
    else:
        return format_html(
            '{}',
            fragment.render_text_or_children(request=request, context=context),
        )


class Fragment(PagePart):
    @dispatch(
        name=None,
        attrs=EMPTY,
        show=True,
    )
    def __init__(self, child: PartType = None, *, name: str = None, tag: str = None, children: Optional[List[PartType]] = None, attrs=None, show, endpoint_dispatch_prefix=NO_ENDPOINT_PREFIX):
        self.name = name
        self.tag = tag
        self.name = name
        self.show = show
        self.children = []
        if child is not None:
            self.children.append(child)

        self.children.extend(children or [])
        self.attrs = attrs
        self.endpoint_dispatch_prefix = endpoint_dispatch_prefix

    def render_text_or_children(self, request, context):
        return format_html(
            '{}' * len(self.children),
            *[
                render_or_respond_part(part=x, request=request, context=context)
                for x in self.children
            ])

    def __getitem__(self, item):
        if isinstance(item, tuple):
            self.children.extend(item)
        else:
            self.children.append(item)
        return self

    def __repr__(self):
        return f'tag:{self.tag}'

    @dispatch(
        context=EMPTY,
        render=fragment__render,
    )
    def render_or_respond(self, *, request, context=None, render=None):
        return render(fragment=self, request=request, context=context)


class Html:
    def __getattr__(self, tag):
        def fragment_constructor(child: PartType = None, **kwargs):
            return Fragment(tag=tag, child=child, **kwargs)
        return fragment_constructor


html = Html()


def portal_page(left=None, center=None, **kwargs):
    part = Namespace()
    if left:
        part.left = html.div(
            attrs__class='left-menu',
            child=left,
        )
    if center:
        part.center = html.div(
            attrs__class='t-main',
            child=center,
        )

    return Page(
        part__main=html.div(
            attrs__class='main-layout',
            child=Page(
                part=part,
                **kwargs
            ),
        ),
    )


def page(*function, **render_kwargs):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(request, *args, **kwargs):
            result = f(request, *args, **kwargs)
            if isinstance(result, Page):
                return result.render_to_response(request=request, **render_kwargs)
            else:
                return result

        return wrapper

    if function:
        assert len(function) == 1
        return decorator(function[0])

    return decorator


def middleware(get_response):
    def _middleware(request):

        response = get_response(request)
        if isinstance(response, Page):
            page = response
            dispatch_commands = {key: value for key, value in request.GET.items() if key.startswith(DISPATCH_PATH_SEPARATOR)}
            assert len(dispatch_commands) in (0, 1), 'You can only have one or no dispatch commands'
            if dispatch_commands:
                dispatch_target, value = next(iter(dispatch_commands.items()))
                key, obj, kwargs = find_target(path=dispatch_target, root=page)
                assert parents[''] is page
                assert parents['t1/query/gui/foo'] is ...
                data = obj.endpoint_dispatch(key=key, value=value, **kwargs)
                if data is not None:
                    return True, HttpResponse(json.dumps(data), content_type='application/json')

            return page.render_to_response(request=request)
        else:
            return response

    return _middleware
