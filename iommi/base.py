from django.db.models import QuerySet
from django.utils.encoding import force_str
from django.utils.safestring import SafeText

NOT_BOUND_MESSAGE = (
    'This object is not bound. You need to call `.bind(request=request)` before you can call this function.'
)


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
    view_wrapper.__iommi_target__ = target

    return view_wrapper


def capitalize(s):
    if isinstance(s, SafeText):
        return SafeText(capitalize('' + s))  # str(s) will give you back SafeText, and then we have infinite recursion
    return s[0].upper() + s[1:] if s else s


# Turns out len(x) is a good idea, and x.values() is a bad idea. Let's do it the way it should be done.
def values(container):
    return type(container).values(container)


def items(container):
    return type(container).items(container)


def keys(container):
    return type(container).keys(container)


def get_display_name(part):
    try:
        if part.model_field.verbose_name:
            return capitalize(part.model_field.verbose_name)
    except AttributeError:
        pass
    return capitalize(force_str(part._name).rsplit('__', 1)[-1].replace("_", " "))
