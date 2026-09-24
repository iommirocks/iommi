# Benchmarks

A representative iommi workload for measuring the effect of performance work: a handful of pages
with tables, forms, an edit table and a composite page, and the requests a browser makes to them
(page loads, filtering, ajax endpoints, valid and invalid posts). `python -m benchmarks.run --list`
shows them all.

The settings are production like: `DEBUG = False`, the bootstrap5 style, no dev tool middleware, and
an in-memory sqlite database with 30 artists, 300 albums and 3000 tracks. The made up artists and
albums are listed in `names.py`. Views are called directly
with requests from `RequestFactory`, so the Django middleware stack is not measured.

```
make benchmark                                   # or: uv run python -m benchmarks.run
make benchmark ARGS="--against master"           # compare the working tree with master
make benchmark ARGS="-k albums -k dashboard"     # only some scenarios
make benchmark ARGS="-k edit_table --profile"    # where does the time go?
```

## Comparing two versions

Timings from separate runs can differ by 5-10% on a laptop from machine noise alone, which is more
than most optimizations gain. So to evaluate a change, run the two versions side by side:

```
uv run python -m benchmarks.run --against master   # changes on a branch
uv run python -m benchmarks.run --against HEAD     # uncommitted changes
```

This extracts the `iommi` package at the given git ref to a temporary directory and starts worker
processes for both versions. The workers take turns in short rounds, so both versions are hit by the
same noise. Both versions run the scenarios from the working tree, so a scenario that uses new API
will fail for the baseline.

- **change** is the median of the per round ratios, current / baseline.
- **faster rounds** is how many rounds the working tree was faster in. It says `faster` or `slower`
  when that count is significant (sign test, p < 0.05). Changes around 1% are at the limit of what
  it can detect.
- **calls** is the number of Python and C function calls in one request, counted with cProfile. It
  is exact, so it shows small differences in the amount of work that timings can't.
- **queries** is the number of SQL queries in one request.
- **output** compares a hash of the response. `CHANGED` means the rendered HTML differs, which a
  pure performance change should never do.

To make the calls and output exact, the runner fixes `PYTHONHASHSEED` (set iteration order affects
how much work the Django ORM does) and makes CSRF tokens deterministic.

`--save results.json` stores the results of a normal run, and `--compare results.json` compares a
later run with them. That is useful as a record, and for the exact columns, but prefer `--against`
for timings.

## Profiling

`--profile` runs the selected scenarios under cProfile and prints the top functions by own time
(`--profile-sort cumulative` to change that). It also saves a `.prof` file in `benchmarks/results/`
(git ignored), for tools like snakeviz or gprof2dot.

## Adding a scenario

Declare the page in `scenarios.py` and add a `Scenario` to `get_scenarios()`. Give it an
`expected_text` that proves the page rendered what you meant, because `tests/test_benchmarks.py` runs
every scenario once with `--smoke` as part of the test suite. Keep the existing scenarios stable: when
a scenario changes, older results are no longer comparable.
