from typing import (
    Iterator,
    List,
    Type,
)

from django.core.exceptions import FieldDoesNotExist
from django.db.models import (
    Field as DjangoField,
    Model,
)
from tri_declarative import (
    dispatch,
    evaluate,
    Namespace,
    Refinable,
    RefinableObject,
    setdefaults_path,
)
from tri_struct import Struct

from iommi.base import MISSING


def create_members_from_model(*, member_class, model, member_params_by_member_name, include: List[str] = None, exclude: List[str] = None):
    def should_include(name):
        if exclude is not None and name in exclude:
            return False
        if include is not None:
            return name in include
        return True

    members = Struct()

    # Validate include/exclude parameters
    field_names = {x.name for x in get_fields(model)}
    if include:
        not_existing = {x for x in include if x not in field_names}
        assert not not_existing, 'You can only include fields that exist on the model: %s specified but does not exist' % ', '.join(sorted(not_existing))
    if exclude:
        not_existing = {x for x in exclude if x not in field_names}
        assert not not_existing, 'You can only exclude fields that exist on the model: %s specified but does not exist' % ', '.join(sorted(not_existing))

    def create_declared_member(field_name):
        definition_or_member = member_params_by_member_name.pop(field_name, {})
        if isinstance(definition_or_member, dict):
            definition = setdefaults_path(
                Namespace(),
                definition_or_member,
                # TODO: this should work, but there's a bug in tri.declarative, working around for now
                # call_target__attribute='from_model' if definition_or_member.get('attr', field_name) is not None else None,
                call_target__cls=member_class,
            )
            if definition_or_member.get('attr', field_name) is not None:
                setdefaults_path(
                    definition,
                    call_target__attribute='from_model',
                )

            member = definition(
                model=model,
                field_name=definition_or_member.get('attr', field_name),
            )
        else:
            member = definition_or_member
        if member is None:
            return
        members[field_name] = member

    for field in get_fields(model):
        if should_include(field.name):
            create_declared_member(field.name)

    for field_name in list(member_params_by_member_name.keys()):
        create_declared_member(field_name)

    return members


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
            result.attr = field_name
            return result

    factory = factory_lookup.get(type(model_field), MISSING)

    if factory is MISSING:
        for django_field_type, foo in reversed(list(factory_lookup.items())):
            if isinstance(model_field, django_field_type):
                factory = foo
                break  # pragma: no mutate optimization

    if factory is MISSING:
        message = f'No factory for {type(model_field).__name__}.'
        if factory_lookup_register_function is not None:
            message += ' Register a factory with %s, you can also register one that returns None to not handle this field type' % factory_lookup_register_function.__name__
        raise AssertionError(message)

    if factory is None:
        return None

    # Not strict evaluate on purpose
    factory = evaluate(factory, model_field=model_field, field_name=field_name)

    setdefaults_path(
        kwargs,
        _name=field_name,
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

    return factory(model_field=model_field, field_name=field_name, model=model, **kwargs)


def get_fields(model: Type[Model]) -> Iterator[DjangoField]:
    # noinspection PyProtectedMember
    for field in model._meta.get_fields():
        yield field


_name_fields_by_model = {}


class NoRegisteredNameException(Exception):
    pass


def get_name_field(*, model):
    name_field = _name_fields_by_model.get(model, MISSING)
    if name_field is MISSING:
        try:
            name_field = model._meta.get_field('name')
        except FieldDoesNotExist:
            raise NoRegisteredNameException(f'{model.__name__} has no registered name field. Please register a name with register_name_field.')
        if not name_field.unique:
            raise NoRegisteredNameException(
                f"The model {model} has no registered name field. Please register a name with register_name_field. It has a field `name` but it's not unique in the database so we can't use that.")
        return 'name'

    return name_field


def register_name_field(*, model, name_field, allow_non_unique=False):
    def validate_name_field(path):
        field = model._meta.get_field(path[0])
        if len(path) == 1:
            if allow_non_unique:
                return

            if not field.unique:
                for unique_together in model._meta.unique_together:
                    if path[0] in unique_together:
                        return
                raise TypeError(f'Cannot register name "{name_field}" for model {model.__name__}. {path[0]} must be unique.')
        else:
            validate_name_field(path[1:])

    validate_name_field(name_field.split('__'))
    _name_fields_by_model[model] = name_field


class AutoConfig(RefinableObject):
    model: Type[Model] = Refinable()  # model is evaluated, but in a special way so gets no EvaluatedRefinable type
    include = Refinable()
    exclude = Refinable()

    @dispatch
    def __init__(self, **kwargs):
        super(AutoConfig, self).__init__(**kwargs)
