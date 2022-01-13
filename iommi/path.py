import functools
import re
from contextlib import contextmanager
from typing import (
    Dict,
    Tuple,
    Type,
)

from django.db.models import Model
from django.http import Http404

from iommi.base import items


_camel_to_snake_regex = re.compile(r'(?<!^)(?=[A-Z])')


class Decoder:
    def __init__(self, *lookups, decode=None):
        self.lookups = lookups
        self._decode = decode

    def decode(self, *, lookup, string, model, **kwargs):
        if self._decode is None:
            return model.objects.get(**{lookup: string})
        else:
            return self._decode(lookup=lookup, string=string, model=model, **kwargs)


_path_component_to_decode_data: Dict[str, Tuple[Type[Model], str, str, Decoder]] = {}


_default_decoder = Decoder('pk', 'name')


def camel_to_snake(s):
    return _camel_to_snake_regex.sub('_', s).lower()


def register_advanced_path_decoding(conf):
    registered_keys = []
    for model, decoder in items(conf):
        snake_name = camel_to_snake(model.__name__)
        for lookup in decoder.lookups:
            key = f'{snake_name}_{lookup}'
            _path_component_to_decode_data[key] = (model, snake_name, lookup, decoder)
            registered_keys.append(key)

    @contextmanager
    def _unregister():
        try:
            yield conf
        finally:
            for key in registered_keys:
                del _path_component_to_decode_data[key]
    return _unregister()


def register_path_decoding(*models):
    return register_advanced_path_decoding(
        {
            model: _default_decoder
            for model in models
        }
    )


def decode_path_components(request, **kwargs):
    decoded_kwargs = {}
    decoded_keys = set()

    if _path_component_to_decode_data:
        for k, v in items(kwargs):
            decode_data = _path_component_to_decode_data.get(k, None)
            if decode_data is None:
                continue

            model, snake_name, lookup, decoder = decode_data

            try:
                obj = decoder.decode(
                    lookup=lookup,
                    string=v,
                    request=request,
                    model=model,
                    snake_name=snake_name,
                    decoded_kwargs=decoded_kwargs,
                    kwargs=kwargs,
                )
            except model.DoesNotExist:
                raise Http404()

            decoded_kwargs[snake_name] = obj
            decoded_keys.add(k)

    if not hasattr(request, 'iommi_view_params'):
        request.iommi_view_params = {}
    request.iommi_view_params.update(kwargs)
    request.iommi_view_params.update(decoded_kwargs)

    return {
        **{k: v for k, v in items(kwargs) if k not in decoded_keys},
        **decoded_kwargs
    }


def decode_path(f):

    @functools.wraps(f)
    def decode_path_wrapper(request, **kwargs):
        decoded_kwargs = decode_path_components(request, **kwargs)
        return f(request=request, **decoded_kwargs)

    return decode_path_wrapper
