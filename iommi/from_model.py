import warnings
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
    Namespace,
    Refinable,
    RefinableObject,
    setdefaults_path,
)
from tri_struct import Struct

from iommi.base import (
    keys,
    MISSING,
)
from iommi.evaluate import evaluate
from iommi.reinvokable import set_and_remember_for_reinvoke


def create_members_from_model(
    *, member_class, model, member_params_by_member_name, include: List[str] = None, exclude: List[str] = None
):
    members = Struct()

    check_list(model, include, 'include')
    check_list(model, exclude, 'exclude')

    def create_declared_member(model_field_name):
        definition_or_member = member_params_by_member_name.pop(model_field_name, {})
        name = model_field_name.replace('__', '_')
        if isinstance(definition_or_member, dict):
            definition = setdefaults_path(
                Namespace(),
                definition_or_member,
                _name=name,
                # TODO: this should work, but there's a bug in tri.declarative, working around for now
                # call_target__attribute='from_model' if definition_or_member.get('attr', model_field_name) is not None else None,
                call_target__cls=member_class,
            )
            if definition_or_member.get('attr', model_field_name) is not None:
                setdefaults_path(
                    definition,
                    call_target__attribute='from_model',
                )
            if include is not None and name in include:
                setdefaults_path(
                    definition,
                    include=True,
                )

            member = definition(
                model=model,
                model_field_name=definition_or_member.get('attr', model_field_name),
            )
        else:
            member = definition_or_member
        if member is None:
            return
        members[name] = member

    model_field_names = include if include is not None else [field.name for field in get_fields(model)]

    for model_field_name in model_field_names:
        if exclude is not None and model_field_name in exclude:
            continue
        create_declared_member(model_field_name)

    for model_field_name in list(keys(member_params_by_member_name)):
        create_declared_member(model_field_name)

    return members


def member_from_model(
    cls,
    model,
    factory_lookup,
    defaults_factory,
    factory_lookup_register_function=None,
    model_field_name=None,
    model_field=None,
    **kwargs,
):
    if model_field is None:
        assert (
            model_field_name is not None
        ), "Field can't be automatically created from model, you must specify it manually"

        sub_field_name, _, field_path_rest = model_field_name.partition('__')

        # noinspection PyProtectedMember
        model_field = get_field(model, sub_field_name)

        if field_path_rest:
            result = member_from_model(
                cls=cls,
                model=model_field.remote_field.model,
                factory_lookup=factory_lookup,
                defaults_factory=defaults_factory,
                factory_lookup_register_function=factory_lookup_register_function,
                model_field_name=field_path_rest,
                **kwargs,
            )
            set_and_remember_for_reinvoke(result, attr=model_field_name)
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
            message += (
                ' Register a factory with register_factory or %s, you can also register one that returns None to not handle this field type'
                % factory_lookup_register_function.__name__
            )
        raise AssertionError(message)

    if factory is None:
        return None

    # Not strict evaluate on purpose
    factory = evaluate(factory, __match_empty=False, model_field=model_field, model_field_name=model_field_name)

    setdefaults_path(
        kwargs,
        _name=model_field_name,
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

    return factory(model_field=model_field, model_field_name=model_field_name, model=model, **kwargs)


def get_fields(model: Type[Model]) -> Iterator[DjangoField]:
    # noinspection PyProtectedMember
    for field in model._meta.get_fields():
        yield field


def get_field(model: Type[Model], field_name: str) -> DjangoField:
    if field_name == 'pk':
        return model._meta.auto_field

    # noinspection PyProtectedMember
    return model._meta.get_field(field_name)


def get_field_path(model, path):
    def _get_field_path(current_model, sub_path):
        first, _, rest = sub_path.partition('__')
        field = get_field(current_model, first)
        if not rest:
            return field
        else:
            return get_field_path(field.remote_field.model, rest)

    try:
        return _get_field_path(model, path)
    except FieldDoesNotExist as e:
        raise FieldDoesNotExist(f"{model._meta.object_name} has no field with path '{path}'") from e


def check_list(model: Type[Model], paths: List[str], operation: str) -> None:
    def existing_alternatives(missing_path):
        prefix = []
        current_model = model
        for part in missing_path.split('__'):
            try:
                current_model = get_field(current_model, part).remote_field.model
            except FieldDoesNotExist:
                return sorted(
                    ['__'.join(prefix + [field.name]) for field in get_fields(current_model)]
                    + ['__'.join(prefix + ['pk'])]
                )
            else:
                prefix.append(part)

    if paths:
        for path in paths:
            try:
                get_field_path(model, path)
            except FieldDoesNotExist:
                assert False, (
                    f'You can only {operation} fields that exist on the model: {path} specified but does not exist\n'
                    f'Existing fields:\n'
                    f'    ' + '\n    '.join(existing_alternatives(path))
                )


_search_fields_by_model = {}


class NoRegisteredSearchFieldException(Exception):
    pass


def get_search_fields(*, model):
    search_fields = _search_fields_by_model.get(model, MISSING)
    if search_fields is MISSING:
        try:
            field = model._meta.get_field('name')
        except FieldDoesNotExist:
            raise NoRegisteredSearchFieldException(
                f'{model.__name__} has no registered search fields. Please register a list of field names with register_search_fields.'
            ) from None
        if not field.unique:
            warnings.warn(
                f"The model {model.__name__} is using the default `name` field as a search field, but it's not unique. You can register_search_fields(model={model.__name__}, search_fields=['name'], allow_non_unique=True) to silence this warning. The reason we are warning is because you won't be able to use the advanced query language with non-unique names."
            )
        return ['name']

    return search_fields


class SearchFieldsAlreadyRegisteredException(Exception):
    pass


def register_search_fields(*, model, search_fields, allow_non_unique=False, overwrite=False):
    assert isinstance(search_fields, (tuple, list))

    def validate_name_field(search_field, path, model):
        field = model._meta.get_field(path[0])
        if len(path) == 1:
            if allow_non_unique:
                return

            if not field.unique:
                for unique_together in model._meta.unique_together:
                    if path[0] in unique_together:
                        return
                raise TypeError(
                    f'Cannot register search field "{search_field}" for model {model.__name__}. {path[0]} must be unique.'
                )
        else:
            validate_name_field(search_field, path[1:], field.remote_field.model)

    for search_field in search_fields:
        if search_field in ('pk', 'id'):
            continue
        validate_name_field(search_field, search_field.split('__'), model)

    if model in _search_fields_by_model and not overwrite:
        raise SearchFieldsAlreadyRegisteredException(
            f'Cannot register search fields for {model}, it already has registered search fields {_search_fields_by_model[model]}.\nTo overwrite the existing registration pass overwrite=True to register_search_fields().'
        )
    _search_fields_by_model[model] = search_fields


class AutoConfig(RefinableObject):
    model: Type[Model] = Refinable()  # model is evaluated, but in a special way so gets no EvaluatedRefinable type
    include = Refinable()
    exclude = Refinable()

    @dispatch
    def __init__(self, **kwargs):
        super(AutoConfig, self).__init__(**kwargs)
