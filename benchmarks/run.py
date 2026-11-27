"""
Run the iommi benchmark suite. See benchmarks/README.md.

    python -m benchmarks.run                          # time every scenario
    python -m benchmarks.run -k albums -k dashboard   # only scenarios whose name contains a substring
    python -m benchmarks.run --against master         # compare the working tree with another commit
    python -m benchmarks.run --save results.json      # save the results...
    python -m benchmarks.run --compare results.json   # ...and compare with them later
    python -m benchmarks.run -k report --profile      # where does the time go?
"""

import argparse
import cProfile
import gc
import hashlib
import io
import json
import math
import os
import platform
import pstats
import statistics
import subprocess
import sys
import tarfile
import tempfile
import time
import tomllib
from pathlib import Path

os.environ['DJANGO_SETTINGS_MODULE'] = 'benchmarks.settings'

ROOT = Path(__file__).parent.parent
RESULTS_DIR = Path(__file__).parent / 'results'
WARMUP_ITERATIONS = 5
MIN_SAMPLES = 20


# --- Measuring --------------------------------------------------------------------------------


def run_once(scenario):
    return scenario.view(scenario.build_request())


def check(scenario, response):
    problems = []
    if response.status_code != scenario.expected_status:
        problems.append(f'status {response.status_code}, expected {scenario.expected_status}')
    content = response.content.decode()
    problems += [f'{text!r} not in response' for text in scenario.expected_text if text not in content]
    return problems


def warm_up(scenario):
    problems = check(scenario, run_once(scenario))
    if problems:
        raise SystemExit(f'{scenario.name}: {", ".join(problems)}')
    for _ in range(WARMUP_ITERATIONS):
        run_once(scenario)


def count_queries(scenario):
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    with CaptureQueriesContext(connection) as queries:
        run_once(scenario)
    return len(queries)


def work(scenario):
    """Deterministic facts about a request: how much work it does, and what it produces."""
    queries = count_queries(scenario)
    if queries != count_queries(scenario):
        print(f'warning: {scenario.name} does not make the same number of queries every time', file=sys.stderr)

    request = scenario.build_request()
    profiler = cProfile.Profile()
    profiler.enable()
    response = scenario.view(request)
    profiler.disable()

    output = f'{response.status_code} {response.get("Location", "")}\n'.encode() + response.content
    return dict(
        calls=pstats.Stats(profiler).total_calls,
        queries=queries,
        status=response.status_code,
        bytes=len(response.content),
        output_hash=hashlib.sha1(output).hexdigest()[:12],
    )


def sample(scenario, seconds, min_samples):
    gc.collect()
    samples = []
    start = time.perf_counter()
    while len(samples) < min_samples or time.perf_counter() - start < seconds:
        request = scenario.build_request()
        t = time.perf_counter_ns()
        scenario.view(request)
        samples.append((time.perf_counter_ns() - t) / 1_000_000)
    return samples


def measure(scenario, min_time):
    warm_up(scenario)
    result = work(scenario)
    samples = sample(scenario, seconds=min_time, min_samples=MIN_SAMPLES)
    q1, median, q3 = statistics.quantiles(samples, n=4)
    return dict(median_ms=median, min_ms=min(samples), q1_ms=q1, q3_ms=q3, samples=len(samples), **result)


def profile(scenario, sort, min_time):
    warm_up(scenario)
    profiler = cProfile.Profile()
    iterations = 0
    start = time.perf_counter()
    while iterations < MIN_SAMPLES or time.perf_counter() - start < min_time:
        request = scenario.build_request()
        profiler.enable()
        scenario.view(request)
        profiler.disable()
        iterations += 1

    RESULTS_DIR.mkdir(exist_ok=True)
    dump = RESULTS_DIR / f'{scenario.name}.prof'
    profiler.dump_stats(dump)
    print(f'\n=== {scenario.name}: {iterations} iterations, saved to {dump.relative_to(ROOT)}')
    pstats.Stats(profiler).strip_dirs().sort_stats(sort).print_stats(30)


