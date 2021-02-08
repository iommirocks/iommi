from typing import Callable

from tri_declarative import (
    dispatch,
    Refinable,
)

from iommi.base import keys
from iommi.traversable import (
    EvaluatedRefinable,
    get_long_path_by_path,
    get_path_by_long_path,
    Traversable,
)

DISPATCH_PATH_SEPARATOR = '/'
DISPATCH_PREFIX = DISPATCH_PATH_SEPARATOR


class InvalidEndpointPathException(Exception):
    pass


class Endpoint(Traversable):
    """
    Class that describes an endpoint in iommi. You can create your own custom
    endpoints on any :doc:`Part`.

    Example:

    .. code:: python

        def my_view(request):
            return Page(
                parts__h1=html.h1('Hi!'),
                endpoints__echo__func=lambda value, **_: value,
            )

    .. test
        import json
        request = req('get', **{'/echo': 'foo'})
        response = my_view(request).bind(request=request).render_to_response()
        assert json.loads(response.content) == 'foo'

    this page will respond to `?/echo=foo` by returning a json response `"foo"`.

    An endpoint can return an HttpResponse directly, a `Part` which is rendered for you,
    and everything else we try to dump to json for you.
    """

    func: Callable = Refinable()
    include: bool = EvaluatedRefinable()

    @dispatch(
        func=None,
        include=True,
    )
    def __init__(self, **kwargs):
        super(Endpoint, self).__init__(**kwargs)

    def on_bind(self) -> None:
        assert callable(self.func)

    @property
    def endpoint_path(self):
        return DISPATCH_PREFIX + self.iommi_path

    def own_evaluate_parameters(self):
        return dict(endpoint=self)


def find_target(*, path, root):
    assert path.startswith(DISPATCH_PATH_SEPARATOR)
    p = path[1:]

    long_path = get_long_path_by_path(root).get(p)
    if long_path is None:
        long_path = p
        if long_path not in keys(get_path_by_long_path(root)):

            def format_paths(paths):
                return '\n        '.join(["''" if not x else x for x in keys(paths)])

            raise InvalidEndpointPathException(
                f"Given path {path} not found.\n"
                f"    Short alternatives:\n        {format_paths(get_long_path_by_path(root))}\n"
                f"    Long alternatives:\n        {format_paths(get_path_by_long_path(root))}"
            )

    node = root
    for part in long_path.split('/'):
        if part == '':
            continue
        next_node = node.iommi_bound_members().get(part)
        assert next_node is not None, f"Failed to traverse long path '{long_path}' (No bound value for '{part}')"
        node = next_node

    return node


def perform_ajax_dispatch(*, root, path, value):
    assert root._is_bound

    target = find_target(path=path, root=root)

    func = getattr(target, 'func', None)
    if not isinstance(target, Endpoint) or func is None:
        raise InvalidEndpointPathException(f'Target {target!r} is not a valid endpoint handler')

    return func(root=root, value=value, **target.iommi_evaluate_parameters())


def perform_post_dispatch(*, root, path, value):
    assert root._is_bound
    assert path[0] in ('/', '-')
    path = '/' + path[1:]  # replace initial - with / to convert from post-y paths to ajax-y paths
    target = find_target(path=path, root=root)

    if getattr(target, 'post_handler', None) is None:
        raise InvalidEndpointPathException(f'Target {target!r} has no registered post_handler')

    return target.post_handler(value=value, **target.iommi_evaluate_parameters())


def path_join(prefix, *args, separator=DISPATCH_PATH_SEPARATOR) -> str:
    if not prefix:
        return separator.join(args)
    return separator.join((prefix,) + args)
