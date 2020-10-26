from iommi import get_current_request
from iommi.from_model import get_search_fields


def register_path_converter(*, model, name=None, use_pk=False, check_access=False, parse=lambda value, lookups, model, **_: model.objects.get(**lookups)):
    if name is None:
        name = model._meta.verbose_name.lower().replace(' ', '_')

    class IommiModelConverter:
        regex = '\d+' if use_pk else '[^//]+'

        def to_python(self, value):
            if use_pk:
                lookups = {'pk': value}
            else:
                search_field = get_search_fields(model=model)[0]
                lookups = {search_field: value}

            request = get_current_request()
            result = parse(model=model, value=value, request=request, url_params=request.url_params, lookups=lookups)

            if check_access:
                # TODO: Form.create/edit/delete needs to check again with a different operation
                result.has_access(user=get_current_request().user, operation='read')

            return result

        def to_url(self, value):
            # TODO: implement this
            pass

    from django.urls import register_converter
    register_converter(IommiModelConverter, name)
