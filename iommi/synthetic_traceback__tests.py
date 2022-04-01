import traceback

from iommi.synthetic_traceback import SyntheticException


def test_synthetic_traceback():
    filename = 'heaven_and_hell.py'
    line_no = 1980
    try:
        raise AttributeError('foo') from SyntheticException(tb=[
            dict(filename=filename, function='Lady Evil', f_lineno=line_no, f_globals={}, f_locals={})
        ])
    except AttributeError:
        f = traceback.format_exc()
        assert '''Traceback (most recent call last):
  File "heaven_and_hell.py", line 1980, in Lady Evil
iommi.synthetic_traceback.SyntheticException

The above exception was the direct cause of the following exception:

Traceback (most recent call last):''' in f
