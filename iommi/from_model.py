import warnings
from typing import (
    Dict,
    List,
    Type,
)

from django.core.exceptions import FieldDoesNotExist
from django.db.models import Field as DjangoField
from django.db.models import (
    ManyToManyRel,
    ManyToOneRel,
    Model,
    OneToOneRel,
)

from iommi.base import MISSING
from iommi.declarative.dispatch import dispatch
from iommi.declarative.namespace import (
    Namespace,
    setdefaults_path,
)
from iommi.evaluate import evaluate
from iommi.refinable import (
    Refinable,
    RefinableObject,
    SpecialEvaluatedRefinable,
)
from iommi.struct import Struct


def create_members_from_model(
    *,
    member_class,
    model,
    include: List[str] = None,
    exclude: List[str] = None,
    default_included=True,
):
    members = Struct()

    check_list(model, include, 'include')
    check_list(model, exclude, 'exclude')

    model_field_names = include if include is not None else list(get_field_by_name(model).keys())

    for model_field_name in model_field_names:
        if exclude is not None and model_field_name in exclude:
            continue
        name = model_field_name.replace('__', '_')
        definition = Namespace(
            _name=name,
            call_target__cls=member_class,
            call_target__attribute='from_model',
            model_field_name=model_field_name,
            model=model,
        )
        if default_included is False:
            setdefaults_path(
                definition,
                include=False,
            )
        if include is not None and name in include:
            setdefaults_path(
                definition,
                include=True,
            )

        member = definition()
        if member is not None:
            members[name] = member

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
            result = result.refine(attr=model_field_name)
            return result
    else:
        if model is None:
            model = model_field.model
        if model_field_name is None:
            model_field_name = model_field.name

    factory = factory_lookup.get(type(model_field), MISSING)

    if factory is MISSING:
        for django_field_type, foo in reversed(list(factory_lookup.items())):
            if isinstance(model_field, django_field_type):
                factory = foo
                break  # pragma: no mutate optimization

    if factory is MISSING:

        def no_factory_defined(**_):
            message = f'No factory for {model.__name__}.{model_field_name} of type {type(model_field).__name__}.'
            if factory_lookup_register_function is not None:
                message += (
                    ' Register a factory with register_factory or %s, you can also register one that returns None to not handle this field type'
                    % factory_lookup_register_function.__name__
                )
            raise AssertionError(message)

        factory = no_factory_defined

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


def get_field_by_name(model: Type[Model]) -> Dict[str, DjangoField]:
    if not hasattr(model._meta, '_iommi_fields'):
        model._meta._iommi_fields = {get_field_name(field): field for field in model._meta.get_fields()}
        if None in model._meta._iommi_fields:
            model._meta._iommi_fields.pop(None)
    return model._meta._iommi_fields


def get_field_name(field: DjangoField) -> str:
    if isinstance(field, ManyToManyRel):
        return field.related_name
    elif isinstance(field, ManyToOneRel):
        if field.related_name == '+':
            return None
        elif field.related_query_name:
            return field.related_query_name
        elif field.related_name:
            return field.related_name
        elif isinstance(field, OneToOneRel):
            return field.name
        else:
            return f'{field.name}_set'
    else:
        return field.name


def get_field(model: Type[Model], field_name: str) -> DjangoField:
    if field_name == 'pk':
        return model._meta.auto_field

    try:
        return get_field_by_name(model)[field_name]
    except KeyError:
        valid_names = '\n    '.join(sorted(get_field_by_name(model).keys()))
        raise FieldDoesNotExist(
            f"{model._meta.object_name} has no field with name '{field_name}', valid names are:\n\n    {valid_names}"
        )


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
                    ['__'.join(prefix + [name]) for name in get_field_by_name(current_model).keys()]
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
            field = get_field(model, 'name')
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
        field = get_field(model, path[0])
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
    model: Type[Model] = SpecialEvaluatedRefinable()
    include = Refinable()
    exclude = Refinable()
    default_included = Refinable()

    @dispatch
    def __init__(self, **kwargs):
        """
        :param model: A Django model class
        :param include: A list of attribute names to include, use `__` to drill down to nested attributes. Example: `['album', 'album__year']`
        :param exclude: A list of attribute names to exclude, use `__` to drill down to nested attributes. Example: `['album', 'album__year']`
        """
        super(AutoConfig, self).__init__(**kwargs)
