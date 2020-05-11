from typing import Callable

from tri_declarative import (
    dispatch,
    Refinable,
)

from iommi.traversable import (
    bound_members,
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
                endpoint__echo__func=lambda value, **_: value,
            )

    this page will respond to `?/echo=foo` by returning a json response `"foo"`.
    """

    name: str = Refinable()
    func: Callable = Refinable()
    include: bool = EvaluatedRefinable()

    @dispatch(
        name=None,
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
        if long_path not in get_path_by_long_path(root).keys():
            def format_paths(paths):
                return '\n        '.join(["''" if not x else x for x in paths.keys()])

            raise InvalidEndpointPathException(
                f"Given path {path} not found.\n"
                f"    Short alternatives:\n        {format_paths(get_long_path_by_path(root))}\n"
                f"    Long alternatives:\n        {format_paths(get_path_by_long_path(root))}"
            )

    node = root
    for part in long_path.split('/'):
        if part == '':
            continue
        next_node = bound_members(node).get(part)
        assert next_node is not None, f'Failed to traverse long path {long_path}'
        node = next_node

    return node


def perform_ajax_dispatch(*, root, path, value):
    assert root._is_bound

    target = find_target(path=path, root=root)

    func = getattr(target, 'func', None)
    if not isinstance(target, Endpoint) or func is None:
        raise InvalidEndpointPathException(f'Target {target!r} is not a valid endpoint handler')

    return func(root=root, value=value, **target._evaluate_parameters)


def perform_post_dispatch(*, root, path, value):
    assert root._is_bound
    assert path[0] in ('/', '-')
    path = '/' + path[1:]  # replace initial - with / to convert from post-y paths to ajax-y paths
    target = find_target(path=path, root=root)

    if getattr(target, 'post_handler', None) is None:
        raise InvalidEndpointPathException(f'Target {target!r} has no registered post_handler')

    return target.post_handler(value=value, **target._evaluate_parameters)


def path_join(prefix, *args, separator=DISPATCH_PATH_SEPARATOR) -> str:
    if not prefix:
        return separator.join(args)
    return separator.join((prefix,) + args)
