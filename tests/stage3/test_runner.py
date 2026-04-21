"""Stage 3 runner smoke test.

Currently ``runner.run`` is a scaffold stub — the test is a placeholder
that will flesh out once the runner is re-implemented. Keeping it in place
ensures the import path is exercised and a future re-implementation has a
ready test file.
"""

from __future__ import annotations

import pytest

from nemos_dream.stage3_validate import runner


def test_runner_stub_raises():
    """Until the runner is implemented, ``run`` must raise a clear signal."""
    with pytest.raises((NotImplementedError, TypeError)):
        runner.run("data/stage2/sample_v3.jsonl", "data/stage3/")
