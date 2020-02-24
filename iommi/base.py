from django.db.models import QuerySet
from tri_declarative import (
    Namespace,
    refinable,
)

MISSING = object()


def evaluated_refinable(f):
    f = refinable(f)
    f.__iommi__evaluated = True
    return f


def model_and_rows(model, rows):
    if rows is None and model is not None:
        rows = model.objects.all()

    if model is None and isinstance(rows, QuerySet):
        model = rows.model

    return model, rows


def build_as_view_wrapper(target):
    def view_wrapper(request, **url_params):
        request.url_params = url_params
        return target.bind(request=request).render_to_response()

    view_wrapper.__name__ = f'{target.__class__.__name__}.as_view'
    view_wrapper.__doc__ = target.__class__.__doc__

    return view_wrapper


