import json
from typing import (
    Dict,
    List,
    Optional,
)

from django.http.response import (
    HttpResponse,
)
from django.utils.html import format_html
from iommi._web_compat import (
    Template,
)
from iommi.base import (
    DISPATCH_PATH_SEPARATOR,
    InvalidEndpointPathException,
    PagePart,
    PartType,
    find_target,
    no_copy_on_bind,
    render_part,
)
from iommi.render import render_attrs
from tri_declarative import (
    EMPTY,
    Namespace,
    declarative,
    dispatch,
    should_show,
    sort_after,
    with_meta,
)
from tri_struct import Struct


@no_copy_on_bind
@with_meta
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
        default_child=None,
    ):
        self.parts = {}  # This is just so that the repr can survive if it gets triggered before parts is set properly

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
                    yield part_
                else:
                    yield Fragment(part_, name=name)

        # TODO: use collect_members and bind_members
        self.declared_parts = {x.name: x for x in sort_after(list(generate_parts()))}

        self.default_child = default_child

    def on_bind(self) -> None:
        parts = {name: p.bind(parent=self) for name, p in self.declared_parts.items()}
        self.parts = Struct({name: p for name, p in parts.items() if should_show(p)})

    def __repr__(self):
        return f'<Page with parts: {list(self.parts.keys())}>'

    def children(self):
        if not self._is_bound:
            # TODO: hmm...
            self.bind(request=None)
        return self.parts

    def endpoint_kwargs(self):
        return dict(page=self)

    @dispatch(
        context=EMPTY,
        render=lambda rendered: format_html('{}' * len(rendered), *rendered.values())
    )
    def render(self, *, context=None, render=None):
        rendered = {}
        for part in self.parts.values():
            assert part.name not in context
            rendered[part.name] = render_part(part=part, context=context)

        return render(rendered)


def fragment__render(fragment, context):
    if fragment.tag:
        return format_html(
            '<{}{}>{}</{}>',
            fragment.tag,
            render_attrs(fragment.attrs),
            fragment.render_text_or_children(context=context),
            fragment.tag,
        )
    else:
        return format_html(
            '{}',
            fragment.render_text_or_children(context=context),
        )


class Fragment(PagePart):
    @dispatch(
        name=None,
        attrs=EMPTY,
        show=True,
    )
    def __init__(self, child: PartType = None, *, name: str = None, tag: str = None, children: Optional[List[PartType]] = None, attrs=None, show, default_child=None):
        self.name = name
        self.tag = tag
        self.name = name
        self.show = show
        self._children = []  # TODO: _children to avoid colliding with PageParts children() API. Not nice. We should do something nicer here.
        if child is not None:
            self._children.append(child)

        self._children.extend(children or [])
        self.attrs = attrs
        self.default_child = default_child

    def render_text_or_children(self, request, context):
        return format_html(
            '{}' * len(self._children),
            *[
                render_part(part=x, context=context)
                for x in self._children
            ])

    def __getitem__(self, item):
        if isinstance(item, tuple):
            self._children.extend(item)
        else:
            self._children.append(item)
        return self

    def __repr__(self):
        return f'tag:{self.tag}'

    @dispatch(
        context=EMPTY,
        render=fragment__render,
    )
    def render(self, *, context=None, render=None):
        return render(fragment=self, context=context)


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


# def page(*function, **render_kwargs):
#     def decorator(f):
#         @functools.wraps(f)
#         def wrapper(request, *args, **kwargs):
#             result = f(request, *args, **kwargs)
#             result.bind(request=request)
#             if isinstance(result, Page):
#                 return result.render_to_response(**render_kwargs)
#             else:
#                 return result
#
#         return wrapper
#
#     if function:
#         assert len(function) == 1
#         return decorator(function[0])
#
#     return decorator


def perform_ajax_dispatch(*, root, path, value, request):
    if not root._is_bound:
        # This is mostly useful for tests
        root.bind(request=request)

    target, parents = find_target(path=path, root=root)

    # TODO: should contain the endpoint_kwargs of all parents I think... or just the target and Field.endpoint_kwargs needs to add `form`
    kwargs = {**parents[-1].endpoint_kwargs(), **target.endpoint_kwargs()}

    if target.endpoint_handler is None:
        raise InvalidEndpointPathException(f'Target {target} has no registered endpoint_handler')

    # TODO: this API should be endpoint(), fix Table.children when this is fixed
    return target.endpoint_handler(request=request, value=value, **kwargs)


def middleware(get_response):
    def _middleware(request):

        response = get_response(request)
        if isinstance(response, Page):
            page = response
            page.bind(request=request)

            dispatch_commands = {key: value for key, value in request.GET.items() if key.startswith(DISPATCH_PATH_SEPARATOR)}
            assert len(dispatch_commands) in (0, 1), 'You can only have one or no dispatch commands'
            if dispatch_commands:
                dispatch_target, value = next(iter(dispatch_commands.items()))
                try:
                    data = perform_ajax_dispatch(root=page, path=dispatch_target, value=value, request=request)
                except InvalidEndpointPathException:
                    data = dict(error=f'Invalid endpoint path')

                if data is not None:
                    return True, HttpResponse(json.dumps(data), content_type='application/json')
                else:
                    return True, HttpResponse(content_type='application/json')

            return page.render_to_response()
        else:
            return response

    return _middleware
