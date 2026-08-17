import re
import sys
from collections import Counter
from io import StringIO
from types import SimpleNamespace

import pytest
from django.http.response import HttpResponseBase
from django.test import override_settings

from iommi.profiling import (
    SAMPLING_SUPPORTED,
    Middleware,
    SampleAggregate,
    SamplingProfiler,
    _html_stats,
    _iter_thread_info,
    _sampling_generate_folded_data,
    _StatsSource,
    get_dot_path,
    should_profile,
    strip_extra_path,
)
from tests.helpers import (
    req,
    staff_req,
    user_req,
)


class Sentinel(HttpResponseBase):
    pass


sentinel = Sentinel()
sentinel.user = None
middleware = Middleware(lambda request: sentinel)


def test_profiler_no_access():
    assert middleware(req('get')) is sentinel
    assert middleware(user_req('get')) is sentinel
    assert middleware(user_req('get', _iommi_prof='')) is sentinel
    assert middleware(user_req('post', _iommi_prof='')) is sentinel


def test_profiler_plain():
    middleware = Middleware(lambda request: sentinel)
    assert 'white-space: nowrap' in middleware(staff_req('get', _iommi_prof='')).content.decode()


def test_profiler_graph_error():
    old_sys_executable = sys.executable
    sys.executable = 'does_not_exist'
    with pytest.raises(Exception) as e:
        middleware(staff_req('get', _iommi_prof='graph'))
    sys.executable = old_sys_executable

    assert str(e.value) == 'gprof2dot not found. Please install it to use the graph feature.'


def test_profiler_graph_dot_present():
    if get_dot_path():
        content = middleware(staff_req('get', _iommi_prof='graph')).content.decode()
        assert '<!DOCTYPE svg ' in content, content


def test_profiler_graph_dot_not_present():
    import iommi.profiling

    orig = iommi.profiling._dot_search_paths[:]
    iommi.profiling._dot_search_paths[:] = ['does_not_exist']

    response = middleware(staff_req('get', _iommi_prof='graph'))

    iommi.profiling._dot_search_paths[:] = orig

    assert response.content.decode().startswith('digraph {')


def test_strip_extra_path():
    # No token -> returned unchanged.
    assert strip_extra_path('abc def', 'XYZ') == 'abc def'
    # With token -> everything up to and including the last token in the last space-separated
    # part is stripped.
    assert strip_extra_path('foo /a/b/site-packages/django/x.py', 'site-packages/') == 'foo django/x.py'
    # When the token appears more than once, the LAST occurrence is used (rindex, not index).
    assert strip_extra_path('foo /x/site-packages/a/site-packages/b.py', 'site-packages/') == 'foo b.py'


class _ProfReq:
    def __init__(self, *, get=None, post=None, is_staff=False, profiler_disabled=True):
        self.GET = get or {}
        self.POST = post or {}
        self.profiler_disabled = profiler_disabled

        class _User:
            pass

        self.user = _User()
        self.user.is_staff = is_staff


@override_settings(DEBUG=True)
def test_should_profile_in_debug():
    assert should_profile(_ProfReq(get={'_iommi_prof': ''})) is True
    assert should_profile(_ProfReq(post={'_iommi_prof': ''})) is True
    # The _iommi_prof marker is required even in DEBUG.
    assert should_profile(_ProfReq()) is False


@override_settings(DEBUG=False)
def test_should_profile_outside_debug_requires_enabled_staff():
    assert should_profile(_ProfReq(get={'_iommi_prof': ''}, is_staff=True, profiler_disabled=False)) is True
    # Not staff, or profiler disabled -> not allowed.
    assert should_profile(_ProfReq(get={'_iommi_prof': ''}, is_staff=False, profiler_disabled=False)) is False
    assert should_profile(_ProfReq(get={'_iommi_prof': ''}, is_staff=True, profiler_disabled=True)) is False


@override_settings(DEBUG=False)
def test_should_profile_defaults_to_disabled_when_attribute_missing():
    class _Req:
        GET = {'_iommi_prof': ''}
        POST = {}

        class user:
            is_staff = True

    # No profiler_disabled attribute -> defaults to disabled=True -> profiling not allowed.
    assert should_profile(_Req()) is False


# Stacks as the unwinder reports them: leaf first, as (filename, lineno, funcname).
def _stack(*frames):
    return tuple(frames)


VIEW = ('/app/views.py', 10, 'view')
RENDER = ('/app/views.py', 20, 'render')
RENDER_OTHER_LINE = ('/app/views.py', 21, 'render')
ESCAPE = ('/site-packages/django/utils/html.py', 100, 'escape')

SAMPLED_STACKS = Counter(
    {
        _stack(ESCAPE, RENDER, VIEW): 6,
        _stack(RENDER_OTHER_LINE, VIEW): 3,
        _stack(VIEW): 1,
    }
)


