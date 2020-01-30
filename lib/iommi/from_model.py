from typing import (
    List,
    Dict,
    Any,
)

from django.core.exceptions import FieldDoesNotExist
from iommi.base import MISSING
from tri_declarative import (
    dispatch,
    Namespace,
    assert_kwargs_empty,
    evaluate,
    setdefaults_path,
)
from tri_struct import Struct


@dispatch  # pragma: no mutate
def create_members_from_model(default_factory, model, member_params_by_member_name, include: List[str] = None, exclude: List[str] = None, extra: Dict[str, Any] = None):
    if extra is None:
        extra = {}

    # TODO: assert that extra does not collide with the include/exclude/etc fields

    def should_include(name):
        if exclude is not None and name in exclude:
            return False
        if include is not None:
            return name in include
        return True

    members = []

    # Validate include/exclude parameters
    field_names = {x.name for x in get_fields(model)}
    if include:
        not_existing = {x for x in include if x.partition('__')[0] not in field_names}
        assert not not_existing, 'You can only include fields that exist on the model: %s specified but does not exist' % ', '.join(sorted(not_existing))
    if exclude:
        not_existing = {x for x in exclude if x not in field_names}
        assert not not_existing, 'You can only exclude fields that exist on the model: %s specified but does not exist' % ', '.join(sorted(not_existing))

    extra_includes = [x for x in include if '__' in x] if include else []

    for field in get_fields(model):
        if should_include(field.name):
            foo = member_params_by_member_name.pop(field.name, {})
            if isinstance(foo, dict):
                subkeys = Namespace(**foo)
                subkeys.setdefault('call_target', default_factory)
                foo = subkeys(name=field.name, model=model, model_field=field)
            if foo is None:
                continue
            if isinstance(foo, list):
                members.extend(foo)
            else:
                assert foo.name, "Fields must have a name attribute"
                assert foo.name == field.name, f"Field {foo.name} has a name that doesn't match the model field it belongs to: {field.name}"
                members.append(foo)
    assert_kwargs_empty(member_params_by_member_name)
    all_members = members + [default_factory(model=model, field_name=x) for x in extra_includes]
    return Struct({x.name: x for x in all_members}, **extra)


def member_from_model(cls, model, factory_lookup, defaults_factory, factory_lookup_register_function=None, field_name=None, model_field=None, **kwargs):
    if model_field is None:
        assert field_name is not None, "Field can't be automatically created from model, you must specify it manually"

        sub_field_name, _, field_path_rest = field_name.partition('__')

        # noinspection PyProtectedMember
        model_field = model._meta.get_field(sub_field_name)

        if field_path_rest:
            result = member_from_model(
                cls=cls,
                model=model_field.remote_field.model,
                factory_lookup=factory_lookup,
                defaults_factory=defaults_factory,
                factory_lookup_register_function=factory_lookup_register_function,
                field_name=field_path_rest,
                **kwargs)
            result.name = field_name
            result.attr = field_name
            return result

    factory = factory_lookup.get(type(model_field), MISSING)

    if factory is MISSING:
        for django_field_type, foo in reversed(list(factory_lookup.items())):
            if isinstance(model_field, django_field_type):
                factory = foo
                break  # pragma: no mutate optimization

    if factory is MISSING:
        message = 'No factory for %s.' % type(model_field)
        if factory_lookup_register_function is not None:
            message += ' Register a factory with %s, you can also register one that returns None to not handle this field type' % factory_lookup_register_function.__name__
        raise AssertionError(message)

    if factory is None:
        return None

    # Not strict evaluate on purpose
    factory = evaluate(factory, model_field=model_field, field_name=field_name)

    setdefaults_path(
        kwargs,
        name=field_name,
        call_target__cls=cls,
    )

    defaults = defaults_factory(model_field)
    if isinstance(factory, Namespace):
        factory = setdefaults_path(
            Namespace(),
            factory,
            defaults,
        )
    else:
        kwargs.update(**defaults)

    return factory(model_field=model_field, model=model, **kwargs)


def get_fields(model):
    # noinspection PyProtectedMember
    for field in model._meta.get_fields():
        yield field


_name_fields_by_model = {}


def get_name_field_for_model(model):
    name_field = _name_fields_by_model.get(model, MISSING)
    if name_field is MISSING:
        try:
            name_field = model._meta.get_field('name')
        except FieldDoesNotExist:
            return None
        return 'name' if name_field.unique else None

    return name_field


def register_name_field_for_model(model, name_field):
    def validate_name_field(path):
        field = model._meta.get_field(path[0])
        if len(path) == 1:
            if not field.unique:
                raise Exception(f'Cannot register name "{name_field}" for model {model}. {path[0]} must be unique.')
        else:
            validate_name_field(path[1:])

    validate_name_field(name_field.split('__'))
    _name_fields_by_model[model] = name_field

# TODO: this would be nice as a default, but where do we initialize it when django is started?
# register_name_field_for_model(User, 'username')