def make_csrf_tokens_deterministic():
    # Random tokens would make the output, and the number of calls made to generate them, vary between requests
    from django.middleware import csrf

    assert hasattr(csrf, '_get_new_csrf_string')
    csrf._get_new_csrf_string = lambda: 'x' * csrf.CSRF_SECRET_LENGTH


# --- Comparing two versions of iommi side by side ----------------------------------------------


class Worker:
    """A process running the benchmarks with the iommi package found in `source_dir`."""

    def __init__(self, source_dir):
        self.source_dir = Path(source_dir)
        # Starting in source_dir makes its iommi package shadow the one in the working tree
        self.process = subprocess.Popen(
            [sys.executable, '-m', 'benchmarks.run', '--worker'],
            cwd=source_dir,
            env={**os.environ, 'PYTHONPATH': os.pathsep.join(filter(None, [str(ROOT), os.environ.get('PYTHONPATH')]))},
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )

    def wait_until_ready(self):
        iommi_dir = self.receive()
        if Path(iommi_dir).resolve() != (self.source_dir / 'iommi').resolve():
            raise SystemExit(f'Benchmark worker for {self.source_dir} imported iommi from {iommi_dir}')

    def receive(self):
        line = self.process.stdout.readline()
        if not line:
            raise SystemExit('Benchmark worker died')
        return json.loads(line)

    def ask(self, **command):
        self.process.stdin.write(json.dumps(command) + '\n')
        self.process.stdin.flush()
        return self.receive()

    def close(self):
        self.process.stdin.close()
        self.process.wait()


def worker(scenarios):
    import iommi

    scenario_by_name = {s.name: s for s in scenarios}
    warmed_up = set()
    print(json.dumps(str(Path(iommi.__file__).parent)), flush=True)
    for line in sys.stdin:
        command = json.loads(line)
        scenario = scenario_by_name[command['scenario']]
        if scenario.name not in warmed_up:
            warm_up(scenario)
            warmed_up.add(scenario.name)
        if command['command'] == 'work':
            reply = work(scenario)
        else:
            reply = sample(scenario, seconds=command['seconds'], min_samples=command['min_samples'])
        print(json.dumps(reply), flush=True)


def sign_test(k, n):
    """Two sided p-value of k out of n rounds going one way, if there is no real difference."""
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(min(k, n - k) + 1)) / 2**n)