def test_sample_aggregate_folds_by_function():
    aggregate = SampleAggregate(SAMPLED_STACKS)

    assert aggregate.self_samples == {
        ('/site-packages/django/utils/html.py', 'escape'): 6,
        ('/app/views.py', 'render'): 3,
        ('/app/views.py', 'view'): 1,
    }
    assert aggregate.cumulative_samples == {
        ('/app/views.py', 'view'): 10,
        ('/app/views.py', 'render'): 9,
        ('/site-packages/django/utils/html.py', 'escape'): 6,
    }
    assert aggregate.edges == {
        (('/app/views.py', 'view'), ('/app/views.py', 'render')): 9,
        (('/app/views.py', 'render'), ('/site-packages/django/utils/html.py', 'escape')): 6,
    }


def test_sample_aggregate_picks_the_most_sampled_line_per_function():
    # A sampled frame reports the line that is executing, so `render` is seen on two
    # different lines. The one with the most samples wins.
    aggregate = SampleAggregate(SAMPLED_STACKS)
    assert aggregate.keys[('/app/views.py', 'render')] == ('/app/views.py', 20, 'render')
    assert aggregate.keys[('/app/views.py', 'view')] == ('/app/views.py', 10, 'view')


def test_sample_aggregate_counts_recursion_once_per_sample():
    recurse = ('/app/views.py', 30, 'recurse')
    aggregate = SampleAggregate(Counter({_stack(recurse, recurse, recurse, VIEW): 4}))

    function = ('/app/views.py', 'recurse')
    # Four samples, even though the function is on the stack three times in each of them.
    assert aggregate.cumulative_samples[function] == 4
    assert aggregate.self_samples[function] == 4
    assert aggregate.edges[(function, function)] == 8


def test_sample_aggregate_to_pstats_dict():
    aggregate = SampleAggregate(SAMPLED_STACKS)
    pdict = aggregate.to_pstats_dict(sample_interval=0.001)

    cc, nc, tt, ct, callers = pdict[('/app/views.py', 20, 'render')]
    # No call counts exist in sampled data, so the ncalls columns carry sample counts.
    assert (cc, nc) == (9, 9)
    assert tt == pytest.approx(0.003)
    assert ct == pytest.approx(0.009)
    assert list(callers) == [('/app/views.py', 10, 'view')]

    # The totals of a function are spread over its callers, so they add back up to it.
    for _, _, tt, ct, callers in pdict.values():
        if callers:
            assert sum(values[2] for values in callers.values()) == pytest.approx(tt)
            assert sum(values[3] for values in callers.values()) == pytest.approx(ct)


def test_sample_aggregate_to_pstats_dict_is_loadable_by_pstats():
    import pstats

    aggregate = SampleAggregate(SAMPLED_STACKS)
    stats = pstats.Stats(_StatsSource(aggregate.to_pstats_dict(sample_interval=0.001)))

    # Self times add up to the wall time that was sampled: 10 samples of 1ms.
    assert stats.total_tt == pytest.approx(0.010)
    assert stats.sort_stats('cumulative') is stats


def test_sampling_generate_folded_data():
    aggregate = SampleAggregate(SAMPLED_STACKS)
    folded = _sampling_generate_folded_data(SAMPLED_STACKS, aggregate, sample_interval=0.001, threshold=0)

    assert sorted(folded.split('\n')) == sorted(
        [
            'view (/app/views.py:10);render (/app/views.py:20);escape (/site-packages/django/utils/html.py:100) 6000',
            # Note that this is the representative line for `render`, not the sampled 21,
            # so that one function doesn't turn into several boxes in the flame graph.
            'view (/app/views.py:10);render (/app/views.py:20) 3000',
            'view (/app/views.py:10) 1000',
        ]
    )


def test_sampling_generate_folded_data_threshold():
    aggregate = SampleAggregate(SAMPLED_STACKS)
    # 1 of 10 samples, so a 20% threshold drops the shortest stack.
    folded = _sampling_generate_folded_data(SAMPLED_STACKS, aggregate, sample_interval=0.001, threshold=0.2)
    assert 'view (/app/views.py:10) 1000' not in folded.split('\n')
    assert len(folded.split('\n')) == 2


def test_sampling_generate_folded_data_without_samples():
    assert _sampling_generate_folded_data(Counter(), SampleAggregate(Counter()), 0.0, 0) == ''


def test_iter_thread_info_handles_both_shapes():
    class Thread:
        pass

    class Interpreter:
        def __init__(self, threads):
            self.threads = threads

    one, two = Thread(), Thread()
    # 3.14 returns the threads directly, 3.15+ groups them per interpreter.
    assert list(_iter_thread_info([one, two])) == [one, two]
    assert list(_iter_thread_info([Interpreter([one]), Interpreter([two])])) == [one, two]


class FakeSamplingProfiler(SamplingProfiler):
    """A profiler with canned samples, so the sampling output can be tested anywhere."""

    def start(self):
        self.stacks = SAMPLED_STACKS
        self.sample_count = sum(SAMPLED_STACKS.values())
        self.elapsed = 0.010
        return True

    def stop(self):
        pass


