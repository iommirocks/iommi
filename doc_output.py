from tri.declarative import *
from tri.table import *
from tri.query import *
from tri.query import MISSING as q_MISSING

documentation = {
    'Table': documentation_tree(Table),
    'Column': documentation_tree(Column),

    # 'Form': documentation_tree(Form),  # TODO
    'Field': documentation_tree(Field),

    'Query': documentation_tree(Query),
    'Variable': documentation_tree(Variable),
}


from json import JSONEncoder, dumps

class PythonObjectEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        if obj is q_MISSING:
            return '<MISSING>'

        return JSONEncoder.default(self, obj)


with open('tri.table-docs.json', 'w') as f:
    f.write('var docs = ' + dumps(documentation, cls=PythonObjectEncoder))
