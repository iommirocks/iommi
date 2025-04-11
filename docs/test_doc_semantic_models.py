from django.db.models import (
    BooleanField,
    CASCADE,
    CharField,
    ForeignKey,
    Model,
)
from django.template import Template

import iommi
from iommi import (
    Form,
    register_factory,
    register_foreign_key_factory,
    Style,
)
from iommi.shortcut import with_defaults
from tests.helpers import req


def test_semantic_models():
    # language=rst
    """
    .. _semantic-models:

    Semantic models
    ===============


    The standard way in Django to define models is something like this:

    """

    class User(Model):
        is_active = BooleanField()
        name = CharField()
        person_number = CharField()
        manager = ForeignKey('self', on_delete=CASCADE)

    # @test
    try:
    # @end

        # language=rst
        """
        The issue with that is that the semantic meaning of each field is hidden behind the name, and not in the type. The `name`
        and `person_number` fields have the same type but should be handled differently. Since iommi shortcut registrations are
        based on the type, you can't customize the parsing or rendering of the `person_number` or `birth_place` fields on
        the project level via the :ref:`style`.
    
        Moreover in this example the type information alone is not enough for other customization. For `ForeignKey`, by default
        in iommi you'll get a select2 drop-down to select from all items in that table. This is not good UX for a location, and
        it's probably not good UX for a manager field either as that should most likely exclude non-active users, and/or limited
        to users with a certain role.
    
        For `CharField`, the default is to present a text field, but in the above model we want a Swedish "person number", which
        has a specific storage format, can accept a variety of input formats that can be unambiguously parsed, and even has a
        checksum that can be used to validate that the user input is correct.
    
        A solution to this is to create an additional specialized type to specify semantic model fields:
    
        """

        class PersonNumberField(CharField):
            pass

        # language=rst
        """
        This field can then be registered in iommi:
    
        """
        register_factory(PersonNumberField, shortcut_name='person_number')

        # language=rst
        """
        Then change the model to use `PersonNumberField`:
        """

        class User(Model):
            is_active = BooleanField()
            name = CharField()
            person_number = PersonNumberField()
            manager = ForeignKey('self', on_delete=CASCADE)

        # language=rst
        """
        For foreign key fields it would be cumbersome to make custom classes, so registrations are done slightly differently:
    
        """

        register_foreign_key_factory(User, shortcut_name='user')

        # @test
        person_number__parse = lambda **_: None
        # @end

        # language=rst
        """
        You will then need to add shortcuts for these in your subclasses of `Column`, `Field`, and `Filter`.
        """

        class Field(iommi.Field):
            @classmethod
            @with_defaults(
                parse=person_number__parse,
            )
            def person_number(cls, **kwargs):
                return cls.text(**kwargs)

            @classmethod
            @with_defaults(
                choices=lambda **_: User.objects.filter(is_active=True),
            )
            def user(cls, **kwargs):
                return cls.foreign_key(**kwargs)

        # language=rst
        """
        ...and similar for `Field` and `Filter`.
        
        You can also add configuration via the `Style` machinery. This is useful for reusable apps.
    
        Semantic models requires a little bit more initial setup, but for commonly used field types, it will make new views correct by default and super easy to setup.
        """

        # @test
        class Form(iommi.Form):
            class Meta:
                member_class = Field

        f = Form.create(auto__model=User).bind(request=req('get'))
        assert str(f.fields.manager.choices.query) == str(User.objects.filter(is_active=True).query)
        # @end

    # @test
    finally:
        from iommi.form import _foreign_key_field_factory_by_model
        if User in _foreign_key_field_factory_by_model:
            del _foreign_key_field_factory_by_model[User]
    # @end
