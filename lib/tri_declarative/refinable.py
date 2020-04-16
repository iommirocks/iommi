from .declarative import declarative
from .dispatch import dispatch


class Refinable:
    pass


# decorator
def refinable(f):
    f.refinable = True
    return f


def is_refinable_function(attr):
    return getattr(attr, 'refinable', False)


@declarative(
    member_class=Refinable,
    parameter='refinable_members',
    is_member=is_refinable_function,
    add_init_kwargs=False,
)
class RefinableObject:
    # This constructor assumes that the class that inherits from RefinableObject
    # has done any attribute assignments to self BEFORE calling super(...)
    @dispatch()
    def __init__(self, **kwargs):
        declared_items = self.get_declared('refinable_members')
        for k, v in declared_items.items():
            if isinstance(v, Refinable):
                setattr(self, k, kwargs.pop(k, None))
            else:
                if k in kwargs:
                    setattr(self, k, kwargs.pop(k))

        if kwargs:
            available_keys = '\n    '.join(sorted(declared_items.keys()))
            raise TypeError(f"""'{self.__class__.__name__}' object has no refinable attribute(s): {', '.join(sorted(kwargs.keys()))}.
Available attributes:
    {available_keys}""")

        super(RefinableObject, self).__init__()
