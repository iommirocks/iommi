__version__ = '1.0.0'

from iommi._db_compat import setup_db_compat
from iommi.table import Table
from iommi.table import Column
from iommi.query import Query
from iommi.query import Variable
from iommi.form import Form
from iommi.form import Field
from iommi.form import Action

setup_db_compat()
