import sys
sys.path.insert(0, 'examples')

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "examples.settings")

from django import setup

setup()

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from iommi.table import endpoint__csv
from iommi import (
    Form,
    Table,
)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    def __repr__(self):
        return '<User %r>' % self.username


db.create_all()


print('----')

for k in db.Model._decl_class_registry.values():
    print(k)

model = list(db.Model._decl_class_registry.values())[0]

db.session.add(User(id=1, username='foo', email='bar'))


# model.name
# model.full_name
# model.primary_key
# model_field = model.metadata.tables['user'].columns['username']
# model_field.autoincrement == 'auto'
# model_field.description
# model_field.primary_key is True
# model_field.nullable
# model_field.index
# model_field.unique

# isinstance(model_field.type, String)
#   model_field.length == 80
#   model_field.python_type is str


# form = Form(auto__model=model).bind()
# print(form.fields)

table = Table(
    auto__model=model,
    extra_evaluated__report_name='foo',
    columns=dict(
        id__extra_evaluated__report_name='id',
        username__extra_evaluated__report_name='id',
        email__extra_evaluated__report_name='id',
    )
).bind()
print(table.columns)
print(b''.join(endpoint__csv(table).streaming_content).decode())
