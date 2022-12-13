import functools
import re
import typing
import warnings
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


class Decoder:
    def __init__(self, *lookups, decode=None):
        self.lookups = lookups
        self._decode = decode

    def decode(self, *, lookup, string, model, **kwargs):
        if self._decode is None:
            return model.objects.get(**{lookup: string})
        else:
            return self._decode(lookup=lookup, string=string, model=model, **kwargs)


class PathDecoder:
    def __init__(self, *, decode=None, model=None, name):
        if decode is None:
            decode = lambda string, _model=model, **_: _model.objects.get(pk=string)

        self.decode = decode
        self.model = model
        self.name = name


_path_component_to_decode_data: typing.Dict[
    str,
    typing.Tuple[typing.Optional[typing.Type[Model]], str, typing.Optional[str], typing.Union[Decoder, PathDecoder]],
] = {}


_default_decoder = Decoder('pk', 'name')


def camel_to_snake(s):
    return _camel_to_snake_regex.sub('_', s).lower()


def register_advanced_path_decoding(conf, *, warn=True):
    if warn:
        warnings.warn(
            '''Path decoder syntax has been changed. Please use the new syntax. The old:

        register_advanced_path_decoder({
            User: Decoder('pk', 'username', 'email'),
            Track: Decoder('foo', decode=lambda string, model, **_: model.objects.get(name__iexact=string.strip())),
        })

        is equivalent to:

        register_path_decoder(
            user_pk=User,
            user_username=User.username,
            user_email=User.email,
            track_foo=lambda string, **_: Track.objects.get(name__iexact=string.strip()),
        )
        ''',
            category=DeprecationWarning,
        )

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


def register_path_decoding(*models, **kwargs):
    assert not (
        models and kwargs
    ), 'Mixing of new and deprecated syntax in the same call to register_path_decoding is not supported.'
    if kwargs:
        return register_explicit_path_decoding(**kwargs)

    warnings.warn(
        'Path decoder syntax has been changed. Please use the new syntax. The old `register_path_decoder(Foo)` is equivalent to `register_path_decoder(foo_pk=Foo, foo_name=Foo.name)`',
        category=DeprecationWarning,
    )
    return register_advanced_path_decoding({model: _default_decoder for model in models}, warn=False)


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
                if isinstance(decoder, Decoder):
                    # deprecated path
                    obj = decoder.decode(
                        lookup=lookup,
                        string=v,
                        request=request,
                        model=model,
                        snake_name=key,
                        decoded_kwargs=decoded_kwargs,
                        kwargs=kwargs,
                    )
                else:
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
