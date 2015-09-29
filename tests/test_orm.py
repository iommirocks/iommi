import pytest

from tri.declarative import declarative, creation_ordered


@creation_ordered
class Field(object):
    def __init__(self, mandatory=False):
        self.mandatory = mandatory


class IntField(Field):
    def render(self, value):
        return '%s' % value


class StringField(Field):
    def render(self, value):
        return "'%s'" % value


@declarative(Field, 'table_fields')
class SimpleSQLModel(object):

    def __init__(self, **kwargs):
        self.table_fields = kwargs.pop('table_fields')

        for name, field in self.table_fields.items():
            if field.mandatory:
                assert name in kwargs

        for name in kwargs:
            assert name in self.table_fields
            setattr(self, name, kwargs[name])

    def insert_statement(self):
        return 'INSERT INTO %s(%s) VALUES (%s)' % (self.__class__.__name__,
                                                 ', '.join(self.table_fields.keys()),
                                                 ', '.join([field.render(getattr(self, name))
                                                            for name, field in self.table_fields.items()]))


class User(SimpleSQLModel):
    username = StringField(mandatory=True)
    password = StringField()
    age = IntField()


def test_orm():
    my_user = User(username='Bruce_Wayne', password='Batman', age=42)

    assert my_user.username == 'Bruce_Wayne'
    assert my_user.password == 'Batman'
    assert my_user.insert_statement() == "INSERT INTO User(username, password, age) VALUES ('Bruce_Wayne', 'Batman', 42)"

    with pytest.raises(AssertionError):
        User(banana="WAT")

    with pytest.raises(AssertionError):
        User(password='Batman', age=42)

