import pytest

from iommi import (
    Field,
    Form,
)
from iommi.test_helpers import (
    do_post,
    req,
    staff_req,
    user_req,
)

request = req('get')

pytestmark = pytest.mark.django_db


def test_testing():
    # language=rst
    """
    .. _testing:

    Testing
    =======

    iommi ships with a small set of helpers in `iommi.test_helpers` to make it
    easy to test your own frontend. The most important of these is `do_post`,
    which simulates a user filling out a form and submitting it.

    """


def test_do_post():
    # language=rst
    """
    do_post
    -------

    Testing a form by hand is tedious: a real POST has to include the CSRF token,
    the hidden post target, and the current value of every field, not just the
    one value you care about. `do_post` takes care of all of that for you.

    It renders the form, extracts the default post data, merges the keyword
    arguments you pass on top, and binds the form to a matching POST request:
    """

    class AlbumForm(Form):
        name = Field()
        year = Field.integer()

    form = do_post(AlbumForm.create(), name='Bringing It All Back Home', year='1965')

    # language=rst
    """
    The returned form is already bound to the POST request, so you can assert on
    validation and on the parsed values:
    """

    assert form.is_valid()
    assert form.fields.name.value == 'Bringing It All Back Home'
    assert form.fields.year.value == 1965

    # @test
    assert form.is_valid()
    assert form.fields.name.value == 'Bringing It All Back Home'
    assert form.fields.year.value == 1965
    # @end

    # language=rst
    """
    Note that you need a form with a post target, so remember to use
    `.create()`, `.edit()` or `.delete()`.

    Key validation
    ~~~~~~~~~~~~~~~~

    By default `do_post` checks that every key you pass actually exists in the
    rendered form. This catches typos in your tests so you don't silently assert
    against a value that was never posted. If you need to post a key that isn't a
    plain field (for example a virtual key for inserting a new row in an
    `EditTable`, like ``columns__name__field/-1``), turn the check off with
    `do_post_key_validation=False`:
    """

    form = do_post(AlbumForm.create(), do_post_key_validation=False, name='Highway 61 Revisited', year='1965')

    # @test
    assert form.is_valid()
    # @end


def test_request_builders():
    # language=rst
    """
    Building requests
    -----------------

    `iommi.test_helpers` also provides helpers for building request objects:

    - `req(method, **data)` builds a request from an anonymous user.
    - `user_req(method, **data)` builds a request from a normal authenticated user.
    - `staff_req(method, **data)` builds a request from an authenticated staff/superuser.

    `do_post` uses `req` by default. Pass `request_builder` to submit the form as
    a different user, which is handy for testing access control:
    """

    class AlbumForm(Form):
        name = Field()

    form = do_post(AlbumForm.create(), name='Slipping Into Darkness', request_builder=staff_req)

    # @test
    assert form.is_valid()
    assert form.get_request().user.is_staff
    # @end

    # language=rst
    """
    These helpers can also be used on their own to build a request to bind any
    iommi component to:
    """

    page = AlbumForm.create().bind(request=user_req('get'))

    # @test
    assert page
    # @end
