from django.db.models import QuerySet
from tri_declarative import refinable


class UnknownMissingValueException(Exception):
    pass


class Missing:
    def __bool__(self):
        raise UnknownMissingValueException('MISSING is neither True nor False, is is unknown')

    def __str__(self):
        return 'MISSING'

    def __repr__(self):
        return str(self)


MISSING = Missing()


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


