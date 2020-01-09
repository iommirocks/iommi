from __future__ import unicode_literals

from tests.helpers import reindent


def test_reindent():

    before = """\
_foo
__bar
_boink__
"""

    after = """\
--foo
----bar
--boink__"""

    assert reindent(before, before="_", after="--") == after
