import subprocess
import sys
from pathlib import Path


def test_benchmark_scenarios_still_work():
    # The benchmarks have their own settings, so they run in a separate process
    result = subprocess.run(
        [sys.executable, '-m', 'benchmarks.run', '--smoke'],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