def run_against(ref, scenarios, min_time, rounds, processes):
    archive = subprocess.run(['git', 'archive', ref, 'iommi'], cwd=ROOT, capture_output=True)
    if archive.returncode:
        raise SystemExit(archive.stderr.decode())

    with tempfile.TemporaryDirectory() as directory:
        tarfile.open(fileobj=io.BytesIO(archive.stdout)).extractall(directory, filter='data')
        # Every process has its own memory layout, which alone can make it a percent or two faster or slower than
        # another process running the same code. Spreading the rounds over several processes evens that out.
        pairs = [(Worker(directory), Worker(ROOT)) for _ in range(processes)]
        try:
            for pair in pairs:
                for w in pair:
                    w.wait_until_ready()

            print(f'baseline: {ref} ({git("rev-parse", "--short", ref)}), current: {describe(get_meta())}\n')
            print(comparison_header(rounds=True))
            changes = []
            for s in scenarios:
                baseline_work = pairs[0][0].ask(command='work', scenario=s.name)
                current_work = pairs[0][1].ask(command='work', scenario=s.name)

                # Alternate between the versions in short rounds, so they are affected by the same machine noise
                baseline_samples, current_samples, ratios = [], [], []
                for i in range(rounds):
                    baseline, current = pairs[i % processes]
                    order = [baseline, current] if (i // processes) % 2 == 0 else [current, baseline]
                    samples = {
                        w: w.ask(command='sample', scenario=s.name, seconds=min_time / rounds, min_samples=3)
                        for w in order
                    }
                    baseline_samples += samples[baseline]
                    current_samples += samples[current]
                    ratios.append(statistics.median(samples[current]) / statistics.median(samples[baseline]))

                # Samples in the same round are taken moments apart, so comparing within rounds is robust to drift
                ratio = statistics.median(ratios)
                changes.append(ratio)
                faster_rounds = sum(r < 1 for r in ratios)
                if sign_test(faster_rounds, rounds) >= 0.05:
                    verdict = ''
                elif faster_rounds > rounds / 2:
                    verdict = 'faster'
                else:
                    verdict = 'slower'
                print(
                    comparison_row(
                        s.name,
                        baseline=dict(median_ms=statistics.median(baseline_samples), **baseline_work),
                        current=dict(median_ms=statistics.median(current_samples), **current_work),
                        ratio=ratio,
                        verdict=f'{verdict:6} {faster_rounds:2}/{rounds:<2}',
                    ),
                    flush=True,
                )
            print(f'\ngeometric mean change: {geometric_mean_change(changes):+.1f}%')
        finally:
            for pair in pairs:
                for w in pair:
                    w.close()


# --- Reporting --------------------------------------------------------------------------------


def git(*args):
    try:
        return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def get_meta():
    import django

    with open(ROOT / 'pyproject.toml', 'rb') as f:
        iommi_version = tomllib.load(f)['project']['version']
    return dict(
        date=time.strftime('%Y-%m-%d %H:%M:%S'),
        commit=git('rev-parse', '--short', 'HEAD'),
        dirty=bool(git('status', '--porcelain', '--untracked-files=no', '--', 'iommi')),
        iommi=iommi_version,
        django=django.get_version(),
        python=sys.version.split()[0],
        platform=platform.platform(),
    )


def describe(meta):
    dirty = ' + uncommitted changes' if meta['dirty'] else ''
    return f'iommi {meta["iommi"]} @ {meta["commit"]}{dirty}, Django {meta["django"]}, Python {meta["python"]}, {meta["platform"]}'


def result_header():
    return f'{"scenario":30} {"median":>9} {"min":>9} {"spread":>7} {"samples":>8} {"calls":>10} {"queries":>8} {"bytes":>8}'


def result_row(name, r):
    spread = (r['q3_ms'] - r['q1_ms']) / 2 / r['median_ms'] * 100
    return f'{name:30} {r["median_ms"]:7.2f}ms {r["min_ms"]:7.2f}ms {spread:6.1f}% {r["samples"]:8} {r["calls"]:10,} {r["queries"]:8} {r["bytes"]:8,}'


def comparison_header(rounds=False):
    verdict = f'{"faster rounds":12}' if rounds else ''
    return f'{"scenario":30} {"baseline":>9} {"current":>9} {"change":>7} {verdict} {"calls":>8} {"queries":>7}  output'


def comparison_row(name, baseline, current, ratio=None, verdict=''):
    if baseline is None:
        return f'{name:30} {"":>9} {current["median_ms"]:7.2f}ms  (not in baseline)'
    change = ((ratio or current['median_ms'] / baseline['median_ms']) - 1) * 100
    calls = (
        f'{(current["calls"] / baseline["calls"] - 1) * 100:+.2f}%' if current['calls'] != baseline['calls'] else 'same'
    )
    queries = f'{current["queries"] - baseline["queries"]:+}' if current['queries'] != baseline['queries'] else 'same'
    output = 'same' if current['output_hash'] == baseline['output_hash'] else 'CHANGED'
    return f'{name:30} {baseline["median_ms"]:7.2f}ms {current["median_ms"]:7.2f}ms {change:+6.1f}% {verdict} {calls:>8} {queries:>7}  {output}'


def geometric_mean_change(ratios):
    return (math.exp(sum(math.log(x) for x in ratios) / len(ratios)) - 1) * 100


# --- Command line -----------------------------------------------------------------------------


def main():
    if os.environ.get('PYTHONHASHSEED') != '0':
        # Hashing of strings is randomized per process. That changes the iteration order of sets, and with it how
        # much work some code does (e.g. join promotion in the Django ORM), so the call counts would not be exact.
        os.environ['PYTHONHASHSEED'] = '0'
        os.execv(sys.executable, sys.orig_argv)

    parser = argparse.ArgumentParser(prog='python -m benchmarks.run', description='Run the iommi benchmark suite')
    parser.add_argument(
        '-k',
        dest='patterns',
        action='append',
        metavar='SUBSTRING',
        help='only run scenarios whose name contains SUBSTRING, can be repeated',
    )
    parser.add_argument(
        '--min-time',
        type=float,
        default=2.0,
        metavar='SECONDS',
        help='time spent sampling each scenario (default: %(default)s)',
    )
    parser.add_argument(
        '--against', metavar='GIT_REF', help='compare with the iommi package at GIT_REF, run side by side'
    )
    parser.add_argument(
        '--rounds',
        type=int,
        default=12,
        help='number of alternations between the versions with --against (default: %(default)s)',
    )
    parser.add_argument(
        '--processes', type=int, default=3, help='number of processes per version with --against (default: %(default)s)'
    )
    parser.add_argument('--save', metavar='PATH', help='save the results as json')
    parser.add_argument('--compare', metavar='PATH', help='compare with results saved by an earlier run')
    parser.add_argument(
        '--profile', action='store_true', help='profile the scenarios with cProfile instead of timing them'
    )
    parser.add_argument(
        '--profile-sort', default='tottime', metavar='KEY', help='pstats sort key for --profile (default: %(default)s)'
    )
    parser.add_argument('--smoke', action='store_true', help='run each scenario once and check the responses')
    parser.add_argument('--list', action='store_true', help='list the scenarios')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.against and (args.save or args.compare):
        parser.error('--against can not be combined with --save or --compare')

    import django

    django.setup()
    make_csrf_tokens_deterministic()

    from benchmarks.scenarios import (
        get_scenarios,
        setup_database,
    )

    setup_database()
    scenarios = [s for s in get_scenarios() if not args.patterns or any(p in s.name for p in args.patterns)]
    if not scenarios:
        parser.error('no scenarios match')

    if args.worker:
        worker(scenarios)
    elif args.list:
        for s in scenarios:
            print(f'{s.name:30} {s.description}')
    elif args.smoke:
        failures = 0
        for s in scenarios:
            problems = check(s, run_once(s))
            failures += bool(problems)
            print(f'{s.name:30} {"FAIL: " + ", ".join(problems) if problems else "ok"}')
        return 1 if failures else 0
    elif args.profile:
        for s in scenarios:
            profile(s, sort=args.profile_sort, min_time=args.min_time)
    elif args.against:
        run_against(args.against, scenarios, min_time=args.min_time, rounds=args.rounds, processes=args.processes)
    else:
        baseline = None
        if args.compare:
            with open(args.compare) as f:
                baseline = json.load(f)

        meta = get_meta()
        print(describe(meta))
        if baseline is not None:
            print(f'baseline: {describe(baseline["meta"])}')
            print('Separate runs can differ by several percent from machine noise alone, --against is more precise.')
        print()
        print(result_header() if baseline is None else comparison_header())
        results = {}
        for s in scenarios:
            r = results[s.name] = measure(s, min_time=args.min_time)
            print(
                result_row(s.name, r)
                if baseline is None
                else comparison_row(s.name, baseline['scenarios'].get(s.name), r),
                flush=True,
            )

        if baseline is not None:
            ratios = [
                r['median_ms'] / baseline['scenarios'][name]['median_ms']
                for name, r in results.items()
                if name in baseline['scenarios']
            ]
            print(f'\ngeometric mean change: {geometric_mean_change(ratios):+.1f}%')

        if args.save:
            Path(args.save).parent.mkdir(parents=True, exist_ok=True)
            with open(args.save, 'w') as f:
                json.dump(dict(meta=meta, min_time=args.min_time, scenarios=results), f, indent=2)
            print(f'\nsaved to {args.save}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
