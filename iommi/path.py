import functools
import re
import typing
from contextlib import contextmanager

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import (
    Model,
)
from django.db.models.base import ModelBase
from django.db.models.query_utils import DeferredAttribute
from django.http import Http404

from iommi.base import items
from iommi.struct import Struct

_camel_to_snake_regex = re.compile(r'(?<!^)(?=[A-Z])')


class PathDecoder:
    def __init__(self, *, decode=None, model=None, name):
        if decode is None:

            def decode(string, _model=model, **_):
                return _model.objects.get(pk=string)

        self.decode = decode
        self.model = model
        self.name = name


_path_component_to_decode_data: typing.Dict[
    str,
    typing.Tuple[
        typing.Optional[typing.Type[Model]],
        str,
        typing.Optional[str],
        PathDecoder,
    ],
] = {}


def camel_to_snake(s):
    return _camel_to_snake_regex.sub('_', s).lower()


def register_explicit_path_decoding(**kwargs):
    registered_keys = []
    for key, definition in items(kwargs):
        if isinstance(definition, ModelBase):
            decoder = PathDecoder(
                model=definition,
                name=camel_to_snake(definition.__name__),
            )
        elif isinstance(definition, property):
            assert False, f'Got a property for {key}. Maybe you did Foo.pk? In that case write just Foo, or Foo.id.'
        elif isinstance(definition, DeferredAttribute):
            field = definition.field
            model = field.model
            attr = field.name
            decoder = PathDecoder(
                decode=lambda string, _model=model, _attr=attr, **_: _model.objects.get(**{attr: string}),
                name=camel_to_snake(model.__name__),
            )
        elif callable(definition):
            decoder = PathDecoder(
                decode=definition,
                name=key,
            )
        else:
            assert isinstance(definition, PathDecoder)
            decoder = definition

        _path_component_to_decode_data[key] = (None, key, None, decoder)
        registered_keys.append(key)

    @contextmanager
    def _unregister():
        try:
            yield
        finally:
            for key in registered_keys:
                del _path_component_to_decode_data[key]

    return _unregister()


def register_path_decoding(**kwargs):
    return register_explicit_path_decoding(**kwargs)


def decode_path_components(request, **kwargs):
    decoded_kwargs = {}
    decoded_keys = set()

    if _path_component_to_decode_data:
        for k, v in items(kwargs):
            decode_data = _path_component_to_decode_data.get(k, None)
            if decode_data is None:
                continue

            model, key, lookup, decoder = decode_data

            try:
                obj = decoder.decode(
                    key=key,
                    string=v,
                    request=request,
                    decoded_kwargs=decoded_kwargs,
                    kwargs=kwargs,
                )
                key = decoder.name
            except ObjectDoesNotExist:
                raise Http404()

            decoded_kwargs[key] = obj
            decoded_keys.add(k)

    if not hasattr(request, 'iommi_view_params'):
        request.iommi_view_params = Struct()
    request.iommi_view_params.update(kwargs)
    request.iommi_view_params.update(decoded_kwargs)

    return {
        **{k: v for k, v in items(kwargs) if k not in decoded_keys},
        **decoded_kwargs,
    }


def decode_path(f):
    @functools.wraps(f)
    def decode_path_wrapper(request, **kwargs):
        decoded_kwargs = decode_path_components(request, **kwargs)
        return f(request=request, **decoded_kwargs)

    return decode_path_wrapper