@pytest.fixture
def sampling(monkeypatch):
    monkeypatch.setattr('iommi.profiling.SamplingProfiler', FakeSamplingProfiler)


def test_profiler_sampling_html(sampling):
    content = middleware(staff_req('get', _iommi_prof='')).content.decode()

    assert '10 samples in 0.010 seconds' in content
    # Sampled data has no call counts, so the ncalls column becomes samples and the two
    # percall columns are dropped.
    assert '>samples</a>' in content
    assert 'percall' not in content
    assert len(re.findall(r'<th[ >]', content)) == len(
        ['samples', 'tottime', 'cumtime', 'function', '', 'filename', 'lineno']
    )
    assert 'escape</a>' in content


def test_profiler_sampling_flame(sampling):
    content = middleware(staff_req('get', _iommi_prof='flame')).content.decode()

    assert 'view (/app/views.py:10);render (/app/views.py:20)' in content
    assert 'flame_graph.js' in content


def test_profiler_sampling_is_used_when_supported(monkeypatch):
    started = []
    monkeypatch.setattr(SamplingProfiler, 'start', lambda self: started.append(self) or True)
    monkeypatch.setattr(SamplingProfiler, 'stop', lambda self: None)

    request = staff_req('get', _iommi_prof='')
    Middleware._start_profiling(request)

    assert len(started) == 1
    assert request._iommi_sampling_profiler is started[0]
    assert request._iommi_prof is True


def test_profiler_falls_back_to_tracing_when_sampling_is_unavailable(monkeypatch):
    monkeypatch.setattr(SamplingProfiler, 'start', lambda self: False)

    request = staff_req('get', _iommi_prof='')
    Middleware._start_profiling(request)

    assert not hasattr(request, '_iommi_sampling_profiler')
    # Either yappi (which sets the flag) or cProfile (which stashes the profiler object).
    assert request._iommi_prof is True or request._iommi_prof[0].__class__.__name__ == 'Profile'
    Middleware._build_stats(request, StringIO())


def test_sampling_profiler_start_returns_false_when_unsupported(monkeypatch):
    monkeypatch.setattr('iommi.profiling.SAMPLING_SUPPORTED', False)
    assert SamplingProfiler().start() is False


def test_sampling_profiler_start_returns_false_when_the_unwinder_cannot_be_built(monkeypatch):
    def boom(*args, **kwargs):
        # This is what CPython 3.15.0a2 and older raise on macOS once `ctypes` is loaded.
        raise RuntimeError("Can't determine the Python version of the remote process")

    monkeypatch.setattr('iommi.profiling.SAMPLING_SUPPORTED', True)
    monkeypatch.setattr('iommi.profiling._remote_debugging', SimpleNamespace(RemoteUnwinder=boom))
    assert SamplingProfiler().start() is False


def test_html_stats_keeps_percall_columns_for_tracing_profilers():
    stream = StringIO()
    stats = _html_stats({}, stream)
    assert stats.sampling is False

    stats.print_title()
    assert stream.getvalue().count('percall') == 2


def test_profiler_sampling_without_a_single_sample(monkeypatch):
    class NothingSampled(FakeSamplingProfiler):
        def start(self):
            super().start()
            self.stacks = Counter()
            self.sample_count = 0
            return True

    monkeypatch.setattr('iommi.profiling.SamplingProfiler', NothingSampled)

    # A request can finish before the sampler gets going, and that has to render rather
    # than blow up.
    content = middleware(staff_req('get', _iommi_prof='')).content.decode()
    assert '0 samples in 0.000 seconds' in content
    assert middleware(staff_req('get', _iommi_prof='flame')).status_code == 200


@pytest.mark.skipif(not SAMPLING_SUPPORTED, reason='needs the CPython sampling profiler engine')
def test_sampling_profiler_actually_samples():
    profiler = SamplingProfiler()
    if not profiler.start():
        pytest.skip('this interpreter cannot sample its own process')

    def leaf():
        total = 0
        for i in range(2_000_000):
            total += i * i
        return total

    def middle():
        return leaf()

    middle()
    profiler.stop()

    assert profiler.sample_count > 0
    assert profiler.error_count == 0
    assert profiler.sample_interval > 0

    aggregate = SampleAggregate(profiler.stacks)
    functions = {funcname for _, funcname in aggregate.cumulative_samples}
    assert {'leaf', 'middle'} <= {name.rpartition('.')[2] for name in functions}

    # The stacks reach all the way out to the test function, rather than stopping at the
    # frame that the sampler happened to catch.
    leaf_function = next(key for key in aggregate.cumulative_samples if key[1].endswith('leaf'))
    assert aggregate.self_samples[leaf_function] > 0
    assert re.search(r'test_sampling_profiler_actually_samples', str(list(profiler.stacks)))
