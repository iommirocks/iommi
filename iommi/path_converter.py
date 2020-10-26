from iommi.from_model import get_search_fields


_path_converters = {}


def parse_url_params(request):
    for k, value in request.iommi_url_params.items():
        if k in _path_converters:
            request.iommi_url_params[k] = _path_converters[k](request, value)


def register_path_converter(*, model, name=None, use_pk=False, check_access=False, parse=lambda value, lookups, model, **_: model.objects.get(**lookups)):
    if name is None:
        name = model._meta.verbose_name.lower().replace(' ', '_')

    # TODO: why does this get called twice in supernaut?
    # assert name not in _path_converters, 'You can only register a path converter once for a specific name.'

    def _path_converter(request, value):
        if use_pk:
            lookups = {'pk': value}
        else:
            search_field = get_search_fields(model=model)[0]
            lookups = {search_field: value}

        result = parse(model=model, value=value, request=request, url_params=request.iommi_url_params, lookups=lookups)

        if check_access:
            # TODO: Form.create/edit/delete needs to check again with a different operation
            result.has_access(user=request.user, operation='read')

        return result

    _path_converters[name] = _path_converter
